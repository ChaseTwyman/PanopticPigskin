# Runbook: one play, from two clips to a finished replay

The same steps, in the same order, for every play. Each step says what to run, what to read in its output, what
"good" looks like, and which knob fixes the failures seen so far. Times are for a 10–15 s clip on one RTX 4080.

| step | who | time |
|---|---|---|
| 0. Read the play before anything runs | you | 15 min |
| 1. Phase 1: cameras, tracks, identity, fits | machine | ~1.5 h |
| 2. Read the ball events off the film | you | 20 min |
| 3. Phase 2: ball, fine-tune, refits, renders, exports | machine | ~3 h |
| 4. Measure | machine + you | 15 min |
| 5. Identity pass (on a copy) | you | 1–4 h |
| 6. Re-render, measure, record | machine | ~2 h |

A play is **done** when, over the live play (snap to down), the census is under 0.2 on every stretch where all 22
players are in view of a camera, no drawn body steps more than 0.6 m in a frame, hops are 0, and every drawn body
stands on its man in the broadcast blend (`outputs/diag/<play>_sideline_blend.mp4`).

## 0. Read the play (before anything runs)

Put the two clips at `data/all22/<game>/<play>/sideline.mp4` and `endzone.mp4`. From the play-by-play: the line of
scrimmage in yards from the nearest goal line (`KC 2-20 BLT 24` → 24), the team with the ball, and which team wears
the coloured (saturated) kit. Off the sideline film, with a contact sheet of every 4th frame:

- `SNAP`: the frame the ball leaves the centre's hands.
- `DOWN`: the frame the carrier is down (or the ball is dead).

These two frames also bound the frames the camera solve samples players from; a clip that runs on after the whistle
with a camera zoomed on the sideline fails the endzone solve without them.

## 1. Phase 1: cameras, tracks, identity, fits (~1.5 h)

```bash
export PY_MAIN=... PY_SMPLX=...
RED=KC OFFENCE=KC SNAP=256 DOWN=552 [SEED_FROM=<solved play-dir of the same game>] STOP_AFTER=refit_mono \
  bash scripts/pipeline_play.sh data/all22/<game>/<play> <play>/sideline.mp4 <play>/endzone.mp4 <los-yards> --from-paint
```

Read these lines in the log. Each is a gate; the knob is the fix that worked when it failed.

| stage | good | when it fails |
|---|---|---|
| `paint` | a candidate with rulers agreeing (hashes ≈ numerals), players 1.75–1.95 m, grid under 25 px | `SEED_FROM` (same game); `GRID_PX` if one witness misses by a hair |
| `paint` / `endzone` | the endzone reconciles ≥ 6 players a frame at a gap under 1 m, heights 1.75–1.95 m | set `SNAP`/`DOWN` (the play window); `MIN_RECONCILED=5` as a last resort |
| `check` | the formation sits within 1 yd of the play description's line of scrimmage | a wrong sideline candidate: `SEED_FROM` |
| `endzone_paint` | the players' line (`sideline feet landing on endzone boxes`) does not fall | "only N frames show the goal line": `EZ_CENTRE` from a play of the same game and half |
| `field` | open `outputs/diag/<play>_field_texture.png`: the footage's paint lies on the drawn field | a shifted field frame: re-check the line of scrimmage |
| `identity` | "N pairs" well above 0 (play 1: 23, play 6: 19) | 0 pairs: the endzone camera is on the wrong yard lines; redo `endzone_paint` |
| `offset` | the endzone clip offset with a ray miss under 0.15 m | — |

## 2. Read the ball events (20 min)

The ids are final after the roles stage, so read these now (`scripts/09b_film_strip.py`, a contact sheet of the
endzone film around the throw):

- `QB`: the passer's id at the snap.
- `RELEASE`, `CATCH`: frames. The endzone film usually shows the ball; the sideline film at broadcast width often
  does not.
- `RECEIVER`: the id **drawn** at the catch, which may not be the id the roster named. Check the drawn id against the
  sideline film (`09b --id <receiver> --at <catch>`): the number on the jersey decides.

## 3. Phase 2: ball, fine-tune, refits, renders, exports (~3 h)

```bash
RED=KC OFFENCE=KC SNAP=... QB=... RELEASE=... CATCH=... RECEIVER=... DOWN=... FINETUNE=1 [same knobs as phase 1] \
  bash scripts/pipeline_play.sh data/all22/<game>/<play> <play>/sideline.mp4 <play>/endzone.mp4 <los-yards> --from-paint
```

The fine-tune trains YOLOv8x-pose on the play's own frames (pseudo-labels from the first fits), re-detects the
keypoints and re-runs every fit on them. If `08y` says "implausible flight", the release or catch frame is off by
more than a few frames: re-read them on the film.

## 4. Measure (15 min)

- `outputs/diag/<play>_latest_plausibility.json` (written by the pipeline's `07l`): census, steps, hops, jitter.
- `eval/surge_ruler.py` on `<play>/timeline.json` for the acceleration spikes.
- Watch `outputs/diag/<play>_sideline_blend.mp4`: the drawn bodies over the broadcast.

A new play fresh out of the pipeline is not done: play 6 measured census 4.55, 29 steps over 0.25 m and 1 hop before
any fixes (`plays/bal_at_kc_2024_wk1/play_006/RESULTS.md`). Almost all of that is identity.

## 5. Identity pass (1–4 h, on a copy)

Work on a copy, keep a fix only if the rulers hold, and record every command, so the pass can be replayed.

1. **Copy** the play folder's top-level tables and clips to `<play>_fix` (not the renders, backups or fine-tune).
2. **Worklist**: export the timeline and list the candidates:
   ```bash
   $PY_SMPLX scripts/export_timeline.py --play-dir P_fix --out P_fix/timeline.json
   $PY_MAIN tools/film/identity_review.py --play-dir P_fix --timeline P_fix/timeline.json --snap SNAP --down DOWN
   ```
   It prints the formation before the snap, every handover (a drawn run that ends, with the runs that start next to
   it), every same-team twin, and every id whose kit contradicts its team.
3. **Formation first.** Before the snap the endzone camera faces the offence's backs: every number is readable
   (`tools/film/grid_crop.py --cam endzone`). Each team must show eleven, each man once, with the number the film
   shows. Wrong number, team or role: `scripts/08zb_set_identity.py` (a wrong number becomes a wrong role and a wrong
   build — a centre read as #92 became a defensive tackle and broke the quarterback rule). Two ids on one man:
   `scripts/08z_fold_ids.py` or `scripts/08za_drop_rows.py`.
4. **The offensive line, by machine.** The sideline tracker swaps linemen whenever they overlap; the endzone sees
   them side by side with their numbers on their backs. `tools/film/line_matcher.py` reads those numbers on the
   endzone tracks, gives every sideline track its lineman frame by frame, and writes the relabels as a plan:
   ```bash
   $PY_MAIN tools/film/line_matcher.py --play-dir P_fix --frames SNAP-25 SNAP+200 --numbers 76 62 52 65 74 --plan-out plan.json
   $PY_SMPLX scripts/08zc_relabel_tracks.py --play-dir P_fix --plan plan.json --apply
   ```
   `08zc` applies a plan in one step, so two tracks that traded ids trade back (a pair of `08z` folds would collide
   and delete one man's box). The matcher proposed nothing on play 1's verified line and undid two planted swaps
   exactly; it only reports twins, never drops them. The same tool reads the defence's chest numbers
   (`--team BAL --other-kit 1`), when the OCR can read them.
5. **Handovers and twins**, in frame order. For each: `scripts/09c_track_audit.py` for the camera tracks and ground
   points, then the film (`09b_film_strip.py`, `tools/film/id_strip.py`) in both cameras; across teams, each sideline
   box's kit colour (red, white, unreadable) over time shows who a track holds. The decision is one of: move a camera
   track's frames to the man's id (a plan for `08zc`, or `08z --keep K --drop D --cam C --track-id T --frames a b`),
   drop a second copy (`08za`), or leave it (a new man, or a man leaving the view). Build each man's whole chain
   before relabelling his pieces: a piece moved alone can leave another man's only drawn copy behind, or lengthen an
   id's sideline span so the loader drops its endzone frames beyond it.
6. **Measure each batch** on the copy (the census by stretch, steps over 0.25 m). Keep a batch only if neither gets
   worse; a fold that is true on the film but measures worse points at a rule that relied on the wrong identity, or
   at the next piece of the same man's chain.
7. **Record** every kept batch in `plays/<game>/<play>/identity_fixes.sh`, with its plan file and its measurement.

After the catch the broadcast cameras follow the ball: men far from it leave both views, and no identity fix draws a
man neither camera sees. Judge the census there against the men in view, not against eleven.

## 6. Re-render, measure, record (~2 h)

Run `identity_fixes.sh` on the real play folder, then the renders and exports again:

```bash
bash plays/<game>/<play>/identity_fixes.sh data/all22/<game>/<play>
rm data/all22/<game>/<play>/.done_render data/all22/<game>/<play>/.done_export_data
<the phase 3 command>
```

Men neither camera can place (feet hidden, never boxed by the endzone camera) get a film-read depth
(`tools/film_read_depth.py --write`). Public renders use `FIELD=procedural`.

Record in `plays/<game>/<play>/`: `events.json` (the six ball events), `film_reads.json`, `identity_fixes.sh`, and a
README with the command line and every knob used, as for plays 001 and 006.
