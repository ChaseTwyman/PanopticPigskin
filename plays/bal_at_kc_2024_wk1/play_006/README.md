# Play 006 — Ravens at Chiefs, 2024 week 1

KC 1-10 BLT 30 (second quarter, 7:15): Patrick Mahomes short right to Xavier Worthy, 12 yards to the BAL 18, tackled
by Brandon Stephens at the far sideline. The second play through the pipeline, run to measure what a new play loses
before any identity fixes by hand.

The footage is not included: the pipeline expects `data/all22/bal_at_kc_2024_wk1/play_006/sideline.mp4` and
`endzone.mp4` (sideline clip 806 frames, endzone 775, both 1920x1080 at 59.94 fps).

## What is read by hand

| file | what |
|---|---|
| `events.json` | all six ball events off the film: the snap (256), the passer (id 8, #15), the release (378), the catch (414, the ball into the carrier's hands in the endzone film), the receiver (id 4, #1 on the sideline film), the down (552) |

No identity fixes and no film-read depths yet: this is the pipeline's own result.

## Running it

```bash
export PY_MAIN=... PY_SMPLX=...
SEED_FROM=data/all22/bal_at_kc_2024_wk1/play_001 EZ_CENTRE="88.28 0.57 20.8" MIN_RECONCILED=5 \
SNAP=256 QB=8 RELEASE=378 CATCH=414 RECEIVER=4 DOWN=552 FINETUNE=1 \
bash scripts/pipeline_play.sh data/all22/bal_at_kc_2024_wk1/play_006 play_006/sideline.mp4 play_006/endzone.mp4 30 --from-paint
```

- `SEED_FROM`: the sideline camera's mount from play 1 (same game); play 6's solved mount lands 0.6 m from it.
- `SNAP`, `DOWN`: frames read before anything runs; they also bound the frames the paint solve samples players from
  (the clip runs 220 frames past the tackle with the endzone zoomed on the sideline).
- `EZ_CENTRE`: the endzone mount where play 1 solved it (same half, behind the offence); only 2 frames of this clip
  show the goal line with the yard lines and hashes, too few to solve it here.
- `MIN_RECONCILED=5`: the paint stage's endzone gate, which the first run failed at 5 of 6 before `--play-window`
  existed; with the window the field-frame solve reconciles 9 at the default.
- `QB`, `RELEASE`, `CATCH`, `RECEIVER`: read after the roles stage (`STOP_AFTER=refit_mono`); the ids are final there.
