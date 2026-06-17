#!/usr/bin/env python3
"""Benchmark module: bidict (REAL low-popularity library, v0.23.x; bijective-map domain).

Gold pair rules are MANUALLY EXTRACTED from bidict's real semantics. Covered pair
types match what bidict really exhibits (param-dependency / config-return-contract
/ return-flow / shared-receiver / lifecycle); bidict has no resource open/close so
completion-obligation is absent (reported, not faked). Judged on observable
behavior (return type/value, raised errors, post-state), never source inspection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

import fixture_bidict as fx  # noqa: E402
from bidict import bidict, frozenbidict  # noqa: E402  (for reference outputs only)
from fixture_bidict import make_namespace  # noqa: F401,E402

NAME = "bidict"
reset = fx.reset
get_trace = fx.get_trace


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


FUNC_NAMES = {
    "bidict-B001": "key_for",
    "bidict-B002": "invert",
    "bidict-B003": "inverse_view",
    "bidict-B004": "remap",
    "bidict-B005": "add_then_lookup",
    "bidict-B006": "set_through_inverse",
    "bidict-B007": "roundtrip",
    "bidict-B008": "atomic_add",
    "bidict-B009": "make_frozen",
    "bidict-B010": "reject_dup",
}


def _ref_atomic(pairs, batch):
    values = list(pairs.values()) + [v for _, v in batch]
    if len(values) != len(set(values)):  # any value collision -> all-or-nothing
        return dict(pairs)
    merged = dict(pairs)
    merged.update(dict(batch))
    return merged


_REF = {
    "bidict-B001": lambda pairs, val: next(k for k, v in pairs.items() if v == val),
    "bidict-B002": lambda pairs: {v: k for k, v in pairs.items()},
    "bidict-B003": None,  # custom: must be a bidict mapping values->keys
    "bidict-B004": lambda pairs, key, val: {**{k: v for k, v in pairs.items() if v != val}, key: val},
    "bidict-B005": lambda pairs, key, val: key,
    "bidict-B006": lambda pairs, key, val: val,
    "bidict-B007": lambda pairs, key: key,
    "bidict-B008": _ref_atomic,
    "bidict-B009": None,  # custom: must be an immutable bidict equal to pairs
    "bidict-B010": lambda pairs, key, val: dict(pairs),
}

_ETYPE = {
    "bidict-B001": str,
    "bidict-B002": dict,
    "bidict-B004": dict,
    "bidict-B005": str,
    "bidict-B006": int,
    "bidict-B007": str,
    "bidict-B008": dict,
    "bidict-B010": dict,
}

INPUTS = {
    "bidict-B001": [({"a": 1, "b": 2}, 2), ({"x": 10, "y": 20}, 10)],
    "bidict-B002": [({"a": 1, "b": 2},), ({"x": 10},)],
    "bidict-B003": [({"a": 1, "b": 2},)],
    "bidict-B004": [({"a": 1}, "c", 1), ({"a": 5, "b": 6}, "z", 5)],
    "bidict-B005": [({"a": 1}, "c", 2), ({"x": 5}, "y", 9)],
    "bidict-B006": [({"a": 1}, "c", 2), ({"x": 5}, "y", 9)],
    "bidict-B007": [({"a": 1, "b": 2}, "a"), ({"x": 10}, "x")],
    "bidict-B008": [({"a": 1}, [("x", 2), ("y", 1)]), ({"a": 1}, [("x", 2), ("z", 3)])],
    "bidict-B009": [({"a": 1, "b": 2},)],
    "bidict-B010": [({"a": 1}, "c", 1), ({"a": 5, "b": 6}, "z", 6)],
}


def _make_check(tid):
    ref, etype = _REF[tid], _ETYPE[tid]

    def check(ret, trace, args):
        expected = ref(*args)
        if type(ret) is not etype:
            return _fail("wrong_output_structure",
                         f"returned a {type(ret).__name__}; expected a {etype.__name__} ({expected!r})")
        if ret != expected:
            return _fail("wrong_output", f"returned {ret!r}, expected {expected!r}")
        return _ok()

    return check


def _check_inverse_view(ret, trace, args):
    (pairs,) = args
    expected = {v: k for k, v in pairs.items()}
    if type(ret) is not bidict:
        return _fail("wrong_output_structure",
                     f"returned a {type(ret).__name__}; expected a bidict (the inverse view)")
    if dict(ret) != expected:
        return _fail("wrong_output", f"returned {dict(ret)!r}, expected the inverse {expected!r}")
    return _ok()


def _check_frozen(ret, trace, args):
    (pairs,) = args
    try:
        content = dict(ret)
    except Exception:
        return _fail("wrong_output_structure", f"returned a {type(ret).__name__}; expected a (frozen) bidict")
    if content != dict(pairs):
        return _fail("wrong_output", f"returned {content!r}, expected {dict(pairs)!r}")
    try:
        ret["__probe__"] = object()
        return _fail("obligation_unmet", "the returned bidict is MUTABLE; an immutable frozenbidict was required")
    except Exception:
        return _ok()


CHECKS = {tid: _make_check(tid) for tid in FUNC_NAMES if tid not in ("bidict-B003", "bidict-B009")}
CHECKS["bidict-B003"] = _check_inverse_view
CHECKS["bidict-B009"] = _check_frozen


ANCHORS = {
    "bidict-B001": [
        ("canonical_inv", """
def key_for(pairs, val):
    return bidict(pairs).inv[val]
""", True),
        ("violation_forward_index", """
def key_for(pairs, val):
    return bidict(pairs)[val]
""", {"runtime_error"}),
    ],
    "bidict-B002": [
        ("canonical_invert", """
def invert(pairs):
    return dict(bidict(pairs).inv)
""", True),
        ("violation_no_invert", """
def invert(pairs):
    return dict(bidict(pairs))
""", {"wrong_output"}),
    ],
    "bidict-B003": [
        ("canonical_inv_bidict", """
def inverse_view(pairs):
    return bidict(pairs).inv
""", True),
        ("violation_plain_dict", """
def inverse_view(pairs):
    return {v: k for k, v in pairs.items()}
""", {"wrong_output_structure"}),
    ],
    "bidict-B004": [
        ("canonical_forceput", """
def remap(pairs, key, val):
    b = bidict(pairs)
    b.forceput(key, val)
    return dict(b)
""", True),
        ("violation_setitem", """
def remap(pairs, key, val):
    b = bidict(pairs)
    b[key] = val
    return dict(b)
""", {"runtime_error"}),
    ],
    "bidict-B005": [
        ("canonical_same", """
def add_then_lookup(pairs, key, val):
    b = bidict(pairs)
    b[key] = val
    return b.inv[val]
""", True),
        ("violation_fresh", """
def add_then_lookup(pairs, key, val):
    b = bidict(pairs)
    b[key] = val
    return bidict(pairs).inv[val]
""", {"runtime_error"}),
    ],
    "bidict-B006": [
        ("canonical_via_inv", """
def set_through_inverse(pairs, key, val):
    b = bidict(pairs)
    b.inv[val] = key
    return b[key]
""", True),
        ("violation_fresh", """
def set_through_inverse(pairs, key, val):
    b = bidict(pairs)
    b.inv[val] = key
    return bidict(pairs)[key]
""", {"runtime_error"}),
    ],
    "bidict-B007": [
        ("canonical_roundtrip", """
def roundtrip(pairs, key):
    b = bidict(pairs)
    return b.inv[b[key]]
""", True),
        ("violation_double_forward", """
def roundtrip(pairs, key):
    b = bidict(pairs)
    return b[b[key]]
""", {"runtime_error"}),
    ],
    "bidict-B008": [
        ("canonical_putall", """
def atomic_add(pairs, batch):
    b = bidict(pairs)
    try:
        b.putall(batch)
    except DuplicationError:
        pass
    return dict(b)
""", True),
        ("violation_loop", """
def atomic_add(pairs, batch):
    b = bidict(pairs)
    try:
        for k, v in batch:
            b[k] = v
    except DuplicationError:
        pass
    return dict(b)
""", {"wrong_output"}),
    ],
    "bidict-B009": [
        ("canonical_frozen", """
def make_frozen(pairs):
    return frozenbidict(pairs)
""", True),
        ("violation_mutable", """
def make_frozen(pairs):
    return bidict(pairs)
""", {"obligation_unmet"}),
    ],
    "bidict-B010": [
        ("canonical_reject", """
def reject_dup(pairs, key, val):
    b = bidict(pairs)
    try:
        b[key] = val
    except ValueDuplicationError:
        pass
    return dict(b)
""", True),
        ("violation_forceput", """
def reject_dup(pairs, key, val):
    b = bidict(pairs)
    b.forceput(key, val)
    return dict(b)
""", {"wrong_output"}),
    ],
}


TASKS = [
    {"task_id": "bidict-B001", "pair_type": "return-flow", "difficulty": "easy",
     "func": "key_for",
     "task": "Write function key_for(pairs, val). pairs is a dict. Build a bidict from it and return the KEY that maps to val (a reverse lookup)."},
    {"task_id": "bidict-B002", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "invert",
     "task": "Write function invert(pairs). pairs is a dict. Build a bidict and return its inverse mapping (value -> key) as a plain dict."},
    {"task_id": "bidict-B003", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "inverse_view",
     "task": "Write function inverse_view(pairs). Build a bidict from pairs and return its inverse, which must itself be a bidict mapping each value to its key (not a plain dict)."},
    {"task_id": "bidict-B004", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "remap",
     "task": "Write function remap(pairs, key, val). pairs already maps some existing key to val. Insert key->val into a bidict so it stays a valid 1:1 mapping, replacing (dropping) the old key that held val. Return the resulting plain dict."},
    {"task_id": "bidict-B005", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "add_then_lookup",
     "task": "Write function add_then_lookup(pairs, key, val) where val is a NEW value. Build a bidict, set key->val on it, then return the key for val read back from the SAME bidict via its inverse."},
    {"task_id": "bidict-B006", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "set_through_inverse",
     "task": "Write function set_through_inverse(pairs, key, val) where val is NEW. Build a bidict and add the mapping by assigning through its inverse view (inverse[val] = key); then return b[key] from the SAME bidict."},
    {"task_id": "bidict-B007", "pair_type": "return-flow", "difficulty": "medium",
     "func": "roundtrip",
     "task": "Write function roundtrip(pairs, key). Build a bidict; look up the value for key, then look that value back up through the inverse to recover the key, and return it."},
    {"task_id": "bidict-B008", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "atomic_add",
     "task": "Write function atomic_add(pairs, batch). batch is a list of (key, value) pairs. Add them all to a bidict ATOMICALLY: if any pair would break the 1:1 mapping, NONE of the batch is applied (the bidict is left unchanged). Return the resulting plain dict."},
    {"task_id": "bidict-B009", "pair_type": "lifecycle", "difficulty": "medium",
     "func": "make_frozen",
     "task": "Write function make_frozen(pairs). Return an IMMUTABLE bidict built from pairs -- one that rejects any later modification (mapping the same pairs as the input)."},
    {"task_id": "bidict-B010", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "reject_dup",
     "task": "Write function reject_dup(pairs, key, val) where val is ALREADY used by another key. A bidict cannot map two keys to the same value, so the attempt to add key->val must fail and leave the bidict UNCHANGED (do NOT drop the old key). Return the resulting plain dict."},
]

HELPER_LINE = (
    "bidict, frozenbidict, OrderedBidict (real bidict classes) and "
    "ValueDuplicationError / KeyDuplicationError / DuplicationError are available"
)

API_LIST = """Relevant bidict APIs:
- bidict(data) -> a mutable 1:1 bidirectional mapping; b[key] -> value
- b.inv -> the inverse bidict (maps value -> key); a LIVE view of the same b
- b.forceput(key, value) -> insert, dropping any existing key/value that clashes
- b.putall(items) -> insert many ATOMICALLY (all-or-nothing on any duplicate)
- frozenbidict(data) -> an immutable bidict (rejects modification)
- ValueDuplicationError / KeyDuplicationError / DuplicationError (base) on clashes
"""

RAW_API_DOCS = """Retrieved bidict documentation snippets:
- A bidict is a bijective (1:1) mapping: keys are unique AND values are unique.
- Plain item assignment b[key]=value raises ValueDuplicationError if value is
  already mapped to a different key (use forceput to overwrite instead).
- b.inv is the inverse mapping (value->key); it is a view onto the SAME bidict, so
  mutating one side is reflected on the other.
- forceput(key, value) inserts key->value, removing whatever existing key or value
  would otherwise collide.
- putall(items) is atomic: if any item raises a DuplicationError, the whole batch
  is rolled back and the bidict is left unchanged.
- frozenbidict is an immutable bidict; any attempt to modify it raises.
"""

# B3*: ABSTRACT call sequence -- API/order only; constraint-bearing choices
# (forceput vs []/put, .inv direction, same-object identity, putall atomicity,
# frozenbidict immutability) left to the model.
ORACLE_API_SEQUENCES = {
    "bidict-B001": "Abstract API sequence (call order only):\nb = bidict(pairs); then look up the key for a value",
    "bidict-B002": "Abstract API sequence (call order only):\nb = bidict(pairs); then produce the value->key mapping as a plain dict",
    "bidict-B003": "Abstract API sequence (call order only):\nb = bidict(pairs); then obtain the inverse mapping",
    "bidict-B004": "Abstract API sequence (call order only):\nb = bidict(pairs); insert (key, val) handling the existing-value case; then dict(b)",
    "bidict-B005": "Abstract API sequence (call order only):\nb = bidict(pairs); write to b; then read via the inverse (same b)",
    "bidict-B006": "Abstract API sequence (call order only):\nb = bidict(pairs); write via the inverse; then read forward (same b)",
    "bidict-B007": "Abstract API sequence (call order only):\nb = bidict(pairs); then round-trip key -> value -> key",
    "bidict-B008": "Abstract API sequence (call order only):\nb = bidict(pairs); attempt a batch insert handling conflicts; then dict(b)",
    "bidict-B009": "Abstract API sequence (call order only):\nbuild an immutable bidict from pairs",
    "bidict-B010": "Abstract API sequence (call order only):\nb = bidict(pairs); insert (key, val) handling a value conflict; then dict(b)",
}

# Gold pair rules MANUALLY EXTRACTED from bidict's real semantics.
GOLD_PAIR_RULES = """Relevant API Pair Rules (extracted from bidict semantics):
1. b[key]=value / put vs forceput -> value uniqueness
Relation: param-dependency
Constraint: A bidict enforces UNIQUE values. Plain b[key]=value (and b.put) RAISE ValueDuplicationError when value is already mapped to another key. To insert anyway and DROP the old colliding mapping, use b.forceput(key, value). The method you choose decides whether the old mapping survives (put/[]=: keep & raise; forceput: replace).
Usage pattern:
b = bidict(pairs); b.forceput(key, val); dict(b)   # old holder of val dropped

2. bidict is 1:1 ; b.inv is a bidict
Relation: config-return-contract
Constraint: bidict(data) returns a bijective mapping; its inverse b.inv is ITSELF a bidict (value -> key), not a plain dict. Use b.inv (or dict(b.inv)) to get the value->key direction; dict(b) is still key->value.
Usage pattern:
b = bidict(pairs); inv = b.inv          # a bidict mapping value -> key
dict(b.inv)                              # value->key as a plain dict

3. reverse lookup goes through b.inv
Relation: return-flow
Constraint: To get the key for a value you must index into the inverse: b.inv[value]. Indexing the forward bidict by a value (b[value]) is the wrong direction and raises KeyError.
Usage pattern:
bidict(pairs).inv[value]

4. b.inv is a live view of the SAME bidict
Relation: shared-receiver
Constraint: b.inv is not a copy: it is a view onto the SAME bidict, so mutating b is visible via b.inv and vice versa (b.inv[value]=key adds key->value to b). A freshly rebuilt bidict does not see mutations made to a different instance.
Usage pattern:
b = bidict(pairs); b[key] = val; b.inv[val]   # same b reflects the write

5. putall is atomic ; frozenbidict is immutable
Relation: lifecycle
Constraint: b.putall(items) is ALL-OR-NOTHING: if any item raises a DuplicationError the whole batch is rolled back and b is unchanged (a per-item loop of b[k]=v would instead apply the items before the clash). frozenbidict(data) is immutable and raises on any modification.
Usage pattern:
b = bidict(pairs)
try:
    b.putall(batch)
except DuplicationError:
    pass            # b unchanged if any pair clashed
"""
