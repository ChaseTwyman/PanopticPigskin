"""Player identity: roster prior, team/referee classification, and a
registry resolving tracks to stable ``player_uid`` values.

The identity layer turns per-play, play-local tracking into named players:
the roster gives each (team, jersey) a name, height and weight, and the
renderer builds each body from them (render.roster_shape).

All modules here are CPU-only (numpy / pandas / scipy / opencv) and safe to
import from either environment.
"""
from __future__ import annotations

from nfl_gsplat.identity.registry import (
    EntityType,
    IdentityMatchConfig,
    REFEREE_UID,
    load_registry,
    register_play,
    resolve_tracks,
)
from nfl_gsplat.identity.roster import (
    IdentitySource,
    OcrOnlySource,
    RosterEntry,
    RosterSource,
)

__all__ = [
    "EntityType",
    "IdentityMatchConfig",
    "REFEREE_UID",
    "load_registry",
    "register_play",
    "resolve_tracks",
    "IdentitySource",
    "OcrOnlySource",
    "RosterEntry",
    "RosterSource",
]
