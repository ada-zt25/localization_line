#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""RQ3-E3 evaluation: does SBFL (failing-vs-passing differential) beat the coverage-FILTER on the
on-path crash subset? Offline (NO GPU/LLM), file-given, def-use ranker as the static base. Arms:
  A = static def-use                          (no coverage)
  B = static ∩ failing-cov   (coverage-FILTER, RQ3-E1, the +14pp)
  D = SBFL-filter            (B, then fail-ONLY lines first via failing∖passing, ties by static)
Needs egl_cov_cache.json (failing) + egl_cov_cache_pass.json (passing; from rq3_collect_passing.py).
Reports R@{1,5,10}+MRR; only instances that HAVE passing coverage are counted for the SBFL arm."""
import json, re, statistics as st
import p0_line_recall as p0
import code_graph as cg
import sbfl

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
covF = json.load(open("egl_cov_cache.json"))
try: covP = json.load(open("egl_cov_cache_pass.json"))
except FileNotFoundError: covP = {}
sub = json.load(open("rq3_subsets.json"))["crash_onpath"]

def cov_for(f, cm):
    if f in cm: return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()
def hitk(rk, gold, k): return 1 if set(rk[:k]) & gold else 0
def rr(rk, gold):
    for i, l in enumerate(rk, 1):
        if l in gold: return 1.0 / i
    return 0.0

arms = {a: {1: [], 5: [], 10: [], "rr": []} for a in "ABD"}
n = n_withpass = 0
for iid in sub:
    r = rows.get(iid); cmF = covF.get(iid)
    if not (r and cmF): continue
    cmP = covP.get(iid)
    gf = p0.parse_patch(r.get("patch") or ""); issue = (r.get("problem_statement") or "")[:5000]
    f = next((x for x in gf if x.endswith(".py") and gf[x]["region"]), None)
    if not f: continue
    gold = set(gf[f]["region"]); exF = cov_for(f, cmF)
    if not (gold & exF): continue
    try:
        src = p0.fetch_file(r["repo"], r["base_commit"], f); G = cg.CodeGraph(src, f)
        if not getattr(G, "ok", False): continue
        sc = G.line_scores_v2(issue, use_coverage=False)
    except Exception: continue
    if not sc: continue
    n += 1
    rankA = sorted(sc, key=lambda l: (-sc[l], l))
    rankB = [l for l in rankA if l in exF]
    for a, rk in (("A", rankA), ("B", rankB)):
        for k in (1, 5, 10): arms[a][k].append(hitk(rk, gold, k))
        arms[a]["rr"].append(rr(rk, gold))
    # SBFL arm only when NON-EMPTY passing coverage exists (django/skipped -> {} excluded, not treated as "nothing passes")
    if cmP:
        exP = cov_for(f, cmP)
        rankD = sbfl.sbfl_filter_rank(rankA, exF, exP, sc)
        for k in (1, 5, 10): arms["D"][k].append(hitk(rankD, gold, k))
        arms["D"]["rr"].append(rr(rankD, gold))
        n_withpass += 1

print(f"on-path 崩溃子集: n={n}（其中有通过覆盖 = SBFL 可算: {n_withpass}）\n")
print(f"{'排序器':<30}{'R@1':>7}{'R@5':>7}{'R@10':>7}{'MRR':>8}{'n':>5}")
print("-" * 64)
for a, label in [("A", "A 纯静态(无覆盖)"), ("B", "B 覆盖过滤 (RQ3-E1)"), ("D", "D SBFL过滤+差分排序 ⭐")]:
    d = arms[a]; m = len(d[1])
    if not m: print(f"{label:<30}{'(无数据,待采通过覆盖)':>30}"); continue
    cells = "".join(f"{100*st.mean(d[k]):>7.1f}" for k in (1, 5, 10))
    print(f"{label:<30}{cells}{st.mean(d['rr']):>8.3f}{m:>5}")
print("\n判读：D(SBFL) > B(过滤) → 差分信号在过滤之上还有增量（把崩溃路径从 import 噪声里再分出来）。")
print("     注意 A/B 用全 n、D 只用『有通过覆盖』的子集；要严格对比，看同 n 下 B vs D（脚本可加 --paired）。")
