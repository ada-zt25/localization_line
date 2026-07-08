#!/usr/bin/env python3
"""
M_hetero — heterogeneous strong-verifier UPPER-BOUND ablation arm (RQ4).

Guardrail compliance (RQ4_SPEC.md §7, changelog v5):
  * Explicitly an UPPER BOUND (oracle selection), never a same-model gain.
  * S1 = crash on-path, file-given, n=57 (frozen; read-only).
  * Base backbone unchanged (Qwen2.5-Coder-32B M4 = ours_dynamic).
  * No new model calls: computed purely from the cached per-instance hits of
    the four backbones already run (T2). Deployable verifier = future work.

Question it answers: is the R@1/R@5 "discrimination ceiling" that same-model
self-consistency hits (RQ3.4) intrinsic to the task, or a *weak-verifier*
ceiling? We upper-bound what an ideal heterogeneous verifier could recover by
oracle-selecting, per instance, whichever of {base, a stronger heterogeneous
model} ranks a gold line higher. If the union lifts R@1/R@5 well above the base,
the ceiling is (partly) verifier-imposed and a heterogeneous verifier is worth
building; if it barely moves, the ceiling is intrinsic.
"""
import json, os, subprocess, random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARM = "ours_dynamic"          # = M4 (coverage-max) per RQ4_SPEC §4b
KS = ("R@1", "R@5", "R@10")
SEED = 20260701
N_BOOT = 10000

BACKENDS = {
    "Qwen2.5-Coder-32B": "results/passB_covnarrow.json",              # base
    "DeepSeek-V3.2":     "results_deepseek-ai_DeepSeek-V3.2/passB_covnarrow.json",
    "Qwen3.6-27B":       "results_Qwen_Qwen3.6-27B/passB_covnarrow.json",
    "GLM-4.5-Air":       "results_zai-org_GLM-4.5-Air/passB_covnarrow.json",
}
BASE = "Qwen2.5-Coder-32B"
STRONG = "DeepSeek-V3.2"       # single strongest heterogeneous verifier (highest M0/M4 R@10)


def load_hits(rel):
    d = json.load(open(HERE / rel))["results"]
    items = d.values() if isinstance(d, dict) else d
    out = {}
    for it in items:
        a = it["arms"][ARM]
        out[it["instance_id"]] = {k: int(a[k] > 0) for k in KS}   # per-instance hit@k in {0,1}
    return out


def rate(hits, ids, k):
    return 100.0 * sum(hits[i][k] for i in ids) / len(ids)


def union_hits(members, ids, k):
    # oracle selection: instance is a hit@k if ANY member surfaces a gold line in top-k
    return [int(any(m[i][k] for m in members)) for i in ids]


def paired_boot_delta(ids, k, base_hits, ub_members):
    # deterministic seed per endpoint (hash() is per-process randomized -> not reproducible)
    rng = random.Random(SEED + KS.index(k))
    n = len(ids)
    base_arr = [base_hits[i][k] for i in ids]
    ub_arr = union_hits(ub_members, ids, k)
    deltas = []
    for _ in range(N_BOOT):
        s = [rng.randrange(n) for _ in range(n)]
        db = sum(base_arr[j] for j in s) / n
        du = sum(ub_arr[j] for j in s) / n
        deltas.append(100.0 * (du - db))
    deltas.sort()
    lo = deltas[int(0.025 * N_BOOT)]
    hi = deltas[int(0.975 * N_BOOT)]
    return round(lo, 1), round(hi, 1)


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=HERE, text=True).strip()
    except Exception:
        return "unknown"


def main():
    hits = {name: load_hits(rel) for name, rel in BACKENDS.items()}
    S1 = json.load(open(HERE / "results/S1_ids.json"))
    S1 = S1 if isinstance(S1, list) else (S1.get("ids") or list(S1.values())[0])
    S1 = [i for i in S1 if all(i in hits[b] for b in BACKENDS)]
    n = len(S1)

    base = hits[BASE]
    strong = hits[STRONG]

    metrics = {"n": n, "base_backbone": BASE, "strong_verifier": STRONG}
    # base (Qwen2.5 M4)
    metrics["base_M4"] = {k: round(rate(base, S1, k), 1) for k in KS}
    # single stronger heterogeneous verifier alone (context)
    metrics["strong_M4"] = {k: round(rate(strong, S1, k), 1) for k in KS}

    # headline UB: oracle union of base + single strongest heterogeneous verifier
    ub2 = {k: round(100.0 * sum(union_hits([base, strong], S1, k)) / n, 1) for k in KS}
    metrics["UB_base_plus_strong"] = ub2
    # loosest UB: oracle union over ALL four backbones (best-of-fleet)
    allm = [hits[b] for b in BACKENDS]
    ubA = {k: round(100.0 * sum(union_hits(allm, S1, k)) / n, 1) for k in KS}
    metrics["UB_best_of_fleet"] = ubA

    # deltas + paired bootstrap CI (UB_base_plus_strong  minus  base_M4)
    metrics["delta_UB_vs_base"] = {}
    for k in KS:
        d = round(ub2[k] - metrics["base_M4"][k], 1)
        lo, hi = paired_boot_delta(S1, k, base, [base, strong])
        metrics["delta_UB_vs_base"][k] = {"delta_pp": d, "ci95": [lo, hi],
                                          "sig": bool(lo > 0)}

    # per-instance hits for reproducibility / recomputation
    per_inst = {i: {"base": base[i], "strong": strong[i],
                    "ub2": {k: int(base[i][k] or strong[i][k]) for k in KS}} for i in S1}

    out = {
        "config": "M_hetero heterogeneous strong-verifier UPPER BOUND (oracle union), RQ4 ablation",
        "arm": "M_hetero_UB",
        "kind": "upper_bound_oracle_selection",
        "note": ("Explicit UPPER BOUND: per-instance oracle selection between the base "
                 "backbone and a stronger heterogeneous model; not a deployable gain. "
                 "No new model calls — computed from cached T2 per-instance hits."),
        "model": f"base={BASE}; verifier={STRONG}",
        "base_url": "offline (cached per-instance hits; no API call)",
        "git_sha": git_sha(),
        "n": n,
        "seed": SEED, "n_boot": N_BOOT,
        "metrics": metrics,
        "per_instance": per_inst,
    }
    outpath = HERE / "results" / "m_hetero_upper.json"
    json.dump(out, open(outpath, "w"), indent=2)

    # console summary
    print(f"S1 n={n}  base={BASE}  strong-verifier={STRONG}")
    print(f"{'k':>5} | {'base M4':>8} | {'strong M4':>9} | {'UB(base+strong)':>15} | {'Δ vs base':>18} | UB(best-of-fleet)")
    for k in KS:
        d = metrics["delta_UB_vs_base"][k]
        print(f"{k:>5} | {metrics['base_M4'][k]:>8} | {metrics['strong_M4'][k]:>9} | "
              f"{ub2[k]:>15} | {d['delta_pp']:>+6} pp {str(d['ci95']):>10} | {ubA[k]}")
    print(f"\nwrote {outpath}")


if __name__ == "__main__":
    main()
