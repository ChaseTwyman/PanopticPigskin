# Rulers

Every change to the pipeline is accepted or rejected on numbers read from what the renderer draws, never from the
tracks underneath it. Three scripts print them; two renders let the eye check them against the film.

## The terms

| term | what it reads | a real player | printed by |
|---|---|---|---|
| census | \|Chiefs drawn − 11\| + \|Ravens drawn − 11\| per frame | 0 | `scripts/07l_measure_plausibility.py` |
| steps | root distance between consecutive drawn frames over 0.25 m (and over 0.6 m) | under 0.20 m/frame (12 m/s at 59.94 fps) | `07l` |
| hops | a step more than 0.15 m longer than the median of its three neighbours each side | 0 | `07l` |
| root jitter | second difference of the root, m/frame² | about 0.003 | `07l` |
| hinges | knees and elbows bent backwards (flexion under −15°) or sideways (over 35° off the hinge axis), share of hinge-frames | 0 | `07l` |
| joint jitter, speed | second and first difference of the pelvis-relative joints, worst joint | jitter 0.01–0.02 (0.05 is a visible twitch); a sprinting hand 0.17 m/frame | `07l --joints` |
| surges | pelvis acceleration over 25 m/s² (centred differences over ±4 frames), share of body-frames | a sprinter's start peaks near 10, a hard tackle's stop near 25–30 | `eval/surge_ruler.py` |
| joint angles | hinge flexion out of range, hinge-angle jerk over 25°/frame², a bent limb's bend plane against the body's own axes | 0 | `scripts/09d_joint_rulers.py` |

`07l` builds the timeline exactly as `05k` renders it and writes its report to
`$DIAG/<play>_<tag>_plausibility.json` (`DIAG` defaults to `outputs/diag`), so two versions are one diff.
`eval/surge_ruler.py` and `09d` read the exports (`scripts/export_timeline.py`, `05k --export-joints`).

## Reading them

1. **State the population and the window.** The live window runs from the snap to the down (`play_end.json`);
   whole-clip numbers include the huddle before and the pile after the whistle. `07l` prints both.
2. **A fix needs a second ruler.** Jitter alone crowns a frozen mannequin; the census alone is blind to a man
   drawn in the wrong place. The second ruler is the other camera: a body fitted to one camera can sit on its
   keypoints there while standing a metre out in depth, so pose and placement are scored by reprojection into the
   camera that did not fit them, and on the film itself — `05q_overlay_footage.py` draws the drawn bodies over the
   footage, and `05k --view-camera sideline|endzone` renders from each broadcast camera's solved pose so the render
   lies frame for frame over the broadcast.

The demo play's values are in the [README](../README.md#results-on-the-demo-play).
