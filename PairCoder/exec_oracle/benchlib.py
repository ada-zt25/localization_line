#!/usr/bin/env python3
"""Generic execution-oracle harness for the PairCoder benchmark libraries.

All six benchmark libraries (simplug, diot, simpleconf, glom, bidict, sqlitedict)
share THIS generic harness, each exposing a small ``lib_<name>`` module with a
uniform interface. simplug's lib_simplug reuses its verified oracle helpers
(fixture_simplug + hidden_tests + anchor_solutions) behind that interface:

    NAME: str
    make_namespace() -> dict
        # names injected as globals for the generated/anchor code (factories,
        # types, hooks). Mirrors simplug's pre-bound make_score_manager().
    reset() -> None                      # optional: clear trace / global state
    get_trace() -> list                  # optional: observation trace (else [])
    FUNC_NAMES: dict[task_id, func_name]
    INPUTS:     dict[task_id, list[tuple]]   # each tuple is call args: func(*args)
    CHECKS:     dict[task_id, callable]      # check(ret, trace, args) -> verdict
    ANCHORS:    dict[task_id, list[(name, code, expectation)]]
    # generation side (used by benchlib_generate.py):
    TASKS, GOLD_PAIR_RULES, API_LIST, RAW_API_DOCS, ORACLE_API_SEQUENCES

The verdict dict is the same shape simplug uses:
    {"ok": bool, "reason": str, "detail": str}

Anchors are TRUSTED gold code, so they run IN-PROCESS here (fast, ~ms). Model
generations are UNTRUSTED and must run via the subprocess runner
(benchlib_runner.py) for crash/hang isolation -- it imports ``evaluate_source``
from here so the judging logic is identical.
"""

from __future__ import annotations

import copy
import traceback
from importlib import import_module


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


def load_lib(name: str):
    """Import the lib_<name> module and sanity-check its interface."""
    mod = import_module(f"lib_{name}")
    for attr in ("make_namespace", "FUNC_NAMES", "INPUTS", "CHECKS", "ANCHORS"):
        if not hasattr(mod, attr):
            raise AttributeError(f"lib_{name} is missing required attribute {attr!r}")
    return mod


def _reset(lib):
    if hasattr(lib, "reset"):
        lib.reset()


def _trace(lib):
    return lib.get_trace() if hasattr(lib, "get_trace") else []


def evaluate_source(lib, task_id: str, source: str) -> dict:
    """Run one solution (anchor or generation) for ``task_id`` and judge it.

    Protocol:
      1. build the library namespace + exec the source (syntax/import errors);
      2. locate the required function;
      3. for each input tuple: reset trace, call func(*args), slice the trace,
         run the task's check on (return, trace, args). All inputs must pass.
    """
    func_name = lib.FUNC_NAMES[task_id]
    check = lib.CHECKS[task_id]
    inputs = lib.INPUTS[task_id]

    if not source.strip():
        return _fail("syntax_error", "empty generation")

    # Most libs' make_namespace() take no args; simplug's accepts the task_id so it
    # can pre-bind the manager the task promises (FIRST/LAST). Pass it when accepted.
    try:
        ns = lib.make_namespace(task_id)
    except TypeError:
        ns = lib.make_namespace()
    ns.setdefault("__name__", "paircoder_generation")
    _reset(lib)

    try:
        code = compile(source, "<solution>", "exec")
    except SyntaxError as exc:
        return _fail("syntax_error", repr(exc))
    try:
        exec(code, ns)  # noqa: S102 - that's the point of the harness
    except BaseException as exc:  # includes SystemExit
        return _fail("import_time_error", f"{type(exc).__name__}: {exc}")

    func = ns.get(func_name)
    if not callable(func):
        return _fail("function_not_defined", f"function {func_name!r} not defined")

    for args in inputs:
        _reset(lib)
        # Deep-copy args per call so a task that mutates its target in place (e.g.
        # glom's Assign) cannot pollute the shared INPUTS objects for later input
        # tuples or anchor cases. The check sees the same (possibly mutated) objects
        # the function received. Harmless for tasks that never mutate their args.
        call_args = copy.deepcopy(args)
        start = len(_trace(lib))
        try:
            ret = func(*call_args)
        except BaseException as exc:
            tb = traceback.format_exception_only(type(exc), exc)
            return _fail("runtime_error", "".join(tb).strip())
        trace = _trace(lib)[start:]
        res = check(ret, trace, call_args)
        if not res["ok"]:
            return res
    return _ok()


# ---------------------------------------------------------------------------
# Anchoring suite (in-process; trusted gold code)
# ---------------------------------------------------------------------------


def run_anchors(name: str, verbose: bool = True) -> bool:
    """Run a library's anchor suite. Returns True iff every case behaves as
    documented. This is the oracle's trustworthiness gate (canonical/variants
    PASS; every documented violation FAILS with an expected reason)."""
    lib = load_lib(name)
    rows = []
    all_ok = True
    for task_id, cases in sorted(lib.ANCHORS.items()):
        for case_name, code, expectation in cases:
            verdict = evaluate_source(lib, task_id, code)
            if expectation is True:
                ok = verdict["ok"]
                exp_str = "PASS"
            else:
                ok = (not verdict["ok"]) and verdict["reason"] in expectation
                exp_str = f"FAIL({'|'.join(sorted(expectation))})"
            got = "PASS" if verdict["ok"] else f"FAIL({verdict['reason']})"
            all_ok = all_ok and ok
            rows.append((task_id, case_name, exp_str, got, ok, verdict["detail"]))

    if verbose:
        width = max((len(r[1]) for r in rows), default=10)
        for task_id, case_name, exp, got, ok, detail in rows:
            mark = "ok " if ok else "FAIL"
            line = f"  [{mark}] {task_id}  {case_name:<{width}}  expected={exp:<28} got={got}"
            if not ok:
                line += f"\n        detail: {detail}"
            print(line)
        n = len(rows)
        n_ok = sum(1 for r in rows if r[4])
        print(f"  -> {n_ok}/{n} anchor cases behave as documented")
    return all_ok


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run a benchmark library's anchor suite.")
    ap.add_argument("lib", help="library name, e.g. msgspec / peewee / niquests")
    args = ap.parse_args()
    ok = run_anchors(args.lib)
    raise SystemExit(0 if ok else 1)
