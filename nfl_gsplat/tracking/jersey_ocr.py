"""Jersey-number OCR (EasyOCR) + majority vote per track, for scripts/08c_identity_all22.py.

Strategy: for each ``(cam, track_id)``, pick the top-K frames by bbox height
as OCR candidates (bigger = more readable), crop the upscaled torso band, run
the OCR, filter results to 1–2 digit strings, majority-vote. Write the result
into ``df['jersey_number_ocr']`` (−1 when no confident result).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from nfl_gsplat.errors import SetupError
from nfl_gsplat.utils.logging import get_logger

_LOG = get_logger(__name__)


@dataclass(frozen=True)
class JerseyOCRConfig:
    top_k_frames: int = 8
    min_bbox_h_px: int = 80
    min_ocr_conf: float = 0.5
    use_gpu: bool = True
    backend: str = "auto"   # auto | easyocr (auto = the first backend that imports)
    # OCR the torso band rather than the whole player, upscaled: measured on
    # real SEA@AZ crops, feeding the full unscaled box read ~2% of crops, while
    # the upscaled torso band read ~30%. The number sits on the upper back /
    # chest, so everything below the waist is noise that drags detection.
    torso_top_frac: float = 0.15
    torso_bot_frac: float = 0.55
    upscale: float = 2.5
    # One vote per PLAYER over both views instead of one per (view, track):
    # the ids are shared across views (08b), the endzone sees backs and the
    # sideline profiles, and a number read in either names the player.
    pool_views: bool = False


def _build_easyocr(use_gpu: bool):
    import easyocr  # type: ignore
    engine = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)

    def read(crop):
        # allowlist digits: jersey numbers are numeric, and constraining the
        # charset stops letters on the uniform (names, logos) from winning.
        return [(t, float(c)) for _box, t, c in
                engine.readtext(crop, allowlist="0123456789")]
    return read


# Insertion order = preference for backend="auto". easyocr is the backend:
# measured on 60 real player crops (RTX 4080, play_002), easyocr on CUDA ran
# 37.7 crops/s with 18/60 reads vs rapidocr's 1.3 crops/s with 14/60 — rapidocr
# rides onnxruntime, whose CUDA provider did not engage, so it stayed CPU-bound
# (~40 min/play); PaddleOCR ships no wheels for the Python this runs on.
_BACKEND_BUILDERS = {
    "easyocr": _build_easyocr,
}


def _lazy_ocr_engine(use_gpu: bool, backend: str = "auto"):
    """Return ``reader(crop) -> [(text, conf), ...]`` for the chosen backend.

    ``auto`` tries each backend in preference order and uses the first that
    imports."""
    if backend != "auto" and backend not in _BACKEND_BUILDERS:
        raise SetupError(
            f"unknown jersey-OCR backend {backend!r} — pick one of "
            f"{sorted(_BACKEND_BUILDERS)} or 'auto'.")

    names = list(_BACKEND_BUILDERS) if backend == "auto" else [backend]
    failures = []
    for name in names:
        try:
            return _BACKEND_BUILDERS[name](use_gpu)
        except ImportError as e:
            failures.append(f"{name} ({e})")
    raise SetupError(
        "no jersey-OCR backend available — tried: " + "; ".join(failures) +
        ". Install it: `pip install easyocr` (SETUP.md §5).")


def _read_frame(video: Path | str, frame_idx: int) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(video))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
        ok, img = cap.read()
        return img if ok else None
    finally:
        cap.release()


def jersey_crop(frame: np.ndarray, box, cfg: JerseyOCRConfig) -> np.ndarray | None:
    """Upscaled torso band of a player box — the region the number sits on.

    ``box`` is (x1, y1, x2, y2) in frame pixels; returns None when the band is
    degenerate. Cropping to the torso and upscaling is what makes small,
    far-from-camera numbers legible (see JerseyOCRConfig)."""
    x1, y1, x2, y2 = (int(v) for v in box)
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return None
    bh = y2 - y1
    ty1 = y1 + int(cfg.torso_top_frac * bh)
    ty2 = y1 + int(cfg.torso_bot_frac * bh)
    band = frame[ty1:ty2, x1:x2]
    if band.size == 0 or band.shape[0] < 2 or band.shape[1] < 2:
        return None
    if cfg.upscale and cfg.upscale != 1.0:
        band = cv2.resize(band, None, fx=cfg.upscale, fy=cfg.upscale,
                          interpolation=cv2.INTER_CUBIC)
    return band


def _ocr_crop(reader, crop: np.ndarray, min_conf: float) -> int | None:
    """Highest-confidence 1-2 digit reading as an int 0..99, else None.
    ``reader`` is a backend adapter returning ``[(text, conf), ...]``."""
    best: tuple[float, str] | None = None
    for text, conf in reader(crop) or []:
        if conf < min_conf:
            continue
        digits = "".join(ch for ch in text if ch.isdigit())
        if 1 <= len(digits) <= 2 and (best is None or conf > best[0]):
            best = (conf, digits)
    return int(best[1]) if best else None


def vote_jersey_numbers(
    df: pd.DataFrame,
    video_paths: dict[str, Path | str],
    cfg: JerseyOCRConfig,
    votes_out: dict | None = None,
) -> pd.DataFrame:
    """Run OCR + majority vote per ``(cam, track_id)`` -- or per ``track_id``
    over both views with ``cfg.pool_views`` -- and write the winning digit
    into ``jersey_number_ocr``.

    The evidence behind the winner is kept: ``jersey_votes_win`` (crops
    that read the winner) and ``jersey_votes_total`` (crops that read any
    digit) per row, and, with ``votes_out`` (a dict), the full count per
    ``(cam, track_id)`` -- two tracks that both read "7" are told apart by
    it (play 1: two endzone tracks named the kicker for 616 frames)."""
    if df.empty:
        return df.copy()

    reader = _lazy_ocr_engine(cfg.use_gpu, cfg.backend)
    out = df.copy()
    out["jersey_votes_win"] = 0
    out["jersey_votes_total"] = 0

    keys = ["track_id"] if cfg.pool_views else ["cam", "track_id"]
    for key, group in df.groupby(keys):
        tid = int(key[-1])
        votes: Counter[int] = Counter()
        for cam, sub in group.groupby("cam"):
            video = video_paths.get(cam)
            if video is None:
                continue
            for _, row in _pick_rows(sub, cfg).iterrows():
                frame = _read_frame(video, int(row["frame"]))
                if frame is None:
                    continue
                crop = jersey_crop(frame, (row["bbox_x1"], row["bbox_y1"],
                                           row["bbox_x2"], row["bbox_y2"]), cfg)
                if crop is None:
                    continue
                digit = _ocr_crop(reader, crop, cfg.min_ocr_conf)
                if digit is not None:
                    votes[digit] += 1

        if votes_out is not None:
            votes_out[("both" if cfg.pool_views else str(key[0]), tid)] = {int(k): int(v) for k, v in votes.items()}
        if not votes:
            continue
        winner, n_win = votes.most_common(1)[0]
        mask = out["track_id"] == tid
        if not cfg.pool_views:
            mask &= out["cam"] == key[0]
        out.loc[mask, "jersey_number_ocr"] = int(winner)
        out.loc[mask, "jersey_votes_win"] = int(n_win)
        out.loc[mask, "jersey_votes_total"] = int(sum(votes.values()))
        _LOG.info(f"jersey OCR: ({'both' if cfg.pool_views else key[0]}, track {tid}) "
                  f"-> #{winner}  (votes={dict(votes)})")

    return out


def _pick_rows(g: pd.DataFrame, cfg: JerseyOCRConfig) -> pd.DataFrame:
    """The crops one (view, track) gets: tall enough, then the top-k by height."""
    g = g.copy()
    g["h"] = g["bbox_y2"] - g["bbox_y1"]
    g = g[g["h"] >= cfg.min_bbox_h_px]
    return g.nlargest(cfg.top_k_frames, "h")
