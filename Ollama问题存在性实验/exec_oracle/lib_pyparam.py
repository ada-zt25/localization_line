#!/usr/bin/env python3
"""Benchmark module: pyparam (REAL low-popularity library, pwwang v0.5.4; arg-parsing domain).

Gold pair rules manually extracted from the real pyparam API/behavior and
verified at runtime (automated-extraction P/R = future work). Covered pair
types: config-return-contract (type= fixes the parsed value's TYPE), param-
dependency (required / default / presence of args), return-flow (parse ->
Namespace -> access), shared-receiver (params must be added to the SAME Params
that is parsed). Discipline enforced by the real lib: fresh Params + single
parse + multi-char option names + complete valid args. No lifecycle/obligation.
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

import fixture_pyparam as fx
from fixture_pyparam import make_namespace  # noqa: F401

NAME = "pyparam"
reset = fx.reset
get_trace = fx.get_trace


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


FUNC_NAMES = {
    "pyparam-P001": "parse_int",
    "pyparam-P002": "parse_float",
    "pyparam-P003": "parse_str",
    "pyparam-P004": "parse_list",
    "pyparam-P005": "required_present",
    "pyparam-P006": "default_when_omitted",
    "pyparam-P007": "parse_given",
    "pyparam-P008": "parse_then_attr",
    "pyparam-P009": "parse_two_fields",
    "pyparam-P010": "parse_then_use",
    "pyparam-P011": "param_on_same_params",
    "pyparam-P012": "two_params_same",
}

_REF = {
    "pyparam-P001": lambda args: int(args[-1]),
    "pyparam-P002": lambda args: float(args[-1]),
    "pyparam-P003": lambda args: str(args[-1]),
    "pyparam-P004": lambda args: [args[i] for i in range(1, len(args), 2)],
    "pyparam-P005": lambda args: int(args[-1]),
    "pyparam-P006": lambda args: "D",
    "pyparam-P007": lambda args: int(args[-1]),
    "pyparam-P008": lambda args: int(args[-1]),
    "pyparam-P009": lambda args: (int(args[1]), args[3]),
    "pyparam-P010": lambda args: int(args[-1]) * 2,
    "pyparam-P011": lambda args: int(args[-1]),
    "pyparam-P012": lambda args: (int(args[1]), args[3]),
}

_ETYPE = {
    "pyparam-P001": int, "pyparam-P002": float, "pyparam-P003": str,
    "pyparam-P004": list, "pyparam-P005": int, "pyparam-P006": str,
    "pyparam-P007": int, "pyparam-P008": int, "pyparam-P009": tuple,
    "pyparam-P010": int, "pyparam-P011": int, "pyparam-P012": tuple,
}

INPUTS = {
    "pyparam-P001": [(["--count", "7"],), (["--count", "3"],)],
    "pyparam-P002": [(["--ratio", "1.5"],)],
    "pyparam-P003": [(["--name", "7"],)],
    "pyparam-P004": [(["--items", "a", "--items", "b"],)],
    "pyparam-P005": [(["--rr", "9"],)],
    "pyparam-P006": [(["--count", "1"],)],
    "pyparam-P007": [(["--count", "7"],), (["--count", "4"],)],
    "pyparam-P008": [(["--count", "7"],)],
    "pyparam-P009": [(["--count", "3", "--label", "hi"],)],
    "pyparam-P010": [(["--count", "6"],)],
    "pyparam-P011": [(["--count", "7"],)],
    "pyparam-P012": [(["--count", "3", "--label", "hi"],)],
}


def _make_check(tid):
    ref, etype = _REF[tid], _ETYPE[tid]

    def check(ret, trace, args):
        expected = ref(*args)
        if type(ret) is not etype:
            return _fail("wrong_output_structure",
                         f"returned a {type(ret).__name__}; expected a {etype.__name__} ({expected!r})")
        if (tuple(ret) if etype is tuple else ret) != (tuple(expected) if etype is tuple else expected):
            return _fail("wrong_output", f"returned {ret!r}, expected {expected!r}")
        return _ok()

    return check


CHECKS = {tid: _make_check(tid) for tid in FUNC_NAMES}


ANCHORS = {
    "pyparam-P001": [
        ("canonical_int", """
def parse_int(args):
    p = Params()
    p.add_param('count', type='int')
    return p.parse(args).count
""", True),
        ("violation_str_type", """
def parse_int(args):
    p = Params()
    p.add_param('count', type='str')
    return p.parse(args).count
""", {"wrong_output_structure"}),
    ],
    "pyparam-P002": [
        ("canonical_float", """
def parse_float(args):
    p = Params()
    p.add_param('ratio', type='float')
    return p.parse(args).ratio
""", True),
        ("violation_str_type", """
def parse_float(args):
    p = Params()
    p.add_param('ratio', type='str')
    return p.parse(args).ratio
""", {"wrong_output_structure"}),
    ],
    "pyparam-P003": [
        ("canonical_str", """
def parse_str(args):
    p = Params()
    p.add_param('name', type='str')
    return p.parse(args).name
""", True),
        ("violation_int_type", """
def parse_str(args):
    p = Params()
    p.add_param('name', type='int')
    return p.parse(args).name
""", {"wrong_output_structure"}),
    ],
    "pyparam-P004": [
        ("canonical_list", """
def parse_list(args):
    p = Params()
    p.add_param('items', type='list', default=[])
    return p.parse(args).items
""", True),
        ("violation_str_type", """
def parse_list(args):
    p = Params()
    p.add_param('items', type='str')
    return p.parse(args).items
""", {"wrong_output_structure", "wrong_output"}),
    ],
    "pyparam-P005": [
        ("canonical_required_present", """
def required_present(args):
    p = Params()
    p.add_param('rr', type='int', required=True)
    return p.parse(args).rr
""", True),
        ("violation_omit_required", """
def required_present(args):
    p = Params()
    p.add_param('rr', type='int', required=True)
    return p.parse([]).rr
""", {"runtime_error"}),
    ],
    "pyparam-P006": [
        ("canonical_default", """
def default_when_omitted(args):
    p = Params()
    p.add_param('count', type='int', default=9)
    p.add_param('label', type='str', default='D')
    return p.parse(args).label
""", True),
        ("violation_no_default", """
def default_when_omitted(args):
    p = Params()
    p.add_param('count', type='int', default=9)
    p.add_param('label', type='str')
    return p.parse(args).label
""", {"wrong_output", "wrong_output_structure"}),
    ],
    "pyparam-P007": [
        ("canonical_given", """
def parse_given(args):
    p = Params()
    p.add_param('count', type='int', default=0)
    return p.parse(args).count
""", True),
        ("violation_parse_empty", """
def parse_given(args):
    p = Params()
    p.add_param('count', type='int', default=0)
    return p.parse([]).count
""", {"runtime_error", "wrong_output"}),
    ],
    "pyparam-P008": [
        ("canonical_attr", """
def parse_then_attr(args):
    p = Params()
    p.add_param('count', type='int')
    ns = p.parse(args)
    return ns.count
""", True),
        ("violation_return_ns", """
def parse_then_attr(args):
    p = Params()
    p.add_param('count', type='int')
    return p.parse(args)
""", {"wrong_output_structure"}),
    ],
    "pyparam-P009": [
        ("canonical_two", """
def parse_two_fields(args):
    p = Params()
    p.add_param('count', type='int')
    p.add_param('label', type='str')
    ns = p.parse(args)
    return (ns.count, ns.label)
""", True),
        ("violation_one", """
def parse_two_fields(args):
    p = Params()
    p.add_param('count', type='int')
    p.add_param('label', type='str')
    ns = p.parse(args)
    return ns.count
""", {"wrong_output_structure"}),
    ],
    "pyparam-P010": [
        ("canonical_use", """
def parse_then_use(args):
    p = Params()
    p.add_param('count', type='int')
    return p.parse(args).count * 2
""", True),
        ("violation_constant", """
def parse_then_use(args):
    p = Params()
    p.add_param('count', type='int')
    p.parse(args)
    return 0
""", {"wrong_output"}),
    ],
    "pyparam-P011": [
        ("canonical_same_params", """
def param_on_same_params(args):
    p = Params()
    p.add_param('count', type='int')
    return p.parse(args).count
""", True),
        ("violation_parse_other", """
def param_on_same_params(args):
    p = Params()
    p.add_param('count', type='int')
    q = Params()
    return q.parse(args).count
""", {"runtime_error"}),
    ],
    "pyparam-P012": [
        ("canonical_both_same", """
def two_params_same(args):
    p = Params()
    p.add_param('count', type='int')
    p.add_param('label', type='str')
    ns = p.parse(args)
    return (ns.count, ns.label)
""", True),
        ("violation_label_other", """
def two_params_same(args):
    p = Params()
    p.add_param('count', type='int')
    q = Params()
    q.add_param('label', type='str')
    ns = p.parse(args)
    return (ns.count, ns.label)
""", {"runtime_error"}),
    ],
}


TASKS = [
    {"task_id": "pyparam-P001", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "parse_int",
     "task": "Write function parse_int(args). args is a list like ['--count','7']. Build a Params with an integer parameter 'count', parse args, and return the parsed count as an int."},
    {"task_id": "pyparam-P002", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "parse_float",
     "task": "Write function parse_float(args). args is like ['--ratio','1.5']. Build a Params with a float parameter 'ratio', parse args, and return the parsed ratio as a float."},
    {"task_id": "pyparam-P003", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "parse_str",
     "task": "Write function parse_str(args). args is like ['--name','7']. Build a Params with a string parameter 'name', parse args, and return the parsed name as a str (the literal text, not an int)."},
    {"task_id": "pyparam-P004", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "parse_list",
     "task": "Write function parse_list(args). args repeats an option, e.g. ['--items','a','--items','b']. Build a Params with a list parameter 'items', parse args, and return the list of all values ['a','b']."},
    {"task_id": "pyparam-P005", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "required_present",
     "task": "Write function required_present(args). args is like ['--rr','9']. Build a Params with a REQUIRED integer parameter 'rr', parse args, and return its value."},
    {"task_id": "pyparam-P006", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "default_when_omitted",
     "task": "Write function default_when_omitted(args). args sets 'count' but omits 'label' (e.g. ['--count','1']). Build a Params with 'count' and a 'label' parameter whose default is 'D', parse args, and return ns.label (which should be the default 'D')."},
    {"task_id": "pyparam-P007", "pair_type": "param-dependency", "difficulty": "easy",
     "func": "parse_given",
     "task": "Write function parse_given(args). args is like ['--count','7']. Build a Params with integer 'count' (default 0), parse the GIVEN args, and return ns.count (the value from args)."},
    {"task_id": "pyparam-P008", "pair_type": "return-flow", "difficulty": "easy",
     "func": "parse_then_attr",
     "task": "Write function parse_then_attr(args). Build a Params with integer 'count', parse args, and return the count attribute from the resulting Namespace."},
    {"task_id": "pyparam-P009", "pair_type": "return-flow", "difficulty": "medium",
     "func": "parse_two_fields",
     "task": "Write function parse_two_fields(args). args is ['--count','3','--label','hi']. Build a Params with integer 'count' and string 'label', parse args, and return the tuple (ns.count, ns.label) from the Namespace."},
    {"task_id": "pyparam-P010", "pair_type": "return-flow", "difficulty": "medium",
     "func": "parse_then_use",
     "task": "Write function parse_then_use(args). Build a Params with integer 'count', parse args, and return the parsed count multiplied by 2."},
    {"task_id": "pyparam-P011", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "param_on_same_params",
     "task": "Write function param_on_same_params(args). Create a Params, add an integer parameter 'count' to it, then parse args with the SAME Params and return ns.count."},
    {"task_id": "pyparam-P012", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "two_params_same",
     "task": "Write function two_params_same(args). args is ['--count','3','--label','hi']. Add BOTH an integer 'count' and a string 'label' to the SAME Params, parse args, and return (ns.count, ns.label)."},
]

HELPER_LINE = "Params (real pyparam class) and POSITIONAL are available"

API_LIST = """Relevant pyparam APIs:
- Params() ; p.add_param(name, type='str'|'int'|'float'|'bool'|'list', default=None, required=False)
- p.parse(args) -> Namespace      # args is a list of strings; use multi-character option names
- the Namespace exposes parsed values by attribute (ns.count)
"""

RAW_API_DOCS = """Retrieved pyparam documentation snippets:
- add_param(name, type=...) declares an option; the type ('int','float','str','bool','list') fixes the type of the parsed value.
- default= supplies the value used when the option is absent; required=True makes the option mandatory.
- parse(args) consumes a list of argument strings and returns a Namespace; access values by attribute.
- Build a fresh Params and parse once; use multi-character option names (e.g. --count).
"""

ORACLE_API_SEQUENCES = {
    "pyparam-P001": "Oracle API sequence:\nParams -> add_param('count', type='int') -> parse(args).count",
    "pyparam-P002": "Oracle API sequence:\nParams -> add_param('ratio', type='float') -> parse(args).ratio",
    "pyparam-P003": "Oracle API sequence:\nParams -> add_param('name', type='str') -> parse(args).name",
    "pyparam-P004": "Oracle API sequence:\nParams -> add_param('items', type='list') -> parse(args).items",
    "pyparam-P005": "Oracle API sequence:\nParams -> add_param('rr', type='int', required=True) -> parse(args).rr",
    "pyparam-P006": "Oracle API sequence:\nParams -> add_param('label', default='D') -> parse(args).label",
    "pyparam-P007": "Oracle API sequence:\nParams -> add_param('count', type='int') -> parse(args).count",
    "pyparam-P008": "Oracle API sequence:\nParams -> add_param -> ns = parse(args) -> ns.count",
    "pyparam-P009": "Oracle API sequence:\nParams -> add_param x2 -> ns = parse(args) -> (ns.count, ns.label)",
    "pyparam-P010": "Oracle API sequence:\nParams -> add_param('count', type='int') -> parse(args).count * 2",
    "pyparam-P011": "Oracle API sequence:\np = Params(); p.add_param('count') -> p.parse(args).count",
    "pyparam-P012": "Oracle API sequence:\np.add_param('count'); p.add_param('label') -> p.parse(args)",
}

GOLD_PAIR_RULES = """Relevant API Pair Rules (extracted from pyparam API):
1. add_param(type=...) -> parsed value type
Relation: config-return-contract
Constraint: The type= passed to add_param fixes the TYPE of the value parse() returns for that option: type='int'/'float'/'bool'/'list' yield an int/float/bool/list; type='str' (or no type) yields the raw string. To get an int you must declare type='int'.
Usage pattern:
p.add_param('count', type='int'); p.parse(args).count   # an int

2. required= / default= and the given args
Relation: param-dependency
Constraint: A required=True option must be present in args (parsing without it errors/exits); default= provides the value used when the option is omitted; the value otherwise comes from the args you parse.
Usage pattern:
p.add_param('label', type='str', default='D'); p.parse(['--count','1']).label   # 'D'

3. parse -> Namespace access
Relation: return-flow
Constraint: parse(args) RETURNS a Namespace; read values by attribute on that returned Namespace (returning the Namespace itself, or a constant, is wrong).
Usage pattern:
ns = p.parse(args); ns.count

4. add_param and parse on the SAME Params
Relation: shared-receiver
Constraint: A parameter is only recognized by the Params it was add_param'd to; you must parse the SAME Params object that holds the definitions. Parsing a different/empty Params does not know the option.
Usage pattern:
p = Params(); p.add_param('count', type='int'); p.parse(args).count   # same p
"""
