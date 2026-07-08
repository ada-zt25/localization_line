import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""Find two REAL worked examples for the paper (no fabrication):
  (A) FILTER-RESCUE: a crash on-path instance where static def-use MISSES the gold @10 but the
      coverage-filter HITS it @10 — report file, sizes, gold rank before/after.
  (B) OFF-PATH MISSED-BRANCH: a crash off-path instance whose gold function executed but gold lines
      did NOT, and whose patch changes a branch condition — print the patch hunk to confirm."""
import json, re
import p0_line_recall as p0
import code_graph as cg

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
cov = json.load(open("egl_cov_cache.json"))
sub = json.load(open("rq3_subsets.json"))
def cov_for(f, cm):
    if f in cm: return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()
def gold_rank(rk, gold):
    for i, l in enumerate(rk, 1):
        if l in gold: return i
    return None

print("=== (A) FILTER-RESCUE 候选 (静态@10漏, 过滤@10中) ===")
found_a = 0
for iid in sub["crash_onpath"]:
    r = rows.get(iid); cm = cov.get(iid)
    if not (r and cm): continue
    gf = p0.parse_patch(r.get("patch") or ""); issue = (r.get("problem_statement") or "")[:5000]
    f = next((x for x in gf if x.endswith(".py") and gf[x]["region"]), None)
    if not f: continue
    gold = set(gf[f]["region"]); ex = cov_for(f, cm)
    if not (gold & ex): continue
    try:
        src = p0.fetch_file(r["repo"], r["base_commit"], f); G = cg.CodeGraph(src, f)
        if not G.ok: continue
        sc = G.line_scores_v2(issue, use_coverage=False)
    except Exception: continue
    if not sc: continue
    rankA = sorted(sc, key=lambda l: (-sc[l], l)); rankB = [l for l in rankA if l in ex]
    rA, rB = gold_rank(rankA, gold), gold_rank(rankB, gold)
    if rA and rA > 10 and rB and rB <= 10:                  # static misses @10, filter hits @10
        print(f"  ⭐ {iid} | {f} ({len(src.splitlines())} LoC) | 静态候选 {len(rankA)} → 过滤 {len(rankB)} 行 | "
              f"金标排名 静态 #{rA} → 过滤 #{rB} | gold lines {sorted(gold)[:6]}")
        found_a += 1
        if found_a >= 4: break

print("\n=== (B) OFF-PATH 漏分支 候选 (gold函数执行了, gold行没执行; patch改条件) ===")
COND = re.compile(r'^[-+].*\b(if|elif|while|and|or|not in| in |==|!=|<=|>=|<|>)\b', re.M)
found_b = 0
for iid in sub["crash_offpath"]:
    r = rows.get(iid); cm = cov.get(iid)
    if not (r and cm): continue
    gf = p0.parse_patch(r.get("patch") or "")
    f = next((x for x in gf if x.endswith(".py") and gf[x]["region"]), None)
    if not f: continue
    gold = set(gf[f]["region"]); ex = cov_for(f, cm)
    if gold & ex: continue                                  # must be off-path
    try:
        src = p0.fetch_file(r["repo"], r["base_commit"], f); G = cg.CodeGraph(src, f)
        franges = [set(range(fd["start"], fd["end"]+1)) for fd in G.funcs]
        goldfuncs = [fr for fr in franges if fr & gold]
        func_ran = any(fr & ex for fr in goldfuncs) if goldfuncs else False
    except Exception: func_ran = False
    # patch 的该文件 hunk 是否含条件改动
    patch = r.get("patch") or ""
    cond_change = bool(COND.search(patch))
    if func_ran and cond_change:
        print(f"  ⭐ {iid} | {f} | gold函数跑了但gold行没跑 | gold lines {sorted(gold)[:6]}")
        # 打印含条件的 patch 行
        for ln in patch.split("\n"):
            if re.match(r'^[-+]', ln) and re.search(r'\b(if|elif|while|==|!=|<=|>=|<|>| in | not )\b', ln) and not ln.startswith(("+++", "---")):
                print(f"       {ln[:100]}")
        found_b += 1
        if found_b >= 3: break
