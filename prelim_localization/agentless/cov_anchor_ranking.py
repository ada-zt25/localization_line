#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""coverage-锚点排序 (本地, 零 API): 只预测【少数】排序靠前的执行行做锚点(±10), 看能否低 LoC 够到 exec±2 的 82% 天花板.

对每实例 (found_files[:3]): 把所有【执行行】按 line_scores_v2 (issue相关+traceback数据流+覆盖率) 排序,
predict top-N, expand10(±10), 量 superset/LoC. 扫 N. 对照: 模型基线 / exec±2 天花板.
两种排序: v2打分 / 崩溃帧优先(crash-frame执行行排前, 再按v2).
"""
import argparse, json, statistics as st
import p0_line_recall as p0
import code_graph as cg
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

NSWEEP=[1,2,3,5,8,10,15,20,30,50,80]

def build(tag):
    cache=json.load(open(f"agentless/al_baseline_cache_{tag}.json"))
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
    cov=json.load(open("egl_cov_cache.json"))
    sub=json.load(open("rq3_subsets.json"))["crash_onpath"]
    inst=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); samples=cache.get(iid)
        if not r or not cm: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]
        issue=(r.get("problem_statement") or "")[:5000]; cctx=E._crash_ctx(r)
        scored=[]; crashset=set(); flen={}; execadj=set()
        for f in ff:
            try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
            except Exception: continue
            flen[f]=len(src.splitlines()); ex=E.cov_for(f,cm)
            for ln in ex:
                for d in range(-2,3): execadj.add((f,ln+d))
            try: g=cg.CodeGraph(src,f)
            except Exception: g=None
            if not (g and g.ok): continue
            sc=g.line_scores_v2(issue,failure=cctx,coverage_lines=ex,graded=True,use_coverage=True)
            for ln in ex: scored.append(((f,ln), sc.get(ln,0.0)))
            for ln in E.crash_frame_exec_lines(src,f,issue,ex): crashset.add((f,ln))
        base=NB.native_pairs(iid,r,samples) if samples else set()
        for f in {p[0] for p in base}:
            if f not in flen:
                try: flen[f]=len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines())
                except Exception: flen[f]=0
        ranked_v2=[p for p,_ in sorted(scored, key=lambda t:-t[1])]
        ranked_cf=[p for p,_ in sorted(scored, key=lambda t:(0 if t[0] in crashset else 1, -t[1]))]
        inst.append(dict(gold=set(gold),flen=flen,base=base,execadj=execadj,rv2=ranked_v2,rcf=ranked_cf))
    return inst

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); a=ap.parse_args()
    inst=build(a.tag); n=len(inst)
    def sc(pairs_fn):
        A=[];L=[]
        for x in inst:
            S=E.expand10(set(pairs_fn(x)),x["flen"]); A.append(1 if x["gold"]<=S else 0); L.append(len(S))
        return 100*st.mean(A), st.mean(L)
    bs,bl=sc(lambda x:x["base"]); cs,cl=sc(lambda x:x["execadj"])
    print(f"\n======== {a.tag}: coverage-锚点排序 (crash·on-path, n={n}) ========")
    print(f"参考:  模型基线 = {bs:.1f}@{bl:.0f}   |   exec±2 天花板 = {cs:.1f}@{cl:.0f}\n")
    for name,key in [("按 v2 打分排序","rv2"),("崩溃帧优先+ v2","rcf")]:
        print(f"[{name}] 预测 top-N 执行锚点(±10):")
        print(f"  {'N':>4}{'superset':>10}{'LoC':>8}{'  vs基线':>12}")
        for N in NSWEEP:
            s,l=sc(lambda x,N=N:x[key][:N])
            v=''
            if s>=bs and l<bl and (s>bs or l<bl): v='  <-- 占优基线'
            print(f"  {N:>4}{s:>10.1f}{l:>8.0f}{v:>12}")
        print()

if __name__=="__main__": main()
