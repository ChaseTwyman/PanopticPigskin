# Play 001 — Ravens at Chiefs, 2024 week 1

KC 2-20 BLT 24: Patrick Mahomes to Noah Gray, a 9.7-yard completion. The demo play every number in this repository
was measured on.

The footage is not included: the pipeline expects `data/all22/bal_at_kc_2024_wk1/play_001/sideline.mp4` and
`endzone.mp4` (the two All-22 broadcast clips of the play), and everything else in that folder is derived from them.

## What is read by hand

These files are the facts a person read off the film. Everything else is computed.

| file | what | used by |
|---|---|---|
| `events.json` | the snap (395), the passer (id 80) and the frame the carrier is down (607), read off the film; the release (530), catch (562) and receiver (id 74), read from the ball in the sideline film by `scripts/09a_ball_in_film.py` | the pipeline's `ball` stage (`SNAP`, `QB`, `DOWN`), `scripts/08y_ball_path.py`, `scripts/08x_play_end.py` |
| `film_reads.json` | one man neither camera can place along the sideline's line of sight: Madubuike (id 4) between the right guard and tackle at 552–596, his feet hidden behind #65 and never boxed by the endzone camera. His helmet read in the endzone film at four frames and triangulated with his sideline box (`tools/film_read_depth.py`; rays within 0.10–0.32 m) | copied into the play folder; the loader applies it after the depth snap (`nfl_gsplat.render.depth_snap.apply_depth_reads`) |

Identity fixes. Where the tracker handed a box from one man to another inside a pile, the film decided who was
who: `tools/film/id_strip.py`, `tools/film/grid_crop.py` and `scripts/09c_track_audit.py` show one id's boxes and
every tracked box in a region frame by frame; `scripts/08z_fold_ids.py` folds one camera track's rows into the right
id and `scripts/08za_drop_rows.py` drops a box that is a second copy of a man, each re-keying the pose caches
(`scripts/08v_remap_poses_after_relabel.py`). Each fix is tried on a copy of the play folder and kept only when the
rulers hold and the film agrees (`tools/film/mark_ids.py` projects every drawn body back onto both films). The last
three on this play:

```bash
# id 84 is #98 Travis Jones (the endzone film before the snap), the same man as the named id 81
python scripts/08z_fold_ids.py --play-dir $P --keep 81 --drop 84 --cam sideline --track-id 13 --apply
python scripts/08z_fold_ids.py --play-dir $P --keep 81 --drop 84 --cam endzone --track-id 13 --apply
python scripts/08z_fold_ids.py --play-dir $P --keep 81 --drop 84 --cam sideline --track-id 84 --frames 437 550 --apply
# sideline track 84 at 566-580 is Joe Thuney (id 139) on the ground under #98
python scripts/08z_fold_ids.py --play-dir $P --keep 139 --drop 84 --cam sideline --track-id 84 --frames 566 580 --apply
# its boxes inside Thuney's own box (551-565) and on #99 (581-587) are second copies
python scripts/08za_drop_rows.py --play-dir $P --id 84 --cam sideline --track-id 84 --frames 551 565 --apply
python scripts/08za_drop_rows.py --play-dir $P --id 84 --cam sideline --track-id 84 --frames 581 587 --apply
```

## Running it

```bash
export PY_MAIN=/path/to/main-env/python PY_SMPLX=/path/to/smplx-env/python
P=data/all22/bal_at_kc_2024_wk1/play_001
cp plays/bal_at_kc_2024_wk1/play_001/film_reads.json $P/
SNAP=395 QB=80 DOWN=607 bash scripts/pipeline_play.sh $P play_001/sideline.mp4 play_001/endzone.mp4 24 --from-paint
FINETUNE=1 SNAP=395 QB=80 DOWN=607 bash scripts/pipeline_play.sh $P play_001/sideline.mp4 play_001/endzone.mp4 24
```

(The clip paths are relative to the game folder, `$P/..`.)

The second run adds the per-play keypoint fine-tune and refits every body on it. The published renders use
`FIELD=procedural` (a painted field, no broadcast pixels).
