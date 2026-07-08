#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""RQ3-E3 driver: collect PASSING-test coverage for the on-path crash subset → egl_cov_cache_pass.json.
Resumable (skips instances already cached), incremental save (survives interrupts). Local Docker, NO GPU.
  python rq3_collect_passing.py [--subset crash_onpath] [--workers 2] [--limit N]
Then: python rq3_e3_sbfl_eval.py  to see SBFL vs coverage-filter R@k."""
import argparse, json, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import p0_line_recall as p0
import cov_collect_pass as cp

ap = argparse.ArgumentParser()
ap.add_argument("--subset", default="crash_onpath")
ap.add_argument("--workers", type=int, default=2)        # Docker pulls are bandwidth-bound; keep low
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--out", default="egl_cov_cache_pass.json")
args = ap.parse_args()

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
todo = json.load(open("rq3_subsets.json"))[args.subset]
try: cache = json.load(open(args.out))
except FileNotFoundError: cache = {}
pending = [i for i in todo if i not in cache]
if args.limit: pending = pending[:args.limit]
print(f"[{args.subset}] {len(todo)} 总; {len(cache)} 已采; {len(pending)} 待采 x {args.workers} workers", file=sys.stderr)

lock = threading.Lock(); done = [0]
def work(iid):
    el = cp.collect_passing(iid, rows[iid])
    return iid, {f: sorted(v) for f, v in el.items()}

with ThreadPoolExecutor(max_workers=args.workers) as ex:
    for fut in as_completed([ex.submit(work, i) for i in pending]):
        iid, res = fut.result()
        with lock:
            cache[iid] = res; done[0] += 1
            json.dump(cache, open(args.out, "w"), indent=1)
            nl = sum(len(v) for v in res.values())
            print(f"[{done[0]}/{len(pending)}] {iid:34} passing_files={len(res)} lines={nl}", file=sys.stderr)
ncov = sum(1 for i in todo if cache.get(i))
print(f"[done] {ncov}/{len(todo)} 有通过覆盖 → 跑 rq3_e3_sbfl_eval.py", file=sys.stderr)
