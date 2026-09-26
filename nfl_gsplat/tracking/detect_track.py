"""The per-detection track table (``tracks.parquet``): its columns and their dtypes.

scripts/08b_export_play_dir.py writes it (per-frame YOLO detections linked on the turf and
paired across the two cameras); every later stage reads it. Schema:
- ``frame``              int
- ``cam``                str  (e.g. "sideline")
- ``track_id``           int  (the camera track the detection belongs to)
- ``global_player_id``   int  (the player: one id across both views)
- ``bbox_x1, y1, x2, y2`` float (pixels)
- ``conf``               float
- ``foot_u, foot_v``     float (pixels)  — bottom-center of bbox
- ``jersey_number_ocr``  int   (filled by :mod:`jersey_ocr` in 08c; -1 until then)
"""
from __future__ import annotations

import pandas as pd

TRACK_COLUMNS: list[str] = [
    "frame", "cam", "track_id", "global_player_id",
    "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
    "conf", "foot_u", "foot_v", "jersey_number_ocr",
]


def empty_tracks() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=_column_dtype(c)) for c in TRACK_COLUMNS})


def _column_dtype(c: str) -> str:
    if c in ("frame", "track_id", "global_player_id", "jersey_number_ocr"):
        return "int64"
    if c == "cam":
        return "object"
    return "float64"
