#!/usr/bin/env python3
"""Benchmark module: diot (REAL low-popularity library, pwwang v0.3.4; attr-dict domain).

Gold pair rules are MANUALLY EXTRACTED from diot's real source (each cited to
vendor/diot/*.py for auditability); automated-extraction precision/recall is a
defined follow-up experiment, not fabricated here. Covered pair types match what
diot really exhibits (param-dependency / config-return-contract / return-flow /
shared-receiver / lifecycle); diot has no resource open/close so
completion-obligation is absent (reported, not faked). Judged on observable
behavior (return type/value, frozen-error), never source inspection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

import fixture_diot as fx
from diot import Diot  # noqa: E402  (for reference outputs only)
from diot.utils import DiotFrozenError  # noqa: E402
from fixture_diot import make_namespace  # noqa: F401

NAME = "diot"
reset = fx.reset
get_trace = fx.get_trace


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


FUNC_NAMES = {
    "diot-D001": "access_camel",
    "diot-D002": "access_snake",
    "diot-D003": "get_default",
    "diot-D004": "to_plain_dict",
    "diot-D005": "nested_stays_dict",
    "diot-D006": "nested_is_diot",
    "diot-D007": "nested_chain",
    "diot-D008": "todict_then_index",
    "diot-D009": "set_then_get",
    "diot-D010": "nested_mutate_reflects",
    "diot-D011": "thaw_to_modify",
    "diot-D012": "thaw_is_temporary",
}

_REF = {
    "diot-D001": lambda data: list(data.values())[0],
    "diot-D002": lambda data: list(data.values())[0],
    "diot-D003": lambda data, key: data.get(key, 0),
    "diot-D004": lambda data: data,
    "diot-D005": lambda data: data["x"],
    "diot-D006": lambda data: data["x"],
    "diot-D007": lambda data: data["x"]["y"],
    "diot-D008": lambda data: data["x"]["y"],
    "diot-D009": lambda key, val: val,
    "diot-D010": lambda data, val: val,
    "diot-D011": lambda data, key, val: val,
    "diot-D012": None,  # custom check
}

_ETYPE = {
    "diot-D001": int, "diot-D002": int, "diot-D003": int,
    "diot-D004": dict, "diot-D005": dict, "diot-D006": Diot,
    "diot-D007": int, "diot-D008": int, "diot-D009": int,
    "diot-D010": int, "diot-D011": int,
}

INPUTS = {
    "diot-D001": [({"foo_bar": 7},), ({"foo_bar": 3},)],
    "diot-D002": [({"fooBar": 7},), ({"fooBar": 4},)],
    "diot-D003": [({"a": 1}, "a"), ({"a": 1}, "zzz")],
    "diot-D004": [({"x": {"y": 1}},)],
    "diot-D005": [({"x": {"y": 1}},)],
    "diot-D006": [({"x": {"y": 1}},)],
    "diot-D007": [({"x": {"y": 7}},)],
    "diot-D008": [({"x": {"y": 7}},)],
    "diot-D009": [("a", 5), ("b", 9)],
    "diot-D010": [({"x": {"y": 1}}, 99)],
    "diot-D011": [({"a": 1}, "a", 5)],
    "diot-D012": [({"a": 1}, "a", 5)],
}


def _is_plain(v):
    if isinstance(v, Diot):
        return False
    if type(v) is dict:
        return all(_is_plain(x) for x in v.values())
    if type(v) in (list, tuple):
        return all(_is_plain(x) for x in v)
    return True


def _make_check(tid):
    ref, etype = _REF[tid], _ETYPE[tid]

    def check(ret, trace, args):
        expected = ref(*args)
        if type(ret) is not etype:
            return _fail("wrong_output_structure",
                         f"returned a {type(ret).__name__}; expected a {etype.__name__} ({expected!r})")
        if tid == "diot-D004" and not _is_plain(ret):
            return _fail("wrong_output_structure", "to_dict must return a recursively PLAIN dict (no Diot inside)")
        if ret != expected:
            return _fail("wrong_output", f"returned {ret!r}, expected {expected!r}")
        return _ok()

    return check


def _check_thaw_temporary(ret, trace, args):
    data, key, val = args
    if not isinstance(ret, Diot):
        return _fail("wrong_output_structure", f"returned a {type(ret).__name__}; return the (frozen) diot")
    if ret.get(key) != val:
        return _fail("wrong_output", f"{key!r}={ret.get(key)!r}, expected {val} (set inside thaw())")
    try:
        ret["__probe__"] = 1
        return _fail("obligation_unmet", "the diot is NOT re-frozen after thaw() exits (thaw must be temporary)")
    except DiotFrozenError:
        return _ok()


CHECKS = {tid: _make_check(tid) for tid in FUNC_NAMES if tid != "diot-D012"}
CHECKS["diot-D012"] = _check_thaw_temporary


ANCHORS = {
    "diot-D001": [
        ("canonical_camel", """
def access_camel(data):
    d = Diot(data, diot_transform='camelCase')
    return d.fooBar
""", True),
        ("violation_no_transform", """
def access_camel(data):
    d = Diot(data)
    return d.fooBar
""", {"runtime_error"}),
    ],
    "diot-D002": [
        ("canonical_snake", """
def access_snake(data):
    d = Diot(data, diot_transform='snake_case')
    return d.foo_bar
""", True),
        ("violation_no_transform", """
def access_snake(data):
    d = Diot(data)
    return d.foo_bar
""", {"runtime_error"}),
    ],
    "diot-D003": [
        ("canonical_get_default", """
def get_default(data, key):
    return Diot(data).get(key, 0)
""", True),
        ("violation_index", """
def get_default(data, key):
    return Diot(data)[key]
""", {"runtime_error"}),
    ],
    "diot-D004": [
        ("canonical_to_dict", """
def to_plain_dict(data):
    return Diot(data).to_dict()
""", True),
        ("violation_return_diot", """
def to_plain_dict(data):
    return Diot(data)
""", {"wrong_output_structure"}),
        ("violation_shallow_dict", """
def to_plain_dict(data):
    return dict(Diot(data))
""", {"wrong_output_structure"}),
    ],
    "diot-D005": [
        ("canonical_nest_false", """
def nested_stays_dict(data):
    return Diot(data, diot_nest=False)['x']
""", True),
        ("violation_nest_default", """
def nested_stays_dict(data):
    return Diot(data)['x']
""", {"wrong_output_structure"}),
    ],
    "diot-D006": [
        ("canonical_nest_true", """
def nested_is_diot(data):
    return Diot(data).x
""", True),
        ("violation_nest_false", """
def nested_is_diot(data):
    return Diot(data, diot_nest=False).x
""", {"wrong_output_structure"}),
    ],
    "diot-D007": [
        ("canonical_chain", """
def nested_chain(data):
    return Diot(data).x.y
""", True),
        ("violation_nest_false", """
def nested_chain(data):
    return Diot(data, diot_nest=False).x.y
""", {"runtime_error"}),
    ],
    "diot-D008": [
        ("canonical_todict_index", """
def todict_then_index(data):
    plain = Diot(data).to_dict()
    return plain['x']['y']
""", True),
        ("violation_return_dict", """
def todict_then_index(data):
    return Diot(data).to_dict()
""", {"wrong_output_structure"}),
    ],
    "diot-D009": [
        ("canonical_same_diot", """
def set_then_get(key, val):
    d = Diot()
    d[key] = val
    return d[key]
""", True),
        ("violation_new_diot", """
def set_then_get(key, val):
    d = Diot()
    d[key] = val
    return Diot()[key]
""", {"runtime_error"}),
    ],
    "diot-D010": [
        ("canonical_mutate_same", """
def nested_mutate_reflects(data, val):
    d = Diot(data)
    d.x.y = val
    return d.x.y
""", True),
        ("violation_read_fresh", """
def nested_mutate_reflects(data, val):
    d = Diot(data)
    d.x.y = val
    return Diot(data).x.y
""", {"wrong_output"}),
    ],
    "diot-D011": [
        ("canonical_thaw", """
def thaw_to_modify(data, key, val):
    d = FrozenDiot(data)
    with d.thaw():
        d[key] = val
    return d[key]
""", True),
        ("violation_no_thaw", """
def thaw_to_modify(data, key, val):
    d = FrozenDiot(data)
    d[key] = val
    return d[key]
""", {"runtime_error"}),
    ],
    "diot-D012": [
        ("canonical_thaw_temporary", """
def thaw_is_temporary(data, key, val):
    d = FrozenDiot(data)
    with d.thaw():
        d[key] = val
    return d
""", True),
        ("violation_not_frozen", """
def thaw_is_temporary(data, key, val):
    d = Diot(data)
    d[key] = val
    return d
""", {"obligation_unmet"}),
    ],
}


TASKS = [
    {"task_id": "diot-D001", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "access_camel",
     "task": "Write function access_camel(data). data is a dict with a snake_case key 'foo_bar'. Build a Diot whose keys are accessible in camelCase, and return d.fooBar."},
    {"task_id": "diot-D002", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "access_snake",
     "task": "Write function access_snake(data). data is a dict with a camelCase key 'fooBar'. Build a Diot whose keys are accessible in snake_case, and return d.foo_bar."},
    {"task_id": "diot-D003", "pair_type": "param-dependency", "difficulty": "easy",
     "func": "get_default",
     "task": "Write function get_default(data, key). Build a Diot from data and return the value for key, or 0 if the key is absent (do not raise)."},
    {"task_id": "diot-D004", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "to_plain_dict",
     "task": "Write function to_plain_dict(data). data is a nested dict. Build a Diot from it and return it converted to a recursively PLAIN dict (no Diot anywhere inside)."},
    {"task_id": "diot-D005", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "nested_stays_dict",
     "task": "Write function nested_stays_dict(data). data is {'x': {...}}. Build a Diot configured so nested dicts are NOT converted, and return d['x'] (which must be a plain dict)."},
    {"task_id": "diot-D006", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "nested_is_diot",
     "task": "Write function nested_is_diot(data). data is {'x': {...}}. Build a Diot (default nesting) and return d.x, which must itself be a Diot (so it supports attribute access)."},
    {"task_id": "diot-D007", "pair_type": "return-flow", "difficulty": "medium",
     "func": "nested_chain",
     "task": "Write function nested_chain(data). data is {'x': {'y': N}}. Build a Diot and return d.x.y by chaining attribute access through the nested Diot."},
    {"task_id": "diot-D008", "pair_type": "return-flow", "difficulty": "medium",
     "func": "todict_then_index",
     "task": "Write function todict_then_index(data). data is {'x': {'y': N}}. Build a Diot, convert it to a plain dict, and from that returned dict index ['x']['y'] and return it."},
    {"task_id": "diot-D009", "pair_type": "shared-receiver", "difficulty": "easy",
     "func": "set_then_get",
     "task": "Write function set_then_get(key, val). Create a Diot, set d[key]=val, then read key back from the SAME Diot and return it."},
    {"task_id": "diot-D010", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "nested_mutate_reflects",
     "task": "Write function nested_mutate_reflects(data, val). data is {'x': {'y': ...}}. Build a Diot, set d.x.y = val, then read d.x.y back from the SAME Diot and return it."},
    {"task_id": "diot-D011", "pair_type": "lifecycle", "difficulty": "medium",
     "func": "thaw_to_modify",
     "task": "Write function thaw_to_modify(data, key, val). Build a FrozenDiot from data. A frozen diot rejects modification; use its thaw() context manager to set d[key]=val, then return d[key]."},
    {"task_id": "diot-D012", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "thaw_is_temporary",
     "task": "Write function thaw_is_temporary(data, key, val). Build a FrozenDiot. Inside its thaw() context set d[key]=val; after the context exits the diot must be frozen again. Return the diot."},
]

HELPER_LINE = (
    "Diot, OrderedDiot, FrozenDiot (real diot classes) and DiotFrozenError are available"
)

API_LIST = """Relevant diot APIs:
- Diot(data, diot_transform='safe', diot_nest=True, diot_frozen=False)
- OrderedDiot(...), FrozenDiot(...)
- d.<key> / d[key] attribute & item access; d.get(key, default)
- d.to_dict() -> a plain (recursive) dict
- frozen diot: d.thaw() context manager to temporarily allow modification
- DiotFrozenError is raised when modifying a frozen diot
"""

RAW_API_DOCS = """Retrieved diot documentation snippets:
- diot_transform controls how keys may be accessed: 'safe' (default), 'snake_case', 'camelCase', etc.
- diot_nest controls whether nested dict values are converted to Diot (True, default) or left as plain dicts (False).
- to_dict() returns a recursively converted plain dict.
- A frozen diot (FrozenDiot or diot_frozen=True) raises DiotFrozenError on modification; use the thaw() context manager to make temporary edits, after which it is frozen again.
- d.get(key, default) returns default when the key is absent (item access raises).
"""

ORACLE_API_SEQUENCES = {
    "diot-D001": "Oracle API sequence:\nDiot(data, diot_transform='camelCase') -> d.fooBar",
    "diot-D002": "Oracle API sequence:\nDiot(data, diot_transform='snake_case') -> d.foo_bar",
    "diot-D003": "Oracle API sequence:\nDiot(data) -> d.get(key, 0)",
    "diot-D004": "Oracle API sequence:\nDiot(data) -> d.to_dict()",
    "diot-D005": "Oracle API sequence:\nDiot(data, diot_nest=False) -> d['x']",
    "diot-D006": "Oracle API sequence:\nDiot(data) -> d.x  (a Diot)",
    "diot-D007": "Oracle API sequence:\nDiot(data) -> d.x -> .y",
    "diot-D008": "Oracle API sequence:\nDiot(data) -> d.to_dict() -> ['x']['y']",
    "diot-D009": "Oracle API sequence:\nDiot() -> d[key]=val -> d[key]",
    "diot-D010": "Oracle API sequence:\nDiot(data) -> d.x.y = val -> d.x.y",
    "diot-D011": "Oracle API sequence:\nFrozenDiot(data) -> with d.thaw(): d[key]=val -> d[key]",
    "diot-D012": "Oracle API sequence:\nFrozenDiot(data) -> with d.thaw(): d[key]=val (re-frozen after)",
}

# Gold pair rules MANUALLY EXTRACTED from the real diot source (citations are to
# vendor/diot/diot.py and vendor/diot/utils.py). Automated extraction P/R: future work.
GOLD_PAIR_RULES = """Relevant API Pair Rules (extracted from diot source):
1. Diot(diot_transform=...) -> attribute/key access
Relation: param-dependency
Constraint: The diot_transform argument fixes how keys may be accessed (diot.py: __init__ stores __diot__["transform"], TRANSFORMS maps names). To read a snake_case source key as camelCase you must build Diot(data, diot_transform='camelCase'); to read a camelCase key as snake_case use diot_transform='snake_case'. The default 'safe' does not provide camel/snake aliasing.
Usage pattern:
d = Diot(data, diot_transform='camelCase'); d.fooBar

2. Diot(diot_nest=...) -> nested value type ; .to_dict() -> plain dict
Relation: config-return-contract
Constraint: diot_nest (diot.py: __diot__["nest"], utils.nest) decides the TYPE of nested values: True (default) converts nested dicts to Diot (attribute-accessible); False leaves them plain dict. d.to_dict() (utils.to_dict) returns a RECURSIVELY plain dict, not a Diot.
Usage pattern:
Diot(data, diot_nest=False)['x']   # a plain dict
Diot(data).to_dict()               # recursively plain dict

3. nested access -> further access
Relation: return-flow
Constraint: With nesting on, d.x returns the nested Diot; you chain through that returned Diot to reach d.x.y. With diot_nest=False, d.x is a plain dict and .y attribute access fails.
Usage pattern:
Diot(data).x.y

4. same Diot mutate/read
Relation: shared-receiver
Constraint: Reads reflect writes only on the SAME Diot object; a freshly built Diot from the original data does not see your mutation. (diot.py: __setitem__/__setattr__ mutate self.)
Usage pattern:
d = Diot(data); d.x.y = val; d.x.y   # same d

5. frozen diot -> thaw() context
Relation: lifecycle
Constraint: A frozen diot (FrozenDiot / diot_frozen=True) raises DiotFrozenError on modification (diot.py: __setattr__/__setitem__ check __diot__["frozen"]). Use the thaw() context manager to modify TEMPORARILY; after the with-block exits, the diot is frozen again.
Usage pattern:
d = FrozenDiot(data)
with d.thaw():
    d[key] = val
"""
