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
