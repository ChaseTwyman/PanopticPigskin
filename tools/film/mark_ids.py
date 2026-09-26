#!/usr/bin/env python
"""Where the drawn bodies stand, on the film: the placement check used for every identity or depth fix.

Each listed id's DRAWN position (a timeline export, scripts/export_timeline.py) is projected into both films as a
vertical stick from the turf to 1.8 m, labelled, on full-resolution crops around those bodies (sideline | endzone per
row; the endzone clip frame is frame + clip_offset.json's offset). A stick standing on its man in BOTH films means the
body is placed right; the sideline alone cannot see an error along its own line of sight. Read-only.

Usage:
  python tools/film/mark_ids.py --play-dir P --timeline tl.json --ids 4 1 12 76 --frames 560 576 588 --out marks.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from nfl_gsplat.calibration.cameras_io import load_camera_track

COLOURS = [(0, 255, 255), (255, 0, 255), (0, 255, 0), (255, 128, 0), (0, 128, 255), (255, 255, 255)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--play-dir", required=True, type=Path)
    ap.add_argument("--timeline", required=True, type=Path, help="a timeline export (scripts/export_timeline.py)")
    ap.add_argument("--ids", required=True, type=int, nargs="+")
    ap.add_argument("--frames", required=True, type=int, nargs="+", help="sideline frame numbers")
    ap.add_argument("--height", type=int, default=440, help="tile height in pixels")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    P = args.play_dir
    off = int(json.loads((P / "clip_offset.json").read_text()).get("offset", 0))
    tl = json.loads(args.timeline.read_text())["frames"]
    tracks = load_camera_track(P / "cameras.npz")
    caps = {c: cv2.VideoCapture(str(P / f"{c}.mp4")) for c in ("sideline", "endzone")}

    def project(cam, f, X):
        intr, pose = tracks[cam].at(f)
        x = intr.K() @ (np.asarray(pose.R, float) @ np.asarray(X, float) + np.asarray(pose.t, float).reshape(3))
        return x[:2] / x[2]

    rows = []
    for f in args.frames:
        drawn = {r[0]: r for r in tl.get(str(f), [])}
        tiles = []
        for cam, fc in (("sideline", f), ("endzone", f + off)):
            caps[cam].set(cv2.CAP_PROP_POS_FRAMES, fc)
            ok, im = caps[cam].read()
            if not ok:
                continue
            sticks = []
            for k, pid in enumerate(args.ids):
                if pid in drawn:
                    x, y = drawn[pid][2], drawn[pid][3]
                    sticks.append((pid, project(cam, fc, (x, y, 0.0)), project(cam, fc, (x, y, 1.8)),
                                   COLOURS[k % len(COLOURS)]))
            if not sticks:
                continue
            pts = np.array([p for _, a, b, _ in sticks for p in (a, b)])
            x0, y0 = (pts.min(axis=0) - 90).astype(int)
            x1, y1 = (pts.max(axis=0) + 90).astype(int)
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(im.shape[1], x1), min(im.shape[0], y1)
            crop = im[y0:y1, x0:x1].copy()
            sc = args.height / max(1, crop.shape[0])
            crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
            for pid, a, b, col in sticks:
                pa = (int((a[0] - x0) * sc), int((a[1] - y0) * sc))
                pb = (int((b[0] - x0) * sc), int((b[1] - y0) * sc))
                cv2.line(crop, pa, pb, col, 2)
                cv2.circle(crop, pa, 5, col, 2)
                cv2.putText(crop, str(pid), (pb[0] + 4, pb[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
            cv2.putText(crop, f"{f} {cam}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            tiles.append(crop)
        if tiles:
            h = max(t.shape[0] for t in tiles)
            rows.append(np.hstack([np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0))) for t in tiles]))
    if not rows:
        raise SystemExit("nothing drawn: check the ids and frames against the timeline export")
    w = max(r.shape[1] for r in rows)
    cv2.imwrite(str(args.out), np.vstack([np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0))) for r in rows]))
    print(f"{args.out}: {len(rows)} rows")


if __name__ == "__main__":
    main()
