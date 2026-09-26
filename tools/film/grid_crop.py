#!/usr/bin/env python
"""Film crops with a pixel grid, for reading positions off the film by hand.

Each tile is one frame of one camera's film, cropped to a region and scaled, with a grid every 20 px (labelled every
40 px in ORIGINAL film coordinates) and every tracked box drawn with its global id. Frames are given in SIDELINE
numbering; the endzone clip frame is frame + clip_offset.json's offset. Read-only.

Usage:
  python tools/film/grid_crop.py --play-dir P --cam endzone --region 1020 460 1260 780 --scale 2.2 \\
      --frames 552 564 576 --out crops.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--play-dir", required=True, type=Path)
    ap.add_argument("--cam", required=True, choices=["sideline", "endzone"])
    ap.add_argument("--region", required=True, type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--frames", required=True, type=int, nargs="+", help="sideline frame numbers")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    P = args.play_dir
    off = int(json.loads((P / "clip_offset.json").read_text()).get("offset", 0)) if args.cam == "endzone" else 0
    X0, Y0, X1, Y1 = args.region
    sc = args.scale
    t = pd.read_parquet(P / "tracks.parquet")
    t = t[(t.cam == args.cam) & (t.track_id >= 0)]
    cap = cv2.VideoCapture(str(P / f"{args.cam}.mp4"))
    tiles = []
    for f in args.frames:
        fc = f + off
        cap.set(cv2.CAP_PROP_POS_FRAMES, fc)
        ok, im = cap.read()
        if not ok:
            continue
        crop = cv2.resize(im[Y0:Y1, X0:X1], None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        for x in range((X0 // 20 + 1) * 20, X1, 20):
            u = int((x - X0) * sc)
            cv2.line(crop, (u, 0), (u, crop.shape[0]), (80, 80, 80) if x % 40 else (0, 200, 255), 1)
            if x % 40 == 0:
                cv2.putText(crop, str(x), (u + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        for y in range((Y0 // 20 + 1) * 20, Y1, 20):
            v = int((y - Y0) * sc)
            cv2.line(crop, (0, v), (crop.shape[1], v), (80, 80, 80) if y % 40 else (0, 200, 255), 1)
            if y % 40 == 0:
                cv2.putText(crop, str(y), (2, v - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        for r in t[t.frame == fc].itertuples():
            if r.bbox_x2 < X0 or r.bbox_x1 > X1 or r.bbox_y2 < Y0 or r.bbox_y1 > Y1:
                continue
            p1 = (int((r.bbox_x1 - X0) * sc), int((r.bbox_y1 - Y0) * sc))
            p2 = (int((r.bbox_x2 - X0) * sc), int((r.bbox_y2 - Y0) * sc))
            cv2.rectangle(crop, p1, p2, (255, 0, 255), 1)
            cv2.putText(crop, str(int(r.global_player_id)), (p1[0] + 2, p1[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 0, 255), 2)
        cv2.putText(crop, f"{f} (film {fc})", (6, crop.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        tiles.append(crop)
    if not tiles:
        raise SystemExit("no frames could be read")
    cols = min(args.cols, len(tiles))
    blank = np.zeros_like(tiles[0])
    rows = [np.hstack(tiles[i:i + cols] + [blank] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    cv2.imwrite(str(args.out), np.vstack(rows))
    print(f"{args.out}: {len(tiles)} tiles")


if __name__ == "__main__":
    main()
