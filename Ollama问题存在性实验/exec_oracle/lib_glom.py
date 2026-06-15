#!/usr/bin/env python3
"""Benchmark module: glom (REAL low-popularity library, v25.x; nested-data access domain).

Gold pair rules are MANUALLY EXTRACTED from glom's real semantics. Covered pair
types match what glom really exhibits (return-flow / config-return-contract /
param-dependency / shared-receiver); glom is otherwise stateless, so lifecycle and
completion-obligation are absent (reported, not faked). Judged on observable
behavior (return type/value, raised errors, target mutation), never source inspection.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path as _Path

_VENDOR = str(_Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

import fixture_glom as fx  # noqa: E402
from glom import glom  # noqa: E402  (for reference outputs only)
from fixture_glom import make_namespace  # noqa: F401,E402

NAME = "glom"
reset = fx.reset
get_trace = fx.get_trace


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


FUNC_NAMES = {
    "glom-G001": "deep_get",
    "glom-G002": "apply_after_nav",
    "glom-G003": "pluck_list",
    "glom-G004": "restructure",
    "glom-G005": "safe_get",
    "glom-G006": "coalesce_get",
    "glom-G007": "assign_in_place",
    "glom-G008": "assign_return_target",
    "glom-G009": "first_item",
    "glom-G010": "summarize",
}


def _nav(data, dotted):
    cur = data
    for part in dotted.split("."):
        cur = cur[int(part)] if part.lstrip("-").isdigit() else cur[part]
    return cur


_REF = {
    "glom-G001": lambda data, path: _nav(data, path),
    "glom-G002": lambda data: sum(data["nums"]),
    "glom-G003": lambda data: [it["v"] for it in data["items"]],
    "glom-G004": lambda data: {"name": _nav(data, "a.b"), "n": len(data["items"])},
    "glom-G005": lambda data, path: (_nav(data, path) if _has(data, path) else -1),
    "glom-G006": lambda data: data.get("primary", data.get("backup")),
    "glom-G007": None,  # custom: in-place mutation of the SAME target
    "glom-G008": None,  # custom: returns the SAME target object
    "glom-G009": lambda data: data["items"][0]["v"],
    "glom-G010": lambda data: {"total": sum(data["nums"]), "count": len(data["nums"])},
}


def _has(data, dotted):
    try:
        _nav(data, dotted)
        return True
    except Exception:
        return False


_ETYPE = {
    "glom-G001": int,
    "glom-G002": int,
    "glom-G003": list,
    "glom-G004": dict,
    "glom-G005": int,
    "glom-G006": int,
    "glom-G009": int,
    "glom-G010": dict,
}

INPUTS = {
    "glom-G001": [({"a": {"b": {"c": 7}}}, "a.b.c"), ({"x": {"y": 5}}, "x.y")],
    "glom-G002": [({"nums": [1, 2, 3]},), ({"nums": [10, 20]},)],
    "glom-G003": [({"items": [{"v": 1}, {"v": 2}]},)],
    "glom-G004": [({"a": {"b": "hi"}, "items": [1, 2, 3]},)],
    "glom-G005": [({"a": {"b": 1}}, "a.b"), ({"a": {"b": 1}}, "a.zzz")],
    "glom-G006": [({"backup": 5},), ({"primary": 9, "backup": 5},)],
    "glom-G007": [({"a": {"b": 1}}, "a.b", 99), ({"x": {"y": 2}}, "x.y", 7)],
    "glom-G008": [({"a": {"b": 1}}, "a.b", 99)],
    "glom-G009": [({"items": [{"v": 10}, {"v": 20}]},), ({"items": [{"v": 3}]},)],
    "glom-G010": [({"nums": [1, 2, 3]},)],
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


def _check_assign_in_place(ret, trace, args):
    data, path, val = args
    if ret != val:
        return _fail("wrong_output", f"returned {ret!r}, expected {val!r}")
    if _nav(data, path) != val:
        return _fail("wrong_output",
                     "the input target was not mutated in place (Assign must run on the SAME object)")
    return _ok()


def _check_assign_return_target(ret, trace, args):
    data, path, val = args
    if ret is not data:
        return _fail("wrong_output",
                     "must return the SAME target object that was assigned (got a different object)")
    if _nav(ret, path) != val:
        return _fail("wrong_output", f"target's {path} is {_nav(ret, path)!r}, expected {val!r}")
    return _ok()


CHECKS = {tid: _make_check(tid) for tid in FUNC_NAMES if tid not in ("glom-G007", "glom-G008")}
CHECKS["glom-G007"] = _check_assign_in_place
CHECKS["glom-G008"] = _check_assign_return_target


ANCHORS = {
    "glom-G001": [
        ("canonical_path", """
def deep_get(data, path):
    return glom(data, path)
""", True),
        ("violation_literal_key", """
def deep_get(data, path):
    return data[path]
""", {"runtime_error"}),
    ],
    "glom-G002": [
        ("canonical_chain", """
def apply_after_nav(data):
    return glom(data, ('nums', sum))
""", True),
        ("violation_no_transform", """
def apply_after_nav(data):
    return glom(data, 'nums')
""", {"wrong_output_structure"}),
    ],
    "glom-G003": [
        ("canonical_list_spec", """
def pluck_list(data):
    return glom(data, ('items', ['v']))
""", True),
        ("violation_no_list", """
def pluck_list(data):
    return glom(data, ('items', 'v'))
""", {"runtime_error"}),
    ],
    "glom-G004": [
        ("canonical_dict_spec", """
def restructure(data):
    return glom(data, {'name': 'a.b', 'n': ('items', len)})
""", True),
        ("violation_scalar", """
def restructure(data):
    return glom(data, 'a.b')
""", {"wrong_output_structure"}),
    ],
    "glom-G005": [
        ("canonical_default", """
def safe_get(data, path):
    return glom(data, path, default=-1)
""", True),
        ("violation_no_default", """
def safe_get(data, path):
    return glom(data, path)
""", {"runtime_error"}),
    ],
    "glom-G006": [
        ("canonical_coalesce", """
def coalesce_get(data):
    return glom(data, Coalesce('primary', 'backup'))
""", True),
        ("violation_primary_only", """
def coalesce_get(data):
    return glom(data, 'primary')
""", {"runtime_error"}),
    ],
    "glom-G007": [
        ("canonical_assign_same", """
def assign_in_place(data, path, val):
    glom(data, Assign(path, val))
    return glom(data, path)
""", True),
        ("violation_copy", """
def assign_in_place(data, path, val):
    import copy
    d = copy.deepcopy(data)
    glom(d, Assign(path, val))
    return glom(d, path)
""", {"wrong_output"}),
    ],
    "glom-G008": [
        ("canonical_return_target", """
def assign_return_target(data, path, val):
    return glom(data, Assign(path, val))
""", True),
        ("violation_return_copy", """
def assign_return_target(data, path, val):
    import copy
    d = copy.deepcopy(data)
    glom(d, Assign(path, val))
    return d
""", {"wrong_output"}),
    ],
    "glom-G009": [
        ("canonical_index_path", """
def first_item(data):
    return glom(data, 'items.0.v')
""", True),
        ("violation_no_index", """
def first_item(data):
    return glom(data, 'items.v')
""", {"runtime_error"}),
    ],
    "glom-G010": [
        ("canonical_dict_spec", """
def summarize(data):
    return glom(data, {'total': ('nums', sum), 'count': ('nums', len)})
""", True),
        ("violation_scalar", """
def summarize(data):
    return glom(data, ('nums', sum))
""", {"wrong_output_structure"}),
    ],
}


TASKS = [
    {"task_id": "glom-G001", "pair_type": "return-flow", "difficulty": "easy",
     "func": "deep_get",
     "task": "Write function deep_get(data, path). path is a dotted string like 'a.b.c'. Return the value at that nested path inside data (navigate through the nested dicts)."},
    {"task_id": "glom-G002", "pair_type": "return-flow", "difficulty": "medium",
     "func": "apply_after_nav",
     "task": "Write function apply_after_nav(data). data has a 'nums' list of integers. Navigate to data['nums'] and return their SUM (a single int) -- in one spec that navigates then aggregates."},
    {"task_id": "glom-G003", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "pluck_list",
     "task": "Write function pluck_list(data). data has a list data['items'] of dicts each with a 'v'. Return the LIST of every item's 'v' value (output must be a list)."},
    {"task_id": "glom-G004", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "restructure",
     "task": "Write function restructure(data). data has data['a']['b'] (a string) and a list data['items']. Return a NEW dict {'name': <data.a.b>, 'n': <number of items>} -- the output shape is a dict you specify."},
    {"task_id": "glom-G005", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "safe_get",
     "task": "Write function safe_get(data, path). path is a dotted string that MAY be missing. Return the value at that path, or -1 if the path is absent (it must NOT raise)."},
    {"task_id": "glom-G006", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "coalesce_get",
     "task": "Write function coalesce_get(data). Return data's 'primary' value if present, otherwise fall back to its 'backup' value -- in a single spec that tries the candidates in order."},
    {"task_id": "glom-G007", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "assign_in_place",
     "task": "Write function assign_in_place(data, path, val). Set the value at the dotted path INSIDE the given data object (mutating it in place), then return the value read back from that SAME data."},
    {"task_id": "glom-G008", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "assign_return_target",
     "task": "Write function assign_return_target(data, path, val). Assign val at the dotted path on data and return the target object itself -- it must be the SAME object that was passed in (mutated), not a copy."},
    {"task_id": "glom-G009", "pair_type": "return-flow", "difficulty": "medium",
     "func": "first_item",
     "task": "Write function first_item(data). data has a list data['items'] of dicts each with a 'v'. Return the 'v' of the FIRST item by navigating through the list index in one path."},
    {"task_id": "glom-G010", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "summarize",
     "task": "Write function summarize(data). data has a 'nums' list of integers. Return a NEW dict {'total': <sum>, 'count': <length>} computed from data['nums'] (the output is a dict you specify)."},
]

HELPER_LINE = (
    "glom, Coalesce, Assign, T, Path and PathAccessError (real glom names) are available"
)

API_LIST = """Relevant glom APIs:
- glom(target, spec) -> pull data out of target according to spec
- spec 'a.b.c' (a dotted string) navigates NESTED structures (incl. list indices like 'items.0.v')
- spec ('a.b', subspec) chains: navigate to 'a.b' then apply subspec (e.g. sum, len, or ['field'])
- spec ['field'] over an iterable returns a LIST of that field; spec {...} returns a dict of that shape
- glom(target, spec, default=X) returns X instead of raising when the path is missing
- Coalesce(s1, s2, ...) tries each spec in order, using the first that succeeds
- glom(target, Assign('a.b', value)) sets target's nested path IN PLACE and returns target
- PathAccessError is raised when a path cannot be accessed (and no default/Coalesce applies)
"""

RAW_API_DOCS = """Retrieved glom documentation snippets:
- A dotted-string spec is a Path: 'a.b.c' walks target['a']['b']['c']; numeric segments index
  into sequences ('items.0.v'). A literal target['a.b.c'] does NOT navigate.
- A tuple spec is a chain: each element is applied to the output of the previous one, so
  ('nums', sum) navigates to nums then sums it.
- The SHAPE of the spec dictates the SHAPE of the output: a list spec ['v'] maps over an
  iterable and yields a list; a dict spec {'k': subspec, ...} yields a dict with those keys.
- Missing paths raise PathAccessError unless you pass default= or wrap candidates in
  Coalesce(...), which returns the first candidate that resolves.
- Assign('path', value) is a spec that MUTATES the target in place (and returns the target).
"""

ORACLE_API_SEQUENCES = {
    "glom-G001": "Oracle API sequence:\nglom(data, path)   # dotted path navigates nested dicts",
    "glom-G002": "Oracle API sequence:\nglom(data, ('nums', sum))   # navigate then aggregate",
    "glom-G003": "Oracle API sequence:\nglom(data, ('items', ['v']))   # list spec -> list output",
    "glom-G004": "Oracle API sequence:\nglom(data, {'name': 'a.b', 'n': ('items', len)})   # dict spec -> dict",
    "glom-G005": "Oracle API sequence:\nglom(data, path, default=-1)   # missing -> -1, no raise",
    "glom-G006": "Oracle API sequence:\nglom(data, Coalesce('primary', 'backup'))   # first that resolves",
    "glom-G007": "Oracle API sequence:\nglom(data, Assign(path, val)); glom(data, path)   # same target",
    "glom-G008": "Oracle API sequence:\nglom(data, Assign(path, val))   # returns the same target",
    "glom-G009": "Oracle API sequence:\nglom(data, 'items.0.v')   # path with a list index",
    "glom-G010": "Oracle API sequence:\nglom(data, {'total': ('nums', sum), 'count': ('nums', len)})",
}

# Gold pair rules MANUALLY EXTRACTED from glom's real semantics.
GOLD_PAIR_RULES = """Relevant API Pair Rules (extracted from glom semantics):
1. glom(target, spec) ; spec shape -> output shape
Relation: config-return-contract
Constraint: The SHAPE of the spec dictates the SHAPE of the return value. A list spec ['field'] maps over an iterable and returns a LIST; a dict spec {'k': subspec, ...} returns a DICT with those keys; a bare string/tuple returns a single (scalar) value. To get a list out, wrap the subspec in [ ]; to get a dict out, use a { } spec.
Usage pattern:
glom(data, ('items', ['v']))                 # -> a list
glom(data, {'name': 'a.b', 'n': ('items', len)})   # -> a dict

2. dotted path / tuple chain navigation
Relation: return-flow
Constraint: A dotted-string spec NAVIGATES nested structures (target['a']['b']['c'] for 'a.b.c', and list indices for 'items.0.v') -- a literal target['a.b.c'] does NOT. A tuple spec is a chain: each element is applied to the previous result, e.g. ('nums', sum) navigates to nums and then sums it.
Usage pattern:
glom(data, 'a.b.c')          # navigates nested dicts
glom(data, ('nums', sum))    # navigate then transform

3. default= / Coalesce on missing paths
Relation: param-dependency
Constraint: A missing path raises PathAccessError. Passing default=X to glom makes it return X instead of raising; Coalesce(s1, s2, ...) tries each candidate spec in order and returns the first that resolves. Which one you use decides the missing-path behavior.
Usage pattern:
glom(data, path, default=-1)
glom(data, Coalesce('primary', 'backup'))

4. Assign mutates the SAME target
Relation: shared-receiver
Constraint: glom(target, Assign('a.b', value)) sets the nested path on the SAME target object IN PLACE (and returns that target). Reads on that same target reflect the assignment; a copy of the target does not.
Usage pattern:
glom(data, Assign(path, val)); glom(data, path)   # same data reflects the write
"""
