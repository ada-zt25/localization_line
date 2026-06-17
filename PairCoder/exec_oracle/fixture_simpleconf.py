#!/usr/bin/env python3
"""Execution fixture for the REAL low-popularity library `simpleconf` (pwwang, v0.9.3).

A genuine PyPI config library (layered config + profiles), same obscure-but-real
profile as simplug. Pairwise constraints are extracted from the real source/API
(see lib_simpleconf.py gold rules) and verified at runtime. Pure-local: all tasks
load from in-memory dicts (no files/env), deterministic.

Covered pair types: param-dependency (merge order / base profile), lifecycle
(use_profile persistent vs with_profile temporary), config-return-contract
(Config.load returns a Diot; active profile fixes values), return-flow (load ->
access), shared-receiver (same conf reflects use_profile). No resource
open/close, so completion-obligation is absent (reported honestly).
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from simpleconf import Config, ProfileConfig  # noqa: E402  (vendored real lib)


def reset() -> None:
    pass


def get_trace() -> list:
    return []


def make_namespace() -> dict:
    return {"Config": Config, "ProfileConfig": ProfileConfig}
