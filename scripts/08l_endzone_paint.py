#!/usr/bin/env python
"""Refine a play-dir's ENDZONE camera track to its own paint (calibration.endzone_paint).

The endzone camera exported by 08/08b comes from the players' feet against the
sideline's placement, with the mount centre a grid prior. Measured on play 1
(2026-09-09) its grid sits 40-85 px off the painted lines and the two cameras'
rays through the same keypoint miss by 0.2-0.5 m; every two-view pose defect
traced back to it. This solves the mount centre once from the paint of a sample
of frames, then every frame's rotation and focal, and judges the result with
the PLAYERS (the independent ruler): the sideline's and the endzone's rays
through the same keypoints must meet closer than before, triangulated ankles
must come down to the turf. It refuses to write when they do not.

    python scripts/08l_endzone_paint.py --play-dir <P> [--out <npz>] [--apply]

--out writes the refined cameras to a side file (measure first); --apply
rewrites cameras.npz (the original kept as cameras_endzone_players.npz).
"""
from __future__ import annotations

import argparse
import pickle
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_gsplat.calibration import endzone_paint as ep
from nfl_gsplat.calibration.cameras_io import load_camera_track, write_camera_track
from nfl_gsplat.errors import CalibrationError


def feet_in_view(side, ez, tdf: pd.DataFrame, *, stride: int = 4, tol_px: float = 150.0) -> float:
    """Median over frames of how many sideline feet, placed on the turf through ``side`` and projected through
    ``ez``, land within ``tol_px`` of an endzone box's feet on the same frame index (offset 0: the clip offset is
    not measured yet; a few frames of drift cost a little, a camera on the wrong yard lines costs everything).
    The tolerance is wide on purpose: the sideline's blind axis (depth, across the field; ~1 m) is the endzone's
    lateral axis, ~130 px at play 1's zoom, so a correct camera lands feet 80-150 px from their boxes."""
    from nfl_gsplat.calibration.from_players import ground_points

    counts = []
    n = min(len(side.conf), len(ez.conf))
    both = np.flatnonzero((side.conf[:n] > 0) & (ez.conf[:n] > 0))
    s_by = dict(tuple(tdf[tdf["cam"] == "sideline"].groupby("frame")))
    e_by = dict(tuple(tdf[tdf["cam"] == "endzone"].groupby("frame")))
    for f in both[::stride]:
        if f not in s_by or f not in e_by:
            continue
        g = ground_points((side.K[f], side.R[f], side.t[f]), s_by[f][["foot_u", "foot_v"]].to_numpy(float))
        g = g[np.isfinite(g).all(1)]
        if not len(g):
            continue
        g = np.column_stack([g[:, :2], np.zeros(len(g))])     # turf points (x, y, 0)
        x = (ez.K[f] @ (ez.R[f] @ g.T + ez.t[f].reshape(3, 1))).T
        uv = x[:, :2] / x[:, 2:3]
        feet = e_by[f][["foot_u", "foot_v"]].to_numpy(float)
        feet = feet[np.isfinite(feet).all(1)]
        if not len(feet):
            continue
        d = np.linalg.norm(uv[:, None, :] - feet[None, :, :], axis=2).min(axis=1)
        counts.append(int(((d <= tol_px) & (x[:, 2] > 0)).sum()))
    return float(np.median(counts)) if counts else float("nan")


def boxes_by_frame(tracks_df: pd.DataFrame, cam: str) -> dict:
    out: dict = {}
    sub = tracks_df[tracks_df["cam"] == cam]
    for f, g in sub.groupby("frame"):
        out[int(f)] = [tuple(map(float, b)) for b in g[["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]].to_numpy(float)]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--play-dir", required=True, type=Path)
    ap.add_argument("--cam", default="endzone")
    ap.add_argument("--other", default="sideline", help="the trusted camera the players are judged against")
    ap.add_argument("--out", type=Path, default=None, help="write the refined cameras here (default <play-dir>/cameras_endzone_paint.npz)")
    ap.add_argument("--apply", action="store_true", help="rewrite cameras.npz (original kept as cameras_endzone_players.npz)")
    ap.add_argument("--centre-frames", type=int, default=12)
    ap.add_argument("--centre", type=float, nargs=3, default=None, help="hold the mount centre at this x y z instead of solving it")
    ap.add_argument("--offset", type=int, default=None, help="endzone frame offset for the player ruler (default: poses_tri.json's, else 0)")
    ap.add_argument("--ruler-stride", type=int, default=2)
    args = ap.parse_args()
    P = args.play_dir

    tracks = load_camera_track(P / "cameras.npz")
    track = tracks[args.cam]
    tdf = pd.read_parquet(P / "tracks.parquet")
    boxes = boxes_by_frame(tdf, args.cam)
    video = P / f"{args.cam}.mp4"

    refined, stats = ep.refine_track(video, track, boxes, centre_frames=args.centre_frames, centre=args.centre)
    before = np.asarray(stats["before"], float)
    after = np.asarray(stats["after"], float)
    dash = np.asarray(stats["dash"], float)
    print(f"{args.cam}: mount centre {np.round(stats['centre'], 1)}; {stats['n_refined']}/{len(stats['frames'])} frames refined; "
          f"line px median {np.nanmedian(before):.1f} -> {np.nanmedian(after):.1f}, dash px {np.nanmedian(dash):.1f}; "
          f"segments/frame {np.median(stats['n_seg']):.0f}, dashes/frame {np.median(stats['n_dash']):.0f}")
    stats_csv = (args.out or (P / "cameras_endzone_paint.npz")).with_suffix(".stats.csv")
    pd.DataFrame({k: stats[k] for k in ("frames", "before", "after", "dash", "n_seg", "n_dash")}).to_csv(stats_csv, index=False)
    print(f"per-frame paint stats: {stats_csv}")
    if not (np.nanmedian(after) < np.nanmedian(before)):
        raise CalibrationError("the paint refinement did not lower the line distance; cameras untouched")

    # the players: independent of the paint
    kp = P / "keypoints_2d.parquet"
    verdict = None
    r0 = r1 = None
    if kp.exists():
        offset = args.offset
        if offset is None:
            offset = 0
            if (P / "poses_tri.json").exists():
                offset = int(pickle.load(open(P / "poses_tri.json", "rb")).get("offset", 0))
        kdf = pd.read_parquet(kp)
        other = tracks[args.other]
        r0 = ep.player_rulers(other, track, kdf, offset=offset, stride=args.ruler_stride)
        r1 = ep.player_rulers(other, refined, kdf, offset=offset, stride=args.ruler_stride)
    if r1 is not None and len(r1["frames"]):
        m0, m1 = np.nanmedian(r0["miss_p50"]), np.nanmedian(r1["miss_p50"])
        a0, a1 = np.nanmedian(r0["ankle_z"]), np.nanmedian(r1["ankle_z"])
        h0, h1 = np.nanmedian(r0["hip_z"]), np.nanmedian(r1["hip_z"])
        print(f"players ({len(r1['frames'])} frames, endzone offset {offset:+d}): ray miss p50 {m0:.3f} -> {m1:.3f} m "
              f"(p90 of frames {np.nanpercentile(r0['miss_p50'], 90):.3f} -> {np.nanpercentile(r1['miss_p50'], 90):.3f}); "
              f"ankle z {a0:+.2f} -> {a1:+.2f} m; hip z {h0:.2f} -> {h1:.2f} m")
        verdict = (m1 < m0) and (abs(a1 - 0.08) < abs(a0 - 0.08))
        if not verdict:
            raise CalibrationError("the players do not confirm the refinement (the ray miss did not drop or the ankles "
                                   "did not come down to the turf); cameras untouched")
    else:
        # No keypoints yet (the pipeline runs 08l before 05m), or none on ids both cameras share: the boxes judge
        # instead. The paint alone cannot:
        # yard lines repeat every 5 yards, and play 6's endzone, moved to a held centre without re-aiming, fitted
        # the lines 44 m up the field at 6.7 px while no sideline player projected into its image.
        n0 = feet_in_view(tracks[args.other], track, tdf)
        n1 = feet_in_view(tracks[args.other], refined, tdf)
        print(f"players (boxes; no keypoints yet): sideline feet landing on an endzone box's feet, median per frame "
              f"{n0:.0f} -> {n1:.0f}")
        if n0 >= 3 and n1 < 0.5 * n0:
            raise CalibrationError(f"the refined endzone camera loses the players ({n0:.0f} -> {n1:.0f} sideline feet "
                                   "on endzone boxes per frame): the paint fit registered the wrong yard lines; "
                                   "cameras untouched")

    tracks[args.cam] = refined
    fps = float(np.load(P / "cameras.npz", allow_pickle=True)["fps"])
    if args.apply:
        backup = P / "cameras_endzone_players.npz"
        if not backup.exists():
            shutil.copy(P / "cameras.npz", backup)
        write_camera_track(P / "cameras.npz", tracks, fps=fps)
        print(f"cameras.npz rewritten ({args.cam} refined to its paint; original in {backup.name})")
    else:
        out = args.out or (P / "cameras_endzone_paint.npz")
        write_camera_track(out, tracks, fps=fps)
        print(f"refined {args.cam} written to {out}; cameras.npz untouched")


if __name__ == "__main__":
    main()
