#!/usr/bin/env python3
"""Execution fixture for the REAL low-popularity library `bidict` (v0.23.x).

bidict is a genuine PyPI library (a bidirectional, 1:1 mapping), not authored
here -- same "obscure, real, low-download" profile as simplug/diot/simpleconf.
Its pairwise constraints are EXTRACTED from the real semantics (see lib_bidict.py
gold rules): value-uniqueness (duplicate values RAISE), put vs forceput (drop the
old mapping), the `.inv` inverse VIEW (live on the SAME object), putall atomicity
(all-or-nothing), and frozenbidict immutability. Vendored under vendor/ ;
pure-local, deterministic.

Covered pair types: param-dependency (put/forceput choice on a value clash),
config-return-contract (bidict is 1:1; `.inv` is itself a bidict), return-flow
(reverse lookup goes THROUGH `.inv`), shared-receiver (`.inv` reflects mutations
of the same bidict), lifecycle (putall atomic rollback / frozenbidict). bidict has
no resource open/close, so completion-obligation is intentionally absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from bidict import (  # noqa: E402  (vendored real lib)
    bidict,
    frozenbidict,
    OrderedBidict,
    ValueDuplicationError,
    KeyDuplicationError,
    DuplicationError,
)


def reset() -> None:
    pass


def get_trace() -> list:
    return []


def make_namespace() -> dict:
    """Names the prompts promise: the real bidict classes + duplication errors."""
    return {
        "bidict": bidict,
        "frozenbidict": frozenbidict,
        "OrderedBidict": OrderedBidict,
        "ValueDuplicationError": ValueDuplicationError,
        "KeyDuplicationError": KeyDuplicationError,
        "DuplicationError": DuplicationError,
    }
