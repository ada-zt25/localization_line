import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""L0 — RQ4 OFFLINE ceiling (NO GPU/LLM). On the FROZEN subsets, ablate every way the def-use ranker
can use coverage, to find the maximal line-recall lift coverage can give *before* the LLM vote, verify
the method, and pick the frozen delta for the GPU run.

Arms (file-given, def-use ranker `code_graph.line_scores_v2`):
  A static       : use_coverage=False                       (paired baseline)
  B filter       : rank by A, keep only executed lines        (the proven +14pp)
  C score        : use_coverage=True (delta term), NO filter
  D filter+score : rank by use_coverage=True, then keep executed
  E{d} delta     : D with delta in {0.8,1.5,3,6}              (best coverage weight)
  F coverage-max : D at the best delta (= the GPU-frozen offline method)
Outputs per-subset R@{1,5,10}+MRR+size and a paired bootstrap 95% CI of Delta(F-A) on S1."""
import json, os, random, statistics as st
import p0_line_recall as p0
import code_graph as cg

SUB = json.load(open("rq4/frozen_subsets.json"))
ISSUE = {r["instance_id"]: (r.get("problem_statement") or "")[:5000] for r in p0.load_rows(500, dataset="lite")}
DELTAS = [0.8, 1.5, 3.0, 6.0]
SUBKEYS = ["S1_crash_onpath", "S2_behav_onpath", "S3_crash_offpath", "S4_behav_offpath"]

def hit(rk, gold, k): return 1 if (set(rk[:k]) & gold) else 0
def rr(rk, gold):
    for i, l in enumerate(rk, 1):
        if l in gold: return 1.0 / i
    return 0.0
def rank(scores, ex=None):
    rk = sorted(scores, key=lambda l: (-scores[l], l))
    return [l for l in rk if l in ex] if ex is not None else rk

REC = {s: [] for s in SUBKEYS}
for skey in SUBKEYS:
    for it in SUB[skey]:
        gold = sorted(set(it["gold_lines"])); ex = set(it["exec_lines"]); issue = ISSUE.get(it["instance_id"], "")
        try:
            src = p0.fetch_file(it["repo"], it["base_commit"], it["gold_file"])
            G = cg.CodeGraph(src, it["gold_file"])
            if not getattr(G, "ok", False): continue
            sA = G.line_scores_v2(issue, use_coverage=False)
            if not sA: continue
            sD = G.line_scores_v2(issue, coverage_lines=ex, use_coverage=True)
            rankA = rank(sA)
            rec = {"iid": it["instance_id"], "gold": gold,
                   "A": rankA, "B": [l for l in rankA if l in ex], "C": rank(sD), "D": rank(sD, ex)}
            for d in DELTAS:
                rec[f"E{d}"] = rank(G.line_scores_v2(issue, coverage_lines=ex, use_coverage=True, delta=d), ex)
            REC[skey].append(rec)
        except Exception:
            continue

ARMS = ["A", "B", "C", "D"] + [f"E{d}" for d in DELTAS]
def agg(recs, arm):
    if not recs: return None
    g = [set(r["gold"]) for r in recs]
    R = {k: 100*st.mean([hit(r[arm], gg, k) for r, gg in zip(recs, g)]) for k in (1, 5, 10)}
    R["MRR"] = round(st.mean([rr(r[arm], gg) for r, gg in zip(recs, g)]), 3)
    R["size"] = round(st.mean([len(r[arm]) for r in recs]), 0)
    return {k: (round(v, 1) if k in (1, 5, 10) else v) for k, v in R.items()}

print("RQ4 离线天花板：def-use 排序器的 coverage 消融（frozen 子集，file-given，无 LLM）\n")
hd = f"{'臂':<8}{'R@1':>7}{'R@5':>7}{'R@10':>7}{'MRR':>7}{'候选':>7}"
for skey in SUBKEYS:
    recs = REC[skey]; print(f"[{skey}]  n={len(recs)}"); print(hd); print("-"*len(hd))
    for arm in ARMS:
        a = agg(recs, arm)
        if a: print(f"{arm:<8}{a[1]:>7.1f}{a[5]:>7.1f}{a[10]:>7.1f}{a['MRR']:>7.3f}{a['size']:>7.0f}")
    print()

s1 = REC["S1_crash_onpath"]
bestE = max(DELTAS, key=lambda d: agg(s1, f"E{d}")[10]) if s1 else DELTAS[0]
F_ARM = f"E{bestE}"
print(f">>> 最优 coverage 权重 delta* = {bestE}  →  F(coverage-max offline) = filter+score @ delta={bestE}\n")

def boot_ci(recs, arm, base, k, N=10000, seed=12345):
    rng = random.Random(seed); gold = [set(r["gold"]) for r in recs]
    dh = [hit(r[arm], gg, k) - hit(r[base], gg, k) for r, gg in zip(recs, gold)]
    n = len(dh); pt = 100*st.mean(dh)
    bs = sorted(100*st.mean([dh[rng.randrange(n)] for _ in range(n)]) for _ in range(N))
    return pt, bs[int(0.025*N)], bs[int(0.975*N)]
print("=== S1 主结论：Δ(F − A) 配对 bootstrap 95% CI（10000 重采样）===")
sig = {}
for k in (1, 5, 10):
    pt, lo, hi = boot_ci(s1, F_ARM, "A", k)
    sig[f"R@{k}"] = {"delta_pp": round(pt, 1), "ci95": [round(lo, 1), round(hi, 1)], "sig": lo > 0}
    print(f"  R@{k}: Δ = {pt:+.1f}pp   95%CI [{lo:+.1f}, {hi:+.1f}]{'  *** 下界>0' if lo > 0 else '  (含0)'}")

out = {"config": {"arms": ARMS, "deltas": DELTAS, "F_arm": F_ARM, "best_delta": bestE},
       "model": "offline-defuse-noLLM", "counts": {s: len(REC[s]) for s in SUBKEYS},
       "summary": {s: {arm: agg(REC[s], arm) for arm in ARMS if agg(REC[s], arm)} for s in SUBKEYS},
       "S1_significance_F_minus_A": sig,
       "S1_per_instance": [{"iid": r["iid"], "gold": r["gold"],
                            **{arm: {str(k): hit(r[arm], set(r["gold"]), k) for k in (1, 5, 10)} for arm in ARMS}}
                           for r in s1]}
os.makedirs("rq4/results", exist_ok=True)
json.dump(out, open("rq4/results/lineloc_offline.json", "w"), indent=1)
print("\n→ 写出 rq4/results/lineloc_offline.json")
