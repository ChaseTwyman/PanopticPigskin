"""The identity pass's worklist: every place the drawn play is likely to have the wrong man, in one read-only report.

An identity fix is always decided on the film (tools/film/*, scripts/09b_film_strip.py, scripts/09c_track_audit.py) and
applied with scripts/08z_fold_ids.py (move a camera track's rows to the right id), scripts/08za_drop_rows.py (drop a
second copy of a man) or scripts/08zb_set_identity.py (fix what an id IS: team, number, role). This lists the
candidates, so the pass is a checklist instead of a search:

1. THE FORMATION at a frame just before the snap: every drawn body by team, with its number and name, its role, and
   the camera tracks behind it. Both teams must show eleven, each man once, and every number the endzone film shows
   on the offence's backs must be the id's number -- a wrong number becomes a wrong role and a wrong build.
2. HANDOVERS: every run of a drawn id that ends inside the play, with the runs that start within 25 frames and 3 m
   of it. A tracker that loses a man hands him to a new id; a new id born next to an ended one is the same man until
   the film says otherwise -- or the man he was engaged with, which is why the film decides.
3. TWINS: same-team pairs drawn within 0.8 m of each other for 4 frames or more. Two drawn bodies on one man.
4. KIT: drawn ids whose boxes' kit colour contradicts their team label on 3 frames or more.

Usage (the main environment; reads a timeline export, tracks.parquet, identity_resolved.pkl, clip_offset.json):
  python scripts/export_timeline.py --play-dir P --out P/timeline.json        # (the SMPL-X environment)
  python tools/film/identity_review.py --play-dir P --timeline P/timeline.json --snap 256 --down 552
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_gsplat.identity.merge_cameras import is_named

HANDOVER_FRAMES = 25     # a successor starts at most this many frames after the run ends (and at most 5 before)
HANDOVER_M = 3.0         # ... and this close to where it ended
TWIN_M = 0.8             # two same-team bodies this close are one man until the film says otherwise
TWIN_FRAMES = 4
KIT_NAMES = {1: "red", 0: "white", -1: "?"}


def runs_of(frames: list[int]) -> list[tuple[int, int]]:
    out, s, p = [], frames[0], frames[0]
    for f in frames[1:]:
        if f != p + 1:
            out.append((s, p))
            s = f
        p = f
    out.append((s, p))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--play-dir", type=Path, required=True)
    ap.add_argument("--timeline", type=Path, required=True, help="scripts/export_timeline.py output")
    ap.add_argument("--snap", type=int, required=True)
    ap.add_argument("--down", type=int, required=True)
    ap.add_argument("--formation-frame", type=int, default=None, help="default: 6 frames before the snap")
    ap.add_argument("--red", default="KC", help="the team in the saturated kit (the pipeline's RED)")
    args = ap.parse_args()
    P = args.play_dir
    tl = {int(f): rows for f, rows in json.loads(args.timeline.read_text())["frames"].items()}
    blob = pickle.load(open(P / "identity_resolved.pkl", "rb"))
    merged, roles = blob["merged"], blob.get("roles", {})
    df = pd.read_parquet(P / "tracks.parquet")
    offset = int(json.loads((P / "clip_offset.json").read_text()).get("offset", 0)) if (P / "clip_offset.json").exists() else 0
    lo, hi = args.snap, args.down

    def name(pid: int) -> str:
        m = merged.get(pid)
        if m is None:
            return f"{pid}(?)"
        num = f" #{m.jersey}" if m.jersey else ""
        who = f" {m.player}" if is_named(m.player) else ""
        return f"{pid}({m.team}{num}{who})"

    tracks_of = {pid: sorted({f"{c[0]}{t}" for c, t in zip(g["cam"], g["track_id"])})
                 for pid, g in df.groupby("global_player_id")}

    # 1. the formation
    ff = args.formation_frame if args.formation_frame is not None else args.snap - 6
    rows = tl.get(ff, [])
    print(f"1. FORMATION at frame {ff} (x along the field, y across; camera tracks: s = sideline, e = endzone)")
    for team in ("KC", "BAL"):
        mine = sorted((r for r in rows if r[1] == team), key=lambda r: (r[2], r[3]))
        print(f"   {team}: {len(mine)} drawn")
        for r in mine:
            print(f"     {name(r[0]):34s} role {str(roles.get(r[0], '-')):3s} ({r[2]:6.1f}, {r[3]:6.1f})  tracks {' '.join(tracks_of.get(r[0], []))}")
    other = [r for r in rows if r[1] not in ("KC", "BAL")]
    if other:
        print(f"   teamless: {[r[0] for r in other]}")

    # 2. handovers
    pos: dict = collections.defaultdict(dict)
    for f, rs in tl.items():
        for r in rs:
            pos[r[0]][f] = (r[2], r[3])
    runs = [(pid, s, e) for pid, fr in pos.items() for s, e in runs_of(sorted(fr))]
    print(f"\n2. HANDOVERS: runs ending inside {lo}-{hi} and runs starting within {HANDOVER_FRAMES} frames, {HANDOVER_M} m")
    n = 0
    for pid, s, e in sorted(runs, key=lambda r: r[2]):
        if not lo <= e < hi:
            continue
        x, y = pos[pid][e]
        cands = []
        for q, s2, _e2 in runs:
            if q != pid and e - 5 <= s2 <= e + HANDOVER_FRAMES:
                d = float(np.hypot(pos[q][s2][0] - x, pos[q][s2][1] - y))
                if d < HANDOVER_M:
                    cands.append((d, s2, q))
        cands.sort()
        n += 1
        print(f"   {name(pid):34s} ends {e:4d} at ({x:6.1f},{y:6.1f})  ->  "
              + (", ".join(f"{name(q)} @{s2} {d:.2f} m" for d, s2, q in cands[:3]) or "nothing near: lost, or left the view"))
    print(f"   {n} run ends")

    # 3. twins
    pairs = collections.defaultdict(list)
    for f, rs in tl.items():
        if not lo <= f <= hi:
            continue
        for a, b in itertools.combinations(rs, 2):
            if a[1] == b[1] and a[1] in ("KC", "BAL"):
                d = float(np.hypot(a[2] - b[2], a[3] - b[3]))
                if d < TWIN_M:
                    pairs[(min(a[0], b[0]), max(a[0], b[0]))].append((f, d))
    print(f"\n3. TWINS: same-team bodies within {TWIN_M} m for {TWIN_FRAMES}+ frames")
    for (a, b), v in sorted(pairs.items(), key=lambda kv: -len(kv[1])):
        if len(v) >= TWIN_FRAMES:
            fs = [f for f, _ in v]
            print(f"   {name(a):30s} & {name(b):30s} {len(v):3d} frames {min(fs)}-{max(fs)}, median {np.median([d for _, d in v]):.2f} m")

    # 4. kit against label
    kit = {}
    for r in df[["cam", "frame", "global_player_id", "kit"]].itertuples(index=False):
        f = r.frame if r.cam == "sideline" else r.frame - offset
        kit.setdefault((r.global_player_id, f), []).append(int(r.kit))
    tally: dict = collections.defaultdict(collections.Counter)
    for f, rs in tl.items():
        if lo <= f <= hi:
            for r in rs:
                for k in kit.get((r[0], f), []):
                    tally[(r[0], r[1])][KIT_NAMES.get(k, "?")] += 1
    print("\n4. KIT: drawn ids whose boxes' kit contradicts their team (red = the saturated kit)")
    red_team = args.red
    for (pid, team), c in sorted(tally.items()):
        right, wrong = (c["red"], c["white"]) if team == red_team else (c["white"], c["red"])
        if wrong >= 3 and wrong >= 0.5 * right:
            print(f"   {name(pid):34s} right {right:4d}  wrong {wrong:4d}  unreadable {c['?']:4d}")


if __name__ == "__main__":
    main()
