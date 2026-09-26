#!/usr/bin/env python
"""The demo play's report, step 2: the page (index.html), from the timeline export and facts.json (report/analyze.py).
Every number on the page is computed here from the tracking; the prose templates only place them. Written for this
play: the roster and roles below were read off the film.

Usage:
  python report/build_report.py --timeline timeline.json --facts facts.json --joints play_001_joints.json \
      --template report/template.html --out index.html
"""
import argparse
import html
import json
import re
import math

import numpy as np

_ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
_ap.add_argument("--timeline", required=True)
_ap.add_argument("--facts", required=True)
_ap.add_argument("--joints", required=True)
_ap.add_argument("--template", required=True)
_ap.add_argument("--out", required=True, help="the report page to write")
_ap.add_argument("--numbers-out", default=None, help="optional JSON of the report's headline numbers and grades")
ARGS = _ap.parse_args()
OUT = ARGS.out
T = json.load(open(ARGS.timeline))["frames"]
F = json.load(open(ARGS.facts))
J = json.load(open(ARGS.joints))
FPS = 59.94
SNAP, REL, CATCH, DOWN = (int(F["events"][k]) for k in ("snap", "release", "catch", "down"))
LOS = F["los"]["x"]
B0 = F["los"]["ball_y_at_snap"]
YD = 0.9144
GOAL = -45.72
BALL = {int(k): np.array(v, float) for k, v in J["ball"].items()}


def pos(p, f):
    for r in T.get(str(f), []):
        if r[0] == p:
            return np.array(r[2:4], float)
    return None


def sec(f):
    return (f - SNAP) / FPS


def yd_past(x):
    return (LOS - x) / YD


def esc(s):
    return html.escape(str(s), quote=True)


def gtxt(g):
    return "0" if g == 0 else mn(f"{g:+.1f}")


def mn(s):
    """Typographic minus before a digit, for text only (never inside data attributes)."""
    return re.sub(r"-(?=\d)", "−", str(s))


# ---------------------------------------------------------------- who is who
P = {  # pid: (jersey, name, team, role, diagram label)
    80: ("15", "Patrick Mahomes", "KC", "Quarterback", "15"),
    74: ("83", "Noah Gray", "KC", "Tight end, inline right", "83"),
    11: ("87", "Travis Kelce", "KC", "Tight end, inline left", "87"),
    5: ("10", "Isiah Pacheco", "KC", "Running back", "10"),
    3: ("", "Receiver A", "KC", "Wide receiver, off the line right (number not read)", "A"),
    9: ("", "Receiver B", "KC", "Wide receiver, off the line right (number not read)", "B"),
    37: ("76", "Kingsley Suamataia", "KC", "Left tackle", "76"),
    139: ("62", "Joe Thuney", "KC", "Left guard", "62"),
    204: ("52", "Creed Humphrey", "KC", "Center", "52"),
    76: ("65", "Trey Smith", "KC", "Right guard", "65"),
    12: ("74", "Jawaan Taylor", "KC", "Right tackle", "74"),
    15: ("99", "Odafe Oweh", "BAL", "Edge, left of the ball", "99"),
    81: ("98", "Travis Jones", "BAL", "Interior line, over the center", "98"),
    4: ("92", "Nnamdi Madubuike", "BAL", "Interior line, over the right guard", "92"),
    1: ("90", "David Ojabo", "BAL", "Edge, right of the ball", "90"),
    171: ("0", "Roquan Smith", "BAL", "Linebacker", "0"),
    7: ("40", "Malik Harrison", "BAL", "Linebacker", "40"),
    28: ("14", "Kyle Hamilton", "BAL", "Safety, down in the box", "14"),
    0: ("21", "Brandon Stephens", "BAL", "Cornerback, left", "21"),
    6: ("", "Cornerback", "BAL", "Cornerback, right (number not read)", "CB"),
    2: ("32", "Marcus Williams", "BAL", "Safety, deep", "32"),
    30: ("39", "Eddie Jackson", "BAL", "Safety, deep", "39"),
}
def full(pid):
    j, n = P[pid][0], P[pid][1]
    return f"#{j} {n}" if j else n


# identity share keyed by our pid: facts.json keys are the tracking ids as strings
TWO = {int(k): v["two_view_share"] for k, v in F["identity"].items()}
VIEWS = {}
for _f in range(SNAP, DOWN + 1):
    for _r in T.get(str(_f), []):
        VIEWS.setdefault(_r[0], {}).setdefault(_r[5], 0)
        VIEWS[_r[0]][_r[5]] += 1
R = {int(k): v for k, v in F["receivers"].items()}
D = {int(k): v for k, v in F["defenders"].items()}
RU = {int(k): v for k, v in F["rush"].items()}

# ---------------------------------------------------------------- derived numbers
qbd = [((pos(80, f)[0] - LOS) / YD, f) for f in range(SNAP, REL + 1)]
qb_top_yd, qb_top_f = max(qbd)
rel_depth = (pos(80, REL)[0] - LOS) / YD
v_ball = F["qb"]["ball_speed_mps"]
air, gain, yac = F["result"]["air_yards"], F["result"]["gain_yards"], F["result"]["yac_yards"]
spot_snap = (LOS - GOAL) / YD
spot_down = spot_snap - gain


def vel(p, f, h=4):
    a, b = pos(p, f - h), pos(p, f + h)
    return None if a is None or b is None else (b - a) / (2 * h / FPS)


def options_at(f):
    """The reach model at frame f for each eligible: lead-point depth (yd), margin (s), limiting defender."""
    out = {}
    qb = pos(80, f)
    bal = [(r[0], np.array(r[2:4], float)) for r in T[str(f)] if r[1] == "BAL"]
    for p in (5, 11, 74, 3, 9):
        a, v = pos(p, f), vel(p, f)
        tau = float(np.hypot(*(a - qb))) / v_ball
        for _ in range(6):
            lead = a + v * tau
            tau = float(np.hypot(*(lead - qb))) / v_ball
        lead = a + v * tau
        ts = sorted((0.2 + max(0.0, float(np.hypot(*(b - lead))) - 1.0) / 7.0, q) for q, b in bal)
        out[p] = {"lead_yd": yd_past(lead[0]), "margin": ts[0][0] - tau, "by": ts[0][1], "tau": tau}
    return out


OPT = options_at(REL)

# openness timelines (reach margin) and rusher distance, every 3 frames
open_tl = {p: [(round(sec(f), 3), round(options_at(f)[p]["margin"], 3)) for f in range(SNAP + 45, REL + 1, 3)] for p in (5, 11, 74, 3, 9)}
rush_tl = {}
for p in (15, 81, 4, 1):
    rush_tl[p] = [(round(sec(f), 3), round(float(np.hypot(*(pos(p, f) - pos(80, f)))), 2)) for f in range(SNAP, REL + 1)]
pach_oweh = min((float(np.hypot(*(pos(5, f) - pos(15, f)))), f) for f in range(SNAP, REL + 1))
depth_at_rel = {p: yd_past(pos(p, REL)[0]) for p in (171, 7, 28, 2, 30, 74)}
lat_at_rel = {p: (pos(p, REL)[1] - B0) / YD for p in (171, 7, 28, 2, 30, 74)}
g_speed_catch = float(np.hypot(*(pos(74, CATCH + 8) - pos(74, CATCH)))) / (8 / FPS) * 2.23694
ham_run = float(np.hypot(*(pos(28, CATCH + 22) - pos(28, CATCH))))
kelce_open_from = next(t for t, m in open_tl[11] if m > 0)
gray_best = max(open_tl[74][6:], key=lambda tm: tm[1])          # after the first 0.3 s of the window
gray_best_depth = yd_past(pos(74, SNAP + int(round(gray_best[0] * FPS)))[0])
fastest = max(((R[p]["top_speed_mph"], p) for p in R))

# ---------------------------------------------------------------- grades (per-play scale -2..+2)
G = {}


def grade(pid, g, well, improve):
    G[pid] = (g, well, improve)


grade(80, 1.0,
      [f"Ball out in {F['time_to_throw_s']:.2f} s from a clean pocket: no Raven within 2 m of him before the throw "
       f"(closest {F['pressure']['closest_m']:.1f} m, Madubuike at {F['pressure']['closest_s']:.1f} s).",
       f"Completed to the deepest receiver who was not clearly covered: Gray, {air:.1f} yd downfield. The two open men "
       f"were short (Kelce {OPT[11]['lead_yd']:.0f} yd, Pacheco behind the line).",
       f"Hit the top of his drop ({qb_top_yd:.1f} yd) at {sec(qb_top_f):.1f} s and climbed a yard before throwing."],
      [f"The tightest window he could have chosen. The reach model calls Gray {OPT[74]['margin']:+.2f} s, with Roquan "
       f"Smith closing at {D[171]['closing_speed_at_catch_mps']:.1f} m/s. It worked, but the margin was thin."])
grade(74, 1.0,
      [f"Caught it {air:.1f} yd downfield between Roquan Smith ({R[74]['sep_catch_m']:.1f} m) and Kyle Hamilton "
       f"({D[28]['dist_to_target_at_catch_m']:.1f} m), both closing at about 3.6 m/s.",
       f"Settled at {depth_at_rel[74]:.1f} yd, in the gap between Hamilton and Smith and "
       f"{depth_at_rel[2] - depth_at_rel[74]:.0f} yd under both deep safeties."],
      [f"The least separated of the five receivers at the throw ({R[74]['sep_release_m']:.1f} m).",
       f"{yac:.1f} yd after the catch: Hamilton reached him {F['tackle']['first_within_1m']['s_after_catch']:.2f} s later."])
grade(11, 0.5,
      [f"Shallow cross from the left of the formation to the right: open from {kelce_open_from:.1f} s to the throw "
       f"(reach margin up to +{max(m for _, m in open_tl[11]):.2f} s; {R[11]['sep_release_m']:.1f} m from Malik Harrison at the release)."],
      [f"Only {R[11]['depth_release_yd']:.1f} yd downfield at the throw: open, but short."])
grade(5, 0.5,
      [f"Came within {pach_oweh[0]:.1f} m of Oweh at {sec(pach_oweh[1]):.1f} s (likely a chip), then released to the left.",
       f"The most open man by the reach model at the throw ({OPT[5]['margin']:+.2f} s)."],
      [f"Still {abs(R[5]['depth_release_yd']):.1f} yd behind the line at the throw: a checkdown, not a gain."])
grade(3, 0.0,
      [f"Ran to the far flat: {R[3]['depth_release_yd']:.1f} yd deep and {R[3]['top_speed_mph']:.0f} mph at the throw."],
      [f"Covered at the throw: the right cornerback limited him ({OPT[3]['margin']:+.2f} s)."])
grade(9, 0.0,
      [f"The deepest route on the play: {R[9]['depth_release_yd']:.1f} yd at the throw, and the fastest player on the field "
       f"({R[9]['top_speed_mph']:.1f} mph)."],
      [f"Capped over the top by Eddie Jackson ({OPT[9]['margin']:+.2f} s): a throw here would have been caught around "
       f"{OPT[9]['lead_yd']:.0f} yd, with the safety there first."])
for pid, rp in ((204, 81), (139, 81), (37, 15), (76, 4), (12, 1)):
    r = RU[rp]
    if pid in (204, 139):
        well = [f"Double-teamed Travis Jones with {'Thuney' if pid == 204 else 'Humphrey'} for the whole dropback. Jones "
                f"never got closer to Mahomes than where he started ({r['closest_to_qb_m']:.1f} m)."]
    else:
        well = [f"Held {P[rp][1]}: never closer than {r['closest_to_qb_m']:.1f} m to Mahomes before the throw."]
    improve = []
    if pid == 76:
        improve = [f"The play's closest rush came through his gap: {r['closest_to_qb_m']:.1f} m at {r['closest_at_s']:.1f} s. "
                   f"Still no pressure, but the pocket's tightest point."]
    grade(pid, 0.5, well, improve)
grade(4, 0.0,
      [f"The best rush on the play: {RU[4]['closest_to_qb_m']:.1f} m from Mahomes at {RU[4]['closest_at_s']:.1f} s."],
      [f"No pressure before the ball came out at {F['time_to_throw_s']:.2f} s."])
grade(81, 0.0,
      ["Drew a double team (Humphrey and Thuney) for the whole dropback."],
      [f"Never closer to the quarterback than at the snap ({RU[81]['closest_to_qb_m']:.1f} m)."])
grade(15, 0.0,
      [f"Drew a chip from Pacheco at {sec(pach_oweh[1]):.1f} s."],
      [f"Closest {RU[15]['closest_to_qb_m']:.1f} m to Mahomes: no pressure."])
grade(1, 0.0,
      [],
      [f"Closest {RU[1]['closest_to_qb_m']:.1f} m to Mahomes: the farthest of the four rushers."])
grade(171, -0.5,
      [f"Stayed within {R[74]['sep_release_m']:.1f} m of Gray through the last second of the route and was closing at "
       f"{D[171]['closing_speed_at_catch_mps']:.1f} m/s at the catch."],
      [f"The nearest defender to Gray from half a second in; allowed the {air:.1f}-yd catch with {R[74]['sep_catch_m']:.1f} m of separation."])
grade(28, 1.0,
      [f"First to the ball carrier: within 1 m of Gray {F['tackle']['first_within_1m']['s_after_catch']:.2f} s after the catch "
       f"({ham_run:.1f} m run). Gray was down {F['catch_to_down_s']:.2f} s after the catch, {yac:.1f} yd further on."],
      [])
grade(7, 0.0,
      [f"Underneath at {depth_at_rel[7]:.1f} yd, between Kelce's crosser and Gray's route."],
      [f"Kelce's crosser was open in his area ({OPT[11]['margin']:+.2f} s): it went unpunished."])
grade(0, 0.0,
      ["Mirrored Pacheco's release to the left."],
      [])
grade(6, 0.5,
      ["Covered both far-side routes: carried Receiver B early, then sat on Receiver A's route "
       f"({OPT[3]['margin']:+.2f} s at the throw)."],
      [])
grade(2, 0.0,
      [f"Deep half at {depth_at_rel[2]:.1f} yd: nothing got behind him."],
      [f"{D[2]['dist_to_target_at_catch_m']:.1f} m from the catch: too deep to affect an 8-yd throw. That is the shell's trade, not a lapse."])
grade(30, 0.5,
      [f"Capped the only deep route (Receiver B) from {depth_at_rel[30]:.1f} yd: a throw there was {OPT[9]['margin']:+.2f} s by the reach model."],
      [f"{D[30]['dist_to_target_at_catch_m']:.1f} m from the catch."])

# ---------------------------------------------------------------- the field diagram (static SVG)
paths = {}
for pid in P:
    if pid in (74,):
        f1 = DOWN
    elif pid in (28, 171):
        f1 = DOWN
    elif P[pid][2] == "KC" and pid not in (80, 204, 139, 37, 76, 12):
        f1 = CATCH
    elif pid in RU or pid in (80, 204, 139, 37, 76, 12):
        f1 = REL
    else:
        f1 = CATCH
    pts = [pos(pid, f) for f in range(SNAP, f1 + 1, 3)]
    paths[pid] = [p for p in pts if p is not None]
allp = np.array([p for ps in paths.values() for p in ps] + [BALL[REL][:2], BALL[CATCH][:2]])
xmin, xmax = allp[:, 0].min() - 2.5, allp[:, 0].max() + 2.5
ymin, ymax = allp[:, 1].min() - 2.5, allp[:, 1].max() + 2.5
K = 960 / (xmax - xmin)
W, H = 960, int((ymax - ymin) * K) + 40
PADT = 26


def sx(x):
    return (x - xmin) * K


def sy(y):
    return (ymax - y) * K + PADT


svg = [f'<svg class="field" viewBox="0 0 {W} {H}" role="img" aria-labelledby="fieldTitle fieldDesc">',
       '<title id="fieldTitle">Play diagram, top-down</title>',
       f'<desc id="fieldDesc">Every player\'s path from the snap: Chiefs in red attacking left, Ravens in violet. Gray\'s route is '
       f'the heavy line; the dotted line is the ball from Mahomes to Gray; the ring marks the catch and the cross the down.</desc>',
       f'<rect x="0" y="{PADT}" width="{W}" height="{H - PADT - 14}" class="turf"/>']
k = math.ceil((xmin - GOAL) / (5 * YD))
while GOAL + k * 5 * YD < xmax:
    x = GOAL + k * 5 * YD
    svg.append(f'<line x1="{sx(x):.1f}" y1="{PADT}" x2="{sx(x):.1f}" y2="{H - 14}" class="yardline"/>')
    svg.append(f'<text x="{sx(x):.1f}" y="{PADT - 8}" class="yardlabel" text-anchor="middle">BAL {k * 5}</text>')
    k += 1
svg.append(f'<line x1="{sx(LOS):.1f}" y1="{PADT}" x2="{sx(LOS):.1f}" y2="{H - 14}" class="los"/>')
svg.append(f'<text x="{sx(LOS) + 5:.1f}" y="{H - 20}" class="loslabel">line of scrimmage</text>')
svg.append(f'<text x="{W - 6}" y="{H - 2}" class="sidelabel" text-anchor="end">near sideline (broadcast camera) side</text>')
order = sorted(P, key=lambda p: (p == 74, P[p][2] == "KC"))
for pid in order:
    ps = paths[pid]
    team = P[pid][2].lower()
    cls = f"path {team}"
    if pid == 74:
        cls += " target"
    elif pid in (204, 139, 37, 76, 12) or pid in RU:
        cls += " line"
    pts = " ".join(f"{sx(p[0]):.1f},{sy(p[1]):.1f}" for p in ps)
    svg.append(f'<polyline points="{pts}" class="{cls}"/>')
bx0, by0 = sx(BALL[REL][0]), sy(BALL[REL][1])
bx1, by1 = sx(BALL[CATCH][0]), sy(BALL[CATCH][1])
svg.append(f'<line x1="{bx0:.1f}" y1="{by0:.1f}" x2="{bx1:.1f}" y2="{by1:.1f}" class="ballpath"/>')
svg.append(f'<circle cx="{bx1:.1f}" cy="{by1:.1f}" r="9" class="catchring"><title>Catch: {air:.1f} yd past the line, '
           f'{sec(CATCH):.2f} s after the snap</title></circle>')
dx, dy = sx(BALL[DOWN][0]), sy(BALL[DOWN][1])
svg.append(f'<path d="M{dx - 6:.1f},{dy - 6:.1f} L{dx + 6:.1f},{dy + 6:.1f} M{dx - 6:.1f},{dy + 6:.1f} L{dx + 6:.1f},{dy - 6:.1f}" '
           f'class="downx"><title>Down: {gain:.1f} yd gained, at the Ravens\' {spot_down:.0f}</title></path>')
for pid in order:
    ps = paths[pid]
    team = P[pid][2].lower()
    g = G[pid][0]
    x0, y0 = sx(ps[0][0]), sy(ps[0][1])
    x1, y1 = sx(ps[-1][0]), sy(ps[-1][1])
    tip = f"{full(pid)} ({P[pid][2]}), {P[pid][3]}. Grade {gtxt(g)}"
    lab = P[pid][4]
    anchor_dx = -11 if team == "bal" else 11
    ta = "end" if team == "bal" else "start"
    svg.append(f'<g class="player {team}" tabindex="0"><title>{esc(tip)}</title>'
               f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="3.5" class="enddot {team}"/>'
               f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="7" class="startdot {team}"/>'
               f'<text x="{x0 + anchor_dx:.1f}" y="{y0 + 4:.1f}" class="plabel" text-anchor="{ta}">{esc(lab)}</text></g>')
svg.append('</svg>')
FIELD_SVG = "\n".join(svg)


# ---------------------------------------------------------------- small multiples (static SVG + data for hover)
def panel(series, *, title, sub, y0, y1, ticks, t0, t1, ref=None, ref_label="", unit="", fmt="{:+.2f}", accent="series",
          mark_min=False, end_note=True):
    w, h, l, r, t, b = 220, 128, 34, 10, 10, 22
    X = lambda v: l + (v - t0) / (t1 - t0) * (w - l - r)
    Y = lambda v: t + (y1 - v) / (y1 - y0) * (h - t - b)
    out = [f'<svg viewBox="0 0 {w} {h}" class="sm" data-series=\'{json.dumps(series)}\' data-unit="{esc(unit)}" '
           f'data-fmt="{"signed" if fmt.startswith("{:+") else "plain"}" data-t0="{t0}" data-t1="{t1}" data-y0="{y0}" data-y1="{y1}" '
           f'data-l="{l}" data-r="{r}" data-t="{t}" data-b="{b}" tabindex="0" role="img" aria-label="{esc(title)}: {esc(sub)}">']
    for v in ticks:
        out.append(f'<line x1="{l}" x2="{w - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>')
        lab = "0" if v == 0 else fmt.format(v)
        out.append(f'<text x="{l - 4}" y="{Y(v) + 3:.1f}" class="tick" text-anchor="end">{mn(lab)}</text>')
    for tv, anc in ((t0, "start"), ((t0 + t1) / 2, "middle"), (t1, "end")):
        out.append(f'<text x="{X(tv):.1f}" y="{h - 6}" class="tick" text-anchor="{anc}">{tv:.2f} s</text>' if anc == "end"
                   else f'<text x="{X(tv):.1f}" y="{h - 6}" class="tick" text-anchor="{anc}">{tv:.2f}</text>')
    if ref is not None:
        out.append(f'<line x1="{l}" x2="{w - r}" y1="{Y(ref):.1f}" y2="{Y(ref):.1f}" class="ref"/>')
        if ref_label:
            out.append(f'<text x="{l + 3}" y="{Y(ref) - 4:.1f}" class="reflabel" text-anchor="start">{esc(ref_label)}</text>')
    pts = " ".join(f"{X(tv):.1f},{Y(min(max(v, y0), y1)):.1f}" for tv, v in series)
    out.append(f'<polyline points="{pts}" class="smline {accent}"/>')
    tv, v = series[-1]
    out.append(f'<circle cx="{X(tv):.1f}" cy="{Y(min(max(v, y0), y1)):.1f}" r="4" class="smdot {accent}"/>')
    if mark_min:
        tm, vm = min(series, key=lambda s: s[1])
        out.append(f'<circle cx="{X(tm):.1f}" cy="{Y(vm):.1f}" r="4" class="smdot {accent}"/>')
        right = X(tm) > l + 0.7 * (w - l - r)
        out.append(f'<text x="{X(tm) + (-7 if right else 7):.1f}" y="{Y(vm) - 7:.1f}" class="smnote" '
                   f'text-anchor="{"end" if right else "start"}">{vm:.1f} m</text>')
    out.append(f'<line class="xhair" x1="0" x2="0" y1="{t}" y2="{h - b}" style="display:none"/>')
    out.append('</svg>')
    return (f'<figure class="smp"><figcaption><b>{esc(title)}</b><span>{esc(sub)}</span></figcaption>'
            + "".join(out) + '<div class="smtip" hidden></div></figure>')


open_panels = []
for p in (74, 11, 5, 9, 3):
    s = open_tl[p]
    sub = mn((f"thrown to · {OPT[p]['lead_yd']:.0f} yd" if p == 74 else f"{OPT[p]['lead_yd']:.0f} yd") + f" · {OPT[p]['margin']:+.2f} s at the throw")
    open_panels.append(panel(s, title=full(p), sub=sub, y0=-0.8, y1=1.0, fmt="{:+.1f}",
                             ticks=[-0.5, 0, 0.5], t0=0.75, t1=2.25, ref=0.0, ref_label="", unit="s",
                             accent="target" if p == 74 else "series"))
rush_panels = []
for p in (4, 81, 15, 1):
    s = rush_tl[p]
    rsub = (f"never closer than at the snap, {RU[p]['closest_to_qb_m']:.1f} m" if RU[p]['closest_at_s'] < 0.1
            else f"closest {RU[p]['closest_to_qb_m']:.1f} m at {RU[p]['closest_at_s']:.1f} s")
    rush_panels.append(panel(s, title=full(p), sub=rsub,
                             y0=0, y1=9, ticks=[0, 2, 4, 6, 8], t0=0.0, t1=2.25, ref=2.0, ref_label="pressure 2 m",
                             unit="m", fmt="{:.0f}", accent="bal", mark_min=True))


def table_rows(series_map, label_of, step=15):
    ts = sorted({t for s in series_map.values() for t, _ in s})
    pick = ts[::step // 3] if step else ts
    head = "<tr><th>Time after snap (s)</th>" + "".join(f"<th>{esc(label_of(p))}</th>" for p in series_map) + "</tr>"
    rows = []
    for tv in pick:
        cells = []
        for p, s in series_map.items():
            v = dict(s).get(tv)
            txt = '' if v is None else f'{v:+.2f}' if min(x for _, x in s) < 0 else f'{v:.2f}'
            cells.append(f"<td>{mn(txt)}</td>")
        rows.append(f"<tr><td>{tv:.2f}</td>{''.join(cells)}</tr>")
    return f"<table class='data'>{head}{''.join(rows)}</table>"


OPEN_TABLE = table_rows({p: open_tl[p] for p in (74, 11, 5, 9, 3)}, full)
RUSH_TABLE = table_rows({p: rush_tl[p][::3] for p in (4, 81, 15, 1)}, full)

# ---------------------------------------------------------------- options table
opt_rows = []
for p in sorted(OPT, key=lambda p: -OPT[p]["lead_yd"]):
    o = OPT[p]
    m = o["margin"]
    wpx = min(60, abs(m) / 0.6 * 60)
    bar = (f'<span class="dbar"><span class="{"pos" if m >= 0 else "neg"}" style="width:{wpx:.0f}px;'
           f'{"left:50%" if m >= 0 else "right:50%"}"></span></span>')
    by = P[o["by"]][1] if o["by"] in P else str(o["by"])
    cls = ' class="thrown"' if p == 74 else ''
    tag = ' <em>thrown</em>' if p == 74 else ''
    opt_rows.append(f"<tr{cls}><td>{esc(full(p))}{tag}</td>"
                    f"<td class='num'>{mn(f'{o['lead_yd']:.1f}')}</td><td class='num'>{R[p]['sep_release_m']:.1f}</td>"
                    f"<td class='num'>{mn(f'{m:+.2f}')} {bar}</td><td>{esc(by)}</td></tr>")
OPT_TABLE = ("<table class='opts'><thead><tr><th>Receiver</th><th>Catch point, yd past the line</th><th>Nearest Raven, m</th>"
             "<th>Reach margin, s</th><th>Limited by</th></tr></thead><tbody>" + "".join(opt_rows) + "</tbody></table>")


# ---------------------------------------------------------------- player cards
def card(pid):
    g, well, imp = G[pid]
    team = P[pid][2].lower()
    wpx = abs(g) / 2 * 28
    gbar = (f'<span class="gbar"><span class="{"pos" if g > 0 else "neg" if g < 0 else "zero"}" '
            f'style="width:{max(2, wpx):.0f}px;{"left:50%" if g >= 0 else "right:50%"}"></span></span>')
    wl = "".join(f"<li>{mn(esc(x))}</li>" for x in well) or "<li class='none'>Nothing the tracking can credit on this play.</li>"
    il = "".join(f"<li>{mn(esc(x))}</li>" for x in imp) or "<li class='none'>Nothing the tracking can fault on this play.</li>"
    share = TWO.get(pid)
    vc = VIEWS.get(pid, {})
    if share is None:
        seen = ""
    elif share >= 0.05:
        seen = f"<span class='seen'>seen by both cameras on {share * 100:.0f}% of live frames</span>"
    else:
        one = max(("sideline", "endzone"), key=lambda c: vc.get(c, 0))
        seen = f"<span class='seen'>placed from one camera ({one}) on almost every live frame</span>"
    return (f"<article class='pcard {team}'><header><span class='jn'>{esc(P[pid][0] or P[pid][4])}</span>"
            f"<div class='who'><b>{esc(P[pid][1])}</b><span>{esc(P[pid][3])}</span></div>"
            f"<div class='grade'><b>{gtxt(g)}</b>{gbar}</div></header>"
            f"<div class='lists'><div><h4>Did well</h4><ul>{wl}</ul></div><div><h4>Could improve</h4><ul>{il}</ul></div></div>"
            f"<footer>{seen}</footer></article>")


KC_ORDER = [80, 74, 11, 5, 9, 3, 37, 139, 204, 76, 12]
BAL_ORDER = [28, 171, 30, 6, 7, 2, 0, 4, 81, 15, 1]
KC_CARDS = "".join(card(p) for p in KC_ORDER)
BAL_CARDS = "".join(card(p) for p in BAL_ORDER)
kc_sum = sum(G[p][0] for p in KC_ORDER)
bal_sum = sum(G[p][0] for p in BAL_ORDER)

CTX = dict(
    ttt=f"{F['time_to_throw_s']:.2f}", closest=f"{F['pressure']['closest_m']:.1f}", closest_s=f"{F['pressure']['closest_s']:.1f}",
    air=f"{air:.1f}", gain=f"{gain:.1f}", yac=f"{yac:.1f}", mph=f"{v_ball * 2.23694:.0f}", mps=f"{v_ball:.1f}",
    sep_catch=f"{R[74]['sep_catch_m']:.1f}", spot_snap=f"{spot_snap:.0f}", spot_down=f"{spot_down:.0f}",
    flight=f"{F['air_time_s']:.2f}", c2d=f"{F['catch_to_down_s']:.2f}", qb_top=f"{qb_top_yd:.1f}", qb_top_s=f"{sec(qb_top_f):.1f}",
    s_deep=f"{(depth_at_rel[2] + depth_at_rel[30]) / 2:.0f}", d_ham=f"{depth_at_rel[28]:.1f}", d_smith=f"{depth_at_rel[171]:.1f}",
    d_gray=f"{depth_at_rel[74]:.1f}", sep_rel=f"{R[74]['sep_release_m']:.1f}", ham_t=f"{F['tackle']['first_within_1m']['s_after_catch']:.2f}",
    gb_t=f"{gray_best[0]:.2f}", gb_m=f"{gray_best[1]:+.2f}", gb_d=f"{gray_best_depth:.1f}", kelce_from=f"{kelce_open_from:.1f}",
    m_gray=f"{OPT[74]['margin']:+.2f}", m_kel=f"{OPT[11]['margin']:+.2f}", m_pac=f"{OPT[5]['margin']:+.2f}",
    m_b=f"{OPT[9]['margin']:+.2f}", m_a=f"{OPT[3]['margin']:+.2f}", lead_b=f"{OPT[9]['lead_yd']:.0f}",
    pach_d=f"{pach_oweh[0]:.1f}", pach_t=f"{sec(pach_oweh[1]):.1f}", vb=f"{v_ball:.1f}", kc_sum=f"{kc_sum:+.1f}", bal_sum=f"{bal_sum:+.1f}",
    fast=f"{fastest[0]:.1f}", gspeed=f"{g_speed_catch:.0f}",
)
if ARGS.numbers_out:
    json.dump({"ctx": CTX, "grades": {str(k): v[0] for k, v in G.items()}}, open(ARGS.numbers_out, "w"), indent=1)
TEMPLATE = open(ARGS.template, encoding="utf-8").read()
page = (TEMPLATE.replace("%%FIELD_SVG%%", FIELD_SVG).replace("%%OPT_TABLE%%", OPT_TABLE)
        .replace("%%OPEN_PANELS%%", "".join(open_panels)).replace("%%RUSH_PANELS%%", "".join(rush_panels))
        .replace("%%OPEN_TABLE%%", OPEN_TABLE).replace("%%RUSH_TABLE%%", RUSH_TABLE)
        .replace("%%KC_CARDS%%", KC_CARDS).replace("%%BAL_CARDS%%", BAL_CARDS))
for k, v in CTX.items():
    page = page.replace("{{" + k + "}}", mn(v))
left = [seg.split("}}")[0] for seg in page.split("{{")[1:]]
if left:
    raise SystemExit(f"unfilled placeholders: {left}")
open(OUT, "w", encoding="utf-8").write(page)
print("wrote", OUT, len(page), "bytes;", "KC sum", kc_sum, "BAL sum", bal_sum)
print(json.dumps(CTX, indent=0))
