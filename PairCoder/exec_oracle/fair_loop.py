#!/usr/bin/env python3
r"""Fair closed-loop evaluation (no train/test leakage).

The original B5_loop refines against the SAME hidden-test oracle it is graded on
(b5_feedback uses benchlib.evaluate_source for feedback; benchlib_eval grades on
the same) -> optimizing on the test set. This harness fixes that:

  * each task's INPUTS are split into a DEV input (loop feedback / best-of-K
    selection) and a HELD-OUT input (evaluation only). No condition ever sees the
    held-out input during generation.
  * every condition gets the SAME budget K. Baselines B0/B1/B3/B4 resample K times
    and keep a generation that passes DEV (best-of-K). B5_loop additionally refines
    its TYPED rule via failure-attribution (the only extra ingredient).
  * final code is graded on the HELD-OUT input -> a fair, leakage-free pass rate.

So "B5_loop > B4" here means: typed-constraint-guided refinement beats gold-rule
injection UNDER EQUAL BUDGET on held-out inputs. Needs Ollama.

    python fair_loop.py --libs simplug,glom --k 3 --model qwen2.5-coder:7b
"""

from __future__ import annotations

import argparse
import importlib

import benchlib
import benchlib_generate as gen
import b5_feedback as fb
import rq2_vetted as rq
import llm_extract as llx

# Default honest comparison: the fair B5 (Phi-seeded typed loop) against the
# baseline gradient B0/B1/B3 and the gold skyline B4. B5_llm (LLM-seeded loop) and
# B4_loop (loop on top of gold) remain available via --conditions.
DEFAULT_CONDITIONS = ["B0", "B1", "B3", "B4", "B5_loop"]
# B5_cert = LLM-propose + execution-certify (the recall fix); B5_llm = same LLM
# proposals WITHOUT certification (ablation isolating what certification buys).
ALL_CONDITIONS = ["B0", "B1", "B3", "B4", "B5_loop", "B5_llm", "B5_cert", "B4_loop"]


def grade_on(lib, task_id, code, inputs):
    """Grade `code` on a SPECIFIC input subset (swap lib.INPUTS around the call)."""
    saved = lib.INPUTS[task_id]
    lib.INPUTS[task_id] = inputs
    try:
        return benchlib.evaluate_source(lib, task_id, code)
    finally:
        lib.INPUTS[task_id] = saved


def _generate(lib, task, payload, notes, model, temp):
    body = payload + (("\n\n" + notes) if notes else "")
    return gen.extract_code(gen.call_model(gen.build_prompt(lib, task, body),
                                            model, temp, "5m", 512, 0.9))


def _payload(lib, lib_name, task, kind, rule):
    if kind == "B0":
        return ""
    if kind == "B1":
        return lib.API_LIST
    if kind == "B3":
        return lib.ORACLE_API_SEQUENCES[task["task_id"]]
    if kind == "B4":
        return gen.method_payload(lib, task, "B4_gold_pair_rule")
    if kind in ("B5_loop", "B5_llm", "B5_cert", "B4_loop"):
        return lib.API_LIST + (("\n\n" + rule) if rule else "")
    raise KeyError(kind)


_REFINE = ("B5_loop", "B5_llm", "B5_cert", "B4_loop")


def _seed_rule(lib, lib_name, task, kind, model):
    """Initial rule: Phi (B5_loop), LLM (B5_llm, high recall), or gold (B4_loop --
    the loop refining on top of gold). Baselines get no rule."""
    if kind == "B5_loop":
        return "\n\n".join(r["rule_text"] for r in rq.unvetted_rules(lib_name, task))
    if kind == "B5_llm":
        return "\n\n".join(r["rule_text"] for r in rq.llm_rules_for_task(lib_name, task, model))
    if kind == "B5_cert":
        return "\n\n".join(r["rule_text"] for r in llx.certified_rules_for_task(lib_name, task, model))
    if kind == "B4_loop":
        return gen.gold_rule_for_task(lib, task)
    return ""


def run_condition(lib, lib_name, task, kind, dev, held, model, temp, k):
    """Budget-K run; feedback on `dev`, evaluation on `held`. Returns held-out pass."""
    relation = task["pair_type"]
    rule = _seed_rule(lib, lib_name, task, kind, model)
    notes, final = "", ""
    for t in range(k):
        code = _generate(lib, task, _payload(lib, lib_name, task, kind, rule), notes, model, temp)
        final = code
        v = grade_on(lib, task["task_id"], code, dev)
        if v["ok"]:
            break                                    # dev passed -> stop (best-of-K)
        if kind in _REFINE:                          # typed refinement (the extra)
            verdict = {"exec_pass": False, "reason": v["reason"], "detail": v["detail"]}
            attr = fb.attribute(verdict, relation)
            if attr.target == "rule":
                rule, _ = fb.refine_rule(rule, attr, relation, t + 1)
            notes = fb.prompt_feedback(verdict, attr)
        # baselines: pure resample (no rule refinement, no prompt feedback)
    return bool(grade_on(lib, task["task_id"], final, held)["ok"])


def main():
    ap = argparse.ArgumentParser(description="Fair leakage-free closed-loop eval.")
    ap.add_argument("--libs", default="simplug,glom")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--runs", type=int, default=1, help="repeat N times; report mean rate")
    ap.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS),
                    help=f"comma-separated subset of {ALL_CONDITIONS}")
    args = ap.parse_args()
    libs = [s for s in args.libs.split(",") if s]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in ALL_CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown condition(s) {unknown}; choose from {ALL_CONDITIONS}")
    tasks = [(importlib.import_module(f"lib_{ln}"), ln, t)
             for ln in libs for t in importlib.import_module(f"lib_{ln}").TASKS
             if len(importlib.import_module(f"lib_{ln}").INPUTS[t["task_id"]]) >= 2]

    totals = {c: 0 for c in conditions}
    print(f"\n# Fair closed-loop (dev-feedback / held-out eval), K={args.k}, "
          f"runs={args.runs}, model={args.model}")
    print(f"conditions: {', '.join(conditions)}\n")
    print(f"splittable tasks: {len(tasks)}  ({', '.join(sorted({t['task_id'][:t['task_id'].index('-')] for _,_,t in tasks}))})")
    for r in range(args.runs):
        for lib, lib_name, task in tasks:
            inputs = lib.INPUTS[task["task_id"]]
            dev, held = inputs[:1], inputs[1:]
            for c in conditions:
                totals[c] += int(run_condition(lib, lib_name, task, c, dev, held,
                                               args.model, args.temperature, args.k))
        print(f"  run {r+1}/{args.runs} done", flush=True)

    denom = len(tasks) * args.runs
    print("\n## Held-out pass rate (fair, equal budget K, mean over runs)")
    for c in conditions:
        print(f"  {c:<9}: {totals[c]}/{denom} = {totals[c]/denom:.3f}")
    if "B4" in totals:
        for c in conditions:
            if c != "B4":
                print(f"  {c} - B4 = {(totals[c]-totals['B4'])/denom:+.3f}")


if __name__ == "__main__":
    main()
