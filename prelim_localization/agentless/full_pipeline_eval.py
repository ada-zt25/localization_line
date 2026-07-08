#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""全 pipeline 评测: 上游(纳入打分执行行) + 中游(条件化生成的候选集做 base) + 下游(按执行邻近度软重排缩 LoC),
   合起来对照【无条件化基线】. 本地零 API (中游已在 --base-cache 里跑好).

  --base-cache : 中游产物 (cov_conditioned_cache_<tag>.json, 默认) 或 al_baseline_cache_<tag>.json 做消融
  --ref        : 对照基线点 (al_baseline_<tag>.json 的 native_baseline = 无条件化 56/64)
"""
import argparse, json, statistics as st
import p0_line_recall as p0
import code_graph as cg
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

TOPK=30
NSWEEP=[3,4,5,6,8,10,12,15,20,25,30,40,60,80,120,10**9]

def build(base_cache):
    cache=json.load(open(base_cache))
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    inst=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); samples=cache.get(iid)
        if not r or not cm or iid not in E.LOC or not samples: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,samples)          # 中游: 条件化生成候选集
        if not base: continue
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]
        issue=(r.get("problem_statement") or "")[:5000]; cctx=E._crash_ctx(r)
        scored=set(); execp=set(); execadj=set(); flen={}
        for f in ff:
            try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
            except Exception: continue
            flen[f]=len(src.splitlines()); ex=E.cov_for(f,cm)
            for ln in ex:
                execp.add((f,ln))
                for d in range(-2,3): execadj.add((f,ln+d))
            try: g=cg.CodeGraph(src,f)
            except Exception: g=None
            if g and g.ok:
                for ln in E.scored_exec_topk(src,f,issue,cctx,ex,TOPK): scored.add((f,ln))
        for f in {p[0] for p in base}:
            if f not in flen:
                try: flen[f]=len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines())
                except Exception: flen[f]=0
        inst.append(dict(gold=set(gold),base=base,scored=scored,execp=execp,execadj=execadj,flen=flen))
    return inst

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tag",required=True)
    ap.add_argument("--base-cache",default="")
    ap.add_argument("--ref",default="")
    a=ap.parse_args()
    base_cache=a.base_cache or f"agentless/cov_upmid_cache_{a.tag}.json"
    ref=a.ref or f"agentless/al_baseline_{a.tag}.json"
    inst=build(base_cache); n=len(inst)
    rb=json.load(open(ref))["native_baseline"]; bs_ref,bl_ref=rb["superset"],rb["LoC"]
    def sc(fn):
        A=[];L=[]
        for x in inst:
            S=E.expand10(set(fn(x)),x["flen"]); A.append(1 if x["gold"]<=S else 0); L.append(len(S))
        return 100*st.mean(A), st.mean(L)
    def excscore(x,p): return 2 if p in x["execp"] else (1 if p in x["execadj"] else 0)
    def soft(x, pool, N):
        return set(sorted(pool, key=lambda p:-excscore(x,p))[:N]) if N<10**8 else set(pool)
    mid_s,mid_l=sc(lambda x:x["base"])   # 中游本身(条件化生成)
    print(f"\n============ {a.tag}: 全 pipeline (上游纳入 + 中游条件化 + 下游软过滤) vs 无条件化基线 (n={n}) ============")
    print(f"  无条件化基线(对照)      : superset={bs_ref:.1f}  LoC={bl_ref:.0f}")
    print(f"  中游·条件化生成(base)   : superset={mid_s:.1f}  LoC={mid_l:.0f}   (Δ vs 基线 {mid_s-bs_ref:+.1f}sup / {mid_l-bl_ref:+.0f}LoC)\n")
    print(f"  [下游] pool=up+mid输出(上游已在生成时并入), 按执行邻近软重排缩LoC, 扫 top-N:")
    print(f"    {'N':>5}{'superset':>10}{'LoC':>8}{'  vs无条件化基线':>20}")
    best=None
    for N in NSWEEP:
        s,l=sc(lambda x,N=N: soft(x, x["base"], N))
        v=''
        if s>bs_ref and l<bl_ref: v='★双轴占优'
        elif s>=bs_ref and l<bl_ref and (s>bs_ref or l<bl_ref): v='LoC↓同/升sup'
        elif s>bs_ref and l<=bl_ref: v='sup↑同/降LoC'
        NN='全pool' if N>=10**8 else str(N)
        print(f"    {NN:>5}{s:>10.1f}{l:>8.0f}{v:>20}")
        if s>=bs_ref and l<=bl_ref and (s>bs_ref or l<bl_ref):
            score=(s-bs_ref)+(bl_ref-l)/bl_ref*10
            if best is None or score>best[0]: best=(score,N,s,l)
    if best:
        _,N,s,l=best
        print(f"\n  ==> 全pipeline 占优基线最优点: N={N}  superset={s:.1f}(基线{bs_ref:.1f}, {s-bs_ref:+.1f})  LoC={l:.0f}(基线{bl_ref:.0f}, {-100*(1-l/bl_ref):+.0f}%)")
    else:
        print(f"\n  ==> 全pipeline 未找到占优基线的点")
    json.dump({"tag":a.tag,"n":n,"ref_baseline":[bs_ref,bl_ref],"mid":[mid_s,mid_l]},
              open(f"agentless/full_pipeline_{a.tag}.json","w"))

if __name__=="__main__": main()
