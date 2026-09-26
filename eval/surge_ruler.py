#!/usr/bin/env python
"""Placement SURGES: a drawn body
whose pelvis (joint 0, xy on the turf) accelerates harder than a man can. The pelvis velocity is a centred difference
over +-HALF frames (0.13 s at HALF 4, 59.94 fps), the acceleration the same difference of that velocity; a body-frame
counts when |a| > AMAX m/s^2 (a sprinter's start peaks near 10, a hard tackle's stop near 25-30). A slide of a metre
spread over a few frames by the smoother reads ~50 and is invisible to the step ruler (> 0.25 m/frame). Per file:
body-frames over AMAX, ids with their runs, and each run's dominant axis (x along the field = the sideline camera's
image axis, y across = its line of sight) with the run's peak speed.

Usage: python eval/surge_ruler.py timeline.json [joints.json ...] --lo SNAP --hi DOWN
(a timeline export from scripts/export_timeline.py, or a joints export from the renderer's --export-joints)"""
import argparse
import collections
import json

import numpy as np

FPS = 59.94
ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+")
ap.add_argument("--lo", type=int, default=-10**9, help="first frame counted (the snap)")
ap.add_argument("--hi", type=int, default=10**9, help="last frame counted (the down)")
ap.add_argument("--amax", type=float, default=25.0)
ap.add_argument("--half", type=int, default=4)
ap.add_argument("--ids", type=str, default=None)
args = ap.parse_args()
want = None if args.ids is None else {int(x) for x in args.ids.split(",")}


def surges(path):
    D = json.load(open(path))
    tr = collections.defaultdict(dict)                     # pid -> frame -> xy
    if "centres" in D:                                     # a timeline export: [pid, team, x, y, ...]
        for f, rows in D["frames"].items():
            for q in rows:
                tr[int(q[0])][int(f)] = np.asarray(q[2:4], float)
    else:                                                  # a joints export (05k --export-joints): the pelvis joint
        for f in D["frames"]:
            for q in D["bodies"].get(str(f), []):
                tr[int(q[0])][int(f)] = np.asarray(q[2], float)[0, :2]
    out = {}
    n_all = 0
    for pid, d in tr.items():
        if want is not None and pid not in want:
            continue
        fs = sorted(d)
        h = args.half
        vel = {}
        for f in fs:
            if f - h in d and f + h in d:
                vel[f] = (d[f + h] - d[f - h]) / (2 * h / FPS)
        bad = []
        for f in fs:
            if not (args.lo <= f <= args.hi):
                continue
            if f - h in vel and f + h in vel:
                a = (vel[f + h] - vel[f - h]) / (2 * h / FPS)
                n_all += 1
                if np.linalg.norm(a) > args.amax:
                    bad.append((f, a, max(np.linalg.norm(vel[f - h]), np.linalg.norm(vel[f + h]))))
        if bad:
            out[pid] = bad
    return out, n_all


for path in args.files:
    out, n_all = surges(path)
    tot = sum(len(v) for v in out.values())
    print(f"{path.replace(chr(92), '/').split('/')[-1]}: {tot} of {n_all} body-frames over {args.amax:g} m/s^2 "
          f"({args.lo}-{args.hi}), {len(out)} ids")
    for pid, bad in sorted(out.items(), key=lambda kv: -len(kv[1]))[:12]:
        runs = []
        for f, a, v in bad:
            if runs and f - runs[-1][1] <= args.half:
                runs[-1][1] = f; runs[-1][2].append(a); runs[-1][3] = max(runs[-1][3], v)
            else:
                runs.append([f, f, [a], v])
        desc = []
        for lo, hi, acc, vmax in runs[:6]:
            A = np.abs(np.array(acc)).sum(axis=0)
            desc.append(f"{lo}-{hi} {'x' if A[0] >= A[1] else 'y'} {vmax:.1f}m/s")
        print(f"  {pid:4d}: {len(bad):3d}  " + "; ".join(desc))
