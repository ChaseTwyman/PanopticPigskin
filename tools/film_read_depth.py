#!/usr/bin/env python
"""Film-read depth: place a man neither camera can place along the sideline's line of sight.

WHY. The sideline camera measures where a man stands ACROSS its view but not how far away he is; the endzone camera
supplies that depth. A man whose feet are hidden behind a blocker in the sideline view (his box is only his head and
shoulders, so its ground point lands deep) and who is never boxed by the endzone camera has no depth at all -- the
depth snap then slides him onto the nearest endzone detection, which is someone else.

WHAT. Read his helmet by hand in the endzone film at a few frames (tools/film/grid_crop.py draws a pixel grid), give
those pixels here with the sideline frame numbers, and this triangulates each read against the top-centre of his
sideline box: the helmet's world position and the two rays' closest-approach gap (a consistent read is within ~0.3 m).
With --write, the reads' y (the sideline's blind axis) go into <play>/film_reads.json, which the loader applies after
the depth snap (render.depth_snap.apply_depth_reads): he slides along his OWN sideline ray to the read depth.

Usage:
  python tools/film_read_depth.py --play-dir data/<game>/<play> --id 4 \\
      --read 552:1130,537 --read 564:1092,528 --read 584:1052,560 --read 596:1040,615 [--write --ramp 6 --who "..."]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_gsplat.calibration.cameras_io import load_camera_track


def pixel_ray(track, frame: int, uv) -> tuple[np.ndarray, np.ndarray]:
    """``(centre, unit direction)`` of the world ray through pixel ``uv`` of ``track`` at ``frame``."""
    intr, pose = track.at(frame)
    K = intr.K()
    R = np.asarray(pose.R, float)
    t = np.asarray(pose.t, float).reshape(3)
    C = -R.T @ t
    d = R.T @ np.linalg.inv(K) @ np.array([uv[0], uv[1], 1.0])
    return C, d / np.linalg.norm(d)


def triangulate(c1, d1, c2, d2) -> tuple[np.ndarray, float]:
    """Midpoint of the closest approach of two rays and the gap between them (metres)."""
    w = c1 - c2
    a, b, c = d1 @ d1, d1 @ d2, d2 @ d2
    d, e = d1 @ w, d2 @ w
    den = a * c - b * b
    if abs(den) < 1e-12:
        raise ValueError("the two rays are parallel")
    s1 = (b * e - c * d) / den
    s2 = (a * e - b * d) / den
    p1, p2 = c1 + s1 * d1, c2 + s2 * d2
    return 0.5 * (p1 + p2), float(np.linalg.norm(p1 - p2))


def parse_read(text: str) -> tuple[int, tuple[float, float]]:
    frame, uv = text.split(":")
    u, v = uv.split(",")
    return int(frame), (float(u), float(v))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--play-dir", required=True, type=Path)
    ap.add_argument("--id", required=True, type=int, help="the man's global player id")
    ap.add_argument("--read", action="append", required=True, type=parse_read,
                    help="SIDELINE_FRAME:U,V -- his helmet pixel in the endzone film at that sideline frame")
    ap.add_argument("--head-px", type=float, default=8.0, help="pixels below the sideline box top for the helmet")
    ap.add_argument("--max-gap", type=float, default=0.35, help="refuse a read whose rays miss by more (metres)")
    ap.add_argument("--write", action="store_true", help="add the reads to <play>/film_reads.json")
    ap.add_argument("--ramp", type=int, default=6, help="frames to blend in and out at the window's ends")
    ap.add_argument("--who", default="", help="a note on who he is and why he needs a read")
    args = ap.parse_args()

    P = args.play_dir
    offset = int(json.loads((P / "clip_offset.json").read_text()).get("offset", 0))
    tracks = load_camera_track(P / "cameras.npz")
    t = pd.read_parquet(P / "tracks.parquet")
    side = t[(t.cam == "sideline") & (t.global_player_id == args.id) & (t.track_id >= 0)]
    ys, pixels = {}, {}
    for f, uv in sorted(args.read):
        rows = side[side.frame.between(f - 2, f + 2)].sort_values("frame")
        if rows.empty:
            print(f"{f}: no sideline box for id {args.id} within 2 frames -- skipped")
            continue
        r = rows.iloc[len(rows) // 2]
        us = (0.5 * (r.bbox_x1 + r.bbox_x2), r.bbox_y1 + args.head_px)
        X, gap = triangulate(*pixel_ray(tracks["sideline"], int(r.frame), us),
                             *pixel_ray(tracks["endzone"], f + offset, uv))
        ok = gap <= args.max_gap
        print(f"{f}: helmet ({X[0]:.2f}, {X[1]:.2f}, {X[2]:.2f}) m, ray gap {gap:.2f} m{'' if ok else '  REFUSED'}")
        if ok:
            ys[str(f)] = round(float(X[1]), 3)
            pixels[str(f)] = [round(uv[0], 1), round(uv[1], 1)]
    if not args.write:
        return
    if len(ys) < 2:
        raise SystemExit("fewer than two consistent reads: nothing written")
    path = P / "film_reads.json"
    doc = json.loads(path.read_text()) if path.exists() else {"depth": []}
    doc["depth"] = [d for d in doc.get("depth", []) if int(d["id"]) != args.id]
    doc["depth"].append({"id": args.id, "who": args.who, "y": ys, "ramp": args.ramp, "endzone_helmet_px": pixels})
    path.write_text(json.dumps(doc, indent=2))
    print(f"wrote {len(ys)} reads for id {args.id} to {path}")


if __name__ == "__main__":
    main()
