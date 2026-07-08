#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""EGL 下游分析 (本地, 零 API): EGL = (基线 ∪ up+mid条件化输出) 按执行邻近软过滤扫 top-N.
在【基线cache ∩ up+mid cache】的公共实例上, 对同一批实例算基线点 vs EGL 曲线 (公平 within 比较).
--tag: 57 用 glm432/deepseekv3/qwen3coder30b; 61 用 bench2_<tag> + 设 EGL_LOC_FILE/EGL_SUBSET_FILE/EGL_COV_FILE/SWEBENCH_DATASET.
"""
import argparse, json, statistics as st
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

NSWEEP=[3,4,5,6,8,10,12,15,20,25,30,40,60,80,120,10**9]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); ap.add_argument("--label",default=""); a=ap.parse_args()
    tag=a.tag; label=a.label or tag
    unc=json.load(open(f"agentless/al_baseline_cache_{tag}.json"))
    try: con=json.load(open(f"agentless/cov_upmid_cache_{tag}.json"))
    except FileNotFoundError: con={}
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    inst=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid); sc=con.get(iid)
        if not r or not cm or iid not in E.LOC or not su or not sc: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        bu=NB.native_pairs(iid,r,su); bc=NB.native_pairs(iid,r,sc)
        if not bu and not bc: continue
        pool=bu|bc
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]; execp=set(); execadj=set(); flen={}
        for f in ff:
            ex=E.cov_for(f,cm)
            for ln in ex:
                execp.add((f,ln))
                for d in range(-2,3): execadj.add((f,ln+d))
        for f in {p[0] for p in pool}|{p[0] for p in bu}:
            try: flen[f]=len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines())
            except Exception: flen[f]=0
        inst.append(dict(gold=set(gold),base=bu,pool=pool,execp=execp,execadj=execadj,flen=flen))
    n=len(inst)
    def score(fn):
        A=[];L=[]
        for x in inst:
            S=E.expand10(set(fn(x)),x["flen"]); A.append(1 if x["gold"]<=S else 0); L.append(len(S))
        return (100*st.mean(A), st.mean(L)) if inst else (0,0)
    def es(x,p): return 2 if p in x["execp"] else (1 if p in x["execadj"] else 0)
    def soft(x,pool,N): return set(sorted(pool,key=lambda p:-es(x,p))[:N]) if N<10**8 else set(pool)
    bs,bl=score(lambda x:x["base"])          # 基线 (同批实例)
    us,ul=score(lambda x:x["pool"])          # up+mid∪基线 全池 (下游前)
    print(f"\n===== {label}  EGL 下游 (n={n}, 公共实例) =====")
    print(f"  基线(native edit-loc)   : superset={bs:.1f}  LoC={bl:.0f}")
    best=None
    for N in NSWEEP:
        s,l=score(lambda x,N=N: soft(x,x["pool"],N))
        if s>=bs and l<=bl and (s>bs or l<bl):
            sc_=(s-bs)+(bl-l)/max(bl,1)*10
            if best is None or sc_>best[0]: best=(sc_,N,s,l)
    if best:
        _,N,s,l=best
        print(f"  EGL (union+软过滤) 最优 : superset={s:.1f}  LoC={l:.0f}   @N={N}  → Δsup {s-bs:+.1f}, ΔLoC {-100*(1-l/bl):+.0f}%  {'★双轴占优' if s>bs and l<bl else '(单轴)'}")
    else:
        print(f"  EGL (union+软过滤)      : 全池 superset={us:.1f} LoC={ul:.0f}; 无双轴占优基线的点")

if __name__=="__main__": main()
