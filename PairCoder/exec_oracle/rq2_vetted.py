#!/usr/bin/env python3
r"""RQ2 (vetted vs unvetted B5): does witness-probe vetting of the extracted rules
improve DOWNSTREAM generation, not just RQ1 precision?

Two conditions, identical except for the injected pair rule(s):
    unvetted-B5   API_LIST  (+)  Phi top-K extracted rules for the task relation
    vetted-B5     API_LIST  (+)  the same rules AFTER witness-probe filtering

Offline mode (default, no model needed): the INJECTION DIFFERENTIAL -- on how many
tasks vetting changes the injected rule, how many removed rules were hallucinations
(FP by gold) vs true (TP), and how many tasks fall back to B1. This bounds where
vetting can possibly help downstream.

Live mode (--generate, needs Ollama): generate under both conditions, grade with
the execution oracle, and report paired pass rates + an exact McNemar test -- the
decisive number that turns the probe from a filter into a method.

    python rq2_vetted.py                       # offline differential (4 probed libs)
    python rq2_vetted.py --generate --model qwen2.5-coder:7b --runs 1
"""

from __future__ import annotations

import argparse
import importlib
import math

import pair_extractor as px
import witness_probe as wp
import eval_extraction as ee
import benchlib_generate as gen
import benchlib

PROBED_LIBS = ["sqlitedict", "bidict", "glom", "diot"]   # libs with probe coverage
_RULES: dict = {}


def lib_module(name):
    return importlib.import_module(f"lib_{name}")


def _extracted(lib_name):
    if lib_name not in _RULES:
        _RULES[lib_name] = px.extract_library(lib_name, platt=None)
    return _RULES[lib_name]


def _candidates(lib_name, relation):
    return sorted((r for r in _extracted(lib_name) if r["relation"] == relation),
                  key=lambda r: -r["score"])


def _topk(cands, keep=None, top_k=3):
    seen, out = set(), []
    for r in cands:
        k = tuple(sorted(r["anchors"]))
        if k in seen:
            continue
        seen.add(k)
        if keep is not None and not keep(r):
            continue
        out.append(r)
        if len(out) >= top_k:
            break
    return out


def unvetted_rules(lib_name, task):
    return _topk(_candidates(lib_name, task["pair_type"]))


def vetted_rules(lib_name, task, policy):
    verds = wp.vet_library(lib_name)

    def keep(r):
        v = verds[(r["relation"], tuple(sorted(r["anchors"])))][0]
        return wp.keep_rule(v, policy)

    return _topk(_candidates(lib_name, task["pair_type"]), keep=keep)


def _is_tp(lib_name, rule):
    return bool(ee._match_gold({"relation": rule["relation"], "anchors": rule["anchors"]}, lib_name))


def _payload(lib, rules):
    text = "\n\n".join(r["rule_text"] for r in rules)
    return lib.API_LIST + ("\n\n" + text if text else "")


# ---------------------------------------------------------------------------
# offline: injection differential
# ---------------------------------------------------------------------------
def offline(policy):
    print(f"\n# RQ2 injection differential (offline)  policy={policy}\n")
    print(f"{'lib':<11} {'task':<16} {'pair_type':<24} change")
    print("-" * 86)
    tot = changed = fp_removed = tp_removed = to_b1 = 0
    for lib_name in PROBED_LIBS:
        lib = lib_module(lib_name)
        for task in lib.TASKS:
            tot += 1
            U = unvetted_rules(lib_name, task)
            V = vetted_rules(lib_name, task, policy)
            ua = {tuple(sorted(r["anchors"])) for r in U}
            va = {tuple(sorted(r["anchors"])) for r in V}
            removed = [r for r in U if tuple(sorted(r["anchors"])) not in va]
            if ua == va:
                continue
            changed += 1
            fps = [r for r in removed if not _is_tp(lib_name, r)]
            tps = [r for r in removed if _is_tp(lib_name, r)]
            fp_removed += len(fps)
            tp_removed += len(tps)
            note = []
            if fps:
                note.append(f"-{len(fps)}FP")
            if tps:
                note.append(f"-{len(tps)}TP")
            if U and not V:
                to_b1 += 1
                note.append("->B1")
            print(f"{lib_name:<11} {task['task_id']:<16} {task['pair_type']:<24} {' '.join(note)}")
    print("\n## Summary")
    print(f"  tasks (4 probed libs)            : {tot}")
    print(f"  injection changed by vetting     : {changed}")
    print(f"  hallucinated rules removed (FP)  : {fp_removed}")
    print(f"  TRUE rules wrongly removed (TP)  : {tp_removed}   <-- must be ~0 (conservative)")
    print(f"  tasks falling back to B1 (no rule): {to_b1}")
    print("\n  (Live downstream pass-rate effect is bounded to the "
          f"{changed} changed tasks; run --generate with Ollama for the number.)")


# ---------------------------------------------------------------------------
# live: paired generation + oracle + McNemar  (needs Ollama)
# ---------------------------------------------------------------------------
def _mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n) * 2
    return min(1.0, p)


def _generate_grade(lib, task, rules, model, temperature, runs):
    payload = _payload(lib, rules)
    prompt = gen.build_prompt(lib, task, payload)
    passes = 0
    for _ in range(runs):
        raw = gen.call_model(prompt, model, temperature, "5m", 512, 0.9)
        code = gen.extract_code(raw)
        verdict = benchlib.evaluate_source(lib, task["task_id"], code)
        passes += int(bool(verdict.get("ok")))
    return passes >= (runs + 1) // 2          # majority vote over runs


def live(policy, model, runs, temperature):
    print(f"\n# RQ2 vetted vs unvetted B5 (live)  model={model} runs={runs} policy={policy}\n")
    rows, b, c = [], 0, 0   # b: vetted pass & unvetted fail ; c: the reverse
    u_pass = v_pass = n = 0
    for lib_name in PROBED_LIBS:
        lib = lib_module(lib_name)
        for task in lib.TASKS:
            U = unvetted_rules(lib_name, task)
            V = vetted_rules(lib_name, task, policy)
            same = ({tuple(sorted(r["anchors"])) for r in U}
                    == {tuple(sorted(r["anchors"])) for r in V})
            up = _generate_grade(lib, task, U, model, temperature, runs)
            # identical injection -> identical condition: reuse the same generation
            # so spurious sampling noise can't create discordant pairs.
            vp = up if same else _generate_grade(lib, task, V, model, temperature, runs)
            n += 1
            u_pass += up
            v_pass += vp
            if vp and not up:
                b += 1
            if up and not vp:
                c += 1
            mark = ("=" if same else "·") if up == vp else ("V+" if vp else "U+")
            rows.append((lib_name, task["task_id"], up, vp, mark))
    print(f"{'lib':<11} {'task':<16} {'unvet':<6} {'vet':<5} delta")
    print("-" * 50)
    for lib_name, tid, up, vp, mark in rows:
        print(f"{lib_name:<11} {tid:<16} {int(up):<6} {int(vp):<5} {mark}")
    print("\n## Result")
    print(f"  unvetted-B5 pass: {u_pass}/{n} = {u_pass/n:.3f}")
    print(f"  vetted-B5   pass: {v_pass}/{n} = {v_pass/n:.3f}")
    print(f"  discordant: vetted-only={b}  unvetted-only={c}")
    print(f"  McNemar exact two-sided p = {_mcnemar_exact(b, c):.4g}")


def _has_fp(lib_name, rules):
    return any(not _is_tp(lib_name, r) for r in rules)


def diagnose(model, runs, temperature):
    """B1 vs unvetted-B5 vs vetted-B5 (conservative). Answers: do injected
    hallucinations HURT (any task where B5 < B1)?  Prompt-cache: each distinct
    prompt is generated once, so the three conditions are compared noise-free."""
    print(f"\n# Diagnosis: do hallucinations hurt?  model={model} runs={runs}\n")
    cache: dict = {}

    def grade(lib, task, rules):
        payload = _payload(lib, rules)
        prompt = gen.build_prompt(lib, task, payload)
        if prompt not in cache:
            passes = 0
            for _ in range(runs):
                code = gen.extract_code(gen.call_model(prompt, model, temperature, "5m", 512, 0.9))
                passes += int(bool(benchlib.evaluate_source(lib, task["task_id"], code).get("ok")))
            cache[prompt] = passes >= (runs + 1) // 2
        return cache[prompt]

    rows = []
    b1p = uvp = vp = n = 0
    hurt = helped = 0
    for lib_name in PROBED_LIBS:
        lib = lib_module(lib_name)
        for task in lib.TASKS:
            U = unvetted_rules(lib_name, task)
            V = vetted_rules(lib_name, task, "conservative")
            r_b1 = grade(lib, task, [])              # B1: API list only
            r_uv = grade(lib, task, U)               # unvetted-B5
            r_v = grade(lib, task, V)                # vetted-B5
            n += 1
            b1p += r_b1; uvp += r_uv; vp += r_v
            fp = _has_fp(lib_name, U)
            if r_uv < r_b1:
                hurt += 1
            if r_uv > r_b1:
                helped += 1
            rows.append((lib_name, task["task_id"], int(r_b1), int(r_uv), int(r_v), fp))

    print(f"{'lib':<11} {'task':<16} {'B1':<3} {'uvB5':<5} {'vB5':<4} {'FP?':<4} flag")
    print("-" * 64)
    for lib_name, tid, rb1, ruv, rv, fp in rows:
        flag = ""
        if ruv < rb1:
            flag = "<-- B5 HURT by rules"
        elif ruv > rb1:
            flag = "rules helped"
        print(f"{lib_name:<11} {tid:<16} {rb1:<3} {ruv:<5} {rv:<4} {('yes' if fp else '-'):<4} {flag}")
    print("\n## Result")
    print(f"  B1          pass: {b1p}/{n} = {b1p/n:.3f}")
    print(f"  unvetted-B5 pass: {uvp}/{n} = {uvp/n:.3f}")
    print(f"  vetted-B5   pass: {vp}/{n} = {vp/n:.3f}")
    print(f"  tasks where hallucinated rules HURT (B5<B1): {hurt}")
    print(f"  tasks where rules HELPED (B5>B1)           : {helped}")
    if hurt == 0:
        print("\n  => hallucinations are HARMLESS here: precision-filtering has no "
              "downstream job. The B5<B4 gap is a RECALL problem, not precision.")


def llm_rules_for_task(lib_name, task, model, top_k=3):
    import llm_extract as llx
    data = llx.propose(lib_name, model, use_cache=True)
    return [p for p in data["proposals"] if p["relation"] == task["pair_type"]][:top_k]


def regime(libs, model, runs, temperature, include_llm=False):
    """B1 vs unvetted-B5 vs B4(gold) on the given libs. Decides whether extraction
    quality can matter downstream AT ALL: if B4 >> B1, rules help (room to improve
    extraction); if B4 ~ B1, the model is high-prior here and no extraction work
    (precision OR recall) can show value."""
    print(f"\n# Regime test: does rule injection help?  libs={libs} model={model} runs={runs}\n")
    cache: dict = {}

    def grade(lib, task, payload):
        prompt = gen.build_prompt(lib, task, payload)
        if prompt not in cache:
            passes = 0
            for _ in range(runs):
                code = gen.extract_code(gen.call_model(prompt, model, temperature, "5m", 512, 0.9))
                passes += int(bool(benchlib.evaluate_source(lib, task["task_id"], code).get("ok")))
            cache[prompt] = passes >= (runs + 1) // 2
        return cache[prompt]

    lcol = f"{'LLM':<4}" if include_llm else ""
    print(f"{'lib':<12} {'task':<18} {'B1':<3} {'B5':<3} {lcol}{'B4':<3}")
    print("-" * 52)
    b1 = b5 = bl = b4 = n = 0
    for lib_name in libs:
        lib = lib_module(lib_name)
        for task in lib.TASKS:
            r1 = grade(lib, task, lib.API_LIST)
            r5 = grade(lib, task, _payload(lib, unvetted_rules(lib_name, task)))
            rl = grade(lib, task, _payload(lib, llm_rules_for_task(lib_name, task, model))) if include_llm else 0
            r4 = grade(lib, task, gen.method_payload(lib, task, "B4_gold_pair_rule"))
            n += 1; b1 += r1; b5 += r5; bl += rl; b4 += r4
            lc = f"{int(rl):<4}" if include_llm else ""
            print(f"{lib_name:<12} {task['task_id']:<18} {int(r1):<3} {int(r5):<3} {lc}{int(r4):<3}")
    print("\n## Result")
    print(f"  B1 (api only)     : {b1}/{n} = {b1/n:.3f}")
    print(f"  static-Phi B5     : {b5}/{n} = {b5/n:.3f}   (B5-B1 = {(b5-b1)/n:+.3f})")
    if include_llm:
        print(f"  LLM-proposed B5   : {bl}/{n} = {bl/n:.3f}   (LLM-B1 = {(bl-b1)/n:+.3f})")
    print(f"  B4 (gold rule)    : {b4}/{n} = {b4/n:.3f}   (B4-B1 = {(b4-b1)/n:+.3f})")


def main():
    ap = argparse.ArgumentParser(description="RQ2 vetted vs unvetted B5.")
    ap.add_argument("--policy", choices=["strict", "conservative"], default="conservative")
    ap.add_argument("--generate", action="store_true", help="live mode (needs Ollama)")
    ap.add_argument("--diagnose", action="store_true", help="B1 vs unvetted vs vetted (needs Ollama)")
    ap.add_argument("--regime", help="comma libs: B1 vs B5 vs B4 gold (needs Ollama)")
    ap.add_argument("--llm", action="store_true", help="add LLM-proposed-B5 column to regime")
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()
    if args.regime:
        regime([s for s in args.regime.split(",") if s], args.model, args.runs,
               args.temperature, include_llm=args.llm)
    elif args.diagnose:
        diagnose(args.model, args.runs, args.temperature)
    elif args.generate:
        live(args.policy, args.model, args.runs, args.temperature)
    else:
        offline(args.policy)


if __name__ == "__main__":
    main()
