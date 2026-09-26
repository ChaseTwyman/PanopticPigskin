#!/usr/bin/env python
"""Export the timeline the renderer draws -- every body's placement per frame -- to JSON.

Rows are ``{frame: [[pid, team, x, y, source, "views", yaw], ...]}`` (metres on the turf, the field frame: x along the
field, y across, z up) plus each camera's median centre. The census, the step/hop and surge rulers, the film checks
(tools/film/mark_ids.py) and the play report all read this file, so they judge exactly what the render draws.

Usage (the SMPL-X environment):
  python scripts/export_timeline.py --play-dir data/<game>/<play> --out timeline.json
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import smplx

from nfl_gsplat.calibration.cameras_io import load_camera_track
from nfl_gsplat.render import timeline as tlm
from nfl_gsplat.render.play_timeline import load_play_timeline


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--play-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--body-models", type=Path, default=Path("data/body_models"))
    args = ap.parse_args()

    P = args.play_dir
    model = smplx.create(str(args.body_models), model_type="smplx", gender="neutral", num_betas=10, use_pca=False,
                         batch_size=1)
    tl, _tracks, _df, _frames, _poses = load_play_timeline(P, model)
    blob = pickle.load(open(P / "identity_resolved.pkl", "rb"))
    team_of = {int(p): v.team for p, v in blob["merged"].items()}
    centres = {}
    for cam, tr in load_camera_track(P / "cameras.npz").items():
        cs = []
        for f in range(0, len(tr.conf), 20):
            if tr.conf[f] <= 0:
                continue
            _, pose = tr.at(f)
            R = np.asarray(pose.R, float)
            t = np.asarray(pose.t, float).reshape(3)
            cs.append((-R.T @ t).tolist())
        centres[cam] = np.median(np.asarray(cs), axis=0).tolist() if cs else None
    doc = {"centres": centres, "frames": {}}
    for f, states in tl.states.items():
        doc["frames"][str(int(f))] = [[int(s.pid), team_of.get(int(s.pid)), float(s.xy[0]), float(s.xy[1]), s.source,
                                        "+".join(sorted(s.views)), float(tlm.yaw_of(s.global_orient))] for s in states]
    args.out.write_text(json.dumps(doc))
    print(f"wrote {args.out}: {len(doc['frames'])} frames")


if __name__ == "__main__":
    main()
