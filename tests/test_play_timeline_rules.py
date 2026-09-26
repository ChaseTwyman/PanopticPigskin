"""render.edge_rule.edge_clipped_ids: one-view ids whose boxes all touch a frame edge."""
import pandas as pd

from nfl_gsplat.render.edge_rule import EDGE_PX, edge_clipped_ids


class _Track:
    height = 1080
    width = 1920


def _rows(pid, cam, boxes):
    return [{"frame": i, "cam": cam, "track_id": pid, "global_player_id": pid,
             "bbox_x1": b[0], "bbox_y1": b[1], "bbox_x2": b[2], "bbox_y2": b[3]}
            for i, b in enumerate(boxes)]


def test_top_clipped_endzone_only_id_is_dropped_two_view_and_interior_are_kept():
    rows = []
    rows += _rows(1, "endzone", [(100, 0, 140, 70), (120, 3, 160, 75)])          # clipped at the top
    rows += _rows(2, "endzone", [(100, 200, 140, 350), (120, 0, 160, 75)])       # one interior box: kept
    rows += _rows(3, "endzone", [(100, 0, 140, 70)]) + _rows(3, "sideline", [(500, 400, 560, 560)])
    rows += _rows(4, "sideline", [(500, 1000, 560, 1080 - 2)])                   # clipped at the bottom
    df = pd.DataFrame(rows)
    views = {0: {3: ("endzone", "sideline")}}
    tracks = {"endzone": _Track(), "sideline": _Track()}
    out = edge_clipped_ids(df, tracks, views)
    assert out == {1, 4}
    assert EDGE_PX >= 1.0


def test_keypoint_confidence_keeps_the_best_camera_per_rotation():
    import numpy as np
    import pandas as pd
    from nfl_gsplat.render import play_timeline as pt, timeline as tlm
    rows = []
    for cam, wrist, elbow in (("sideline", 0.1, 0.9), ("endzone", 0.8, 0.2)):
        for joint in range(17):
            conf = {9: wrist, 7: elbow}.get(joint, 0.95)
            rows.append(dict(frame=100, cam=cam, global_player_id=4, joint=joint, x=0.0, y=0.0, conf=conf))
    kdf = pd.DataFrame(rows)
    both = pt.keypoint_confidence(kdf)[4][100]
    side = pt.keypoint_confidence(kdf, cam="sideline")[4][100]
    assert both.shape == (21,)
    assert abs(both[17] - 0.8) < 1e-9 and abs(side[17] - 0.1) < 1e-9      # the left elbow's rotation <- the left wrist (COCO 9)
    assert abs(both[15] - 0.9) < 1e-9 and abs(side[15] - 0.9) < 1e-9      # the left shoulder's <- the left elbow (COCO 7)
    assert np.isnan(both[2]) and np.isnan(both[11])                        # spine, neck: no keypoint vouches
    assert set(tlm.CONF_GATE_KEYPOINT) == {0, 1, 3, 4, 6, 7, 15, 16, 17, 18, 19, 20}
    assert pt.keypoint_confidence(kdf[kdf.cam == "nowhere"]) == {}
