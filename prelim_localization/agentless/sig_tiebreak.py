#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""可复现显著性脚本 (framing-A, no-expand10). 检验覆盖率作为【vote 排序的 tiebreaker】的边际价值.
公平对照 (审计 steelman): vote+cov-tiebreak  vs  vote+random-tiebreak (真 Monte-Carlo, K 种子).
  - 每实例在预算N下: cov_flag = gold⊆(vote主, cov二级, 行号三级)的topN; rand_prob = K个真随机tiebreak下 gold⊆topN 的比例.
  - 判别: cov-win = cov_flag=1 且 rand_prob<τ; cov-loss = cov_flag=0 且 rand_prob>1-τ (τ=0.5, 紧N下random≈0).
  - per-model exact McNemar; POOLED-naive(三模型堆叠) 与 CLUSTER-ROBUST(去重实例,取净方向) 都报; Holm 校正跨N.
也报 vote+cov vs vote-alone(字典序) 作透明对照 (审计指出字典序 tiebreak 本身混淆).
无 API. 用 caches. python agentless/sig_tiebreak.py
"""
import json, random, statistics as st
from math import comb
from collections import defaultdict
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

TAGS=["deepseekv3","glm432","qwen3coder30b"]
NBUDGET=[10,15,20,40]
K=200; TAU=0.5

def mcnemar_exact(b,c):
    dn=b+c; k=min(b,c)
    return min(1.0, sum(comb(dn,i) for i in range(0,k+1))*2/(2**dn)) if dn else 1.0

def holm(pairs):  # pairs=[(name,p)] -> {name: adj_p}
    m=len(pairs); out={}; run=0.0
    for rank,(name,p) in enumerate(sorted(pairs,key=lambda x:x[1])):
        adj=min(1.0,(m-rank)*p); run=max(run,adj); out[name]=run
    return out

def load(tag, rows, cov, sub):
    unc=json.load(open(f"agentless/al_baseline_cache_{tag}.json")); inst={}
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su)
        if not base: continue
        vote=defaultdict(int)
        for s in su:
            for p in NB.native_pairs(iid,r,[s]): vote[p]+=1
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]; execp=set(); execadj=set()
        for f in ff:
            for ln in E.cov_for(f,cm):
                execp.add((f,ln))
                for d in range(-2,3): execadj.add((f,ln+d))
        def es(p): return 2 if p in execp else (1 if p in execadj else 0)
        inst[iid]=dict(gold=set(gold),base=sorted(base),vote=dict(vote),es={p:es(p) for p in base})
    return inst

def main():
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    data={t:load(t,rows,cov,sub) for t in TAGS}
    for t in TAGS: print(f"  {t}: n={len(data[t])}")
    # 每(model,N,iid): cov_flag, rand_prob
    holm_in=[]; report={}
    for N in NBUDGET:
        report[N]={}
        # per-model + 汇总
        pooled=[]   # (iid, model, covwin, covloss)
        for t in TAGS:
            b=c=0; per=[]
            for iid,x in data[t].items():
                g=x["gold"]; base=x["base"]; vote=x["vote"]; esm=x["es"]
                covtop=set(sorted(base,key=lambda p:(-vote.get(p,0),-esm[p],p))[:N])
                cov_flag=1 if g<=covtop else 0
                # random tiebreak: vote 主, 随机二级
                rp=0
                for k in range(K):
                    rng=random.Random(k*7919+hash(iid)%100003)
                    rtop=set(sorted(base,key=lambda p:(-vote.get(p,0), rng.random()))[:N])
                    if g<=rtop: rp+=1
                rand_prob=rp/K
                cw=1 if (cov_flag==1 and rand_prob<TAU) else 0
                cl=1 if (cov_flag==0 and rand_prob>1-TAU) else 0
                b+=cw; c+=cl; pooled.append((iid,t,cw,cl))
            p=mcnemar_exact(b,c); report[N][t]=(b,c,p); holm_in.append((f"{t}@N{N}",p))
        # pooled naive (堆叠)
        B=sum(w for _,_,w,_ in pooled); C=sum(l for _,_,_,l in pooled)
        # cluster-robust: 每实例取净方向 (跨模型合计 cov-win − cov-loss 的符号)
        byiid=defaultdict(lambda:[0,0])
        for iid,t,w,l in pooled: byiid[iid][0]+=w; byiid[iid][1]+=l
        cb=sum(1 for v in byiid.values() if v[0]>v[1]); cc=sum(1 for v in byiid.values() if v[1]>v[0])
        report[N]["POOL_naive"]=(B,C,mcnemar_exact(B,C))
        report[N]["POOL_cluster"]=(cb,cc,mcnemar_exact(cb,cc))
    adj=holm(holm_in)
    print(f"\n===== 覆盖率 tiebreaker 显著性: vote+cov vs vote+random ({K}种子, framing-A) =====")
    print(f"  (cov-win = cov救回gold而random<{TAU}概率救回; exact two-sided McNemar)")
    hdr=f"  {'N':>4}"+"".join(f"{t[:8]:>16}" for t in TAGS)+f"{'POOL堆叠':>16}{'POOL去重':>16}"
    print(hdr)
    for N in NBUDGET:
        row=f"  {N:>4}"
        for t in TAGS:
            b,c,p=report[N][t]; ap=adj[f"{t}@N{N}"]; star='*' if ap<0.05 else ''
            row+=f"{f'{b}-{c} p={p:.3f}{star}':>16}"
        Bn,Cn,pn=report[N]["POOL_naive"]; cb,cc,pc=report[N]["POOL_cluster"]
        row+=f"{f'{Bn}-{Cn} p={pn:.3f}':>16}{f'{cb}-{cc} p={pc:.3f}':>16}"
        print(row)
    print(f"  (* = per-model Holm-adj p<0.05 跨{len(NBUDGET)}个N预算; POOL堆叠=非独立(近似复制品,勿信); POOL去重=cluster-robust)")

if __name__=="__main__": main()
