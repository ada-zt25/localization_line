#!/usr/bin/env python3
"""Run ONE generated solution for a generic benchmark library, in isolation.

Spawned as a subprocess by benchlib_eval.py (one process per generation, so a
hang/crash in untrusted model code cannot poison other evaluations). The
judging logic itself lives in benchlib.evaluate_source -- identical to what the
anchor suite uses -- so anchors and model generations are scored the same way.

    python3 benchlib_runner.py --lib glom --task glom-G001 \
        --gen path/to/gen.py --out verdict.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import benchlib

COARSE = {
    "syntax_error": "exec_error",
    "import_time_error": "exec_error",
    "runtime_error": "exec_error",
    "function_not_defined": "exec_error",
    "timeout": "exec_error",
    "harness_error": "exec_error",
    "wrong_output": "wrong_behavior",
    "wrong_output_structure": "wrong_behavior",
    "obligation_unmet": "pair_state_violation",
    "": "",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--gen", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    try:
        lib = benchlib.load_lib(args.lib)
        source = Path(args.gen).read_text(encoding="utf-8")
        res = benchlib.evaluate_source(lib, args.task, source)
        verdict = {
            "exec_pass": res["ok"],
            "reason": res["reason"],
            "reason_coarse": COARSE.get(res["reason"], "exec_error"),
            "detail": res["detail"],
        }
    except Exception as exc:  # harness bug, not the generation's fault
        verdict = {
            "exec_pass": False,
            "reason": "harness_error",
            "reason_coarse": "exec_error",
            "detail": repr(exc),
        }

    Path(args.out).write_text(
        json.dumps(verdict, ensure_ascii=False, default=repr), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
