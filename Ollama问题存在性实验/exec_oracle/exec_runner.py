#!/usr/bin/env python3
"""Run ONE generated solution against the execution oracle, in isolation.

Invoked as a subprocess by run_exec_eval.py (one process per generation, so
a hang/crash in generated code can never poison other evaluations):

    python3 exec_runner.py --task simplug-T001 --gen path/to/gen.py \
        --out verdict.json [--values 5,11]

Protocol
--------
1. Build a module namespace containing the instrumented fixture
   (``make_score_manager``) and pre-bound globals
   ``sp, alpha, beta, gamma = make_score_manager()`` -- so both styles of
   generated code work: code that calls the helper itself and code that
   uses the globals directly (the prompt allows both readings).
2. ``exec`` the generated source (syntax / import-time errors recorded).
3. For each test value v: mark the trace, call the function, snapshot every
   manager's enabled-state, and run the task's hidden test on
   (return value, trace slice, final state, v). All values must pass.
4. Write a JSON verdict to --out (never to stdout: generated code could
   print arbitrary bytes).
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

import fixture_simplug as fx
from hidden_tests import CHECKS, COARSE, FUNC_NAMES

DEFAULT_VALUES = (5, 11)


def evaluate(task_id: str, gen_path: Path, values) -> dict:
    func_name = FUNC_NAMES[task_id]
    check = CHECKS[task_id]

    try:
        source = gen_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _verdict(False, "harness_error", f"cannot read generation: {exc!r}")

    if not source.strip():
        return _verdict(False, "syntax_error", "empty generation")

    fx.reset_trace()
    ns: dict = {"__name__": "paircoder_generation"}
    # Expose every fixture factory (make_score_manager, make_first_score_manager,
    # make_last_score_manager, ...) so tasks that promise a differently-configured
    # manager work; the task prompt tells the model which helper to call.
    for _fname in dir(fx):
        if _fname.startswith("make_") and callable(getattr(fx, _fname)):
            ns[_fname] = getattr(fx, _fname)
    try:
        # Bind ambient sp with the manager the TASK promises (FIRST/LAST for the
        # config-return tasks, default ALL_AVAILS otherwise) so the prompt's
        # "this helper already exists and is correct" holds for code that, as
        # instructed, uses the existing variables instead of re-creating them.
        factory = fx.MANAGER_FACTORY_BY_TASK.get(task_id, fx.make_score_manager)
        ns["sp"], ns["alpha"], ns["beta"], ns["gamma"] = factory()
    except Exception as exc:  # pragma: no cover - fixture must not fail
        return _verdict(False, "harness_error", f"fixture failed: {exc!r}")

    try:
        code = compile(source, str(gen_path), "exec")
    except SyntaxError as exc:
        return _verdict(False, "syntax_error", repr(exc))

    try:
        exec(code, ns)  # noqa: S102 - that's the point of the harness
    except BaseException as exc:  # includes SystemExit
        return _verdict(
            False,
            "import_time_error",
            f"{type(exc).__name__}: {exc}",
        )

    func = ns.get(func_name)
    if not callable(func):
        return _verdict(
            False,
            "function_not_defined",
            f"function {func_name!r} not defined by the generation",
        )

    per_value = []
    for v in values:
        start = len(fx.TRACE)
        try:
            ret = func(v)
        except BaseException as exc:
            tb = traceback.format_exception_only(type(exc), exc)
            res = {
                "ok": False,
                "reason": "runtime_error",
                "detail": "".join(tb).strip(),
            }
            per_value.append({"value": v, **res})
            return _verdict(False, res["reason"], res["detail"], per_value)
        events = fx.TRACE[start:]
        final_state = fx.managers_enabled_state()
        res = check(ret, events, final_state, v)
        per_value.append({"value": v, **res})
        if not res["ok"]:
            return _verdict(False, res["reason"], res["detail"], per_value)

    return _verdict(True, "", "", per_value)


def _verdict(ok: bool, reason: str, detail: str, per_value=None) -> dict:
    return {
        "exec_pass": ok,
        "reason": reason,
        "reason_coarse": COARSE.get(reason, "exec_error"),
        "detail": detail,
        "per_value": per_value or [],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=sorted(FUNC_NAMES))
    ap.add_argument("--gen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--values", default=",".join(str(v) for v in DEFAULT_VALUES))
    args = ap.parse_args()

    values = [int(x) for x in args.values.split(",") if x.strip()]
    try:
        verdict = evaluate(args.task, Path(args.gen), values)
    except Exception as exc:  # harness bug, not the generation's fault
        verdict = _verdict(False, "harness_error", repr(exc))

    Path(args.out).write_text(
        json.dumps(verdict, ensure_ascii=False, default=repr), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
