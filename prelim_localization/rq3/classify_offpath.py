import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""Classify the 11 crash off-path instances into the exact mechanism, so the paper's breakdown sums.
  insertion        : the gold hunk is a pure addition (no '-' deletions in the gold file hunk)
  func-never-reached: the gold function is entirely absent from failing coverage
  missed-branch    : gold function executed, but the gold lines themselves did not"""
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
def gold_hunk_has_deletion(patch, f):
    """True if the hunk(s) touching file f contain any '-' (real deletion) line."""
    cur=None; has=False
    for ln in patch.split("\n"):
        if ln.startswith("diff --git") or ln.startswith("+++ "):
            cur = f in ln
        if cur and ln.startswith("-") and not ln.startswith("---"):
            has=True
    return has

counts={"insertion":0,"func-never-reached":0,"missed-branch":0,"other":0}
detail=[]
for iid in sub["crash_offpath"]:
    r=rows.get(iid); cm=cov.get(iid)
    if not (r and cm):
        detail.append((iid,"NO-DATA")); counts["other"]+=1; continue
    gf=p0.parse_patch(r.get("patch") or "")
    f=next((x for x in gf if x.endswith(".py") and gf[x]["region"]), None)
    if not f:
        detail.append((iid,"NO-REGION")); counts["other"]+=1; continue
    gold=set(gf[f]["region"]); ex=cov_for(f,cm)
    patch=r.get("patch") or ""
    has_del=gold_hunk_has_deletion(patch,f)
    try:
        src=p0.fetch_file(r["repo"],r["base_commit"],f); G=cg.CodeGraph(src,f)
        franges=[set(range(fd["start"],fd["end"]+1)) for fd in G.funcs]
        goldfuncs=[fr for fr in franges if fr & gold]
        func_ran=any(fr & ex for fr in goldfuncs) if goldfuncs else False
    except Exception:
        func_ran=False
    if not has_del:
        cat="insertion"
    elif func_ran:
        cat="missed-branch"
    else:
        cat="func-never-reached"
    counts[cat]+=1; detail.append((iid,cat))

print(f"crash off-path total = {len(sub['crash_offpath'])}")
for c,n in counts.items(): print(f"  {c:20s} {n}")
print("  sum =", sum(counts.values()))
print("---")
for iid,cat in detail: print(f"  {cat:20s} {iid}")
