#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""动态因果切片信号测试 (file-given, crash·on-path, 本地零 API).

问题: raw coverage 太粗 (召回信号, 判别=0). 更细的信号 = 执行 × 数据流:
  动态切片 = dataflow_slice(traceback+issue 播种, def-use BFS) ∩ 执行覆盖率
          = "实际运行、且因果通向失败的语句" (ARISE 的静态 def-use 切片被执行剪成实际那条链).

对比三个纯信号定位器 (给定金标文件, gold⊆预测±10 = superset; |预测±10| = LoC):
  raw_cov      : 全部执行行             (粗覆盖率: 召回天花板, LoC 巨大)
  static_slice : def-use 切片 (无执行剪枝) (ARISE 式静态: 过近似)
  dyn_slice    : static ∩ exec           (我们: 执行剪枝的因果链)
另报: gold⊆exec 精确天花板 (任何覆盖率信号的召回上限).
"""
import argparse, json, statistics as st
import p0_line_recall as p0
import code_graph as cg
import agentless.al_vote_eval as E

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--depth",type=int,default=3)
    ap.add_argument("--dir",default="both")
    ap.add_argument("--seed",default="tb+issue",help="tb | tb+issue")
    a=ap.parse_args()
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
    cov=json.load(open("egl_cov_cache.json"))
    sub=json.load(open("rq3_subsets.json"))["crash_onpath"]
    arms=["raw_cov","static_slice","dyn_slice"]
    acc={k:{"sup":[], "loc":[]} for k in arms}
    ceil_exec=[]; rawsz={k:[] for k in arms}; n=0
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid)
        if not r or not cm: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        goldfiles={p[0] for p in gold if p[0].endswith(".py")}
        issue=(r.get("problem_statement") or "")[:5000]; cctx=E._crash_ctx(r)
        raw=set(); stat=set(); dyn=set(); flen={}; execp=set()
        for f in goldfiles:
            try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
            except Exception: continue
            flen[f]=len(src.splitlines()); ex=E.cov_for(f,cm)
            for ln in ex: raw.add((f,ln)); execp.add((f,ln))
            try: g=cg.CodeGraph(src,f)
            except Exception: g=None
            if not (g and g.ok): continue
            seeds=g.seed_from_traceback(cctx)
            if "issue" in a.seed: seeds=seeds|g.seed_from_issue(issue)
            sl=g.dataflow_slice(seeds, a.dir, depth=a.depth)
            for ln in sl:
                stat.add((f,ln))
                if (f,ln) in {(f,e) for e in ex}: dyn.add((f,ln))
        n+=1
        gold=set(gold)
        ceil_exec.append(1 if gold<=execp else 0)   # 精确 (无±10) 召回天花板
        for k,pairs in [("raw_cov",raw),("static_slice",stat),("dyn_slice",dyn)]:
            S=E.expand10(pairs, flen)
            acc[k]["sup"].append(1 if gold<=S else 0)
            acc[k]["loc"].append(len(S)); rawsz[k].append(len(pairs))
    print(f"\n==== 动态切片信号测试 (file-given, crash·on-path, n={n}, seed={a.seed}, dir={a.dir}, depth={a.depth}) ====")
    print(f"  gold⊆exec 精确召回天花板 = {100*st.mean(ceil_exec):.1f}%  (任何覆盖率信号的上限)\n")
    print(f"  {'信号':<14}{'superset':>10}{'any-LoC(±10)':>14}{'原始行数(无±10)':>16}")
    for k in arms:
        sup=100*st.mean(acc[k]["sup"]); loc=st.mean(acc[k]["loc"]); rs=st.mean(rawsz[k])
        print(f"  {k:<14}{sup:>10.1f}{loc:>14.1f}{rs:>16.1f}")
    print("\n读法: dyn_slice 若 superset≈raw_cov 但 LoC/原始行数 远小 => 又准又精的细信号(执行剪枝有效);")
    print("      若 dyn_slice superset << raw_cov => 执行×数据流剪枝掉了金标(切片太窄/跨过程漏).")

if __name__=="__main__": main()
