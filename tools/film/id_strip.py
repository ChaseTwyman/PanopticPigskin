#!/usr/bin/env python
"""One id's film crops over time: who a tracked box really is, frame by frame.

Each tile is centred on the id's box in one camera's film (yellow), with its keypoints (green, confidence >= 0.3,
COCO skeleton), other ids' boxes that overlap the crop (grey) and, given a joints export, the drawn body's joints
projected into the same film (magenta; a second export in cyan). Under each tile: the frame, the box's width and
height, and its width over the id's median width (a box far wider than the man is usually two men merged). Frames
are SIDELINE numbering; the endzone clip frame is frame + clip_offset.json's offset. Read-only.

Usage:
  python tools/film/id_strip.py --play-dir P --cam sideline --id 84 --frames 440 568 16 --out strip.png \\
      [--joints joints.json [--joints2 other.json]] [--keypoints keypoints_2d_ft2.parquet]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

SKELETON = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
# SMPL-X body joint -> COCO keypoint, for drawing the drawn body with the detector's skeleton
SMPLX_TO_COCO = [(16, 5), (17, 6), (18, 7), (19, 8), (20, 9), (21, 10), (1, 11), (2, 12), (4, 13), (5, 14), (7, 15), (8, 16)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--play-dir", required=True, type=Path)
    ap.add_argument("--cam", required=True, choices=["sideline", "endzone"])
    ap.add_argument("--id", required=True, type=int)
    ap.add_argument("--frames", required=True, type=int, nargs=3, metavar=("FIRST", "LAST", "STEP"))
    ap.add_argument("--keypoints", type=Path, default=None, help="default <play>/keypoints_2d_ft2.parquet")
    ap.add_argument("--joints", type=Path, default=None, help="a joints export (the renderer's --export-joints)")
    ap.add_argument("--joints2", type=Path, default=None)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    P = args.play_dir
    off = int(json.loads((P / "clip_offset.json").read_text()).get("offset", 0)) if args.cam == "endzone" else 0
    t = pd.read_parquet(P / "tracks.parquet")
    t = t[(t.cam == args.cam) & (t.track_id >= 0)]
    me = t[t.global_player_id == args.id]
    if me.empty:
        raise SystemExit(f"id {args.id} has no {args.cam} boxes")
    med_w = float((me.bbox_x2 - me.bbox_x1).median())
    k = pd.read_parquet(args.keypoints or (P / "keypoints_2d_ft2.parquet"))
    k = k[(k.cam == args.cam) & (k.global_player_id == args.id) & (k.conf >= 0.3)]
    exports = [json.loads(p.read_text()) if p else None for p in (args.joints, args.joints2)]
    cap = cv2.VideoCapture(str(P / f"{args.cam}.mp4"))

    def project(c, X):
        K = c["K"]
        R = np.asarray(c["R"], float).reshape(3, 3)
        x = (R @ np.asarray(X, float).T).T + np.asarray(c["t"], float)
        return np.stack([K[0] * x[:, 0] / x[:, 2] + K[2], K[1] * x[:, 1] / x[:, 2] + K[3]], axis=1)

    tiles = []
    SC = 3
    first, last, step = args.frames
    for f in range(first, last + 1, step):
        fc = f + off
        b = me[me.frame == fc]
        cap.set(cv2.CAP_PROP_POS_FRAMES, fc)
        ok, im = cap.read()
        if not ok or b.empty:
            continue
        x1, y1, x2, y2 = (float(v) for v in b.iloc[0][["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]])
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        half = max(x2 - x1, y2 - y1) * 0.9 + 10
        X0, Y0 = int(max(0, cx - half)), int(max(0, cy - half))
        X1, Y1 = int(min(im.shape[1], cx + half)), int(min(im.shape[0], cy + half))
        crop = cv2.resize(im[Y0:Y1, X0:X1], None, fx=SC, fy=SC, interpolation=cv2.INTER_CUBIC)
        s = lambda u, v: (int((u - X0) * SC), int((v - Y0) * SC))  # noqa: E731
        for r in t[(t.frame == fc) & (t.global_player_id != args.id)].itertuples():
            if r.bbox_x2 < X0 or r.bbox_x1 > X1 or r.bbox_y2 < Y0 or r.bbox_y1 > Y1:
                continue
            cv2.rectangle(crop, s(r.bbox_x1, r.bbox_y1), s(r.bbox_x2, r.bbox_y2), (150, 150, 150), 1)
        cv2.rectangle(crop, s(x1, y1), s(x2, y2), (0, 220, 255), 2)
        g = k[k.frame == fc]
        kk = {int(j): (x, y) for j, x, y in zip(g.joint, g.x, g.y)}
        for a, bb in SKELETON:
            if a in kk and bb in kk:
                cv2.line(crop, s(*kk[a]), s(*kk[bb]), (0, 230, 0), 2)
        for exp, col in zip(exports, ((255, 0, 255), (255, 255, 0))):
            if exp is None:
                continue
            c = exp["cameras"][args.cam].get(str(f))
            body = next((q for q in exp["bodies"].get(str(f), []) if int(q[0]) == args.id), None)
            if c is None or body is None:
                continue
            J = np.asarray(body[2], float)
            uv = project(c, J[[sm for sm, _ in SMPLX_TO_COCO]])
            d = {co: tuple(p) for (_sm, co), p in zip(SMPLX_TO_COCO, uv)}
            for a, bb in SKELETON:
                if a in d and bb in d:
                    cv2.line(crop, s(*d[a]), s(*d[bb]), col, 2)
        lab = np.zeros((26, crop.shape[1], 3), np.uint8)
        cv2.putText(lab, f"{f} w{x2 - x1:.0f} h{y2 - y1:.0f} x{(x2 - x1) / med_w:.2f}", (4, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        tiles.append(np.vstack([crop, lab]))
    if not tiles:
        raise SystemExit("no tiles: the id has no boxes on those frames")
    H = max(x.shape[0] for x in tiles)
    W = max(x.shape[1] for x in tiles)
    tiles = [cv2.copyMakeBorder(x, 0, H - x.shape[0], 0, W - x.shape[1], cv2.BORDER_CONSTANT) for x in tiles]
    cols = args.cols
    rows = [np.hstack(tiles[i:i + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[i:i + cols])))
            for i in range(0, len(tiles), cols)]
    cv2.imwrite(str(args.out), np.vstack(rows))
    print(f"{args.out}: {len(tiles)} tiles, id {args.id} median width {med_w:.0f} px")


if __name__ == "__main__":
    main()
