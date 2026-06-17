#!/usr/bin/env python3
r"""B5 closed loop: extract -> generate -> execute -> attribute failure -> refine -> regenerate.

The static extractor (pair_extractor.Phi) emits a typed pair rule once.  Real
extractions are imperfect (RQ1: precision ~0.5), so a wrong/incomplete rule can
mislead generation.  This module closes the loop with EXECUTION FEEDBACK:

    r_0 = Phi(lib, task)                                  # static extraction
    for t in 0..K-1:
        g_t      = LLM(prompt(API_LIST, r_t, notes_t))    # generate
        v_t      = Oracle(g_t)                            # execute hidden tests
        if v_t.pass: return (r_t, g_t, t)                 # fixpoint reached
        a_t      = Attribute(v_t)                         # failure -> coupling channel
        r_{t+1}  = Refine(r_t, a_t)                       # correct/strengthen the rule
        notes_{t+1} = PromptFeedback(v_t, a_t)            # or feed the error to the prompt

So the *complete* B5 = automatic extraction + failure attribution + feedback
regeneration.  Two scientific points make this a method, not just self-debugging:

  1. Attribution reuses the typed taxonomy.  The execution oracle's reason codes
     were DESIGNED per relation (wrong_output_structure<->config-return,
     state_not_restored/disable_not_persistent<->lifecycle, "same object"<->
     shared-receiver, ValueDuplicationError/PathAccessError<->param-dependency).
     So Attribute is the INVERSE of the same kappa bijection that drives Phi --
     failure is mapped back to the coupling channel it implicates, not guessed.

  2. Refinement is typed and self-correcting.  If the failure's channel == the
     extracted rule's channel, the rule was right and the model didn't comply ->
     strengthen it with a concrete "common mistake -> required behavior" clause.
     If the channel DIFFERS, the static extraction was incomplete -> ADD the
     implicated channel's clause.  Execution thereby *corrects the extraction*.
     A Beta(a,b) confidence is updated each round (pass: a+1, fail: b+1), giving
     a second, dynamic calibration signal on top of the static LOLO one.

Code-level failures (syntax/import/undefined-name) are not pair-constraint
violations; their feedback goes to the PROMPT (fix the code), not the rule.
This realises "inject the failure into the rule OR the prompt" -- the attribution
decides which.

CLI (offline, no Ollama):
    python b5_feedback.py --simulate --lib glom --task glom-G003   # full loop plumbing
    python b5_feedback.py --explain-failures --lib bidict          # attribute REAL verdicts
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import benchlib
import pair_extractor as px

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "benchlib_runner.py"

# ---------------------------------------------------------------------------
# Failure attribution: verdict  ->  implicated coupling channel (inverse kappa).
# ---------------------------------------------------------------------------
# Code-level errors are not pair-constraint violations -> feedback goes to prompt.
CODE_ERROR_REASONS = {
    "syntax_error", "import_time_error", "function_not_defined", "timeout", "harness_error",
}

# Reason codes that pin a relation unambiguously (they were defined per relation).
RELATION_BY_REASON = {
    "wrong_output_structure": "config-return-contract",
    "disable_not_persistent": "lifecycle",
    "state_not_restored": "lifecycle",
    "obligation_unmet": "lifecycle",
    "wrong_enabled_set": "shared-receiver",
    "mechanism_not_used": "shared-receiver",
    "no_score_call": "return-flow",
}

# For ambiguous reasons (runtime_error / wrong_output) read the detail string.
# Ordered: first cue that matches wins. Only STRONGLY discriminative cues appear
# here; an ambiguous exception (e.g. PathAccessError, which can be a missing-path
# param issue OR a wrong-spec config issue) is intentionally absent, so it defers
# to the task's extracted relation instead of overriding it.
DETAIL_CUES = [
    (r"in place|same object|same target|not mutated|same receiver|live view", "shared-receiver"),
    (r"DuplicationError|duplicat|already mapped|forceput", "param-dependency"),
    (r"FrozenError|\bfrozen\b|immutable|thaw|reverted|temporar|persistent", "lifecycle"),
    (r"cannot import name|is not defined|has no attribute|ImportError|AttributeError", "__code__"),
    (r"expected a |returned a |NoneType; expected|unsupported operand", "config-return-contract"),
]


@dataclass
class Attribution:
    kind: str            # "pair_violation" | "code_error"
    relation: str        # implicated coupling channel's relation (or "" for code_error)
    target: str          # "rule" | "prompt"
    reason: str
    cue: str             # short human-readable cue
    detail: str


def attribute(verdict: dict, extracted_relation: str = "") -> Attribution:
    reason = verdict.get("reason", "") or ""
    detail = verdict.get("detail", "") or ""

    if reason in CODE_ERROR_REASONS:
        return Attribution("code_error", "", "prompt", reason,
                           f"code-level error ({reason})", detail)

    rel = RELATION_BY_REASON.get(reason)
    if rel is None:                                   # runtime_error / wrong_output: use detail
        for pat, mapped in DETAIL_CUES:
            if re.search(pat, detail, re.I):
                rel = mapped
                break
    if rel == "__code__":                             # hallucinated/undefined API name
        return Attribution("code_error", "", "prompt", reason,
                           "used a non-existent API name", detail)
    if rel is None:                                   # last resort: reinforce the rule we had
        rel = extracted_relation or "return-flow"
    return Attribution("pair_violation", rel, "rule", reason,
                       f"violates {rel}", detail)


# ---------------------------------------------------------------------------
# Typed corrective clauses (keyed by the implicated relation).
# ---------------------------------------------------------------------------
_CORRECTIVE = {
    "param-dependency":
        "The previous attempt used the wrong argument/variant ({detail!s}). Choose the "
        "argument or method variant that handles the missing/duplicate case (e.g. a "
        "default value, a Coalesce of candidates, or a force-variant that drops the clash).",
    "return-flow":
        "The previous attempt produced the wrong value ({detail!s}). Feed the value produced "
        "by the first call into the second (chain/navigate); do not re-derive or short-circuit it.",
    "shared-receiver":
        "The previous attempt operated on a COPY ({detail!s}). Mutate and read back the SAME "
        "object that was passed in; a freshly rebuilt object will not reflect the change.",
    "config-return-contract":
        "The previous attempt returned the wrong TYPE/shape ({detail!s}). Pick the spec/argument "
        "that makes the return type match exactly; do not wrap a scalar in a list or index a "
        "single result as if it were a list.",
    "lifecycle":
        "The previous attempt broke temporary-vs-persistent scope ({detail!s}). Use the "
        "context-managed (temporary) form and let it revert on exit, or the persistent form, as "
        "the task requires; do not modify frozen state outside the provided scope.",
    "completion-obligation":
        "The previous attempt staged the operation but never discharged it ({detail!s}). After "
        "the write/update/delete you MUST call the discharge partner (e.g. commit) for it to take "
        "effect; close() or leaving a with-block does NOT discharge it.",
}


def refine_rule(rule_text: str, attr: Attribution, extracted_relation: str,
                round_idx: int) -> tuple[str, str]:
    """Return (refined_rule_text, kind_note). Same-relation -> strengthen;
    cross-relation -> ADD the implicated channel's clause (extraction was incomplete)."""
    clause = _CORRECTIVE[attr.relation].format(detail=attr.detail.strip()[:160])
    if attr.relation == extracted_relation:
        note = "strengthen (model did not comply with the correct rule)"
        header = f"\n[execution feedback, round {round_idx}] {note}:"
    else:
        note = f"correct (extraction missed the {attr.relation} channel)"
        header = (f"\n[execution feedback, round {round_idx}] {note} -- "
                  f"also enforce Relation: {attr.relation}:")
    return rule_text.rstrip() + header + "\n" + clause + "\n", note


def prompt_feedback(verdict: dict, attr: Attribution) -> str:
    """Short note appended to the prompt (for code-level errors, or as a hint
    alongside a rule refinement)."""
    return (f"NOTE: a previous attempt failed with {verdict.get('reason','')}: "
            f"{(verdict.get('detail','') or '').strip()[:200]}. Fix this and keep the "
            f"function signature unchanged.")


# ---------------------------------------------------------------------------
# Beta confidence: execution feedback as a dynamic calibration signal.
# ---------------------------------------------------------------------------
@dataclass
class BetaConfidence:
    a: float = 1.0
    b: float = 1.0

    def update(self, passed: bool):
        if passed:
            self.a += 1
        else:
            self.b += 1

    @property
    def value(self) -> float:
        return self.a / (self.a + self.b)


# ---------------------------------------------------------------------------
# Oracle adapters (local, no Ollama).
# ---------------------------------------------------------------------------
def oracle_inproc(lib_name: str, task_id: str, code: str) -> dict:
    """Run the hidden-test oracle in-process (use for trusted anchor code)."""
    lib = benchlib.load_lib(lib_name)
    res = benchlib.evaluate_source(lib, task_id, code)
    return {"exec_pass": res["ok"], "reason": res["reason"], "detail": res["detail"]}


def oracle_subprocess(lib_name: str, task_id: str, code: str) -> dict:
    """Run the oracle in an isolated subprocess (use for untrusted model code)."""
    with tempfile.TemporaryDirectory() as td:
        gen, out = Path(td) / "gen.py", Path(td) / "v.json"
        gen.write_text(code, encoding="utf-8")
        cmd = [sys.executable, str(RUNNER), "--lib", lib_name, "--task", task_id,
               "--gen", str(gen), "--out", str(out)]
        try:
            subprocess.run(cmd, cwd=str(HERE), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=60)
            return json.loads(out.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"exec_pass": False, "reason": "harness_error", "detail": repr(exc)}


# ---------------------------------------------------------------------------
# The closed-loop orchestrator.
# ---------------------------------------------------------------------------
@dataclass
class Round:
    idx: int
    rule: str
    passed: bool
    reason: str
    attribution: str
    confidence: float


@dataclass
class LoopResult:
    lib: str
    task: str
    extracted_relation: str
    passed: bool
    rounds_used: int
    final_confidence: float
    trace: list = field(default_factory=list)
    final_rule: str = ""
    final_code: str = ""


def run_loop(lib_name: str, task_id: str, initial_rule: str, extracted_relation: str,
             gen_fn, oracle_fn, k_max: int = 3) -> LoopResult:
    """gen_fn(rule_text, notes) -> code ;  oracle_fn(lib, task, code) -> verdict."""
    conf = BetaConfidence()
    rule, notes = initial_rule, ""
    trace = []
    passed, used = False, 0
    code = ""
    for t in range(k_max):
        used = t
        code = gen_fn(rule, notes)
        v = oracle_fn(lib_name, task_id, code)
        ok = bool(v.get("exec_pass"))
        conf.update(ok)
        if ok:
            trace.append(Round(t, rule, True, "", "pass", round(conf.value, 3)))
            passed = True
            break
        attr = attribute(v, extracted_relation)
        if attr.target == "rule":
            rule, note = refine_rule(rule, attr, extracted_relation, t + 1)
            notes = prompt_feedback(v, attr)
        else:
            note = "prompt-feedback (code error)"
            notes = prompt_feedback(v, attr)
        trace.append(Round(t, rule, False, v.get("reason", ""),
                           f"{attr.target}:{attr.relation or attr.reason} ({note})",
                           round(conf.value, 3)))
    return LoopResult(lib_name, task_id, extracted_relation, passed, used + 1,
                      round(conf.value, 3), trace, rule, code)


# ---------------------------------------------------------------------------
# Offline demo 1: full-loop plumbing with anchor code (violation -> canonical).
# ---------------------------------------------------------------------------
def _anchor_codes(lib, task_id):
    """(failing_code, passing_code) from the task's anchors: a violation then the canonical."""
    anchors = lib.ANCHORS[task_id]
    passing = next(c for (_n, c, exp) in anchors if exp is True)
    failing = next((c for (_n, c, exp) in anchors if exp is not True), None)
    return failing, passing


def simulate(lib_name: str, task_id: str, k_max: int = 3):
    lib = benchlib.load_lib(lib_name)
    failing, passing = _anchor_codes(lib, task_id)
    if failing is None:
        raise SystemExit(f"{task_id}: no violation anchor to simulate a failure")
    # static extraction: the rule Phi would emit for this task's relation
    task = next(t for t in lib.TASKS if t["task_id"] == task_id)
    relation = task["pair_type"]
    rules = px.extract_library(lib_name, platt=None)
    same = [r for r in rules if r["relation"] == relation]
    init_rule = (same[0]["rule_text"] if same
                 else f"Relevant API Pair Rule (auto-extracted):\nRelation: {relation}\n"
                      f"Constraint: (extractor produced no rule for this relation)")

    # simulate generation: round 0 returns the FAILING code; once the rule has been
    # refined (>=1 feedback round) the model 'fixes it' -> the PASSING code. This
    # exercises attribute->refine->terminate against the REAL oracle.
    state = {"n": 0}

    def gen_fn(rule_text, notes):
        code = failing if state["n"] == 0 else passing
        state["n"] += 1
        return code

    res = run_loop(lib_name, task_id, init_rule, relation, gen_fn, oracle_inproc, k_max)

    print(f"# B5 closed-loop simulation  {lib_name} / {task_id}  (relation={relation})\n")
    print("Initial extracted rule:")
    print("    " + init_rule.strip().replace("\n", "\n    ") + "\n")
    for r in res.trace:
        verdict = "PASS" if r.passed else f"FAIL[{r.reason}]"
        print(f"-- round {r.idx}: {verdict}   attribution: {r.attribution}   conf={r.confidence}")
    print(f"\nconverged={res.passed}  rounds_used={res.rounds_used}  "
          f"final_confidence={res.final_confidence}")
    print("\nFinal (refined) rule injected:")
    print("    " + res.final_rule.strip().replace("\n", "\n    "))


# ---------------------------------------------------------------------------
# Offline demo 2: attribute REAL recorded failures (no regeneration).
# ---------------------------------------------------------------------------
def explain_failures(lib_name: str, limit: int = 12):
    vdir = HERE.parent / "result" / f"{lib_name}_5model" / "exec_eval" / "verdicts"
    if not vdir.exists():
        raise SystemExit(f"no recorded verdicts at {vdir}")
    lib = benchlib.load_lib(lib_name)
    relation_of = {t["task_id"]: t["pair_type"] for t in lib.TASKS}   # per-task prior
    by_target = Counter()
    by_relation = Counter()
    shown = 0
    print(f"# Attribution of REAL recorded failures: {lib_name}\n")
    for f in sorted(vdir.glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        if v.get("exec_pass"):
            continue
        task_id = f.name.split("__", 1)[0]
        a = attribute(v, relation_of.get(task_id, ""))
        by_target[a.target] += 1
        by_relation[a.relation or f"code:{a.reason}"] += 1
        if shown < limit:
            print(f"  {f.name.split('__',1)[1][:46]:46}  {v.get('reason',''):18} -> "
                  f"{a.target}:{a.relation or a.reason}")
            shown += 1
    print(f"\nrouting: {dict(by_target)}")
    print(f"implicated channel / code: {dict(by_relation.most_common())}")


def main():
    ap = argparse.ArgumentParser(description="B5 closed loop: attribute -> refine -> regenerate.")
    ap.add_argument("--lib", required=True)
    ap.add_argument("--task", help="task id (for --simulate)")
    ap.add_argument("--simulate", action="store_true", help="full-loop plumbing demo (offline)")
    ap.add_argument("--explain-failures", action="store_true", help="attribute real recorded verdicts")
    ap.add_argument("--k-max", type=int, default=3)
    args = ap.parse_args()

    if args.simulate:
        if not args.task:
            raise SystemExit("--simulate needs --task")
        simulate(args.lib, args.task, args.k_max)
    elif args.explain_failures:
        explain_failures(args.lib)
    else:
        raise SystemExit("choose --simulate (with --task) or --explain-failures")


if __name__ == "__main__":
    main()
