"""Give camera-track rows their man, all at once: the plan tools/film/line_matcher.py writes, applied atomically.

    $PY_SMPLX scripts/08zc_relabel_tracks.py --play-dir P --plan plan.json [--apply]

    plan.json: [{"cam": "sideline", "track_id": 25, "frames": [300, 450], "id": 17, "why": "#52 by the line matcher"}, ...]

WHY. When two linemen's sideline tracks have traded ids -- the centre's rows under the guard's id and the guard's under
the centre's -- no sequence of 08z folds undoes it safely: the first fold puts two rows of one id on the same frames
and 08z's dedupe keeps one, deleting the other man's box. Play 1's untangle (2026-09-25) worked around it by parking
rows under a spare id of the same man. This sets every listed (camera, track, frame span) to its id in one step, so a
swap is undone without a collision, and only then checks that no id holds two boxes on one frame of one camera.

WHAT IT DOES. tracks.parquet: each entry's rows (every row of that camera track on those frames, whatever id it carries)
take the entry's id; if an id still ends up with two boxes on one frame of one camera (a real twin the plan did not
resolve), the more confident, then taller, box survives and the count is printed. Every keypoint table follows the
rows (tracking.relabel), the pose caches are carried by 08v, and ids left with no rows lose their identity entries.
Backups: *.pre_relabel[.N]. Without --apply it prints what would change and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from nfl_gsplat.errors import SetupError
from nfl_gsplat.tracking.fold import carry_roles, keypoint_map
from nfl_gsplat.tracking.relabel import assert_numpy1_for_pickles, backup_path, relabel_keypoint_tables


def relabel(df: pd.DataFrame, plan: list[dict]) -> tuple[pd.DataFrame, list[str], int]:
    """``(relabelled tracks, per-entry report lines, boxes dropped as same-id collisions)``."""
    out = df.copy()
    report = []
    target = pd.Series(-1, index=out.index)
    for e in plan:
        lo, hi = map(int, e["frames"])
        m = ((out["cam"].astype(str) == str(e["cam"])) & (out["track_id"].astype(int) == int(e["track_id"]))
             & out["frame"].astype(int).between(lo, hi))
        before = out.loc[m, "global_player_id"].astype(int).value_counts().to_dict()
        target[m] = int(e["id"])
        report.append(f"{e['cam']} t{e['track_id']} {lo}-{hi} -> id {e['id']}: {int(m.sum())} rows (ids before {before})"
                      + (f"  [{e['why']}]" if e.get("why") else ""))
    set_ = target >= 0
    out.loc[set_, "global_player_id"] = target[set_].astype(out["global_player_id"].dtype)
    sub = out.copy()
    sub["_conf"] = out["conf"] if "conf" in out else 1.0
    sub["_h"] = out["bbox_y2"] - out["bbox_y1"]
    sub = sub.sort_values(["_conf", "_h"], ascending=False)
    dup = sub.index[sub.duplicated(subset=["cam", "frame", "global_player_id"], keep="first")]
    return out.drop(index=dup), report, int(len(dup))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--play-dir", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    P = args.play_dir
    plan = json.loads(args.plan.read_text())
    blob = pickle.load(open(P / "identity_resolved.pkl", "rb"))
    missing = sorted({int(e["id"]) for e in plan} - {int(k) for k in blob["merged"]})
    if missing:
        raise SetupError(f"08zc: plan ids {missing} have no identity: fold into an existing id of the same man")
    df = pd.read_parquet(P / "tracks.parquet")
    out, report, n_dup = relabel(df, plan)
    print("\n".join(report))
    print(f"{n_dup} boxes dropped: an id still held two boxes on one frame of one camera after the relabel")
    if not args.apply:
        print("dry run: nothing written (--apply writes)")
        return
    assert_numpy1_for_pickles()
    tb = backup_path(P / "tracks.parquet", ".pre_relabel")
    shutil.copy2(P / "tracks.parquet", tb)
    out.to_parquet(P / "tracks.parquet", index=False)
    print(f"wrote tracks.parquet (backup {tb.name})")
    for name, n_rows, kdrop, n_changed, kb in relabel_keypoint_tables(P, keypoint_map(df, out), ".pre_relabel"):
        print(f"{name}: {n_rows} rows written, {kdrop} dropped, {n_changed} relabelled (backup {kb})")
    subprocess.run([sys.executable, str(Path(__file__).with_name("08v_remap_poses_after_relabel.py")),
                    "--play-dir", str(P), "--before", tb.name, "--apply"], check=True)
    ib = backup_path(P / "identity_resolved.pkl", ".pre_relabel")
    shutil.copy2(P / "identity_resolved.pkl", ib)
    gone = sorted(set(df["global_player_id"].astype(int)) - set(out["global_player_id"].astype(int)))
    for g in gone:
        # the id that took most of the gone id's rows inherits its role when it has none (fold.carry_roles)
        took = out.loc[out.index.intersection(df.index[df["global_player_id"].astype(int) == g]), "global_player_id"]
        if len(took):
            blob["roles"] = carry_roles(blob.get("roles", {}) or {}, keep=int(took.mode().iloc[0]), gone=[g])
        blob["merged"].pop(g, None)
    pickle.dump(blob, open(P / "identity_resolved.pkl", "wb"))
    print(f"wrote identity_resolved.pkl (backup {ib.name}); ids left with no rows: {gone}")


if __name__ == "__main__":
    main()
