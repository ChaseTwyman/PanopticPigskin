#!/usr/bin/env python
"""The demo play's report, step 1: every measurable fact, from the timeline export (the positions the render draws,
every frame at 59.94 fps), the viewer's joints export (names, the ball) and the play's hand-read events (ball.json).
Written for this play: the roster and roles below were read off the film. Writes facts.json.

Usage:
  python report/analyze.py --timeline timeline.json --joints play_001_joints.json --events ball.json --out facts.json
"""
import argparse
import collections
import json

import numpy as np

_ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
_ap.add_argument("--timeline", required=True, help="scripts/export_timeline.py output")
_ap.add_argument("--joints", required=True, help="the renderer's --export-joints output")
_ap.add_argument("--events", required=True, help="the play's ball.json (snap, release, catch, down, passer, receiver)")
_ap.add_argument("--out", required=True, help="facts.json to write")
ARGS = _ap.parse_args()
T = json.load(open(ARGS.timeline))["frames"]
J = json.load(open(ARGS.joints))
EV = json.load(open(ARGS.events))
FPS = 59.94
SNAP, REL, CATCH, DOWN = EV["snap"], EV["release"], EV["catch"], EV["down"]
LOS_X = float(J["los"]["x"])
ATTACK = -1.0                     # KC moves toward -x (the ball goes from -18 at the release to -31.5 at the catch)
GOAL_X = -45.72
YD = 0.9144
QB, TGT = EV["passer"], EV["receiver"]
OL = {204: "C", 139: "LG", 37: "LT", 76: "RG", 12: "RT"}
NAMES = {int(k): v for k, v in J["names"].items()}
NAMES[QB] = "15 Patrick Mahomes"                              # the passer (ball.json), unnamed in the export
NAMES[171] = "0 Roquan Smith"
TEAM = {}
for f, rows in T.items():
    for r in rows:
        TEAM[r[0]] = r[1]
BALL = {int(k): np.array(v, float) for k, v in J["ball"].items()}


def pos(pid, f):
    for r in T.get(str(f), []):
        if r[0] == pid:
            return np.array(r[2:4], float)
    return None


def views(pid, f):
    for r in T.get(str(f), []):
        if r[0] == pid:
            return r[5]
    return None


def on_field(f, team=None):
    return {r[0]: np.array(r[2:4], float) for r in T.get(str(f), []) if team is None or r[1] == team}


def vel(pid, f, h=4):
    a, b = pos(pid, f - h), pos(pid, f + h)
    if a is None or b is None:
        return None
    return (b - a) / (2 * h / FPS)


def speed_series(pid, f0, f1):
    out = {}
    for f in range(f0, f1 + 1):
        v = vel(pid, f)
        if v is not None:
            out[f] = float(np.hypot(*v))
    return out


def top_speed(pid, f0, f1, win=15):
    s = speed_series(pid, f0, f1)
    fs = sorted(s)
    best, at = 0.0, None
    for i in range(len(fs) - win + 1):
        m = float(np.mean([s[fs[j]] for j in range(i, i + win)]))
        if m > best:
            best, at = m, fs[i + win // 2]
    return best, at


def yards_past_los(x):
    return ATTACK * (x - LOS_X) / YD


def sec(f):
    return (f - SNAP) / FPS


def name(pid):
    return NAMES.get(pid, f"{TEAM.get(pid, '?')} id {pid} (number not read)")


facts = {"events": {"snap": SNAP, "release": REL, "catch": CATCH, "down": DOWN, "fps": FPS},
         "time_to_throw_s": (REL - SNAP) / FPS, "air_time_s": (CATCH - REL) / FPS, "catch_to_down_s": (DOWN - CATCH) / FPS}
ball_snap = BALL[SNAP]
facts["los"] = {"x": LOS_X, "yards_to_goal": (LOS_X - GOAL_X) * -ATTACK / YD, "ball_y_at_snap": float(ball_snap[1])}

# ---- who is on the field at the snap, and where
snap_q = on_field(SNAP)
kc = sorted(p for p in snap_q if TEAM[p] == "KC")
bal = sorted(p for p in snap_q if TEAM[p] == "BAL")
align = {}
for p, xy in snap_q.items():
    depth = (xy[0] - LOS_X) * (1 if TEAM[p] == "KC" else -1)          # metres off the ball on his own side
    align[p] = {"team": TEAM[p], "name": name(p), "x": float(xy[0]), "y": float(xy[1]),
                "depth_m": float(depth), "lat_m": float(xy[1] - ball_snap[1])}
facts["alignment"] = align

# ---- rush: defenders who cross into the offense's backfield before the release
rush = {}
for p in bal:
    cross = None
    for f in range(SNAP, REL + 1):
        xy = pos(p, f)
        if xy is not None and (xy[0] - LOS_X) > 0.5:                 # past the line on KC's side (+x)
            cross = f
            break
    if cross is not None:
        dmin, fmin = 99.0, None
        for f in range(SNAP, REL + 1):
            a, b = pos(p, f), pos(QB, f)
            if a is not None and b is not None:
                d = float(np.hypot(*(a - b)))
                if d < dmin:
                    dmin, fmin = d, f
        near = collections.Counter()
        for f in range(SNAP + 15, REL + 1, 3):
            a = pos(p, f)
            if a is None:
                continue
            dd = [(float(np.hypot(*(a - pos(o, f)))), o) for o in OL if pos(o, f) is not None]
            if dd:
                d, o = min(dd)
                if d < 1.6:
                    near[o] += 1
        rush[p] = {"name": name(p), "crossed_s": sec(cross), "closest_to_qb_m": dmin, "closest_at_s": sec(fmin),
                   "engaged_with": [(name(o), c) for o, c in near.most_common(2)]}
facts["rush"] = rush
facts["coverage_defenders"] = [name(p) for p in bal if p not in rush]

# ---- the quarterback
qb_path = [pos(QB, f) for f in range(SNAP, REL + 1)]
qb_path = [p for p in qb_path if p is not None]
rel_pt = BALL[REL][:2]
catch_pt = BALL[CATCH][:2]
down_pt = BALL[DOWN][:2]
throw_d = float(np.hypot(*(catch_pt - rel_pt)))
facts["qb"] = {"drop_depth_yd": max((p[0] - LOS_X) for p in qb_path) / YD,
               "release_depth_yd": float(rel_pt[0] - LOS_X) / YD,
               "lateral_drift_m": float(max(p[1] for p in qb_path) - min(p[1] for p in qb_path)),
               "release_height_m": float(BALL[REL][2]),
               "throw_distance_m": throw_d, "ball_speed_mps": throw_d / ((CATCH - REL) / FPS)}
dmin_all = (99.0, None, None)
first2 = None
for f in range(SNAP, REL + 1):
    b = pos(QB, f)
    if b is None:
        continue
    for p in bal:
        a = pos(p, f)
        if a is None:
            continue
        d = float(np.hypot(*(a - b)))
        if d < dmin_all[0]:
            dmin_all = (d, f, p)
        if d < 2.0 and first2 is None:
            first2 = (f, p, d)
facts["pressure"] = {"closest_m": dmin_all[0], "closest_s": sec(dmin_all[1]), "closest_by": name(dmin_all[2]),
                     "first_within_2m": None if first2 is None else {"s": sec(first2[0]), "by": name(first2[1])}}
facts["result"] = {"air_yards": yards_past_los(catch_pt[0]), "gain_yards": yards_past_los(down_pt[0]),
                   "yac_yards": yards_past_los(down_pt[0]) - yards_past_los(catch_pt[0]),
                   "catch_y_rel_ball": float(catch_pt[1] - ball_snap[1])}

# ---- receivers: route, separation, openness
ELIG = [p for p in kc if p not in OL and p != QB]


def nearest_def(p, f):
    a = pos(p, f)
    if a is None:
        return None, None
    dd = [(float(np.hypot(*(a - b))), q) for q, b in on_field(f, "BAL").items()]
    return min(dd) if dd else (None, None)


V_DEF, T_REACT, R_CONTEST = 7.0, 0.2, 1.0


def margin(p, f, v_ball):
    """Openness at frame f: the defenders' best time to the lead point minus the ball's time to it (s)."""
    a, qb, v = pos(p, f), pos(QB, f), vel(p, f)
    if a is None or qb is None or v is None:
        return None, None
    tau = float(np.hypot(*(a - qb))) / v_ball
    for _ in range(6):
        lead = a + v * tau
        tau = float(np.hypot(*(lead - qb))) / v_ball
    lead = a + v * tau
    best = 99.0
    for q, b in on_field(f, "BAL").items():
        t = T_REACT + max(0.0, float(np.hypot(*(b - lead))) - R_CONTEST) / V_DEF
        best = min(best, t)
    return best - tau, lead


v_ball = facts["qb"]["ball_speed_mps"]
recv = {}
for p in ELIG:
    d_rel, q_rel = nearest_def(p, REL)
    d_cat, q_cat = nearest_def(p, CATCH)
    m_rel, lead = margin(p, REL, v_ball)
    cov = collections.Counter()
    tl = []
    for f in range(SNAP, CATCH + 1, 3):
        d, q = nearest_def(p, f)
        if d is not None:
            tl.append((round(sec(f), 3), round(d, 2)))
            if f >= SNAP + 30:
                cov[q] += 1
    mtl = []
    for f in range(SNAP + 45, REL + 1, 3):
        m, _ = margin(p, f, v_ball)
        if m is not None:
            mtl.append((round(sec(f), 3), round(m, 3)))
    ts, tsf = top_speed(p, SNAP, DOWN)
    route = [(round(sec(f), 3), float(pos(p, f)[0]), float(pos(p, f)[1])) for f in range(SNAP, (DOWN if p == TGT else CATCH) + 1, 3) if pos(p, f) is not None]
    recv[p] = {"name": name(p), "sep_release_m": d_rel, "nearest_release": name(q_rel) if q_rel is not None else None,
               "sep_catch_m": d_cat, "nearest_catch": name(q_cat) if q_cat is not None else None,
               "depth_release_yd": yards_past_los(pos(p, REL)[0]), "margin_release_s": m_rel,
               "covered_mostly_by": [(name(q), c) for q, c in cov.most_common(2)],
               "sep_timeline": tl, "margin_timeline": mtl, "top_speed_mph": ts * 2.23694, "top_speed_s": sec(tsf) if tsf else None,
               "route": route, "target": p == TGT}
facts["receivers"] = recv

# ---- the target after the catch, and the tackle
first_contact = None
for f in range(CATCH, DOWN + 1):
    g = pos(TGT, f)
    for q, b in on_field(f, "BAL").items():
        if float(np.hypot(*(g - b))) < 1.0:
            first_contact = (f, q)
            break
    if first_contact:
        break
near_down = sorted((float(np.hypot(*(pos(TGT, DOWN) - b))), q) for q, b in on_field(DOWN, "BAL").items())[:3]
facts["tackle"] = {"first_within_1m": None if not first_contact else {"s_after_catch": (first_contact[0] - CATCH) / FPS, "by": name(first_contact[1])},
                   "nearest_at_down": [(name(q), round(d, 2)) for d, q in near_down]}

# ---- defenders: what each did
defs = {}
for p in bal:
    cov = collections.Counter()
    for f in range(SNAP + 30, REL + 1, 3):
        a = pos(p, f)
        if a is None:
            continue
        dd = [(float(np.hypot(*(a - pos(e, f)))), e) for e in ELIG if pos(e, f) is not None]
        if dd:
            cov[min(dd)[1]] += 1
    ts, tsf = top_speed(p, SNAP, DOWN)
    x0 = pos(p, SNAP); xr = pos(p, REL)
    d_catch = float(np.hypot(*(pos(p, CATCH) - pos(TGT, CATCH)))) if pos(p, CATCH) is not None else None
    close_speed = None
    if pos(p, CATCH) is not None and vel(p, CATCH) is not None:
        u = pos(TGT, CATCH) - pos(p, CATCH)
        close_speed = float(vel(p, CATCH) @ (u / max(1e-6, np.hypot(*u))))
    defs[p] = {"name": name(p), "rusher": p in rush, "nearest_receiver_mostly": [(name(e), c) for e, c in cov.most_common(1)],
               "depth_snap_m": float(LOS_X - x0[0]), "depth_release_m": float(LOS_X - xr[0]) if xr is not None else None,
               "dist_to_target_at_catch_m": d_catch, "closing_speed_at_catch_mps": close_speed,
               "top_speed_mph": ts * 2.23694}
facts["defenders"] = defs

# ---- offensive line: the rusher each was nearest, and the closest that rusher got to the QB
ol = {}
for o, spot in OL.items():
    near = collections.Counter()
    for f in range(SNAP + 15, REL + 1, 3):
        a = pos(o, f)
        if a is None:
            continue
        dd = [(float(np.hypot(*(a - pos(p, f)))), p) for p in rush if pos(p, f) is not None]
        if dd and min(dd)[0] < 1.6:
            near[min(dd)[1]] += 1
    ol[o] = {"name": name(o), "spot": spot, "blocked_mostly": [(name(p), c) for p, c in near.most_common(2)],
             "their_closest_to_qb_m": [round(rush[p]["closest_to_qb_m"], 2) for p, _ in near.most_common(2)]}
facts["ol"] = ol

# ---- identity confidence: share of live frames seen by both cameras
conf = {}
for p in set(kc) | set(bal):
    vs = [views(p, f) for f in range(SNAP, DOWN + 1)]
    vs = [v for v in vs if v]
    conf[p] = {"name": name(p), "two_view_share": sum("endzone" in v and "sideline" in v for v in vs) / max(1, len(vs)),
               "frames": len(vs)}
facts["identity"] = conf
facts["model"] = {"v_def_mps": V_DEF, "t_react_s": T_REACT, "r_contest_m": R_CONTEST, "v_ball_mps": v_ball}
json.dump(facts, open(ARGS.out, "w"), indent=1, default=float)

# ---- readable summary
print(f"time to throw {facts['time_to_throw_s']:.2f} s | air {facts['air_time_s']:.2f} s | catch to down {facts['catch_to_down_s']:.2f} s")
print("LOS", facts["los"])
print("QB", {k: round(v, 2) for k, v in facts["qb"].items()})
print("pressure", facts["pressure"])
print("result", {k: round(v, 2) for k, v in facts["result"].items()})
print("rushers:")
for p, r in rush.items():
    print(f"  {r['name']:26s} crossed {r['crossed_s']:.2f}s closest {r['closest_to_qb_m']:.1f} m at {r['closest_at_s']:.2f}s engaged {r['engaged_with']}")
print("coverage:", facts["coverage_defenders"])
print("receivers:")
for p, r in recv.items():
    print(f"  {r['name']:26s} depth@rel {r['depth_release_yd']:5.1f} yd sep@rel {r['sep_release_m']:.1f} ({r['nearest_release']}) "
          f"sep@catch {r['sep_catch_m']:.1f} margin@rel {r['margin_release_s']:+.2f}s top {r['top_speed_mph']:.1f} mph cov {r['covered_mostly_by']}")
    print("      margin timeline", r["margin_timeline"][::4])
print("tackle", facts["tackle"])
print("defenders:")
for p, d in defs.items():
    print(f"  {d['name']:26s} rush={d['rusher']!s:5s} depth {d['depth_snap_m']:.1f}->{(d['depth_release_m'] or 0):.1f} m mostly {d['nearest_receiver_mostly']} "
          f"to target@catch {d['dist_to_target_at_catch_m']:.1f} m closing {d['closing_speed_at_catch_mps'] if d['closing_speed_at_catch_mps'] is None else round(d['closing_speed_at_catch_mps'], 1)} top {d['top_speed_mph']:.1f} mph")
print("OL:")
for o, d in ol.items():
    print(f"  {d['spot']} {d['name']:24s} blocked {d['blocked_mostly']} rusher closest {d['their_closest_to_qb_m']}")
print("identity two-view share:", {v["name"]: round(v["two_view_share"], 2) for v in conf.values()})
