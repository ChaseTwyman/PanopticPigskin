#!/bin/bash
# Play 006 identity fixes, read off the film (docs/RUNBOOK.md, step 5). Run once, on a play folder fresh out of the
# pipeline:   bash plays/bal_at_kc_2024_wk1/play_006/identity_fixes.sh data/all22/bal_at_kc_2024_wk1/play_006
# Each line was measured on a copy of the play folder first; the census by stretch after each batch is noted.
set -euo pipefail
P="$1"
PY="${PY_SMPLX:-python}"

# --- batch 1: the formation (endzone film, frame 249: the offence's backs, every number readable) ----------------
# census 256-329 3.23 -> 2.32 (KC 10.04 -> 11.04, BAL 13.05 -> 12.50); live 4.55 -> 4.30; steps unchanged (29)
# the centre: OCR read #92 (the roster made him a KC defensive tackle, role DL, so the loader found no centre)
"$PY" scripts/08zb_set_identity.py --play-dir "$P" --id 17 --team KC --jersey 52 --role OL --apply
# a tight end in a three-point stance outside the right tackle, red on both films; labelled BAL (Roquan Smith)
"$PY" scripts/08zb_set_identity.py --play-dir "$P" --id 7 --team KC --unname --role TE --apply
# the right tackle (#74) and the left guard (#62, the endzone-only id 107), unnamed
"$PY" scripts/08zb_set_identity.py --play-dir "$P" --id 10 --team KC --jersey 74 --role OL --apply
"$PY" scripts/08zb_set_identity.py --play-dir "$P" --id 107 --team KC --jersey 62 --role OL --apply
# Xavier Worthy (#1 on the sideline film at the catch), unnamed and given a tight end's build by the formation
"$PY" scripts/08zb_set_identity.py --play-dir "$P" --id 4 --team KC --jersey 1 --role WR --apply

# --- batch 2: the offensive line, by tools/film/line_matcher.py (numbers read on the endzone tracks, each sideline
# track given its lineman by the across-field order; validated on play 1: 0 relabels on its verified tables, 2 of 2
# planted swaps undone exactly). Applied in one step (08zc): the centre's and the left guard's tracks had traded.
# census live 4.30 -> 3.87 (330-413 4.64 -> 3.96, 480-552 4.73 -> 3.93); 256-329 unchanged 2.32; steps unchanged
# python tools/film/line_matcher.py --play-dir P --frames 230 450 --numbers 76 62 52 65 74 --plan-out line_plan_kc.json
"$PY" scripts/08zc_relabel_tracks.py --play-dir "$P" --plan plays/bal_at_kc_2024_wk1/play_006/line_plan_kc.json --apply

# --- batch 3: the tight end and the two Ravens on him (sideline kit colour per box + the film at 330, 353, 380):
# the tight end's track took the Raven he blocked at 286, that Raven's track took the tight end, and the linebacker's
# own track took the tight end on his crossing route at 356 while the linebacker ran on under a new id (170).
# census live 3.87 -> 2.29 (256-329 2.32 -> 1.78, 330-413 3.96 -> 1.96, 480-552 3.93 -> 2.15); steps 29 -> 26
"$PY" scripts/08zc_relabel_tracks.py --play-dir "$P" --plan plays/bal_at_kc_2024_wk1/play_006/plan_te.json --apply

# --- batch 4: the formation's left side and Raven 20 (line matcher + ray/position checks against the endzone's
# numbered tracks): the left guard #62 held twice at the snap (sideline t25 and the endzone-only id 107) and later
# under the ids 158/204 labelled BAL; the left tackle's continuation (t28, both cameras); a second sideline track on
# Raven 20 (t95, 0.31 m over 311-361).
# census 256-329 1.78 -> 0.22 (61 of 74 frames exactly 11 v 11), 330-413 1.96 -> 1.50, live 2.29 -> 1.98; steps 26.
# Cost: the guard's endzone-only frames after 395 are no longer drawn (his id now has a sideline span that ends at
# 395; the loader leaves out endzone frames beyond it): 480-552 2.15 -> 2.95. He is out of the sideline view by then.
"$PY" scripts/08zc_relabel_tracks.py --play-dir "$P" --plan plays/bal_at_kc_2024_wk1/play_006/plan_line_left.json --apply
