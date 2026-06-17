#!/usr/bin/env python3
r"""LLM-proposes-from-docs pair-rule extractor  (high-recall stage of B5+).

The static extractor Phi (pair_extractor.py) is high-precision / LOW-RECALL: on the
low-prior libraries it misses the return-flow / shared-receiver / param rules that
actually help downstream (regime test: gold B4-B1=+0.179 but static B5-B1=+0.036,
5/6 of the gap = EMPTY extraction). This module recovers recall by asking an LLM to
propose the typed pairwise constraints from ONLY the library's docs (API_LIST +
RAW_API_DOCS) -- never the gold rules or hidden tests. The proposals are HIGH-RECALL
but NOISY; the witness probe (witness_probe.py) then certifies each by execution,
so the LLM proposes and reality certifies.

Test-free, same evidence class as Phi: docstrings / API list only.

    python llm_extract.py --lib simpleconf            # propose + probe verdicts
    python llm_extract.py --lib simplug --no-cache
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
from pathlib import Path

import benchlib_generate as gen
import witness_probe as wp
import pair_extractor as px

RELATIONS = set(px.RELATIONS)
_CACHE_DIR = Path(__file__).resolve().parent.parent / "result" / "llm_extract"

_PROMPT = """You are analyzing the {name} Python library. Using ONLY the API list and \
docs below, list the PAIRWISE API composition constraints: cases where two specific \
APIs must be combined in a particular way, or the code fails / misbehaves at runtime.

Output ONE line per constraint, EXACTLY in this format (no extra prose):
RELATION: <one of param-dependency|return-flow|shared-receiver|config-return-contract|lifecycle|completion-obligation> | APIS: <ApiOne>, <ApiTwo> | RULE: <one sentence>

Guidance on the relation types:
- param-dependency: a parameter/variant choice decides which paired operation is correct.
- return-flow: the value produced by one call must be fed into / navigated by the next.
- shared-receiver: two calls must act on the SAME object (a live view / same receiver).
- config-return-contract: an argument/spec decides the return TYPE or shape.
- lifecycle: order/scope matters (temporary vs persistent, immutable, atomic).
- completion-obligation: a staged op must be paired with a discharge call to take effect.

Only use APIs shown below. Prefer concrete method/attribute names.

API list:
{api}

Docs:
{docs}
"""

_LINE = re.compile(
    r"RELATION:\s*(?P<rel>[a-z\-]+)\s*\|\s*APIS:\s*(?P<apis>.+?)\s*\|\s*RULE:\s*(?P<rule>.+)",
    re.I)


def _norm_anchors(apis: str):
    """Pull API tokens from the APIS field, keeping dotted names, dropping call args."""
    out = []
    for tok in re.split(r"[,\s]+", apis.strip()):
        tok = tok.strip().strip("`'\"")
        tok = re.sub(r"\(.*?\)", "", tok)          # drop (args)
        tok = tok.strip(".")
        if re.fullmatch(r"[A-Za-z_][\w.]*", tok):
            out.append(tok)
    return out


def _wrap_rule(rel: str, rule: str) -> str:
    return ("Relevant API Pair Rule (LLM-proposed):\n"
            f"Relation: {rel}\nConstraint: {rule.strip()}")


def _parse(text: str):
    proposals = []
    for line in text.splitlines():
        m = _LINE.search(line)
        if not m:
            continue
        rel = m.group("rel").lower().strip()
        if rel not in RELATIONS:
            continue
        anchors = _norm_anchors(m.group("apis"))
        if not anchors:
            continue
        proposals.append({"relation": rel, "anchors": anchors,
                          "rule_text": _wrap_rule(rel, m.group("rule")),
                          "rule": m.group("rule").strip()})
    return proposals


def propose(lib_name: str, model: str, use_cache=True, temperature=0.2):
    """LLM proposals for a library (cached to result/llm_extract for reproducibility)."""
    cache = _CACHE_DIR / f"{lib_name}__{gen.safe_name(model)}.json"
    if use_cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    lib = importlib.import_module(f"lib_{lib_name}")
    prompt = _PROMPT.format(name=lib_name, api=lib.API_LIST,
                            docs=getattr(lib, "RAW_API_DOCS", ""))
    raw = gen.call_model(prompt, model, temperature, "5m", 800, 0.9)
    proposals = _parse(raw)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"raw": raw, "proposals": proposals}, indent=2,
                                ensure_ascii=False), encoding="utf-8")
    return {"raw": raw, "proposals": proposals}


def certify(lib_name: str, proposals):
    """Attach the (hand-written) witness-probe verdict to each LLM proposal."""
    ns = px.Evidence(lib_name).namespace
    for p in proposals:
        v, d = wp.verdict_for_rule(ns, p["relation"], p["anchors"])
        p["verdict"], p["detail"] = v, d
    return proposals


# ---------------------------------------------------------------------------
# General certifier: the LLM also WRITES the witness programs; real execution
# is the arbiter. Handles arbitrary proposals (incl. return-flow) without any
# author-written per-library synthesis -- model proposes hypothesis AND
# experiment, reality certifies.
# ---------------------------------------------------------------------------
_WITNESS_PROMPT = """You are testing whether a claimed rule about the {name} library is REAL.

Available (already imported, do not import): {helper}

{name} API reference (use ONLY these APIs; match their exact names and calling conventions):
{api}

Docs:
{docs}

Claimed rule:
{rule}

Write TWO Python functions that take no arguments:
- compliant(): uses the APIs in a way that FOLLOWS the rule, and RETURNS an observable result.
- violating(): does the same task but BREAKS the rule (wrong order / fresh object / missing pair / wrong variant), and RETURNS its observable result (or let it raise).

If the rule is real, compliant() and violating() must OBSERVABLY DIFFER (different return value, or violating() raises while compliant() does not). Use only the available objects. Return ONLY the two function definitions, no prose, no markdown fences.
"""


def _run_fn(code: str, fn: str, ns: dict):
    g = dict(ns)
    try:
        exec(code, g)                       # noqa: S102 (sandboxed namespace, prototype)
        return ("ok", g[fn]())
    except Exception as exc:
        return ("err", repr(exc))


def certify_by_witness(lib_name, proposal, model, ns, temperature=0.2):
    """LLM writes compliant()/violating(); execution decides FIRES/NO_DIVERGENCE/ABSTAIN."""
    lib = importlib.import_module(f"lib_{lib_name}")
    prompt = _WITNESS_PROMPT.format(name=lib_name, helper=lib.HELPER_LINE,
                                    api=lib.API_LIST, docs=getattr(lib, "RAW_API_DOCS", ""),
                                    rule=proposal["rule_text"])
    code = gen.extract_code(gen.call_model(prompt, model, temperature, "5m", 800, 0.9))
    comp = _run_fn(code, "compliant", ns)
    viol = _run_fn(code, "violating", ns)
    if comp[0] != "ok":
        return "ABSTAIN", f"compliant() did not run: {comp[1]}", code
    if viol[0] == "err":
        return "FIRES", f"violating() raises while compliant() returns {comp[1]!r}", code
    if comp[1] != viol[1]:
        return "FIRES", f"compliant={comp[1]!r} vs violating={viol[1]!r}", code
    return "NO_DIVERGENCE", f"both return {comp[1]!r}", code


# ---------------------------------------------------------------------------
# LLM-propose + execution-certify, as a seed-rule provider for the fair B5 loop.
# Cached per (lib, model) so the (expensive) witness step runs once per library.
# ---------------------------------------------------------------------------
_KEEP = {"strict": {"FIRES"}, "lenient": {"FIRES", "ABSTAIN"}}


def certified_proposals(lib_name, model, use_cache=True, temperature=0.2):
    """LLM-propose (from docs) then execution-certify each via LLM-written
    witness programs. Returns proposals tagged with a 'witness' verdict
    (FIRES / NO_DIVERGENCE / ABSTAIN). Cached per (lib, model). Test-free:
    only the library + its docs are touched, never gold rules or hidden tests."""
    cache = _CACHE_DIR / f"{lib_name}__{gen.safe_name(model)}__certified.json"
    if use_cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    proposals = propose(lib_name, model, use_cache=use_cache, temperature=temperature)["proposals"]
    ns = px.Evidence(lib_name).namespace
    for p in proposals:
        v, d, _code = certify_by_witness(lib_name, p, model, ns, temperature=temperature)
        p["witness"], p["witness_detail"] = v, d
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(proposals, indent=2, ensure_ascii=False), encoding="utf-8")
    return proposals


def certified_rules_for_task(lib_name, task, model, top_k=3, policy="lenient", use_cache=True):
    """Certified LLM rules for a task's relation: keep those the witness probe did
    NOT disprove. policy='lenient' drops only proven-inert (NO_DIVERGENCE) rules;
    'strict' keeps only FIRES."""
    keep = _KEEP[policy]
    props = certified_proposals(lib_name, model, use_cache=use_cache)
    rel = task["pair_type"]
    out = [p for p in props if p["relation"] == rel and p.get("witness") in keep]
    return out[:top_k]


def main():
    ap = argparse.ArgumentParser(description="LLM-proposes-from-docs pair rules + probe certify.")
    ap.add_argument("--lib", required=True)
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--witness", action="store_true",
                    help="certify by LLM-written witness programs + execution (general)")
    args = ap.parse_args()

    data = propose(args.lib, args.model, use_cache=not args.no_cache)
    proposals = data["proposals"]
    print(f"\n# LLM-proposed pair rules for '{args.lib}'  ({len(proposals)} parsed)\n")
    if args.witness:
        ns = px.Evidence(args.lib).namespace
        print(f"{'relation':<22} {'witness':<14} apis / detail")
        print("-" * 84)
        for p in proposals:
            v, d, _ = certify_by_witness(args.lib, p, args.model, ns)
            p["witness"] = v
            print(f"{p['relation']:<22} {v:<14} {p['anchors']}")
            print(f"{'':<22} -> {d[:88]}")
        from collections import Counter
        print(f"\nwitness verdicts: {dict(Counter(p['witness'] for p in proposals))}")
    else:
        certify(args.lib, proposals)
        print(f"{'relation':<24} {'probe':<14} apis")
        print("-" * 80)
        for p in proposals:
            print(f"{p['relation']:<24} {p['verdict']:<14} {p['anchors']}")
            print(f"{'':<24} -> {p['rule'][:90]}")
        from collections import Counter
        print(f"\nprobe verdicts: {dict(Counter(p['verdict'] for p in proposals))}")


if __name__ == "__main__":
    main()
