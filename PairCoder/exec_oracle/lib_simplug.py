#!/usr/bin/env python3
"""Benchmark module: simplug (REAL vendored library, v0.5.7; plugin/extension domain).

This is simplug on the SAME uniform benchlib interface the other libraries use
(make_namespace / FUNC_NAMES / INPUTS / CHECKS / ANCHORS / TASKS / ...), so the
generic engine (benchlib_generate.py / benchlib_eval.py / benchlib.py) drives it
exactly like glom/diot/simpleconf/bidict. It REUSES the verified simplug oracle:

  * fixture_simplug.py  -- instrumented manager + runtime trace,
  * hidden_tests.py     -- the per-task execution checks (4-arg),
  * anchor_solutions.py -- the anchoring suite (canonical + violations).

The only adaptation is the calling convention: benchlib's check signature is
``check(ret, trace, args)``; simplug's hidden tests are ``check(ret, events,
final_state, value)``. The wrapper below supplies ``final_state`` from
``fx.managers_enabled_state()`` and ``value`` from ``args[0]``.
"""

from __future__ import annotations

import fixture_simplug as fx
from anchor_solutions import ANCHORS  # noqa: F401  (benchlib interface attribute)
from hidden_tests import CHECKS as _HIDDEN_CHECKS, FUNC_NAMES  # noqa: F401

NAME = "simplug"

# Each simplug task forwards two test values (the original simplug oracle did too).
_VALUES = (5, 11)
INPUTS = {tid: [(v,) for v in _VALUES] for tid in FUNC_NAMES}


def _wrap(hidden_check):
    """benchlib (ret, trace, args) -> simplug (ret, events, final_state, value)."""
    def check(ret, trace, args):
        return hidden_check(ret, list(trace), fx.managers_enabled_state(), args[0])
    return check


CHECKS = {tid: _wrap(_HIDDEN_CHECKS[tid]) for tid in FUNC_NAMES}


# ---------------------------------------------------------------------------
# Namespace + trace (benchlib calls these). make_namespace accepts the task_id
# so it can pre-bind the manager the task promises (FIRST/LAST for T007/T008),
# as the original simplug oracle did. reset() clears only the TRACE (NOT MANAGERS,
# which must survive for managers_enabled_state in the checks).
# ---------------------------------------------------------------------------
def make_namespace(task_id=None):
    fx.reset_trace()
    ns = {"__name__": "paircoder_generation"}
    for fname in dir(fx):
        if fname.startswith("make_") and callable(getattr(fx, fname)):
            ns[fname] = getattr(fx, fname)
    ns["Simplug"] = fx.Simplug
    ns["SimplugResult"] = fx.SimplugResult
    factory = fx.MANAGER_FACTORY_BY_TASK.get(task_id, fx.make_score_manager)
    ns["sp"], ns["alpha"], ns["beta"], ns["gamma"] = factory()
    return ns


def reset():
    del fx.TRACE[:]


def get_trace():
    return fx.TRACE


# ---------------------------------------------------------------------------
# Generation side (B0-B4 payloads).
# ---------------------------------------------------------------------------
HELPER_LINE = (
    "make_score_manager(), make_first_score_manager() and make_last_score_manager() "
    "are available; each returns (sp, alpha, beta, gamma) backed by the real simplug "
    "library (sp is a Simplug manager with a 'score' hook and three plugins)."
)

TASKS = [
    {"task_id": "simplug-T001", "pair_type": "param-dependency", "difficulty": "easy",
     "func": "only_beta_score",
     "task": "Write function only_beta_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Run sp.hooks.score(value) with only the beta plugin enabled temporarily, then return the hook result."},
    {"task_id": "simplug-T002", "pair_type": "param-dependency", "difficulty": "medium",
     "func": "only_alpha_gamma_score",
     "task": "Write function only_alpha_gamma_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Run sp.hooks.score(value) with only alpha and gamma enabled temporarily, then return the hook result."},
    {"task_id": "simplug-T003", "pair_type": "shared-receiver", "difficulty": "easy",
     "func": "disable_beta_then_score",
     "task": "Write function disable_beta_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Disable beta by name, then call sp.hooks.score(value), and return the result."},
    {"task_id": "simplug-T004", "pair_type": "return-flow", "difficulty": "medium",
     "func": "get_beta_wrapper_disable_then_score",
     "task": "Write function get_beta_wrapper_disable_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Get beta's plugin wrapper from the manager, disable that wrapper, then call sp.hooks.score(value), and return the result."},
    {"task_id": "simplug-T005", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "beta_only_inside_context_then_all_score",
     "task": "Write function beta_only_inside_context_then_all_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. First collect sp.hooks.score(value) inside a temporary context where only beta is enabled. Then after the context exits, collect sp.hooks.score(value) again with the original plugin state restored. Return both results."},
    {"task_id": "simplug-T006", "pair_type": "shared-receiver", "difficulty": "medium",
     "func": "disable_alpha_gamma_then_score",
     "task": "Write function disable_alpha_gamma_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Disable alpha and gamma by name, then call sp.hooks.score(value), and return the result."},
    {"task_id": "simplug-T007", "pair_type": "config-return-contract", "difficulty": "easy",
     "func": "first_score",
     "task": "Write function first_score(value). Use make_first_score_manager() to get sp, alpha, beta, gamma. Call sp.hooks.score(value) and return its result directly."},
    {"task_id": "simplug-T008", "pair_type": "config-return-contract", "difficulty": "medium",
     "func": "last_score",
     "task": "Write function last_score(value). Use make_last_score_manager() to get sp, alpha, beta, gamma. Call sp.hooks.score(value) and return its result directly."},
    {"task_id": "simplug-T009", "pair_type": "return-flow", "difficulty": "hard",
     "func": "disable_alpha_gamma_via_wrappers_then_score",
     "task": "Write function disable_alpha_gamma_via_wrappers_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Get the plugin wrapper for alpha and disable it, then get the plugin wrapper for gamma and disable it, then call sp.hooks.score(value), and return the result."},
    {"task_id": "simplug-T010", "pair_type": "lifecycle", "difficulty": "hard",
     "func": "persistent_disable_beta_then_temp_only_alpha_score",
     "task": "Write function persistent_disable_beta_then_temp_only_alpha_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. First disable beta by name. Then, inside a temporary context where only alpha is enabled, collect sp.hooks.score(value). After the context exits, collect sp.hooks.score(value) again. Return both results (inside, after)."},
]

API_LIST = """Relevant simplug APIs:
- from simplug import Simplug
- make_score_manager() -> returns (sp, alpha, beta, gamma)
- make_first_score_manager() -> like make_score_manager, score hook uses result=FIRST
- make_last_score_manager() -> like make_score_manager, score hook uses result=LAST
- sp.plugins_context(plugins): context manager that temporarily changes enabled plugins.
- sp.hooks.score(value): calls the score hook and returns collected results.
- sp.disable(*names): disable plugins.
- sp.enable(*names): enable plugins.
- sp.get_plugin(name): get a plugin wrapper.
- wrapper.disable(): disable this plugin wrapper.
- wrapper.enable(): enable this plugin wrapper.
"""

RAW_API_DOCS = """Retrieved simplug documentation snippets:
- make_score_manager() returns a Simplug manager and plugin objects: sp, alpha, beta, gamma.
- make_first_score_manager()/make_last_score_manager() return a manager whose score hook is declared with result=SimplugResult.FIRST/LAST.
- A hook's result mode controls what hooks.<name>(...) returns: ALL_AVAILS returns a list of every enabled plugin's result; FIRST/LAST return a single result (the first/last enabled plugin's).
- plugins_context(plugins) creates a temporary plugin context and restores the previous plugin state after the context exits.
- hooks.score(value) invokes the score hook through the manager and returns the collected hook results.
- disable(*names) disables plugins on the manager.
- enable(*names) enables plugins on the manager.
- get_plugin(name) returns a plugin wrapper object for a registered plugin.
- wrapper.disable() disables the plugin represented by that wrapper.
- wrapper.enable() enables the plugin represented by that wrapper.
"""

# B3*: ABSTRACT call sequence -- API names/order only (no constraint-bearing args:
# names-vs-objects, same-sp identity, persistent-vs-temporary, single-vs-list).
ORACLE_API_SEQUENCES = {
    "simplug-T001": "Abstract API sequence (call order only):\nmake_score_manager -> sp.plugins_context -> sp.hooks.score",
    "simplug-T002": "Abstract API sequence (call order only):\nmake_score_manager -> sp.plugins_context -> sp.hooks.score",
    "simplug-T003": "Abstract API sequence (call order only):\nmake_score_manager -> sp.disable -> sp.hooks.score",
    "simplug-T004": "Abstract API sequence (call order only):\nmake_score_manager -> sp.get_plugin -> wrapper.disable -> sp.hooks.score",
    "simplug-T005": "Abstract API sequence (call order only):\nmake_score_manager -> sp.plugins_context -> sp.hooks.score -> sp.hooks.score",
    "simplug-T006": "Abstract API sequence (call order only):\nmake_score_manager -> sp.disable -> sp.hooks.score",
    "simplug-T007": "Abstract API sequence (call order only):\nmake_first_score_manager -> sp.hooks.score",
    "simplug-T008": "Abstract API sequence (call order only):\nmake_last_score_manager -> sp.hooks.score",
    "simplug-T009": "Abstract API sequence (call order only):\nmake_score_manager -> sp.get_plugin -> wrapper.disable -> sp.get_plugin -> wrapper.disable -> sp.hooks.score",
    "simplug-T010": "Abstract API sequence (call order only):\nmake_score_manager -> sp.disable -> sp.plugins_context -> sp.hooks.score -> sp.hooks.score",
}

# Gold pair rules MANUALLY EXTRACTED from simplug's real semantics. The lifecycle
# rule is tagged "lifecycle" (the legacy pilot tagged it "state-lifecycle"); the
# canonical relation name is used here so it matches each task's pair_type.
GOLD_PAIR_RULES = """Relevant API Pair Rules:
1. sp.plugins_context -> sp.hooks.score
Relation: param-dependency
Constraint: To run a hook with only an existing plugin enabled, pass plugin names as strings, e.g. ["beta"]. Passing the plugin object beta means add/enable beta, not only-beta mode.
Usage pattern:
with sp.plugins_context(["beta"]):
    result = sp.hooks.score(value)

2. sp.disable -> sp.hooks.score
Relation: shared-receiver
Constraint: sp.disable("beta") changes the enabled state in the same Simplug manager; the following sp.hooks.score(value) should be called on the same sp.
Usage pattern:
sp.disable("beta")
result = sp.hooks.score(value)

3. sp.get_plugin -> wrapper.disable -> sp.hooks.score
Relation: return-flow
Constraint: sp.get_plugin("beta") returns the wrapper that should be used as the receiver of wrapper.disable(); the later hook call should use the same manager sp.
Usage pattern:
wrapper = sp.get_plugin("beta")
wrapper.disable()
result = sp.hooks.score(value)

4. sp.spec(result=...) -> sp.hooks.score
Relation: config-return-contract
Constraint: The hook's result mode decides the RETURN SHAPE of sp.hooks.score(value). make_first_score_manager / make_last_score_manager declare the score hook with result=FIRST / result=LAST, so sp.hooks.score(value) returns a SINGLE result (the first/last enabled plugin's, by registration order) -- NOT a list. Return it directly; do not wrap it in a list or index into it as if it were a list.
Usage pattern:
result = sp.hooks.score(value)   # a single ("name", number) tuple
return result

5. sp.disable / sp.plugins_context -> sp.hooks.score
Relation: lifecycle
Constraint: sp.disable(name) is PERSISTENT -- the plugin stays disabled after the call and across a later plugins_context. plugins_context temporarily changes the enabled set and, on exit, restores the state that held WHEN THE CONTEXT WAS ENTERED -- not "all plugins enabled". A plugin disabled before entering the context therefore remains disabled after the context exits.
Usage pattern:
sp.disable("beta")
with sp.plugins_context(["alpha"]):
    inside = sp.hooks.score(value)   # only alpha
after = sp.hooks.score(value)        # alpha and gamma (beta still disabled)
"""
