#!/usr/bin/env python3
"""Execution fixture for the REAL low-popularity library `glom` (v25.x).

glom is a genuine PyPI library (declarative nested-data access & restructuring),
not authored here -- same "real, low-download" profile as simplug/diot/simpleconf/
bidict. Its pairwise constraints are EXTRACTED from real semantics (see lib_glom.py
gold rules): a dotted-path spec NAVIGATES nested structures (unlike a literal key),
the spec SHAPE determines the output shape (dict spec -> dict, list spec -> list),
the default=/Coalesce parameters change missing-path behavior, and Assign mutates
the SAME target in place. Vendored under vendor/ ; pure-local, deterministic.

Covered pair types: return-flow (path navigation / navigate-then-transform),
config-return-contract (spec shape -> output shape), param-dependency (default= /
Coalesce on missing paths), shared-receiver (Assign mutates the same target). glom
is otherwise stateless, so lifecycle / completion-obligation are intentionally
absent (reported honestly, not faked).
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path

_VENDOR = str(_Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from glom import (  # noqa: E402  (vendored real lib)
    glom,
    Coalesce,
    Assign,
    T,
    Path,
    PathAccessError,
)


def reset() -> None:
    pass


def get_trace() -> list:
    return []


def make_namespace() -> dict:
    """Names the prompts promise: glom plus the specs used by the tasks."""
    return {
        "glom": glom,
        "Coalesce": Coalesce,
        "Assign": Assign,
        "T": T,
        "Path": Path,
        "PathAccessError": PathAccessError,
    }
