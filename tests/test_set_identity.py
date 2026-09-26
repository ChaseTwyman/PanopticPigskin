"""scripts/08zb_set_identity.py: an id's team, number, roster name and build, and role, as the film shows them."""
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pandas as pd

from nfl_gsplat.identity.merge_cameras import PlayerIdentity

REPO = Path(__file__).resolve().parents[1]


def _play(tmp_path):
    P = tmp_path / "play"
    P.mkdir()
    merged = {17: PlayerIdentity(jersey=92, player="Neil Farrell", team="KC", height_m=1.93, weight_lb=325.0,
                                 tracks={"sideline": 17, "endzone": 17})}
    pickle.dump({"merged": merged, "roles": {17: "DL"}}, open(P / "identity_resolved.pkl", "wb"))
    R = tmp_path / "rosters" / "2024"
    R.mkdir(parents=True)
    pd.DataFrame({"team": ["KC", "KC"], "jersey_number": [52.0, 92.0], "week": [1, 1],
                  "full_name": ["Creed Humphrey", "Neil Farrell"], "height": [76.0, 76.0], "weight": [316, 325]}
                 ).to_parquet(R / "roster_weekly.parquet")
    return P, tmp_path / "rosters"


def _run(*args):
    return subprocess.run([sys.executable, str(REPO / "scripts" / "08zb_set_identity.py"), *args],
                          capture_output=True, text=True, cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO)})


def test_jersey_takes_the_rosters_name_and_build_and_the_role(tmp_path):
    P, rosters = _play(tmp_path)
    r = _run("--play-dir", str(P), "--id", "17", "--jersey", "52", "--role", "OL", "--rosters", str(rosters), "--apply")
    assert r.returncode == 0, r.stderr
    blob = pickle.load(open(P / "identity_resolved.pkl", "rb"))
    ident = blob["merged"][17]
    assert (ident.jersey, ident.player, ident.team, ident.weight_lb) == (52, "Creed Humphrey", "KC", 316.0)
    assert abs(ident.height_m - 76 * 0.0254) < 1e-9
    assert ident.tracks == {"sideline": 17, "endzone": 17}          # the camera tracks are not touched
    assert blob["roles"][17] == "OL"
    assert (P / "identity_resolved.pkl.pre_setid").exists()


def test_dry_run_writes_nothing_and_unname_clears_the_name(tmp_path):
    P, rosters = _play(tmp_path)
    before = (P / "identity_resolved.pkl").read_bytes()
    r = _run("--play-dir", str(P), "--id", "17", "--team", "BAL", "--unname", "--rosters", str(rosters))
    assert r.returncode == 0, r.stderr
    assert (P / "identity_resolved.pkl").read_bytes() == before
    r = _run("--play-dir", str(P), "--id", "17", "--team", "BAL", "--unname", "--rosters", str(rosters), "--apply")
    ident = pickle.load(open(P / "identity_resolved.pkl", "rb"))["merged"][17]
    assert (ident.team, ident.jersey, ident.player, ident.weight_lb) == ("BAL", 0, "P17", 0.0)
