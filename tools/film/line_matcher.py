"""The offensive line on the SIDELINE, man by man: which sideline camera track holds which lineman, frame by frame.

WHY. At the line the sideline camera sees the linemen one behind another along its line of sight -- the one axis it
cannot measure -- and its tracker swaps them whenever they overlap. The endzone camera sees the same men side by side
with their numbers on their backs, so its tracks are the reliable ones there. Nothing in the pipeline tied the two:
08r pairs cameras by foot rays, and the rays of two linemen a metre apart miss by as little as one man's do. Play 6
(2026-09-26): 08r joined 3 tracks in the whole play, and the centre's and the left guard's sideline tracks swapped
twice in the first 40 frames after the snap.

HOW. Three steps, each printed so the film can check it:
1. THE MEN, from the endzone film: every listed endzone track's back number read by OCR every few frames (the same
   EasyOCR reader and torso crop as 08c), so a lineman is a set of (endzone track, frame span) pieces with his number
   read on them -- a track that swaps men shows the swap as a change of number. --men overrides this by hand.
2. EACH FRAME: every sideline box that is not the defence's kit is compared with every lineman present in the endzone
   on the ground, with each camera trusted on its own good axis. The sideline measures x (along the field) well and y
   (its line of sight) badly, and its y error is common to all men on a frame, so it is removed first (the median y
   offset of the frame's best pairs); the endzone measures y well and x badly. Cost = (dx / SIGMA_X)^2 +
   (dy / SIGMA_Y)^2 on the ankles' ground points (the box bottom when the ankles are not seen).
3. EACH SIDELINE TRACK over time: the lineman sequence that minimises the per-frame costs plus a penalty per change
   of man (Viterbi), so a single ambiguous frame cannot flip a track; then each lineman keeps, frame by frame, the one
   track that fits him best, and any other track on him is reported as a twin.

It proposes; it does not write. Every proposal is an 08z fold (a sideline track's frames into the lineman's id) or an
08za drop (a twin); review each on the film (tools/film/grid_crop.py) before applying it on a copy of the play.

Usage (the main environment; reads tracks.parquet, keypoints_2d[_ft2].parquet, cameras.npz, clip_offset.json, the
endzone clip):
  python tools/film/line_matcher.py --play-dir P --frames 250 420 --numbers 76 62 52 65 74 --ez-tracks 18 107 17 108 10 25 28
  python tools/film/line_matcher.py --play-dir P --frames 250 420 --men 76:18:106-292 62:107:106-440 ...
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from nfl_gsplat.calibration.cameras_io import load_camera_track
from nfl_gsplat.calibration.from_players import ground_points

SIGMA_X = 0.9            # m: the endzone's depth error along the field dominates the pair's x difference
SIGMA_Y = 0.45           # m: across the field, after the sideline's common-mode offset is removed
NONE_COST = 4.0          # a box costs this to leave unassigned (2 sigma in one axis). Play 1's verified linemen
                         # median 0.4-1.1; a tight end beside the right tackle 4.1 (at 9 he became the tackle's twin)
FOLD_COST = 2.0          # a fold is proposed only for a run whose median cost is under this
SWITCH_COST = 25.0       # a change of man along one sideline track (a real swap persists for many frames)
ABSENT_COST = NONE_COST + 1.0   # a man the endzone does not see on a frame: a track may hold him through a short gap,
                                # but never for free (at NONE_COST every idle track drifted onto some lineman)
GATE = 6.0               # m: pairs further apart on either axis are not considered
ANKLES = (15, 16)        # COCO left and right ankle
MIN_ANKLE_CONF = 0.3
OCR_STEP = 3             # frames between OCR reads of an endzone track
OCR_PAD = 12             # a read number holds for this many frames either side, until another number is read
MIN_READS = 3            # reads a piece needs (a single read of a one-digit-off number is how #52 became #62)


def load(P: Path):
    df = pd.read_parquet(P / "tracks.parquet")
    kp_path = P / "keypoints_2d_ft2.parquet"
    kp = pd.read_parquet(kp_path if kp_path.exists() else P / "keypoints_2d.parquet")
    kp = kp[kp.joint.isin(ANKLES) & (kp.conf >= MIN_ANKLE_CONF)]
    ankles = kp.groupby(["cam", "frame", "global_player_id"])[["x", "y"]].mean()
    off = int(json.loads((P / "clip_offset.json").read_text()).get("offset", 0)) if (P / "clip_offset.json").exists() else 0
    return df, ankles, off, load_camera_track(P / "cameras.npz")


def foot_px(row, cam, ankles):
    key = (cam, int(row.frame), int(row.global_player_id))
    if key in ankles.index:
        a = ankles.loc[key]
        return float(a.x), float(a.y)
    return float(row.foot_u), float(row.foot_v)


def ground(cams, cam, f, uv):
    tr = cams[cam]
    return np.asarray(ground_points((tr.K[f], tr.R[f], tr.t[f]), np.asarray([uv], float)), float)[0, :2]


def ocr_men(P, df, numbers, ez_tracks, lo, hi, off):
    """{jersey: [(endzone track, first, last), ...]} (sideline frame numbering) from the numbers read on each track."""
    from nfl_gsplat.tracking.jersey_ocr import JerseyOCRConfig, _lazy_ocr_engine, _ocr_crop, jersey_crop

    cfg = JerseyOCRConfig()
    reader = _lazy_ocr_engine(cfg.use_gpu, cfg.backend)
    ez = df[(df.cam == "endzone") & df.track_id.isin(ez_tracks)]
    ez = ez[(ez.frame >= lo + off) & (ez.frame <= hi + off)]
    cap = cv2.VideoCapture(str(P / "endzone.mp4"))
    reads = collections.defaultdict(list)            # track -> [(sideline frame, number)]
    for f in sorted(ez.frame.unique())[::OCR_STEP]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, img = cap.read()
        if not ok:
            continue
        for r in ez[ez.frame == f].itertuples(index=False):
            crop = jersey_crop(img, (r.bbox_x1, r.bbox_y1, r.bbox_x2, r.bbox_y2), cfg)
            n = _ocr_crop(reader, crop, cfg.min_ocr_conf) if crop is not None else None
            if n is not None:
                reads[int(r.track_id)].append((int(f) - off, int(n)))
    men = collections.defaultdict(list)
    print("1. THE MEN: numbers read on the endzone tracks (sideline frames)")
    for t in ez_tracks:
        rs = [(f, n) for f, n in reads.get(t, []) if n in numbers]
        other = [(f, n) for f, n in reads.get(t, []) if n not in numbers]
        print(f"   endzone t{t}: " + (" ".join(f"{f}:#{n}" for f, n in rs) or "no listed number read")
              + (f"   (other reads {other[:6]})" if other else ""))
        if len(rs) < MIN_READS:
            continue
        # OCR confuses 5 and 6 (#52 and #62 stand side by side): the mode of each read's neighbourhood decides it,
        # so a real swap has to be read MIN_READS times running to count
        ns = [n for _, n in rs]
        sm = [collections.Counter(ns[max(0, i - 2):i + 3]).most_common(1)[0][0] for i in range(len(ns))]
        pieces, s, cur, cnt = [], 0, sm[0], 1
        for i in range(1, len(rs) + 1):
            if i == len(rs) or sm[i] != cur:
                pieces.append((cur, rs[s][0], rs[i - 1][0], cnt))
                if i < len(rs):
                    s, cur, cnt = i, sm[i], 1
            else:
                cnt += 1
        for k, (n, a, b, c) in enumerate(pieces):
            if c < MIN_READS:
                continue
            # pad each piece halfway to its neighbours on the same track, at most OCR_PAD
            a0 = max(a - OCR_PAD, (pieces[k - 1][2] + a) // 2 + 1) if k else a - OCR_PAD
            b0 = min(b + OCR_PAD, (b + pieces[k + 1][1]) // 2) if k + 1 < len(pieces) else b + OCR_PAD
            men[n].append((t, a0, b0, c))
    # a man read on two tracks at once: each frame takes the piece with more reads
    return {n: [(t, a, b) for t, a, b, _c in sorted(v, key=lambda p: -p[3])] for n, v in men.items()}


def parse_men(specs):
    men = collections.defaultdict(list)
    for spec in specs:
        jersey, track, span = spec.split(":")
        a, b = map(int, span.split("-"))
        men[int(jersey)].append((int(track), a, b))
    return dict(men)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--play-dir", type=Path, required=True)
    ap.add_argument("--frames", type=int, nargs=2, required=True, metavar=("LO", "HI"))
    ap.add_argument("--numbers", type=int, nargs="+", help="the linemen's jersey numbers, read on --ez-tracks by OCR")
    ap.add_argument("--ez-tracks", type=int, nargs="*", default=None,
                    help="endzone tracks to read numbers on (default: every endzone track in the window not in the defence's kit)")
    ap.add_argument("--men", nargs="+", help="by hand instead of OCR: JERSEY:ENDZONE_TRACK:FIRST-LAST (sideline frames)")
    ap.add_argument("--ids", nargs="*", default=[], help="JERSEY:GLOBAL_ID, the id each man's rows belong under "
                    "(default: the global id his endzone pieces carry most)")
    ap.add_argument("--defence-kit", type=int, default=0, help="kit label of the defence's boxes (08b: 1 = saturated)")
    ap.add_argument("--offence", default="KC", help="the offence's team: rows under the defence's ids are left out")
    ap.add_argument("--min-run", type=int, default=4)
    ap.add_argument("--plan-out", type=Path, default=None,
                    help="write the relabels as a plan for scripts/08zc_relabel_tracks.py (a swap needs it: 08z folds collide)")
    args = ap.parse_args()
    P, (lo, hi) = args.play_dir, args.frames
    df, ankles, off, cams = load(P)
    if args.men:
        men = parse_men(args.men)
    elif args.numbers:
        tracks = args.ez_tracks
        if not tracks:
            w = df[(df.cam == "endzone") & (df.frame >= lo + off) & (df.frame <= hi + off)]
            kit = w.groupby("track_id").kit.agg(lambda k: k.value_counts().index[0])
            tracks = sorted(int(t) for t, k in kit.items() if k != args.defence_kit)
        men = ocr_men(P, df, set(args.numbers), tracks, lo, hi, off)
    else:
        raise SystemExit("give --men, or --numbers (and optionally --ez-tracks)")
    import pickle

    merged = pickle.load(open(P / "identity_resolved.pkl", "rb"))["merged"]
    ez = df[df.cam == "endzone"]
    gid_of = {}
    for n, pieces in men.items():
        votes = collections.Counter()
        for t, a, b in pieces:
            rows = ez[(ez.track_id == t) & (ez.frame >= a + off) & (ez.frame <= b + off)]
            votes.update(rows.global_player_id.astype(int).tolist())
        gid_of[n] = votes.most_common(1)[0][0] if votes else None
        # an id the identity already names with this number wins over the vote (play 1: the centre's verified id is
        # 204, while his endzone rows late in the window sit under 174, an endzone-only id also named #52)
        named = [k for k, v in merged.items() if getattr(v, "jersey", 0) == n and getattr(v, "team", None) == args.offence]
        if named:
            # two ids named alike (an endzone-only split of the man): the one the sideline places him by
            win = df[(df.cam == "sideline") & (df.frame >= lo) & (df.frame <= hi)]
            gid_of[n] = int(max(named, key=lambda k: (int((win.global_player_id == k).sum()), -int(k))))
    for spec in args.ids:
        n, g = map(int, spec.split(":"))
        gid_of[n] = g
    print("   men: " + "; ".join(f"#{n} -> id {gid_of[n]}: " + ", ".join(f"t{t} {a}-{b}" for t, a, b in p)
                               for n, p in sorted(men.items())))

    # 2. per-frame costs
    ez_idx = ez.set_index(["track_id", "frame"]).sort_index()
    import pickle

    team = {int(k): v.team for k, v in pickle.load(open(P / "identity_resolved.pkl", "rb"))["merged"].items()}
    defence_ids = {k for k, v in team.items() if v not in (None, args.offence)}
    # a defender engaged with a lineman stands where the lineman stands: his rows would win the lineman's cost and
    # be proposed as the lineman's twin. Rows under the defence's ids and boxes in the defence's kit are left out.
    side = df[(df.cam == "sideline") & (df.frame >= lo) & (df.frame <= hi) & (df.kit != args.defence_kit)
              & ~df.global_player_id.isin(defence_ids)]
    cost = collections.defaultdict(dict)       # sideline track -> {frame: {jersey: cost}}
    gid_at = collections.defaultdict(dict)     # sideline track -> {frame: current global id}
    order = sorted(men)
    for f in range(lo, hi + 1):
        present = {}
        for n in order:
            for t, a, b in men[n]:
                if a <= f <= b and (t, f + off) in ez_idx.index:
                    r = ez_idx.loc[(t, f + off)]
                    r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
                    row = pd.Series({**r.to_dict(), "frame": f + off})
                    present[n] = ground(cams, "endzone", f + off, foot_px(row, "endzone", ankles))
                    break
        boxes = side[side.frame == f]
        if not present or boxes.empty:
            continue
        g_s = np.array([ground(cams, "sideline", f, foot_px(r, "sideline", ankles)) for r in boxes.itertuples(index=False)])
        g_e = np.array([present[n] for n in present])
        dx = g_s[:, None, 0] - g_e[None, :, 0]
        dyr = g_s[:, None, 1] - g_e[None, :, 1]
        bad = ~np.isfinite(dx) | ~np.isfinite(dyr)          # a foot point off the ground plane
        dx, dyr = np.where(bad, 1e3, dx), np.where(bad, 1e3, dyr)
        dy0 = 0.0
        for _ in range(2):                       # the sideline's common-mode depth offset on this frame
            c = (dx / SIGMA_X) ** 2 + ((dyr - dy0) / SIGMA_Y) ** 2
            c[(np.abs(dx) > GATE) | (np.abs(dyr - dy0) > GATE)] = 1e6
            ri, ci = linear_sum_assignment(c)
            good = c[ri, ci] < NONE_COST * 4
            if good.any():
                dy0 = float(np.median(dyr[ri[good], ci[good]]))
        c = (dx / SIGMA_X) ** 2 + ((dyr - dy0) / SIGMA_Y) ** 2
        c[(np.abs(dx) > GATE) | (np.abs(dyr - dy0) > GATE)] = 1e6
        for i, r in enumerate(boxes.itertuples(index=False)):
            cost[int(r.track_id)][f] = {n: float(c[i, j]) for j, n in enumerate(present)}
            gid_at[int(r.track_id)][f] = int(r.global_player_id)

    # 3. Viterbi per sideline track, states = men + none
    states = order + [None]
    path = {}
    for t, byf in cost.items():
        fs = sorted(byf)
        if len(fs) < args.min_run:
            continue
        acc = {s: (min(byf[fs[0]].get(s, ABSENT_COST), NONE_COST * 3) if s is not None else NONE_COST) for s in states}
        back = []
        for p, f in zip(fs, fs[1:]):
            gap = f - p > 5                          # a gap in the track: a change there costs nothing extra
            new, bk = {}, {}
            for s in states:
                e = NONE_COST if s is None else min(byf[f].get(s, ABSENT_COST), NONE_COST * 3)
                prev = min(states, key=lambda q: acc[q] + (0 if (q == s or gap) else SWITCH_COST))
                new[s] = acc[prev] + (0 if (prev == s or gap) else SWITCH_COST) + e
                bk[s] = prev
            acc = new
            back.append(bk)
        s = min(acc, key=acc.get)
        seq = [s]
        for bk in reversed(back):
            s = bk[s]
            seq.append(s)
        path[t] = dict(zip(fs, reversed(seq)))

    # exclusivity: each man, each frame, the best-fitting track keeps him; the rest are twins
    owner = {}
    for t, seq in path.items():
        for f, s in seq.items():
            if s is None:
                continue
            c = cost[t][f].get(s, NONE_COST)
            if (f, s) not in owner or c < owner[(f, s)][1]:
                owner[(f, s)] = (t, c)
    print("\n2-3. SIDELINE TRACKS: runs of one man (cost median), and the rows' current ids")
    folds, drops, plan = [], [], []
    for t in sorted(path):
        fs = sorted(path[t])
        runs, s0 = [], fs[0]
        for p, f in zip(fs, fs[1:] + [None]):
            if f is None or path[t][f] != path[t][p] or f - p > 5:
                runs.append((s0, p, path[t][p]))
                s0 = f
        lines = []
        for a, b, n in runs:
            if n is None:
                continue
            frames = [f for f in fs if a <= f <= b]
            twin = [f for f in frames if owner.get((f, n), (t,))[0] != t]
            med = np.median([cost[t][f].get(n, NONE_COST) for f in frames])
            gids = collections.Counter(gid_at[t][f] for f in frames)
            tag = f"  TWIN of the owner on {len(twin)}/{len(frames)} frames" if twin else ""
            lines.append(f"   {a}-{b}: #{n} (cost {med:.1f}; ids {dict(gids)}){tag}")
            if len(frames) >= args.min_run:
                if len(twin) > len(frames) // 2:
                    # never proposed as a drop: a twin by cost can be a real man beside the lineman (a tight end,
                    # a back chipping) whom the matcher cannot name -- the film decides
                    drops.append(f"t{t} {a}-{b} (ids {dict(gids)}) sits on #{n} beside the track that owns him: "
                                 f"a second copy (08za_drop_rows.py) or another man (leave it)")
                elif med < FOLD_COST:
                    if any(g != gid_of.get(n) for g in gids):
                        plan.append({"cam": "sideline", "track_id": int(t), "frames": [int(a), int(b)],
                                     "id": int(gid_of.get(n)), "why": f"#{n}, cost {med:.1f}, ids before {dict(gids)}"})
                    for g in gids:
                        if g != gid_of.get(n):
                            folds.append(f"08z_fold_ids.py --keep {gid_of.get(n)} --drop {g} --cam sideline "
                                         f"--track-id {t} --frames {a} {b}")
        if lines:
            print(f"   sideline t{t}:")
            print("\n".join(lines))
    print("\nfolds proposed (review on the film, then run with --play-dir P --apply, on a copy first):")
    for c in folds:
        print("  " + c)
    if not folds:
        print("  none: every sideline track the matcher is sure of already sits under its lineman's id")
    if drops:
        print("twins to look at on the film:")
        for c in drops:
            print("  " + c)
    if args.plan_out:
        args.plan_out.write_text(json.dumps(plan, indent=1))
        print(f"wrote {len(plan)} relabels to {args.plan_out} (scripts/08zc_relabel_tracks.py --plan; one step, no collisions)")


if __name__ == "__main__":
    main()
