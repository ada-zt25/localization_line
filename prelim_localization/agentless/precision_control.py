#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""精度轴对照 (framing-A, no-expand10): 在同一 LoC 预算 N 下, 覆盖率软过滤 是否比 覆盖率无关排序 更好保金标?
若覆盖率排序 superset(@N) > 随机排序(@N) 显著, 则覆盖率对【精度】(等LoC召回更高 / 等召回LoC更少)有真实增益.
否则缩LoC只是'过滤到N行'的通用效应, 覆盖率无贡献.
基线pool=native edit-loc ±10 并集; 排序器: cov-soft(执行邻近) vs random(K次平均) vs center(离模型预测中心近, 覆盖率无关的合理基线).
无 API. --tag deepseekv3|glm432|qwen3coder30b.
"""
import argparse, json, random, statistics as st
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

def seeded_shuffle(seq, seed):
    """真随机打散 (每 seed 一个不同排列; 修旧版对所有 seed 只产生1个排列的退化 bug)."""
    r=random.Random(seed*7919+1); out=list(seq); r.shuffle(out); return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); ap.add_argument("--K",type=int,default=25); a=ap.parse_args()
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    inst=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su)
        if not base: continue
        vote={}   # 覆盖率无关强对照: 4采样自一致投票数 (越多采样的±10窗口覆盖=模型越自信)
        for s in su:
            ps=NB.native_pairs(iid,r,[s])
            for p in ps: vote[p]=vote.get(p,0)+1
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]; execp=set(); execadj=set()
        for f in ff:
            ex=E.cov_for(f,cm)
            for ln in ex:
                execp.add((f,ln))
                for d in range(-2,3): execadj.add((f,ln+d))
        inst.append(dict(gold=set(gold),base=sorted(base),execp=execp,execadj=execadj,vote=vote))
    n=len(inst)
    def es(x,p): return 2 if p in x["execp"] else (1 if p in x["execadj"] else 0)
    def vt(x,p): return x["vote"].get(p,0)
    NSWEEP=[10,15,20,25,30,40,60,80,120]
    print(f"\n===== {a.tag} 精度轴对照 (framing-A no-expand10, n={n}) =====")
    print(f"  同一 base pool, 不同排序器在预算N下的 superset (gold⊆topN):")
    fullsup=100*st.mean([1 if x['gold']<=set(x['base']) else 0 for x in inst])
    print(f"  全pool superset={fullsup:.1f} (LoC=平均{st.mean([len(x['base']) for x in inst]):.0f})")
    print(f"  排序器 superset@N (关键: vote+cov 是否 > vote-alone => 覆盖率的边际贡献):")
    print(f"  {'N':>5}{'cov-only':>9}{'vote-only':>10}{'vote→cov':>10}{'cov→vote':>10}{'random':>8}{'Δ(v+c − v)':>12}")
    for N in NSWEEP:
        acc={k:[] for k in ["cov","vote","vc","cv","rand"]}; marg_win=0; marg_lose=0
        for x in inst:
            covtop =set(sorted(x['base'], key=lambda p:(-es(x,p), p))[:N])
            votetop=set(sorted(x['base'], key=lambda p:(-vt(x,p), p))[:N])
            vctop  =set(sorted(x['base'], key=lambda p:(-vt(x,p), -es(x,p), p))[:N])   # vote 主, cov 二级
            cvtop  =set(sorted(x['base'], key=lambda p:(-es(x,p), -vt(x,p), p))[:N])   # cov 主, vote 二级
            g=x['gold']
            gvc=1 if g<=vctop else 0; gv=1 if g<=votetop else 0
            acc["cov"].append(1 if g<=covtop else 0); acc["vote"].append(gv)
            acc["vc"].append(gvc); acc["cv"].append(1 if g<=cvtop else 0)
            acc["rand"].append(st.mean([1 if g<=set(seeded_shuffle(x['base'],k)[:N]) else 0 for k in range(a.K)]))
            if gvc and not gv: marg_win+=1
            if gv and not gvc: marg_lose+=1
        m={k:100*st.mean(v) for k,v in acc.items()}
        print(f"  {N:>5}{m['cov']:>9.1f}{m['vote']:>10.1f}{m['vc']:>10.1f}{m['cv']:>10.1f}{m['rand']:>8.1f}{m['vc']-m['vote']:>+12.1f}   (v+c独赢 {marg_win}, v独赢 {marg_lose})")

if __name__=="__main__": main()
