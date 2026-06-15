#!/usr/bin/env python3
"""Execution fixture for the REAL low-popularity library `diot` (pwwang, v0.3.4).

diot is a genuine PyPI library (attribute-access dict with key transforms,
nesting control and freezing), not authored here -- same "obscure, real,
low-download" profile as simplug. Its pairwise constraints are EXTRACTED from
the real source (see lib_diot.py gold rules, each cited to vendor/diot/*.py),
not invented. Vendored under vendor/ ; pure-local, deterministic.

Covered pair types (the ones diot really exhibits): param-dependency
(diot_transform / diot_nest), config-return-contract (.to_dict() / nested type),
return-flow (nested sub-Diot access), shared-receiver (same diot), lifecycle
(diot_frozen + the .thaw() context). diot has no resource open/close, so
completion-obligation is intentionally absent (reported honestly, not faked).
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from diot import Diot, FrozenDiot, OrderedDiot  # noqa: E402  (vendored real lib)
from diot.utils import DiotFrozenError  # noqa: E402


def reset() -> None:
    pass


def get_trace() -> list:
    return []


def make_namespace() -> dict:
    """Names the prompts promise: the real diot classes + the frozen error."""
    return {
        "Diot": Diot,
        "OrderedDiot": OrderedDiot,
        "FrozenDiot": FrozenDiot,
        "DiotFrozenError": DiotFrozenError,
    }
