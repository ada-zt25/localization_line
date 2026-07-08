#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""EGL 二次判别 下游评测 (本地零 API), framing-A 正确指标 (transfer-10, NO expand10).
  EGL = 基线(native edit-loc, ±10) ∪ 二次判别additions(±10), 按执行邻近软过滤扫 top-N.
公平 within 对比: 基线点 与 EGL 曲线 在【基线cache ∩ rediscr cache】公共实例上、同一 no-expand10 口径.
--tag: 57 用 deepseekv3/glm432/qwen3coder30b (需 al_baseline_cache_<tag>.json + rediscr_cache_<tag>.json).
"""
import argparse, json, statistics as st
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

NSWEEP=[3,4,5,6,8,10,12,15,20,25,30,40,60,80,120,200,10**9]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); ap.add_argument("--label",default="")
    ap.add_argument("--expand10",type=int,default=0,help="1=对照旧±20口径; 默认0=framing-A正确指标")
    a=ap.parse_args()
    tag=a.tag; label=a.label or tag; EXP=bool(a.expand10)
    unc=json.load(open(f"agentless/al_baseline_cache_{tag}.json"))
    try: red=json.load(open(f"agentless/rediscr_cache_{tag}.json"))
    except FileNotFoundError: red={}
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    inst=[]; nred=0
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid); ra=red.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        bu=NB.native_pairs(iid,r,su)                       # 基线 ±10 窗口
        radd=NB.native_pairs(iid,r,[ra]) if ra else set()  # 二次判别 additions ±10 窗口 (ra=单采样)
        if radd-bu: nred+=1
        pool=bu|radd
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
    def S_of(pairs,flen): return E.expand10(set(pairs),flen) if EXP else set(pairs)
    def score(fn):
        A=[];L=[]
        for x in inst:
            S=S_of(fn(x),x["flen"]); A.append(1 if x["gold"]<=S else 0); L.append(len(S))
        return (100*st.mean(A), st.mean(L), A) if inst else (0,0,[])
    def es(x,p): return 2 if p in x["execp"] else (1 if p in x["execadj"] else 0)
    def soft(x,pool,N): return set(sorted(pool,key=lambda p:(-es(x,p),p))[:N]) if N<10**8 else set(pool)  # (,p) 全序, 修 hash 不确定性
    bs,bl,bA=score(lambda x:x["base"])          # 基线 (同批实例, no-expand10)
    us,ul,uA=score(lambda x:x["pool"])          # EGL 全池 (下游前)
    print(f"\n===== {label}  EGL二次判别下游 ({'±20旧口径' if EXP else 'framing-A: transfer-10 no-expand10'}, n={n}, {nred}例有新additions) =====")
    print(f"  基线(native edit-loc)   : superset={bs:.1f}  LoC={bl:.0f}")
    print(f"  EGL全池(base∪rediscr)   : superset={us:.1f}  LoC={ul:.0f}   (下游前, Δsup {us-bs:+.1f})")
    best=None; rows_out=[]
    for N in NSWEEP:
        s,l,A=score(lambda x,N=N: soft(x,x["pool"],N))
        rows_out.append((N,s,l,A))
        if s>=bs and l<=bl and (s>bs or l<bl):
            sc_=(s-bs)+(bl-l)/max(bl,1)*10
            if best is None or sc_>best[0]: best=(sc_,N,s,l,A)
    print(f"  {'N':>6}{'superset':>10}{'LoC':>8}")
    for N,s,l,A in rows_out:
        NN='全池' if N>=10**8 else str(N)
        print(f"  {NN:>6}{s:>10.1f}{l:>8.0f}")
    if best:
        _,N,s,l,A=best
        # McNemar 配对 (基线 vs EGL@bestN superset 命中)
        b01=sum(1 for i in range(n) if bA[i]==0 and A[i]==1); b10=sum(1 for i in range(n) if bA[i]==1 and A[i]==0)
        print(f"\n  ==> EGL(union+软过滤) 最优: superset={s:.1f}(基线{bs:.1f}, {s-bs:+.1f})  LoC={l:.0f}(基线{bl:.0f}, {-100*(1-l/bl):+.0f}%)  @N={N}  {'★双轴占优' if s>bs and l<bl else '(单轴)'}")
        print(f"      McNemar 配对(superset): EGL独赢 b01={b01}, 基线独赢 b10={b10} (discordant={b01+b10})")
    else:
        print(f"\n  ==> 无双轴占优基线的点 (EGL全池 sup={us:.1f} LoC={ul:.0f})")

if __name__=="__main__": main()
