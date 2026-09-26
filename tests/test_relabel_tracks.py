"""scripts/08zc_relabel_tracks.py: a plan's relabels land all at once, so two tracks that traded ids trade back."""
import importlib.util
from pathlib import Path

import pandas as pd

_spec = importlib.util.spec_from_file_location(
    "zc", Path(__file__).resolve().parents[1] / "scripts" / "08zc_relabel_tracks.py")
zc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zc)


def _tracks():
    rows = []
    for f in range(10):
        # sideline track 1 is the centre (id 52) and track 2 the guard (id 62), but on frames 4-7 their ids traded
        swapped = 4 <= f <= 7
        rows.append(dict(cam="sideline", frame=f, track_id=1, global_player_id=62 if swapped else 52,
                         conf=0.9, bbox_x1=0, bbox_y1=0, bbox_x2=10, bbox_y2=30))
        rows.append(dict(cam="sideline", frame=f, track_id=2, global_player_id=52 if swapped else 62,
                         conf=0.9, bbox_x1=20, bbox_y1=0, bbox_x2=30, bbox_y2=30))
        rows.append(dict(cam="endzone", frame=f, track_id=1, global_player_id=52,
                         conf=0.9, bbox_x1=0, bbox_y1=0, bbox_x2=10, bbox_y2=30))
    df = pd.DataFrame(rows)
    df["global_player_id"] = df["global_player_id"].astype("int32")
    return df


def test_a_swap_is_undone_in_one_step_without_losing_a_box():
    df = _tracks()
    plan = [{"cam": "sideline", "track_id": 1, "frames": [0, 9], "id": 52},
            {"cam": "sideline", "track_id": 2, "frames": [0, 9], "id": 62}]
    out, report, n_dup = zc.relabel(df, plan)
    assert n_dup == 0 and len(out) == len(df)
    side = out[out.cam == "sideline"]
    assert (side[side.track_id == 1].global_player_id == 52).all()
    assert (side[side.track_id == 2].global_player_id == 62).all()
    assert (out[out.cam == "endzone"].global_player_id == 52).all()          # rows outside the plan untouched
    assert len(report) == 2


def test_two_boxes_left_on_one_id_keep_the_more_confident():
    df = _tracks()
    df.loc[(df.cam == "sideline") & (df.track_id == 2), "conf"] = 0.5
    plan = [{"cam": "sideline", "track_id": 2, "frames": [0, 1], "id": 52}]  # track 2 put on the centre's id too
    out, _report, n_dup = zc.relabel(df, plan)
    assert n_dup == 2                                                         # frames 0 and 1: one box of 52 each
    kept = out[(out.cam == "sideline") & out.frame.isin([0, 1])]
    assert set(kept.track_id) == {1}
