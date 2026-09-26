"""Set one id's identity -- team, jersey, the roster's name and build, and role -- as the film shows it.

    $PY_SMPLX scripts/08zb_set_identity.py --play-dir P --id 17 --team KC --jersey 52 [--role OL] [--apply]
    $PY_SMPLX scripts/08zb_set_identity.py --play-dir P --id 7 --team KC --unname --role TE --apply

WHY. 08c names an id from its jersey votes and its kit, and both fail in ways the film settles at a glance. Play 6
(2026-09-26): the centre's back reads #52 in the endzone film before the snap, OCR read #92, and the roster turned
that into a KC defensive tackle -- whose DL role then took the centre out of the offensive line, and the loader's
quarterback-under-centre rule looked for the centre in the wrong man. A tight end in a three-point stance on the
far side of the line, in a red jersey on both films, was labelled BAL (his kit votes were unreadable) and named
Roquan Smith. The fold tools (08z, 08za) move rows between ids; this fixes what an id IS.

WHAT IT DOES. identity_resolved.pkl only: ``merged[id]`` takes the team; with ``--jersey`` the roster's name, height
and weight for that team and number (data/rosters/<season>/roster_weekly.parquet, the week given), with ``--unname``
the generic name P<id> and no build (08n's role builds apply); ``--role`` sets ``roles[id]``. Backup:
identity_resolved.pkl.pre_setid[.N]. Without ``--apply`` it prints the change and writes nothing.
"""
from __future__ import annotations

import argparse
import dataclasses
import pickle
import shutil
from pathlib import Path

import pandas as pd

from nfl_gsplat.errors import SetupError
from nfl_gsplat.tracking.relabel import backup_path

INCH_M = 0.0254


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--play-dir", type=Path, required=True)
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--team", default=None, help="the team the film shows (the kit)")
    ap.add_argument("--jersey", type=int, default=None, help="the number the film shows: name and build from the roster")
    ap.add_argument("--unname", action="store_true", help="no name: P<id>, the build from its role (08n)")
    ap.add_argument("--role", default=None, help="position group for 08n's builds and the loader's rules (OL, QB, RB, TE, WR, DL, LB, DB)")
    ap.add_argument("--rosters", type=Path, default=Path("data/rosters"))
    ap.add_argument("--season", type=int, default=2024)
    ap.add_argument("--week", type=int, default=1)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.jersey is not None and args.unname:
        raise SetupError("08zb: --jersey names the id and --unname clears the name; give one")

    f = args.play_dir / "identity_resolved.pkl"
    blob = pickle.load(open(f, "rb"))
    merged = blob["merged"]
    if args.id not in merged:
        raise SetupError(f"08zb: id {args.id} is not in {f.name} (folded away, or a typo)")
    ident = merged[args.id]
    before = (ident.team, ident.jersey, ident.player, round(ident.height_m, 3), round(ident.weight_lb, 1),
              blob.get("roles", {}).get(args.id))
    change: dict = {}
    if args.team is not None:
        change["team"] = args.team
    team = change.get("team", ident.team)
    if args.jersey is not None:
        weekly = pd.read_parquet(args.rosters / str(args.season) / "roster_weekly.parquet")
        hit = weekly[(weekly["team"] == team) & (weekly["jersey_number"] == args.jersey)]
        if "week" in hit:
            hit = hit[hit["week"] == args.week] if (hit["week"] == args.week).any() else hit
        if hit.empty:
            raise SetupError(f"08zb: no {team} #{args.jersey} on the {args.season} roster")
        row = hit.iloc[0]
        change.update(jersey=int(args.jersey), player=str(row["full_name"]),
                      height_m=float(row["height"]) * INCH_M, weight_lb=float(row["weight"]))
    if args.unname:
        change.update(jersey=0, player=f"P{args.id}", weight_lb=0.0)
    ident = merged[args.id] = dataclasses.replace(ident, **change)       # PlayerIdentity is frozen
    if args.role is not None:
        blob.setdefault("roles", {})[args.id] = args.role
    after = (ident.team, ident.jersey, ident.player, round(ident.height_m, 3), round(ident.weight_lb, 1),
             blob.get("roles", {}).get(args.id))
    print(f"id {args.id}: (team, jersey, name, height m, weight lb, role) {before} -> {after}")
    if not args.apply:
        print("dry run: nothing written (--apply writes)")
        return
    b = backup_path(f, ".pre_setid")
    shutil.copy(f, b)
    pickle.dump(blob, open(f, "wb"))
    print(f"wrote {f} (backup {b.name})")


if __name__ == "__main__":
    main()
