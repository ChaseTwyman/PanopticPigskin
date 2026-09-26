# Play 006 — what a new play loses

The pipeline run end to end on a second play of the same game with no identity fixes by hand, against the demo play
(play 001) after its fixes. Live play = snap to down (play 6: frames 256–552, 297 frames; play 1: 395–607, 213).

## The numbers

| ruler | play 6, pipeline only | play 1, final |
|---|---|---|
| census: \|KC − 11\| + \|BAL − 11\| per frame | **4.55** (KC 8.3, BAL 12.8; no frame 11 v 11) | 0.00 (213 of 213) |
| steps over 0.25 m / over 0.6 m | 29 / 1 | 0 / 0 |
| hops | 1 | 0 |
| surges (pelvis over 25 m/s²) | 10.2 % | 4.3 % |
| root jitter p50 / p90 (m/frame²) | 0.0044 / 0.0172 | 0.0033 / 0.0136 |
| joint jitter p50 / p90 (m/frame²) | 0.021 / 0.081 | 0.016 / 0.059 |
| hinges hyperextended / off axis | 0.0 % / 0.0 % | 0.0 % / 0.1 % |

The pose fine-tune moved the pose numbers (triangulation 4.4 → 1.4 px, two-view refit 0.073 → 0.049 m, one-view
reprojection 2.9 → 2.2 px, joint jitter p50 0.024 → 0.021) and not the census (4.52 → 4.55): what is lost is identity.

## Where the census goes

| stretch | KC drawn | BAL drawn | total (22) |
|---|---|---|---|
| snap to throw (256–329) | 10.2 | 13.0 | 23.2 |
| pocket (330–413) | 8.3 | 12.9 | 21.3 |
| after the catch (414–479) | 7.0 | 12.6 | 19.6 |
| run to the tackle (480–552) | 7.6 | 12.2 | 19.8 |

- **Chiefs drawn as Ravens**: at the snap id 7 (labelled BAL and named Roquan Smith) stands on KC's side of the
  line; four ids read KC-only numbers (#1, #37) on a Raven's kit.
- **Chiefs lost mid-play**: tracks break and the pieces survive as endzone-only fragments the timeline leaves out.
  Worthy alone is sideline id 4 to ~482, then id 12, and endzone ids 147 then 145 (the one named Worthy); none of
  them joined.
- **Duplicates**: 0.73 same-team pairs under 0.6 m a frame among the Ravens, 0.33 among the Chiefs (e.g. KC 17 and
  26, 0.5 m apart at the snap).
- **Names**: jersey numbers read on 28 of 171 ids; three KC
  defenders' names (#6, #55, #92) came out of misreads while KC had the ball; Worthy's sideline id got a tight
  end's build from the formation (1.96 m, 245 lb for a 1.80 m, 172 lb receiver).

## What the run broke, and what fixed it (branch `second-play`)

Eight things a fresh play exposed, each a commit with the measurement: the paint solve sampling players after the
play (`--play-window`); an endzone mount no frame could solve (`EZ_CENTRE`), which silently fitted the wrong yard
lines until each frame was re-aimed and a boxes judge was added to 08l; stale pose caches after a re-link; the
ball finder's cubic search (hand-read `RELEASE`/`CATCH`/`RECEIVER`); the ball stage needing the play's end before
08x writes it; the fine-tune's weights landing under `runs/`; and the fine-tune dying at the machine's commit limit
(`--resume`).

## To get it looking good

The identity recipe used on play 1 (film strips with ids, folds and drops per camera track; its census went 0.94 →
0.18 in one night of it, and to 0.00 with later fixes):
fold Worthy's four ids; settle id 7 and the other kit-overruled ids on the film; drop the twins; recover the KC
bodies lost after the throw. Then a film-read depth wherever a man is hidden, and the renders checked against the
broadcast (`05k --view-camera sideline`).
