import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""F0 — freeze the RQ4 evaluation subsets (anti-drift). Emits rq4/frozen_subsets.json with the EXACT
instance lists + per-instance {gold_file, gold_lines, exec_lines}. Run ONCE; the run never re-derives.
Selection logic is IDENTICAL to rq3/crash_coverage_rank_test.py (first .py gold file with gold∩region
and non-empty coverage), so the locked n's match the paper's Table-5 derivation."""
import json, re
import p0_line_recall as p0

TB = re.compile(r"Traceback \(most recent call last\)")
FRAME2 = re.compile(r'File "[^"]+", line \d+')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")
def is_crash(i, t):
    i = i or ""; return bool(TB.search(i)) or len(FRAME2.findall(i)) >= 2 or bool(RAISES.search(t or ""))
def cov_for(f, cm):
    if f in cm: return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
cov = json.load(open("egl_cov_cache.json"))
SUB = {"S1_crash_onpath": [], "S2_behav_onpath": [], "S3_crash_offpath": [], "S4_behav_offpath": []}
nocov = []
KEY = {"crash_onpath": "S1_crash_onpath", "behav_onpath": "S2_behav_onpath",
       "crash_offpath": "S3_crash_offpath", "behav_offpath": "S4_behav_offpath"}

for iid, r in rows.items():
    cm = cov.get(iid)
    if not cm:
        nocov.append(iid); continue
    crash = is_crash(r.get("problem_statement"), r.get("test_patch"))
    gf = p0.parse_patch(r.get("patch") or "")
    picked = None
    for f in [x for x in gf if x.endswith(".py")]:        # first qualifying .py gold file (matches Table-5)
        gold = sorted(set(gf[f]["region"]))
        if not gold: continue
        ex = cov_for(f, cm)
        if not ex: continue
        picked = (f, gold, sorted(ex)); break
    if not picked: continue
    f, gold, ex = picked
    onpath = bool(set(gold) & set(ex))
    skey = KEY[f"{'crash' if crash else 'behav'}_{'onpath' if onpath else 'offpath'}"]
    SUB[skey].append({"instance_id": iid, "repo": r["repo"], "base_commit": r["base_commit"],
                      "gold_file": f, "gold_lines": gold, "exec_lines": ex,
                      "n_gold": len(gold), "n_exec": len(ex)})

counts = {k: len(v) for k, v in SUB.items()}
out = {"meta": {"derivation": "is_crash × on-path(gold∩cov); first .py gold file w/ region & coverage",
                "source": "egl_cov_cache.json + load_rows(500, lite)", "dataset": "SWE-bench-Lite",
                "frozen": True, "counts": counts, "n_cov_missing": len(nocov)},
       **SUB}
json.dump(out, open("rq4/frozen_subsets.json", "w"), indent=1)
print("frozen_subsets.json written. counts:")
for k, v in counts.items(): print(f"  {k}: {v}")
print(f"  (instances w/o coverage cache: {len(nocov)})")
print(f"  S1 crash·on-path repos:", end=" ")
from collections import Counter
print(dict(Counter(x["instance_id"].split("__")[0] for x in SUB["S1_crash_onpath"])))
