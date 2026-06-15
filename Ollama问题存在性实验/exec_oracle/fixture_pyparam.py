#!/usr/bin/env python3
"""Execution fixture for the REAL low-popularity library `pyparam` (pwwang, v0.5.4).

A genuine PyPI argument-parsing library, same obscure-but-real profile as
simplug. Tasks parse an explicit args LIST (no sys.argv), deterministic and
pure-local. Discipline (from the real library's behavior): build a FRESH Params
and parse ONCE per task, with multi-character option names and complete valid
args (pyparam caches a Params' first parse and prints help / SystemExits on
empty/missing/error input).

Covered pair types: config-return-contract (type= fixes the parsed value's
type), param-dependency (required / default / which args), return-flow (parse ->
Namespace access), shared-receiver (params must be added to the SAME Params that
is parsed). pyparam has no resource/profile lifecycle, so lifecycle &
completion-obligation are absent here (covered by other libs / reported).
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from pyparam import POSITIONAL, Params  # noqa: E402,F401  (vendored real lib)


def reset() -> None:
    pass


def get_trace() -> list:
    return []


def make_namespace() -> dict:
    return {"Params": Params, "POSITIONAL": POSITIONAL}
