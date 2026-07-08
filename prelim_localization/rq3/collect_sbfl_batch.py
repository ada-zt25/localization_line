import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""SBFL cross-repo confirmation: collect PASS_TO_PASS + isolated FAIL_TO_PASS coverage for a diverse
set of on-path crash instances (sympy/matplotlib/sklearn/seaborn) to test if the SBFL-null (failing
⊆ passing → empty differential) generalizes beyond astropy. One image pull per instance (keep_image
on the passing run, reused by the failing run, removed after). Resumable. Local Docker, NO GPU."""
import json
import p0_line_recall as p0
import cov_collect_pass as cp

TARGETS = ["sympy__sympy-12419", "sympy__sympy-13471", "sympy__sympy-13773",
           "matplotlib__matplotlib-22711", "matplotlib__matplotlib-22835", "matplotlib__matplotlib-23299",
           "scikit-learn__scikit-learn-10508", "mwaskom__seaborn-3010"]

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
def load(p):
    try: return json.load(open(p))
    except FileNotFoundError: return {}
cpass = load("egl_cov_cache_pass.json"); cfail = load("egl_cov_cache_failiso.json")

for k, iid in enumerate(TARGETS, 1):
    if iid in cpass and iid in cfail:
        print(f"[{k}/{len(TARGETS)}] {iid} 已采，跳过", flush=True); continue
    row = rows.get(iid)
    if not row:
        print(f"[{k}/{len(TARGETS)}] {iid} 不在 rows，跳过", flush=True); continue
    elp = cp.collect_passing(iid, row, field="PASS_TO_PASS", keep_image=True)    # pull + keep
    elf = cp.collect_passing(iid, row, field="FAIL_TO_PASS", keep_image=False)   # reuse + rmi
    cpass[iid] = {f: sorted(v) for f, v in elp.items()}
    cfail[iid] = {f: sorted(v) for f, v in elf.items()}
    json.dump(cpass, open("egl_cov_cache_pass.json", "w"), indent=1)
    json.dump(cfail, open("egl_cov_cache_failiso.json", "w"), indent=1)
    print(f"[{k}/{len(TARGETS)}] {iid}  pass_lines={sum(len(v) for v in elp.values())} "
          f"failiso_lines={sum(len(v) for v in elf.values())}", flush=True)
print("[done] SBFL 跨仓库采集完成 → 跑 rq3/rq3_e3_sbfl_eval.py + 差分检查", flush=True)
