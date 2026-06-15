#!/usr/bin/env python3
"""Benchmark module: simpleconf (REAL low-popularity library, pwwang v0.9.3; config domain).

Gold pair rules manually extracted from the real simpleconf API and verified at
runtime (automated-extraction P/R = future work). Covered pair types:
param-dependency (merge order), config-return-contract (Config.load -> Diot;
active profile fixes values), return-flow (load -> access), shared-receiver
(same conf reflects use_profile), lifecycle (use_profile persistent vs
with_profile temporary). No completion-obligation (config lib).
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

import fixture_simpleconf as fx
from diot import Diot  # noqa: E402
from fixture_simpleconf import make_namespace  # noqa: F401
from simpleconf import Config, ProfileConfig  # noqa: E402

NAME = "simpleconf"
reset = fx.reset
get_trace = fx.get_trace

# A fixed profile spec used across tasks: prod overrides x, inherits y from default.
PROFILES = {"default": {"x": 1, "y": 2}, "prod": {"x": 99}}


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


# ---- reference outputs (replicate the canonical use of the REAL library) ----
def _r_merge(base, override, key):
    return Config.load(base, override)[key]


def _r_merge3(a, b, c, key):
    return Config.load(a, b, c)[key]


def _r_profile_x(profiles, profile):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, profile)
    return c.x


def _r_current(profiles, profile):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, profile)
    return ProfileConfig.current_profile(c)


def _r_load_get(data, key):
    return Config.load(data)[key]


def _r_profile_default_x(profiles):
    return ProfileConfig.load(profiles).x


def _r_nested(data, k1, k2):
    return Config.load(data)[k1][k2]


def _r_switch_two(profiles):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, "prod")
    v1 = c.x
    ProfileConfig.use_profile(c, "default")
    return (v1, c.x)


def _r_with_temp(profiles, profile):
    c = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(c, profile):
        inside = c.x
    return (inside, c.x)


def _r_use_then_with(profiles):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, "prod")
    with ProfileConfig.with_profile(c, "default"):
        mid = c.x
    return (mid, c.x)


def _r_nested_with(profiles):
    c = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(c, "prod"):
        a = c.x
        with ProfileConfig.with_profile(c, "default"):
            b = c.x
        cc = c.x
    return (a, b, cc)


def _r_use_survives(profiles):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, "prod")
    with ProfileConfig.with_profile(c, "default"):
        pass
    return c.x


def _r_double_use(profiles):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, "prod")
    ProfileConfig.use_profile(c, "default")
    return c.x


def _r_two_reads(profiles):
    c = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c, "prod")
    return (c.x, c.x)


FUNC_NAMES = {
    "simpleconf-S001": "merge_get",
    "simpleconf-S002": "merge_three",
    "simpleconf-S003": "load_is_diot",
    "simpleconf-S004": "profile_value",
    "simpleconf-S005": "active_profile_name",
    "simpleconf-S006": "load_then_get",
    "simpleconf-S007": "profile_load_attr",
    "simpleconf-S008": "merge_then_nested",
    "simpleconf-S009": "use_profile_same_conf",
    "simpleconf-S010": "mutate_then_read",
    "simpleconf-S011": "switch_two_profiles",
    "simpleconf-S012": "with_profile_temporary",
    "simpleconf-S013": "use_then_with_restore",
    "simpleconf-S014": "with_profile_keeps_current",
    "simpleconf-S015": "nested_with_profiles",
    "simpleconf-S016": "use_survives_with",
    "simpleconf-S017": "double_use_persistent",
    "simpleconf-S018": "two_reads_same_conf",
}

INPUTS = {
    "simpleconf-S001": [({"k": 1, "a": 10}, {"k": 2}, "k"), ({"k": 1}, {"k": 5}, "k")],
    "simpleconf-S002": [({"k": 1}, {"k": 2}, {"k": 3}, "k")],
    "simpleconf-S003": [({"a": 1, "b": 2},)],
    "simpleconf-S004": [(PROFILES, "prod"), (PROFILES, "default")],
    "simpleconf-S005": [(PROFILES, "prod")],
    "simpleconf-S006": [({"a": 1, "b": 2}, "b")],
    "simpleconf-S007": [(PROFILES,)],
    "simpleconf-S008": [({"a": {"b": 5}}, "a", "b")],
    "simpleconf-S009": [(PROFILES, "prod")],
    "simpleconf-S010": [({"a": 1}, "a", 42)],
    "simpleconf-S011": [(PROFILES,)],
    "simpleconf-S012": [(PROFILES, "prod")],
    "simpleconf-S013": [(PROFILES,)],
    "simpleconf-S014": [(PROFILES,)],
    "simpleconf-S015": [(PROFILES,)],
    "simpleconf-S016": [(PROFILES,)],
    "simpleconf-S017": [(PROFILES,)],
    "simpleconf-S018": [(PROFILES,)],
}

_REF = {
    "simpleconf-S001": _r_merge,
    "simpleconf-S002": _r_merge3,
    "simpleconf-S003": lambda data: data,
    "simpleconf-S004": _r_profile_x,
    "simpleconf-S005": _r_current,
    "simpleconf-S006": _r_load_get,
    "simpleconf-S007": _r_profile_default_x,
    "simpleconf-S008": _r_nested,
    "simpleconf-S009": _r_profile_x,
    "simpleconf-S010": lambda data, key, val: val,
    "simpleconf-S011": _r_switch_two,
    "simpleconf-S012": _r_with_temp,
    "simpleconf-S013": _r_use_then_with,
    "simpleconf-S014": lambda profiles: "prod",
    "simpleconf-S015": _r_nested_with,
    "simpleconf-S016": _r_use_survives,
    "simpleconf-S017": _r_double_use,
    "simpleconf-S018": _r_two_reads,
}

_ETYPE = {
    "simpleconf-S001": int, "simpleconf-S002": int, "simpleconf-S003": Diot,
    "simpleconf-S004": int, "simpleconf-S005": str, "simpleconf-S006": int,
    "simpleconf-S007": int, "simpleconf-S008": int, "simpleconf-S009": int,
    "simpleconf-S010": int, "simpleconf-S011": tuple, "simpleconf-S012": tuple,
    "simpleconf-S013": tuple, "simpleconf-S014": str,
    "simpleconf-S015": tuple, "simpleconf-S016": int,
    "simpleconf-S017": int, "simpleconf-S018": tuple,
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
    "simpleconf-S001": [
        ("canonical_order", """
def merge_get(base, override, key):
    return Config.load(base, override)[key]
""", True),
        ("violation_swapped", """
def merge_get(base, override, key):
    return Config.load(override, base)[key]
""", {"wrong_output"}),
    ],
    "simpleconf-S002": [
        ("canonical_three", """
def merge_three(a, b, c, key):
    return Config.load(a, b, c)[key]
""", True),
        ("violation_order", """
def merge_three(a, b, c, key):
    return Config.load(c, b, a)[key]
""", {"wrong_output"}),
    ],
    "simpleconf-S003": [
        ("canonical_load", """
def load_is_diot(data):
    return Config.load(data)
""", True),
        ("violation_plain_dict", """
def load_is_diot(data):
    return dict(data)
""", {"wrong_output_structure"}),
    ],
    "simpleconf-S004": [
        ("canonical_use_profile", """
def profile_value(profiles, profile):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, profile)
    return conf.x
""", True),
        ("violation_no_switch", """
def profile_value(profiles, profile):
    conf = ProfileConfig.load(profiles)
    return conf.x
""", {"wrong_output"}),
    ],
    "simpleconf-S005": [
        ("canonical_current", """
def active_profile_name(profiles, profile):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, profile)
    return ProfileConfig.current_profile(conf)
""", True),
        ("violation_no_switch", """
def active_profile_name(profiles, profile):
    conf = ProfileConfig.load(profiles)
    return ProfileConfig.current_profile(conf)
""", {"wrong_output"}),
    ],
    "simpleconf-S006": [
        ("canonical_get", """
def load_then_get(data, key):
    conf = Config.load(data)
    return conf[key]
""", True),
        ("violation_return_conf", """
def load_then_get(data, key):
    return Config.load(data)
""", {"wrong_output_structure"}),
    ],
    "simpleconf-S007": [
        ("canonical_attr", """
def profile_load_attr(profiles):
    conf = ProfileConfig.load(profiles)
    return conf.x
""", True),
        ("violation_return_conf", """
def profile_load_attr(profiles):
    return ProfileConfig.load(profiles)
""", {"wrong_output_structure"}),
    ],
    "simpleconf-S008": [
        ("canonical_nested", """
def merge_then_nested(data, k1, k2):
    return Config.load(data)[k1][k2]
""", True),
        ("violation_one_level", """
def merge_then_nested(data, k1, k2):
    return Config.load(data)[k1]
""", {"wrong_output_structure"}),
    ],
    "simpleconf-S009": [
        ("canonical_same_conf", """
def use_profile_same_conf(profiles, profile):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, profile)
    return conf.x
""", True),
        ("violation_fresh_conf", """
def use_profile_same_conf(profiles, profile):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, profile)
    return ProfileConfig.load(profiles).x
""", {"wrong_output"}),
    ],
    "simpleconf-S010": [
        ("canonical_mutate_same", """
def mutate_then_read(data, key, val):
    conf = Config.load(data)
    conf[key] = val
    return conf[key]
""", True),
        ("violation_read_fresh", """
def mutate_then_read(data, key, val):
    conf = Config.load(data)
    conf[key] = val
    return Config.load(data)[key]
""", {"wrong_output"}),
    ],
    "simpleconf-S011": [
        ("canonical_switch_two", """
def switch_two_profiles(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    v1 = conf.x
    ProfileConfig.use_profile(conf, "default")
    return (v1, conf.x)
""", True),
        ("violation_fresh_each", """
def switch_two_profiles(profiles):
    c1 = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c1, "prod")
    c2 = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(c2, "prod")
    return (c1.x, c2.x)
""", {"wrong_output"}),
    ],
    "simpleconf-S012": [
        ("canonical_with_temp", """
def with_profile_temporary(profiles, profile):
    conf = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(conf, profile):
        inside = conf.x
    return (inside, conf.x)
""", True),
        ("violation_use_persistent", """
def with_profile_temporary(profiles, profile):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, profile)
    inside = conf.x
    return (inside, conf.x)
""", {"wrong_output"}),
    ],
    "simpleconf-S013": [
        ("canonical_use_then_with", """
def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    with ProfileConfig.with_profile(conf, "default"):
        mid = conf.x
    return (mid, conf.x)
""", True),
        ("violation_nested_persistent", """
def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    ProfileConfig.use_profile(conf, "default")
    mid = conf.x
    return (mid, conf.x)
""", {"wrong_output"}),
    ],
    "simpleconf-S014": [
        ("canonical_restore_current", """
def with_profile_keeps_current(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    with ProfileConfig.with_profile(conf, "default"):
        pass
    return ProfileConfig.current_profile(conf)
""", True),
        ("violation_switch_persistent", """
def with_profile_keeps_current(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    ProfileConfig.use_profile(conf, "default")
    return ProfileConfig.current_profile(conf)
""", {"wrong_output"}),
    ],
    "simpleconf-S015": [
        ("canonical_nested", """
def nested_with_profiles(profiles):
    conf = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(conf, "prod"):
        a = conf.x
        with ProfileConfig.with_profile(conf, "default"):
            b = conf.x
        c = conf.x
    return (a, b, c)
""", True),
        ("violation_use_inside", """
def nested_with_profiles(profiles):
    conf = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(conf, "prod"):
        a = conf.x
        ProfileConfig.use_profile(conf, "default")
        b = conf.x
        c = conf.x
    return (a, b, c)
""", {"wrong_output"}),
    ],
    "simpleconf-S016": [
        ("canonical_survives", """
def use_survives_with(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    with ProfileConfig.with_profile(conf, "default"):
        pass
    return conf.x
""", True),
        ("violation_persistent_switch", """
def use_survives_with(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    ProfileConfig.use_profile(conf, "default")
    return conf.x
""", {"wrong_output"}),
    ],
    "simpleconf-S017": [
        ("canonical_double_use", """
def double_use_persistent(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    ProfileConfig.use_profile(conf, "default")
    return conf.x
""", True),
        ("violation_with_temp", """
def double_use_persistent(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    with ProfileConfig.with_profile(conf, "default"):
        pass
    return conf.x
""", {"wrong_output"}),
    ],
    "simpleconf-S018": [
        ("canonical_two_reads", """
def two_reads_same_conf(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    return (conf.x, conf.x)
""", True),
        ("violation_second_fresh", """
def two_reads_same_conf(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, "prod")
    return (conf.x, ProfileConfig.load(profiles).x)
""", {"wrong_output"}),
    ],
}


TASKS = [
    {"task_id": "simpleconf-S001", "pair_type": "param-dependency", "difficulty": "easy",
     "func": "merge_get",
     "task": "Write function merge_get(base, override, key). Load a merged config from base then override (so override wins on conflicts) and return the value for key."},
    {"task_id": "simpleconf-S002", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "merge_three",
     "task": "Write function merge_three(a, b, c, key). Load a merged config from a, b, c in that order (later sources override earlier) and return the value for key."},
    {"task_id": "simpleconf-S003", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "load_is_diot",
     "task": "Write function load_is_diot(data). Load a config from the dict data and return it (it must be a Diot supporting attribute access, not a plain dict)."},
    {"task_id": "simpleconf-S004", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "profile_value",
     "task": "Write function profile_value(profiles, profile). Load a ProfileConfig from profiles, switch to the given profile, and return conf.x for that profile (inheriting from the default/base profile)."},
    {"task_id": "simpleconf-S005", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "active_profile_name",
     "task": "Write function active_profile_name(profiles, profile). Load a ProfileConfig, switch to the given profile, and return the name of the currently active profile (a str)."},
    {"task_id": "simpleconf-S006", "pair_type": "return-flow", "difficulty": "easy",
     "func": "load_then_get",
     "task": "Write function load_then_get(data, key). Load a config from data and return the value at key from that loaded config."},
    {"task_id": "simpleconf-S007", "pair_type": "return-flow", "difficulty": "easy",
     "func": "profile_load_attr",
     "task": "Write function profile_load_attr(profiles). Load a ProfileConfig from profiles and return conf.x (the default profile's value)."},
    {"task_id": "simpleconf-S008", "pair_type": "return-flow", "difficulty": "medium",
     "func": "merge_then_nested",
     "task": "Write function merge_then_nested(data, k1, k2). Load a config from data and return the nested value config[k1][k2]."},
    {"task_id": "simpleconf-S009", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "use_profile_same_conf",
     "task": "Write function use_profile_same_conf(profiles, profile). Load a ProfileConfig, switch it to the given profile, and read conf.x back from the SAME config object."},
    {"task_id": "simpleconf-S010", "pair_type": "shared-receiver", "difficulty": "easy",
     "func": "mutate_then_read",
     "task": "Write function mutate_then_read(data, key, val). Load a config, set conf[key]=val, then read key back from the SAME config and return it."},
    {"task_id": "simpleconf-S011", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "switch_two_profiles",
     "task": "Write function switch_two_profiles(profiles). On ONE loaded ProfileConfig, switch to 'prod' and read x, then switch to 'default' and read x; return the tuple (prod_x, default_x)."},
    {"task_id": "simpleconf-S012", "pair_type": "lifecycle", "difficulty": "medium",
     "func": "with_profile_temporary",
     "task": "Write function with_profile_temporary(profiles, profile). Load a ProfileConfig. Inside a with_profile(profile) context read conf.x; after the context exits read conf.x again (it reverts to the default profile). Return (inside, after)."},
    {"task_id": "simpleconf-S013", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "use_then_with_restore",
     "task": "Write function use_then_with_restore(profiles). Load a ProfileConfig and persistently switch to 'prod'. Inside a temporary with_profile('default') context read conf.x; after the context exits read conf.x (it reverts to 'prod', not 'default'). Return (mid, after)."},
    {"task_id": "simpleconf-S014", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "with_profile_keeps_current",
     "task": "Write function with_profile_keeps_current(profiles). Load a ProfileConfig and persistently switch to 'prod'. Enter and exit a temporary with_profile('default') context; afterwards return the active profile name (it must still be 'prod')."},
    {"task_id": "simpleconf-S015", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "nested_with_profiles",
     "task": "Write function nested_with_profiles(profiles). Load a ProfileConfig. Inside with_profile('prod') read x (a), then in a NESTED with_profile('default') read x (b), then after the inner context read x again (c) -- back in 'prod'. Return (a, b, c)."},
    {"task_id": "simpleconf-S016", "pair_type": "lifecycle", "difficulty": "medium",
     "func": "use_survives_with",
     "task": "Write function use_survives_with(profiles). Load a ProfileConfig and persistently switch to 'prod'. Enter and exit a temporary with_profile('default') context; afterwards return conf.x (it must still be the 'prod' value)."},
    {"task_id": "simpleconf-S017", "pair_type": "lifecycle", "difficulty": "medium",
     "func": "double_use_persistent",
     "task": "Write function double_use_persistent(profiles). Load a ProfileConfig, persistently switch to 'prod', then persistently switch to 'default'; return conf.x (the final, persistent value)."},
    {"task_id": "simpleconf-S018", "pair_type": "shared-receiver", "difficulty": "easy",
     "func": "two_reads_same_conf",
     "task": "Write function two_reads_same_conf(profiles). Load a ProfileConfig, switch it to 'prod', and read conf.x twice from the SAME config; return the tuple (x1, x2)."},
]

HELPER_LINE = "Config and ProfileConfig (real simpleconf classes) are available"

API_LIST = """Relevant simpleconf APIs:
- Config.load(*configs, loader=None) -> Diot   # merge configs; later overrides earlier
- ProfileConfig.load(profiles, base='default') -> Diot
- ProfileConfig.use_profile(conf, profile)        # switch active profile (persistent)
- ProfileConfig.with_profile(conf, profile)       # context manager: switch temporarily
- ProfileConfig.current_profile(conf) -> str
- the loaded config is a Diot (attribute & item access)
"""

RAW_API_DOCS = """Retrieved simpleconf documentation snippets:
- Config.load merges multiple config sources into a single Diot; sources given later override earlier ones.
- ProfileConfig organizes configs into named profiles; non-default profiles inherit from the base profile (default 'default').
- use_profile(conf, name) switches the active profile on conf persistently; with_profile(conf, name) is a context manager that switches temporarily and reverts on exit.
- current_profile(conf) returns the active profile's name.
- A loaded config is a Diot, so values are accessible by attribute or item.
"""

ORACLE_API_SEQUENCES = {
    "simpleconf-S001": "Oracle API sequence:\nConfig.load(base, override) -> [key]",
    "simpleconf-S002": "Oracle API sequence:\nConfig.load(a, b, c) -> [key]",
    "simpleconf-S003": "Oracle API sequence:\nConfig.load(data)  (a Diot)",
    "simpleconf-S004": "Oracle API sequence:\nProfileConfig.load -> use_profile(profile) -> conf.x",
    "simpleconf-S005": "Oracle API sequence:\nProfileConfig.load -> use_profile -> current_profile",
    "simpleconf-S006": "Oracle API sequence:\nConfig.load(data) -> [key]",
    "simpleconf-S007": "Oracle API sequence:\nProfileConfig.load -> conf.x",
    "simpleconf-S008": "Oracle API sequence:\nConfig.load(data) -> [k1][k2]",
    "simpleconf-S009": "Oracle API sequence:\nProfileConfig.load -> use_profile -> conf.x (same conf)",
    "simpleconf-S010": "Oracle API sequence:\nConfig.load -> conf[key]=val -> conf[key]",
    "simpleconf-S011": "Oracle API sequence:\nload -> use_profile('prod') -> use_profile('default') (same conf)",
    "simpleconf-S012": "Oracle API sequence:\nload -> with_profile(profile): conf.x ; conf.x",
    "simpleconf-S013": "Oracle API sequence:\nload -> use_profile('prod') -> with_profile('default'): conf.x ; conf.x",
    "simpleconf-S014": "Oracle API sequence:\nload -> use_profile('prod') -> with_profile('default') -> current_profile",
    "simpleconf-S015": "Oracle API sequence:\nload -> with_profile('prod'): conf.x ; with_profile('default'): conf.x ; conf.x   (nested; inner reverts to 'prod')",
    "simpleconf-S016": "Oracle API sequence:\nload -> use_profile('prod') -> with_profile('default'): pass ; conf.x   ('prod' survives the temporary block)",
    "simpleconf-S017": "Oracle API sequence:\nload -> use_profile('prod') -> use_profile('default') -> conf.x   (final persistent profile)",
    "simpleconf-S018": "Oracle API sequence:\nload -> use_profile('prod') -> (conf.x, conf.x)   (two reads, same conf)",
}

GOLD_PAIR_RULES = """Relevant API Pair Rules (extracted from simpleconf API):
1. Config.load(*configs) -> merge precedence
Relation: param-dependency
Constraint: Config.load merges sources left-to-right; sources given LATER override earlier ones on conflicting keys. The argument ORDER decides the merged value.
Usage pattern:
Config.load(base, override)[key]   # override wins

2. Config.load / ProfileConfig.load -> returned Diot; profile -> values
Relation: config-return-contract
Constraint: load returns a Diot (attribute/item access), not a plain dict. For a ProfileConfig, the ACTIVE profile fixes the values you read; non-default profiles inherit missing keys from the base profile.
Usage pattern:
conf = ProfileConfig.load(profiles); ProfileConfig.use_profile(conf, 'prod'); conf.x

3. load -> access
Relation: return-flow
Constraint: To read a value you must index/attribute into the config RETURNED by load (not the input dict, not the config object itself).
Usage pattern:
Config.load(data)[key]

4. same conf + use_profile
Relation: shared-receiver
Constraint: use_profile mutates the active profile on the SAME conf object; reads on that conf reflect the switch. A freshly reloaded config starts at the default profile.
Usage pattern:
conf = ProfileConfig.load(profiles); ProfileConfig.use_profile(conf, 'prod'); conf.x   # same conf

5. use_profile (persistent) vs with_profile (temporary)
Relation: lifecycle
Constraint: use_profile switches the active profile PERSISTENTLY; with_profile is a context manager that switches TEMPORARILY and reverts to the previously-active profile on exit. After a with_profile block, the profile active before the block is restored.
Usage pattern:
ProfileConfig.use_profile(conf, 'prod')
with ProfileConfig.with_profile(conf, 'default'):
    ...   # default here
# 'prod' restored here
"""
