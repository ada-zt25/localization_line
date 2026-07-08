#!/usr/bin/env python3
"""驱动: 对【有执行漏金标或被probe的实例】跑 value_collect, 存 value_cache.json (可续跑).
只跑 DS+GLM 判别墙/covered 涉及的实例(省 Docker 时间). 结果 {iid: {file: {line: {var:repr}}}}.
  python value_collect_all.py            # 跑并集
  python value_collect_all.py --all      # 跑全部 crash_onpath 57
"""
import argparse, json, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB
import value_collect as VC

def miss_instances(tags):
    """有执行漏金标(C_infile_exec/adj2)或有covered金标的实例(即probe会用到的)."""
    import os
    cov=json.load(open("egl_cov_cache.json"))
    sub=json.load(open("rq3_subsets.json"))["crash_onpath"]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
    need=set()
    for tag in tags:
        unc=json.load(open(f"agentless/al_baseline_cache_{tag}.json"))
        for iid in sub:
            r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
            if not r or not cm or iid not in E.LOC or not su: continue
            gold=E.gold_pairs(r)
            if not gold: continue
            base=NB.native_pairs(iid,r,su); missed=set(gold)-set(base)
            if missed: need.add(iid)          # 有漏金标 => probe 会用到(墙+covered都在这些实例)
    return sub, need, rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--all",action="store_true")
    ap.add_argument("--cache",default="value_cache.json"); ap.add_argument("--workers",type=int,default=1)
    a=ap.parse_args()
    sub, need, rows = miss_instances(["deepseekv3","glm432"])
    ids = sub if a.all else sorted(need)
    cache_path=Path(a.cache)
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    todo=[i for i in ids if i not in cache]
    print(f"目标实例 {len(ids)} (已缓存 {len(ids)-len(todo)}, 待跑 {len(todo)}, workers={a.workers})", file=sys.stderr)
    lock=threading.Lock(); done=[0]
    def work(iid):
        t0=time.time()
        try: vt=VC.collect(iid, rows[iid])
        except Exception as e: vt={}; print("  EXC", repr(e)[:100], file=sys.stderr)
        nlines=sum(len(v) for v in vt.values())
        with lock:
            cache[iid]=vt; cache_path.write_text(json.dumps(cache)); done[0]+=1
            print(f"[{done[0]}/{len(todo)}] {iid} files={len(vt)} lines={nlines} ({time.time()-t0:.0f}s)", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(as_completed([ex.submit(work,i) for i in todo]))
    print(f"done. cached {len(cache)} -> {a.cache}", file=sys.stderr)

if __name__=="__main__": main()
