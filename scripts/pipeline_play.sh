#!/bin/bash
# One All-22 play, end to end, RESUMABLE. Every stage leaves a marker in the play-dir (.done_<stage>) and is skipped
# when the marker exists; --fresh clears every marker, so every stage runs again, and first deletes the identity,
# pose and keypoint outputs a re-run would otherwise read back. A run that dies mid-stage costs that stage only:
# re-run the same command and it continues.
#
#   bash scripts/pipeline_play.sh <play-dir> <sideline.mp4> <endzone.mp4> <los-yards> [--fresh] [--from-paint]
#
# Environments: PY_MAIN runs detection, calibration, identity and keypoints (numpy 2); PY_SMPLX runs SMPL-X, the pose
# fits and the render (numpy 1). The pose caches are numpy-1 pickles: only PY_SMPLX may write them.
#   export PY_MAIN=/path/to/main-env/python PY_SMPLX=/path/to/smplx-env/python
#
# Stages (play-dir relative):
#   paint      08 full paint solve of the sideline + endzone cameras        -> recon.npz          [--from-paint]
#   export     08b                                                           -> cameras.npz, tracks.parquet
#   refine     08e every frame's camera to the paint                         -> cameras.npz
#   shift      08d --no-rows --apply: the rule-book field frame              -> cameras.npz
#   endzone    08 --sideline-from (mirror check), then 08b again             -> recon_abs.npz, cameras.npz
#   check      08d --los-yards: hash and numeral rulers, line of scrimmage   -> field_offset.json
#   endzone_paint 08l the endzone camera on its own paint                    -> cameras.npz
#   link       08b --cameras --pairing track --pair-gap 0                    -> tracks.parquet (per-camera ids)
#   split      08k tracks cut where the kit changes for good                 -> tracks.parquet
#   field      05l the footage warped onto the ground plane                  -> field_texture.npz
#   identity   08c jersey OCR -> 08i pairing by number/kit -> 08c --from-cache -> identity_resolved.pkl
#   pose_s/_e  05c SMPLest-X per camera                                      -> poses_sideline/endzone.json
#   keypoints  05m YOLOv8x-pose per tracked person, both views               -> keypoints_2d.parquet
#   offset     05o the endzone clip's frame offset                           -> clip_offset.json
#   repair     08i --lag, 08m, 08c --from-cache: re-pair at the offset       -> tracks.parquet
#   twins      08o two ids on one body folded                                -> tracks.parquet
#   pair       08r propose + 08s apply cross-camera joins in their intervals -> tracks.parquet
#   switches   08u unpair bad runs, 08t cut switches to a fixpoint, 08v      -> tracks.parquet, pose caches
#   roles      08n builds for unnamed ids from the pre-snap formation        -> identity_resolved.pkl
#   tri        05n joints triangulated from both cameras' keypoints          -> poses_tri.json
#   refit      05f SMPL-X refit to the triangulated joints                   -> poses_refit.json
#   refit_mono 05p every body fitted to its keypoints, both views            -> poses_refit.json
#   ball       09a ball in the film, 08y ball path (SNAP, QB, DOWN read off the film) -> ball.json
#   play_end   08x when the play is dead                                     -> play_end.json
#   refit_ez   05r bodies only the endzone camera sees, fitted to its keypoints -> poses_refit.json
#   finetune   09g pseudo-labels from the fits, 09h YOLOv8x-pose fine-tune, 05m -> keypoints_2d_ft2.parquet,
#              then the fit stages re-run on the fine-tuned keypoints          [FINETUNE=1]
#   measure    07l the rulers on the timeline the renderer draws             -> $DIAG/<play>_latest_plausibility.json
#   render     05k hero follow camera, skycam, the sideline broadcast pose   -> render_hifi*/, render_view/
#   export_data 05k --export-joints (the Film Room), export_timeline.py      -> play_joints.json, timeline.json
#
# Hand-read inputs (see plays/): SNAP, QB, DOWN for the ball stage; <play-dir>/film_reads.json for men no camera can
# place; identity fixes read off the film with tools/film and applied with 08z (fold) / 08za (drop) between runs.
#
# Knobs (environment variables, defaults in brackets):
#   RED [KC]          the team in the coloured kit; 08c splits the two kits on it. One of the game's two teams.
#   OFFENCE [$RED]    the team with the ball: its pre-snap formation gives unnamed ids their builds (08n)
#   SNAP QB DOWN      the ball stage's hand-read inputs: the snap frame, the passer's id, the frame the carrier is down;
#                     SNAP and DOWN (frames, readable before any stage runs) also bound the frames 08 samples players from
#   FINETUNE [0]      1 = the pose fine-tune pass;  FIELD [footage]: procedural renders on a painted field
#   ENDZONE_WEIGHT [0.3]  the endzone keypoints' weight in the two-view fit; 0 or ONE_VIEW=1: sideline only
#   REFIT_EZ [1]      0 skips the endzone-only fits;  KICKING [0]: 1 for a kickoff, punt or field goal
#   SEED_FROM GRID_PX the paint solve (08): a solved play-dir of the same game to seed the mount; a wider grid judge
#   MIN_RECONCILED    lower the endzone-from-players minimum (08, default 6) for one play; check the gap and heights
#   EZ_CENTRE "x y z" hold the endzone mount (08l) where a play of the same game and half solved it, when too few
#                     frames show the goal line with yard lines and hashes to solve it
#   PAIR_ADDITIONS_ONLY [0], CUT_TO_FRAME  the pair and switches stages' scope;  DIAG [outputs/diag] the reports
#   STOP_AFTER        stop once that stage is marked done, e.g. refit_mono: the ids are final there, so the passer's
#                     id (QB) can be read off the film before the ball stage; re-run without it to continue
set -u
# KICKING=1 for a kickoff, punt or field goal: kickers, punters and long snappers
# may be named (08c vetoes them on scrimmage downs; play 1 named the kicker twice).
KICK_FLAG=""; [ "${KICKING:-0}" = "1" ] && KICK_FLAG="--kicking-play"
# The two-camera players are fitted to BOTH cameras' keypoints at ENDZONE_WEIGHT
# now that the endzone camera is on its paint (08l) and the clip offset measured
# (05o). Default 0.3 (was 1.0): measured 2026-09-16 with the hard hinge bounds on
# play 1's eight worst ids, at the TIMELINE's placement in both cameras -- one-view
# + bounds laid the legs along the sideline ray (endzone lower joints 52 px);
# two-view at 0.3 gave joint jitter p90 0.34 -> 0.20, sideline limbs 16.7 -> 9.5 px,
# endzone 16.4/32.1 -> 20.0/28.7 (07l v45 -> v47 on the whole play: joints p90
# 0.102 -> 0.090, p99 0.69 -> 0.44, root and census not worse). ONE_VIEW=1 fits
# every body to the sideline alone (the v25 mode, right while the endzone camera
# was 40-85 px off its paint; wrong now).
EZW="${ENDZONE_WEIGHT:-0.3}"
if [ "${ONE_VIEW:-0}" = "1" ] || [ "$EZW" = "0" ]; then ONE_VIEW_FLAG="--one-view-only"; else ONE_VIEW_FLAG="--two-view --endzone-weight $EZW"; fi
# A stage is a python run piped through grep for the log; without pipefail
# the grep decided the stage's fate and a traceback that contained the
# word "shift" passed the shift stage (play 2, 2026-09-03).
set -o pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && (pwd -W 2>/dev/null || pwd))"
export PYTHONIOENCODING=utf-8 PYTHONPATH="$REPO"
PYN="${PY_MAIN:-python}"; PYS="${PY_SMPLX:-python}"
cd "$REPO" || exit 1
P="$1"; SIDE="$2"; END="$3"; LOS="$4"; shift 4
DIAG="${DIAG:-$REPO/outputs/diag}"; PLAY="$(basename "$P")"; mkdir -p "$DIAG"
RED="${RED:-KC}"                                 # the team in the coloured kit (08c --saturated)
OFFENCE="${OFFENCE:-$RED}"                       # the team with the ball: its formation gives the roles (08n)
# With the snap and the down known, 08 samples players inside the play (2.5 s before the snap to the down): a clip
# that runs on after the whistle with the endzone zoomed on a sideline failed the endzone solve on play 6.
PLAY_WINDOW=""
if [ -n "${SNAP:-}" ] && [ -n "${DOWN:-}" ]; then PLAY_WINDOW="--play-window $(( SNAP > 150 ? SNAP - 150 : 0 )) $DOWN"; fi
SEED_FROM="${SEED_FROM:-}"                       # a solved play-dir of the same game: its sideline mount seeds 08
GRID_PX="${GRID_PX:-}"                           # widen 08's grid judge for ONE play (px); printed with the verdict
FRESH=0; FROM_PAINT=0
for a in "$@"; do
  case "$a" in --fresh) FRESH=1;; --from-paint) FROM_PAINT=1;; esac
done
ROOT="$(dirname "$P")"
NAME="$(basename "$P")"
mkdir -p "$P"

log()  { echo; echo "=== $(date +%H:%M:%S) [$NAME] $1"; }
done_() { [ -f "$P/.done_$1" ]; }
mark() {
  date +%s > "$P/.done_$1"
  if [ "${STOP_AFTER:-}" = "$1" ]; then log "STOP_AFTER=$1: stopping here; re-run without it to continue"; exit 0; fi
}
fail() { echo "FAILED at $1 -- re-run the same command to resume"; exit 1; }

if [ "$FRESH" = 1 ]; then
  log "fresh: wiping markers and stage outputs"
  rm -f "$P"/.done_* "$P/poses_sideline.json" "$P/poses_endzone.json" "$P/poses_fused.json" \
        "$P/poses_refit.json" "$P/poses_refit_fused.json" "$P/identity_resolved.pkl" "$P/identity_unnamed.pkl" "$P/identity_fused.pkl" \
        "$P/tracks_identity.parquet" "$P/tracks_unsplit.parquet" "$P/cameras_relative.npz" "$P/field_offset.json" \
        "$P/clip_offset.json" "$P/keypoints_2d.parquet" "$P/keypoints_2d_ft2.parquet"
fi

if [ "$FROM_PAINT" = 1 ] && ! done_ paint; then
  log "paint solve (08)"
  "$PYN" scripts/08_reconstruct_all22.py --root "$ROOT" --sideline "$SIDE" --endzone "$END" --no-mirror-check ${SEED_FROM:+--seed-from "$SEED_FROM"} ${GRID_PX:+--max-grid-px "$GRID_PX"} \
     ${MIN_RECONCILED:+--min-reconciled "$MIN_RECONCILED"} $PLAY_WINDOW --out "$P/recon.npz" 2>&1 | grep -v "Warning\|warn" \
     | grep -E "candidate|rulers|pass the|gap  |reconciled  |player height|] sideline |must reconcile|Error|Exit|refus" || fail paint
  rm -f "$P/.done_export" "$P/.done_refine" "$P/.done_shift" "$P/.done_endzone"
  mark paint
fi

if ! done_ export; then
  log "export (08b)"
  RECON="$P/recon.npz"; [ -f "$RECON" ] || { echo "no $RECON: run with --from-paint first"; fail export; }
  "$PYN" scripts/08b_export_play_dir.py --recon "$RECON" --root "$ROOT" --sideline "$SIDE" --endzone "$END" --out "$P" \
     2>&1 | grep -v "Warning\|warn" | grep -E "cameras:|linked|tracks.parquet" || fail export
  # Every later stage reads the clips from the play-dir (05l, 08e, 05c, 05m ...).
  [ -f "$P/sideline.mp4" ] || cp "$ROOT/$SIDE" "$P/sideline.mp4"
  [ -f "$P/endzone.mp4" ] || cp "$ROOT/$END" "$P/endzone.mp4"
  mark export
fi

if ! done_ refine; then
  log "refine every frame's camera to the paint (08e)"
  out="$("$PYN" scripts/08e_refine_cameras.py --play-dir "$P" 2>&1 | grep -v "Warning\|warn")"
  echo "$out" | grep -E "grid|rewritten|Error"
  if echo "$out" | grep -q "median grid nan"; then
    log "refine: the grid instrument read NaN on every sampled frame (no segments) -- cameras kept as solved"
  elif ! echo "$out" | grep -q "rewritten"; then
    echo "$out" | grep -q "did not lower" && log "refine: not better than the solve; cameras kept as solved" || fail refine
  fi
  mark refine
fi

if ! done_ shift; then
  log "shift (08d --no-rows --apply)"
  "$PYN" scripts/08d_field_offset.py --play-dir "$P" --no-rows --apply --los-yards "$LOS" \
     2>&1 | grep -v "Warning\|warn" | grep -E "shift|scrimmage|rewritten" || fail shift
  mark shift
fi

if ! done_ endzone; then
  log "endzone re-solve in the field frame with the mirror check (08 --sideline-from), then export again"
  "$PYN" scripts/08_reconstruct_all22.py --sideline-from "$P" --root "$ROOT" --sideline "$SIDE" --endzone "$END" \
     ${MIN_RECONCILED:+--min-reconciled "$MIN_RECONCILED"} $PLAY_WINDOW --out "$P/recon_abs.npz" 2>&1 | grep -v "Warning\|warn" \
     | grep -E "mount side|mirror|gap  |reconciled  |player height|] sideline |must reconcile|Error|Exit" || fail endzone
  "$PYN" scripts/08b_export_play_dir.py --recon "$P/recon_abs.npz" --root "$ROOT" --sideline "$SIDE" --endzone "$END" --out "$P" \
     2>&1 | grep -v "Warning\|warn" | grep -E "cameras:|linked|tracks.parquet" || fail endzone-export
  rm -f "$P"/.done_pose_s "$P"/.done_pose_e "$P"/.done_identity "$P"/.done_keypoints "$P"/.done_tri "$P"/.done_refit "$P"/.done_refit_mono "$P"/.done_refit_ez "$P"/.done_render \
        "$P/poses_sideline.json" "$P/poses_endzone.json"
  mark endzone
fi

if ! done_ check; then
  log "rulers + line of scrimmage (08d)"
  out="$("$PYN" scripts/08d_field_offset.py --play-dir "$P" --los-yards "$LOS" 2>&1)" || { echo "$out" | tail -3; fail check; }
  echo "$out" | grep -E "by ruler|agree|DISAGREE|shift|scrimmage"
  echo "$out" | grep -q "MISMATCH" && fail "check: the formation is not at the play description's line of scrimmage"
  if echo "$out" | grep -q "DISAGREE"; then
    # Two of three: the hash ruler is fooled by the midfield logo's white paint
    # (play 4, KC 49: hashes 1.82, numerals 0.99, LOS 48 vs 49, and the footage
    # field through the camera landed every numeral on the drawn one). A
    # disagreement passes only when the numeral ruler reads within 5 % of
    # unity AND the line of scrimmage matched; otherwise it stops the play.
    numerals="$(echo "$out" | grep -oE "numerals [0-9.]+" | tail -1 | awk '{print $2}')"
    los_ok="$(echo "$out" | grep -c "line of scrimmage.*(ok)")"
    if [ -n "$numerals" ] && [ "$los_ok" -ge 1 ] && awk -v n="$numerals" 'BEGIN{exit !(n>=0.95 && n<=1.05)}'; then
      log "check: rulers DISAGREE but numerals $numerals and the line of scrimmage agree -- passing on two of three (hash ruler suspect: logo or ticks)"
    else
      fail "check: the hash and numeral rulers disagree on this calibration and no second witness backs the numerals"
    fi
  fi
  mark check
fi

if ! done_ endzone_paint; then
  log "the endzone camera on its own paint (08l): yard lines, hash columns, the mount solved; the players judge"
  # At this stage there are no keypoints yet, so 08l writes on the paint alone; the players'
  # verdict (ray miss, ankle height) prints once 05o/05n run. Play 1: paint 55 -> 2.3 px,
  # ray miss 0.213 -> 0.135 m, ankles +0.33 -> +0.05 m, mount (60,0,20) -> (88,1,21).
  # EZ_CENTRE="x y z" holds the mount where another play of the same game and half solved it: play 6 (LOS 30 yd
  # out) shows the goal line with the yard lines and hashes on 2 frames, too few to solve the centre.
  "$PYN" scripts/08l_endzone_paint.py --play-dir "$P" ${EZ_CENTRE:+--centre $EZ_CENTRE} --apply 2>&1 | grep -v "Warning\|warn" \
     | grep -E "mount centre|re-sweep|players|rewritten|paint alone|Error|Traceback" || fail endzone_paint
  mark endzone_paint
fi

if ! done_ link; then
  log "per-camera tracks with the per-frame cameras (08b --cameras --pairing track --pair-gap 0)"
  cp "$P/tracks.parquet" "$P/tracks_export.parquet"
  "$PYN" scripts/08b_export_play_dir.py --recon "$P/recon.npz" --cameras "$P/cameras.npz" --root "$P" \
     --sideline sideline.mp4 --endzone endzone.mp4 --out "$P" --pairing track --pair-gap 0 \
     2>&1 | grep -v "Warning\|warn" | grep -E "kits|per-camera|linked|tracks.parquet|Error" || fail link
  rm -f "$P/.done_pose_s" "$P/.done_pose_e" "$P/.done_identity" "$P/.done_keypoints" "$P/.done_tri" "$P/.done_refit" "$P/.done_refit_ez"
  mark link
fi

if ! done_ split; then
  log "per-camera tracks cut where the kit changes for good (08k; a track the linker handed to another player)"
  "$PYN" scripts/08k_split_by_kit.py --play-dir "$P" 2>&1 | grep -v "Warning\|warn" | grep -E "kit split|wrote|kept|Error|Traceback" || fail split
  mark split
fi

if ! done_ field; then
  log "field texture from the footage (05l; LOOK at the PNG: paint must land on the drawn field)"
  "$PYN" scripts/05l_field_from_footage.py --play-dir "$P" --preview "$DIAG/${PLAY}_field_texture.png"      2>&1 | grep -v "Warning\|warn\|nanmedian" | grep -E "field texture|footage turf|Error" || fail field
  mark field
fi

if ! done_ identity; then
  log "identity (08c)"
  "$PYN" scripts/08c_identity_all22.py --play-dir "$P" --week 1 --saturated "$RED" $KICK_FLAG 2>&1 | grep -v "Warning\|warn" | grep -E "OCR:|kit split|Error" || fail identity
  # pair the camera tracks by appearance (number, kit) then position (08i), and name the paired ids
  "$PYN" scripts/08i_pair_by_appearance.py --play-dir "$P" 2>&1 | grep -v "Warning\|warn" || fail identity
  cp "$P/tracks_identity.parquet" "$P/tracks.parquet"
  "$PYN" scripts/08c_identity_all22.py --play-dir "$P" --week 1 --saturated "$RED" $KICK_FLAG --from-cache 2>&1 | grep -v "Warning\|warn" | tail -6 || fail identity
  # --saturated: the coloured kit's team is RED by construction (rule D, the
  # kit decides the roster, 2026-09-05); the roster vote prints as a check.
  mark identity
fi

if ! done_ pose_s; then
  log "pose sideline (05c, resumes per frame)"
  "$PYS" scripts/05c_pose_play.py --play-dir "$P" --cam sideline --out "$P/poses_sideline.json" \
     2>&1 | grep -v Warning | tail -1 || fail pose_s
  mark pose_s
fi

if ! done_ pose_e; then
  log "pose endzone (05c --match-frames)"
  "$PYS" scripts/05c_pose_play.py --play-dir "$P" --cam endzone --match-frames "$P/poses_sideline.json" \
     --out "$P/poses_endzone.json" 2>&1 | grep -v Warning | tail -1 || fail pose_e
  mark pose_e
fi


if ! done_ keypoints; then
  log "2-D keypoints per tracked person in both views (05m, YOLOv8-pose)"
  "$PYN" scripts/05m_keypoints_2d.py --play-dir "$P" 2>&1 | grep -v "Warning\|warn" | grep -E "keypoints:|matched|Error" || fail keypoints
  mark keypoints
fi

if ! done_ offset; then
  log "the endzone clip's frame offset from the players who move (05o)"
  "$PYN" scripts/05o_clip_offset.py --play-dir "$P" 2>&1 | grep -v "Warning\|warn" | grep -E "clip offset|wrote|Error|Traceback" || fail offset
  mark offset
fi

if ! done_ repair; then
  # The identity stage paired the camera tracks at lag 0 (the offset was unknown); with it
  # known the pairing is redone and the per-id caches (keypoints, poses) follow their boxes
  # to the new ids -- no GPU stage reruns. 08m must run under numpy 1 (the caches are pickles).
  LAG="$("$PYN" -c "import json,sys; print(json.load(open(sys.argv[1]))['offset'])" "$P/clip_offset.json")"
  log "re-pair the camera tracks at lag $LAG (08i), carry the caches (08m), name the ids (08c --from-cache)"
  "$PYN" scripts/08i_pair_by_appearance.py --play-dir "$P" --tracks "$P/tracks_identity_unpaired.parquet" --lag "$LAG" 2>&1 | grep -v "Warning\|warn" | tail -2 || fail repair
  "$PYS" scripts/08m_relabel_caches.py --play-dir "$P" --old "$P/tracks.parquet" --new "$P/tracks_identity.parquet" 2>&1 | grep -v "Warning\|warn" || fail repair
  cp "$P/tracks_identity.parquet" "$P/tracks.parquet"
  "$PYN" scripts/08c_identity_all22.py --play-dir "$P" --week 1 --saturated "$RED" $KICK_FLAG --from-cache 2>&1 | grep -v "Warning\|warn" | tail -3 || fail repair
  mark repair
fi

if ! done_ twins; then
  # Two tracker ids on ONE body put two avatars on one man (play 1: the left tackle and the
  # quarterback). They are told apart from two men stacked along the sideline's line of sight by
  # their ankle rays on the turf, not by their boxes. The ids change, so 08c names them again.
  log "fold the ids that hold one body (08o), name them again"
  "$PYS" scripts/08o_merge_twins.py --play-dir "$P" 2>&1 | grep -v "Warning\|warn" || fail twins
  "$PYN" scripts/08c_identity_all22.py --play-dir "$P" --week 1 --saturated "$RED" $KICK_FLAG --from-cache 2>&1 | grep -v "Warning\|warn" | tail -2 || fail twins
  mark twins
fi

if ! done_ pair; then
  # The two cameras hold the same man under two global ids -- at play 1's snap the sideline has 21 ids
  # and the endzone 24 with only 12 shared, while the two POOLED see Kansas City in the right 11-12
  # places. 08r proposes joins from one global assignment on per-pair median ankle-ray miss (a per-frame
  # test cannot pick a partner: at ~100 m a neighbour misses almost as little as the right man), gates
  # each on the turf gap, and emits the interval its rays actually agree over; 08s relabels the other
  # camera's rows onto the sideline id INSIDE that interval only, never unioning the global ids.
  # Measured on play 1 (v36-v38): along-ray p90 0.21 -> 0.04 m with no player worse, endzone p99
  # 341 -> 60 px, census 2.95 -> 2.84. It must run BEFORE roles/tri/refit, which all read these tables.
  # v38's gains came FROM the re-pairings (sideline 7 <- endzone 89 at 0.08 m over 184 frames, 25 <- 33),
  # each of which gives up a sitting endzone track to a fresh unused id rather than deleting it. The gate
  # (beat the incumbent on both rulers, turf gap capped) and the interval trim are what make that safe, so
  # they are ON by default -- a pipeline that shipped without them could not reproduce the measured best
  # state. PAIR_ADDITIONS_ONLY=1 restricts to joins that evict nothing.
  if [ "${PAIR_ADDITIONS_ONLY:-0}" = "1" ]; then PAIR_PROPOSE=""; PAIR_APPLY=""
  else PAIR_PROPOSE="--allow-repairing"; PAIR_APPLY="--give-up-incumbent"; fi
  log "join the ids the two cameras hold separately (08r propose, 08s apply inside their intervals)"
  "$PYN" scripts/08r_pair_by_rays.py --play-dir "$P" $PAIR_PROPOSE 2>&1 \
     | grep -v "Warning\|warn" | grep -E "assignment|PROPOSE|survive|Error|Traceback" || fail pair
  if [ -s "$P/pair_proposal.json" ] && grep -q '"rejected": null' "$P/pair_proposal.json"; then
    "$PYN" scripts/08s_apply_pairs.py --play-dir "$P" $PAIR_APPLY 2>&1 \
       | grep -v "Warning\|warn" | grep -E "proposals|moved|gives up|now has|Error|Traceback" || fail pair
    "$PYN" scripts/08c_identity_all22.py --play-dir "$P" --week 1 --saturated "$RED" $KICK_FLAG --from-cache 2>&1 | grep -v "Warning\|warn" | tail -2 || fail pair
  else
    log "pair: no proposal survived the gate; tables unchanged"
  fi
  mark pair
fi

if ! done_ switches; then
  # A global id that holds TWO men is what the viewer sees as a player teleporting (play 1 v38: a Baltimore
  # man in the Chiefs' O-line who snaps back to linebacker). Two shapes, neither visible to mispaired_ids,
  # which gates on a whole-track median: (08u) a pairing right for most of a track and wrong for a stretch
  # -- id 17 carried four sideline frames of a man 6.2 m from its endzone track; (08t) one camera's own track
  # switching men across a short gap -- id 82's sideline sat at x=-23.1 to frame 307 and resumed at 315 at
  # x=-28.9, which fill_gaps drew as a body crossing the field. Each moves the offending rows to a FRESH id
  # with a team from its own kit colour; nothing is deleted. Runs AFTER 08c (inside `pair`), which rebuilds
  # identity_resolved.pkl and would erase the fragment identities if it came later. Measured on play 1
  # (2026-09-15): contiguous steps over 0.6 m/frame 26 -> 3 together with the smooth_xy fix.
  # 08t ran on the LIVE play only at first (END_LIVE), on the argument that post-whistle hops between
  # milling bodies were not worth fragmenting. Measured 2026-09-15 (07l v44 -> v45, the whole clip to
  # a fixpoint): live steps > 0.25 m/frame 15 -> 9, whole clip 186 -> 150, census on the play 1.94 ->
  # 1.66 (four of the post-whistle switches were CROSS-TEAM tails drawn in the head's colour), root
  # jitter p90 down, joints unchanged. The whole clip is the default; CUT_TO_FRAME narrows it.
  log "unpair intervals where the cameras hold different men (08u); cut tracks that switch men (08t)"
  # snapshot first: 08v carries posed frames across every relabel below by joining this table to the
  # result on (cam, frame, track_id), so the caches stop rendering fragments default-posed
  cp "$P/tracks.parquet" "$P/tracks.parquet.preswitches"
  "$PYN" scripts/08u_unpair_bad_runs.py --play-dir "$P" --apply 2>&1 \
     | grep -v "Warning\|warn" | grep -E "intervals|rows moved|identit|Error|Traceback" || fail switches
  # 08t reports ONE cut per id (the earliest), and the fragments it creates carry switches of their
  # own: play 1 needed four passes to a fixpoint (25 + 8 + 4 + 0 cuts, six of them inside the live
  # play on first-pass fragments). Loop until a pass cuts nothing.
  for pass in 1 2 3 4 5 6 7 8; do
    out="$("$PYN" scripts/08t_cut_track_switches.py --play-dir "$P" --max-frame "${CUT_TO_FRAME:-999999}" --apply 2>&1 \
       | grep -v "Warning\|warn" | grep -E "cuts|rows moved|Error|Traceback")" || fail switches
    log "08t pass $pass: $(echo "$out" | tr '\n' ' ')"
    case "$out" in *Error*|*Traceback*) fail switches;; *" 0 cuts"*) break;; esac
  done
  # the caches are numpy-1 pickles: only PYS may write them
  "$PYS" scripts/08v_remap_poses_after_relabel.py --play-dir "$P" --before tracks.parquet.preswitches --apply 2>&1 \
     | grep -v "Warning\|warn" | grep -E "relabels|posed frames|Error|Traceback" || fail switches
  mark switches
fi

if ! done_ roles; then
  # The jersey OCR names about half the ids and the rest were 1.85 m with no weight, so a
  # defensive lineman and a cornerback came out the same body. The pre-snap formation gives the
  # role, the role gives the position group's roster height and weight (08n) -- read by the fits
  # (05p) and the render, so it must run BEFORE the refit.
  log "builds for the unnamed ids from the pre-snap formation (08n, offence $OFFENCE)"
  "$PYN" scripts/08n_role_builds.py --play-dir "$P" --offence "$OFFENCE" 2>&1 | grep -v "Warning\|warn" | tail -4 || fail roles
  mark roles
fi

# The fits (05n, 05p, 05r) read the per-play fine-tuned detector's keypoints once 09h has written them
# (keypoints_2d_ft2.parquet; play 1 from v106, film-checked), else the pretrained detector's. Until 2026-09-25 the
# stages below read keypoints_2d.parquet whatever existed, while play 1's live caches were fitted on ft2 by hand:
# a re-run from the tri stage would have quietly refitted on the pretrained keypoints.
KP="$P/keypoints_2d.parquet"
[ -f "$P/keypoints_2d_ft2.parquet" ] && KP="$P/keypoints_2d_ft2.parquet"

if ! done_ tri; then
  log "joints triangulated from the keypoints with both cameras (05n; the offset from clip_offset.json; $(basename "$KP"))"
  "$PYS" scripts/05n_triangulate_keypoints.py --play-dir "$P" --keypoints "$KP" 2>&1 | grep -v "Warning\|warn" | grep -E "offset|triangulated|Error" || fail tri
  mark tri
fi

if ! done_ refit; then
  log "refit SMPL-X to fused joints (05f)"
  "$PYS" scripts/05f_refit_fused.py --play-dir "$P" --fused "$P/poses_tri.json" --poses "$P/poses_sideline.json" \
     --identity "$P/identity_resolved.pkl" --out "$P/poses_refit.json" \
     --min-valid-joints 6 --min-frame-frac 0.5 2>&1 | grep -v Warning | grep "refit" || fail refit
  # 6 joints / half the frames: triangulation passes 23-28 % of joints on plays 2 and 4
  # and the 10 / 0.7 default refit only 9 of 30 and 19 of 43 players; the rest fell
  # back to single-view poses (measured 2026-09-05).
  mark refit
fi

if ! done_ refit_mono; then
  log "one-view bodies refit to the sideline keypoints (05p; feet on the turf, fused records win)"
  # The regressor's poses glide (play 1 v14: 0.21 m/s body-frame joint speed, 34 px off the
  # keypoints); the fit follows the keypoints (2.5 px) and moves (0.55 m/s). Re-runs start
  # from poses_refit_fused.json, the 05f cache kept beside the merged one.
  "$PYS" scripts/05p_refit_mono.py --play-dir "$P" --keypoints "$KP" $ONE_VIEW_FLAG 2>&1 | grep -v "Warning\|warn"      | grep -E "players with|^fitted|wrote|already merged|no fused|Error|Traceback" || fail refit_mono
  mark refit_mono
fi

# The ball (09a, 08y): the release, catch and receiver are read from the ball in the sideline film; the snap, the
# passer's id and the frame the carrier is down are read off the film by hand (SNAP, QB, DOWN). Without them the stage
# is skipped and 08x finds the play's end from the bodies alone.
if ! done_ ball; then
  if [ -n "${SNAP:-}" ] && [ -n "${QB:-}" ] && [ -n "${DOWN:-}" ]; then
    log "the ball in the film (09a) and its path (08y; snap $SNAP, passer $QB, down $DOWN)"
    "$PYS" scripts/09a_ball_in_film.py --play-dir "$P" --start "$SNAP" --end "$DOWN" 2>&1 | grep -v "Warning\|warn" \
       | grep -E "release|catch|receiver|wrote|Error|Traceback" || fail ball
    "$PYS" scripts/08y_ball_path.py --play-dir "$P" --from-film --qb "$QB" --down "$DOWN" --snap "$SNAP" 2>&1 \
       | grep -v "Warning\|warn" | grep -E "ball|wrote|Error|Traceback" || fail ball
    mark ball
  else
    log "ball: SNAP, QB and DOWN not given (read them off the film); skipped"
  fi
fi

# When the play is dead (08x): after the ball, whose down frame it uses; 05k stops the clip there plus a short tail.
if ! done_ play_end; then
  log "when the play is dead (08x)"
  "$PYS" scripts/08x_play_end.py --play-dir "$P" ${SNAP:+--snap "$SNAP"} 2>&1 \
     | grep -v "Warning\|warn" | grep -E "play dead|wrote|Error|Traceback" || fail play_end
  mark play_end
fi

# Bodies only the endzone camera sees (05r): the sideline fit (05p) has no record for a man the sideline has lost; 05r
# fits the endzone keypoints there, from the snap to the play's end plus tail, in place (existing records win).
if [ "${REFIT_EZ:-1}" != "0" ] && ! done_ refit_ez; then
  log "bodies only the endzone camera sees refit to its keypoints (05r; the snap to the play's end)"
  read -r EZ_LO EZ_HI <<< "$("$PYN" -c "import json; d=json.load(open(r'$P/play_end.json')); print(d['snap'], d['end'] + d.get('tail', 0))")"
  "$PYS" scripts/05r_refit_endzone_only.py --play-dir "$P" --keypoints "$KP" --frames "$EZ_LO" "$EZ_HI" --lying-aspect 1.3 --out "$P/poses_refit.json" 2>&1 \
     | grep -v "Warning\|warn" | grep -E "ids with|wrote|nothing to fit|Error|Traceback" || fail refit_ez
  mark refit_ez
fi

# The per-play keypoint fine-tune (FINETUNE=1): pseudo-labels from the fits made on the pretrained keypoints (09g),
# thirty epochs of YOLOv8x-pose on this play's own frames (09h), the keypoints again with the fine-tuned weights (05m).
# The fit stages then re-run on keypoints_2d_ft2.parquet: the script re-invokes itself once the markers are cleared.
if [ "${FINETUNE:-0}" = "1" ] && ! done_ finetune; then
  read -r FT_LO FT_HI <<< "$("$PYN" -c "import json; d=json.load(open(r'$P/play_end.json')); print(d['start'] - 1, d['end'] + d.get('tail', 0) + 1)")"
  log "pose fine-tune: labels from the fit (09g, frames $FT_LO-$FT_HI), training (09h), keypoints (05m)"
  "$PYS" scripts/09g_pose_labels.py --play-dir "$P" --out "$P/pose_ds2" --lo "$FT_LO" --hi "$FT_HI" --stride 2 --val-every 5 \
     --refit "$P/poses_refit.json" 2>&1 | grep -v "Warning\|warn" | tail -3 || fail finetune
  "$PYN" scripts/09h_finetune_pose.py --dataset "$P/pose_ds2" --weights yolov8x-pose.pt --out "$P/pose_ft2" 2>&1 \
     | grep -v "Warning\|warn" | tail -3 || fail finetune
  "$PYN" scripts/05m_keypoints_2d.py --play-dir "$P" --weights "$P/pose_ft2/train/weights/best.pt" --imgsz 1920 \
     --out "$P/keypoints_2d_ft2.parquet" 2>&1 | grep -v "Warning\|warn" | grep -E "keypoints:|matched|Error" || fail finetune
  mark finetune
  rm -f "$P/.done_tri" "$P/.done_refit" "$P/.done_refit_mono" "$P/.done_refit_ez"
  log "re-running the fit stages on the fine-tuned keypoints"
  exec bash "${BASH_SOURCE[0]}" "$P" "$SIDE" "$END" "$LOS"
fi

# The rulers on the timeline the renderer is about to draw: steps, hops, the census (eleven a side), root and joint
# jitter. Not a marked stage: cheap on the CPU and meant to be re-read after every data change.
log "plausibility rulers on the timeline 05k will draw (07l)"
"$PYS" scripts/07l_measure_plausibility.py --play-dir "$P" --tag latest --joints --gait 2>&1 \
   | grep -v "Warning\|warn" | grep -E "^(steps|root|census|joints|report| +worst)|Error|Traceback" || log "07l failed; the render goes ahead unscored"

# The renders: the players in the kits the film shows, lit, in a bowl of seats. FIELD=procedural draws a painted field
# instead of the footage's turf (the public renders use it: no broadcast pixels).
if ! done_ render; then
  FIELD_FLAG=(--field-texture "$P/field_texture.npz"); [ "${FIELD:-footage}" = "procedural" ] && FIELD_FLAG=()
  LOOK=(--uniforms --numbers --helmets --gait --ball --sky --shade)
  FFBIN="$("$PYS" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")"
  render() {  # name, out-dir, extra 05k flags...
    local name="$1" out="$2"; shift 2
    log "render: $name (05k)"
    "$PYS" scripts/05k_render_hifi.py --play-dir "$P" --out-dir "$out" "${FIELD_FLAG[@]}" "${LOOK[@]}" "$@" 2>&1 \
       | grep -v "Warning\|warn" | grep -E "timeline:|field from|wrote|left out|Error|Traceback" || fail "render $name"
    [ -f "$out/play.mp4" ] && "$FFBIN" -y -loglevel error -i "$out/play.mp4" -c:v libx264 -crf 18 -preset slow \
       -pix_fmt yuv420p -movflags +faststart "$DIAG/${PLAY}_${name}.mp4" && log "encoded $DIAG/${PLAY}_${name}.mp4"
  }
  render follow "$P/render_hifi" --pads --follow --eye-offset 2 -26 10 --fov 50
  render skycam "$P/render_hifi_skycam" --pads --follow --eye-offset 18 -3 7 --fov 55
  render broadcast "$P/render_view" --view-camera sideline --width 1280 --height 720
  mark render
fi

# The exports: the Film Room's joints (viewer/play_room.html reads play_joints.json beside it) and the timeline the
# rulers, the film tools and the report read.
if ! done_ export_data; then
  log "exports: the Film Room joints (05k --export-joints) and the timeline (export_timeline.py)"
  "$PYS" scripts/05k_render_hifi.py --play-dir "$P" --out-dir "$P/export" --gait --ball --export-joints "$P/play_joints.json" \
     --no-render 2>&1 | grep -v "Warning\|warn" | grep -E "exported joints|Error|Traceback" || fail export_data
  "$PYS" scripts/export_timeline.py --play-dir "$P" --out "$P/timeline.json" 2>&1 | grep -E "wrote|Error|Traceback" || fail export_data
  mark export_data
fi

echo; echo "PLAY DONE $NAME"
