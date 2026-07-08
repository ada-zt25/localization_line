#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""上游+下游【合并成一条】: pool = 基线 ∪ 打分执行行(recall天花板), 按 line_scores_v2 金标可能性排序(下游精排),
扫 top-N -> 找同时 superset↑ & LoC↓ 占优基线的点. 全本地, 零 API.

排序信号 (都不用模型):
  - base 成员 (模型自己选的, 强先验)  -> 大 bonus
  - line_scores_v2: issue相关 + traceback数据流 + 覆盖率 (对执行行按金标可能性打分)
两个变体: with/without base-bonus, 取更优.
"""
import argparse, json, statistics as st
import p0_line_recall as p0
import code_graph as cg
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

TOPK_EXEC=30
NSWEEP=[3,4,5,6,8,10,12,15,20,25,30,40,60,80,120,10**9]

def build(tag):
    cache=json.load(open(f"agentless/al_baseline_cache_{tag}.json"))
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
    cov=json.load(open("egl_cov_cache.json"))
    sub=json.load(open("rq3_subsets.json"))["crash_onpath"]
    inst=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); samples=cache.get(iid)
        if not r or not cm or iid not in E.LOC or not samples: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid, r, samples)
        if not base: continue
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]
        issue=(r.get("problem_statement") or "")[:5000]; cctx=E._crash_ctx(r)
        pool=set(base); score={}; flen={}
        for f in ff:
            try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
            except Exception: continue
            flen[f]=len(src.splitlines()); ex=E.cov_for(f,cm)
            try: g=cg.CodeGraph(src,f)
            except Exception: g=None
            sc=g.line_scores_v2(issue,failure=cctx,coverage_lines=ex,graded=True,use_coverage=True) if (g and g.ok) else {}
            for l in sorted((l for l in sc if l in ex), key=lambda l:-sc[l])[:TOPK_EXEC]:
                pool.add((f,l)); score[(f,l)]=max(score.get((f,l),0.0), sc[l])
            for (bf,bl) in [p for p in base if p[0]==f]:
                score[(bf,bl)]=max(score.get((bf,bl),0.0), sc.get(bl,0.0))
        for f in {p[0] for p in base}:
            if f not in flen:
                try: flen[f]=len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines())
                except Exception: flen[f]=0
        execp=set(); execadj=set()
        for f in ff:
            try: ex=E.cov_for(f,cm)
            except Exception: ex=set()
            for ln in ex:
                execp.add((f,ln))
                for d in range(-2,3): execadj.add((f,ln+d))
        inst.append(dict(iid=iid,gold=gold,base=base,pool=pool,score=score,flen=flen,
                         execp=execp,execadj=execadj))
    return inst

def prune_then_add(inst, bs, blo):
    """先按执行邻近度软剪 base 到 top-Nb, 再定点补 top-K 打分执行行. 找双轴占优基线的点."""
    print("[先剪枝后补: softfilter(base,Nb) ∪ scored_top(K)]  搜 superset↑ 且 LoC↓:")
    def excscore(x,p): return 2 if p in x["execp"] else (1 if p in x["execadj"] else 0)
    hits=[]
    for Nb in [10,15,20,25,30,40]:
        for K in [0,1,2,3,4,6]:
            a=[];l=[]
            for x in inst:
                bsel=sorted(x["base"], key=lambda p:-excscore(x,p))[:Nb]
                scored_only=[p for p in x["pool"] if p not in x["base"]]
                ksel=sorted(scored_only, key=lambda p:-x["score"].get(p,0.0))[:K]
                S=E.expand10(set(bsel)|set(ksel), x["flen"])
                a.append(1 if x["gold"]<=S else 0); l.append(len(S))
            s=100*sum(a)/len(a); loc=sum(l)/len(l)
            if s>bs and loc<blo: hits.append((s-bs,100*(1-loc/blo),Nb,K,s,loc))
    if hits:
        hits.sort(reverse=True)
        print(f"  {'Nb':>4}{'K':>3}{'superset':>10}{'LoC':>8}{'  Δsup':>8}{'  ΔLoC%':>8}")
        for _,__,Nb,K,s,loc in hits[:8]:
            print(f"  {Nb:>4}{K:>3}{s:>10.1f}{loc:>8.1f}{s-bs:>+8.1f}{-100*(1-loc/blo):>+7.0f}%")
        return hits[0]
    else:
        print("  网格内无双轴占优点")
        return None

def sweep(inst, base_bonus):
    # 每实例: 按 (base_bonus if in base) + score 排序 pool
    ranked={}
    for x in inst:
        mx=max(x["score"].values() or [1.0])
        key={p:(mx*3 if (base_bonus and p in x["base"]) else 0.0)+x["score"].get(p,0.0) for p in x["pool"]}
        ranked[x["iid"]]=sorted(x["pool"], key=lambda p:-key[p])
    rows=[]
    for N in NSWEEP:
        a=[];an=[];l=[]
        for x in inst:
            top=set(ranked[x["iid"]][:N]) if N<10**8 else set(x["pool"])
            S=E.expand10(top, x["flen"]); g=x["gold"]
            a.append(1 if g<=S else 0); an.append(1 if g&S else 0); l.append(len(S))
        rows.append((N,100*st.mean(a),100*st.mean(an),st.mean(l)))
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); a=ap.parse_args()
    inst=build(a.tag); n=len(inst)
    # 基线点
    ba=[];bl=[]
    for x in inst:
        S=E.expand10(set(x["base"]),x["flen"]); ba.append(1 if x["gold"]<=S else 0); bl.append(len(S))
    bs,blo=100*st.mean(ba),st.mean(bl)
    print(f"\n============ {a.tag}: 上游+下游合并臂 (crash·on-path, n={n}) ============")
    print(f"基线 base: superset={bs:.1f}  LoC={blo:.1f}\n")
    best=None
    for bonus in [True, False]:
        rows=sweep(inst, bonus)
        print(f"[合并臂, base先验={'开' if bonus else '关'}]  pool=base∪打分执行行, 按 line_scores_v2 排序:")
        print(f"  {'N':>5}{'superset':>10}{'any':>7}{'LoC':>8}{'  判定':>18}")
        for N,s,an,l in rows:
            verdict=''
            if s>bs and l<blo: verdict='★ 双轴占优基线'
            elif s>=bs and l<blo: verdict='LoC↓ 同superset'
            elif s>bs and l<=blo: verdict='superset↑ 同LoC'
            elif s>=bs and l<=blo and (s>bs or l<blo): verdict='弱占优'
            NN='全pool' if N>=10**8 else str(N)
            print(f"  {NN:>5}{s:>10.1f}{an:>7.1f}{l:>8.1f}{verdict:>18}")
            if s>bs and l<blo and (best is None or (s-bs)+(blo-l)/blo*10 > best[0]):
                best=((s-bs)+(blo-l)/blo*10, bonus, N, s, l)
        print()
    if best:
        _,bo,N,s,l=best
        print(f"==> 混排合并臂找到双轴占优点: base先验={'开' if bo else '关'}, N={N}, superset={s:.1f}(+{s-bs:.1f}), LoC={l:.1f}(-{100*(1-l/blo):.0f}%)")
    else:
        print(f"==> 混排合并臂未找到双轴占优点")
    print()
    pta=prune_then_add(inst, bs, blo)
    if pta:
        _,__,Nb,K,s,l=pta
        print(f"==> ★先剪后补找到双轴占优: Nb={Nb},K={K}  superset={s:.1f}(基线{bs:.1f}, +{s-bs:.1f})  LoC={l:.1f}(基线{blo:.1f}, -{100*(1-l/blo):.0f}%)")
    json.dump({"tag":a.tag,"n":n,"baseline":[bs,blo]}, open(f"agentless/combined_{a.tag}.json","w"))

if __name__=="__main__": main()
