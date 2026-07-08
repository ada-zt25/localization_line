#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""把 execution coverage 解耦出投票、直接叠到模型【自己的】Agentless 基线上（本地, 零 API）。

回答用户 3 阶段思路 (上游纳入 / 下游过滤) 对弱模型基线是否有用, 并用数据判 崩溃帧 vs 打分扩区。
所有臂都对每个模型自身的 native 基线 (al_baseline_cache_<tag>.json) 计算, 指标 = Agentless superset/LoC (expand10 ±10).

臂:
  base            : 模型自身基线 (4采样并集)                      [参考点]
  +crash          : base ∪ 崩溃帧执行行            (纳入·崩溃帧)   [superset单调↑, LoC↑]
  +scored(K=30)   : base ∪ 打分执行行 top-K        (纳入·打分)     [superset单调↑, LoC↑; 天花板高但盲纳入更脏?]
  hard∩exec±2     : base ∩ 执行±2  (硬过滤)                        [验证 Part2: 会砸 superset]
  soft-topN       : base 按执行邻近度重排, 扫 top-N (软过滤)        [superset-安全, 省LoC 的 Pareto 曲线]
  +scored∘soft    : (base ∪ scored) 再软重排扫 top-N               [上游+下游合并 Pareto 曲线]

  MODEL 无关, 用 --tag 指定; python agentless/coverage_on_baseline.py --tag qwen3coder30b
"""
import argparse, json, statistics as st
from pathlib import Path
import p0_line_recall as p0
import agentless.al_vote_eval as E          # crash_frame_exec_lines, scored_exec_topk, cov_for, expand10, gold_pairs, intervals_to_lines, _crash_ctx
import agentless.al_baseline_native as NB   # native_pairs, TOP_N

NSWEEP=[5,10,20,30,40,60,80,120,160,200,300,10**9]   # 10**9 = 全量(=基线本身)

def score_set(pairs, gold, flen):
    S=E.expand10(set(pairs), flen)
    return (1 if gold<=S else 0, 1 if gold&S else 0, len(S))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tag",required=True,help="qwen3coder30b | hunyuanA13B")
    ap.add_argument("--out",default="")
    args=ap.parse_args()
    tag=args.tag
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
        crash_pairs=set(); scored_pairs=set(); exec_pairs=set(); execadj=set()
        flen={}
        try:
            for f in ff:
                src=p0.fetch_file(r["repo"],r["base_commit"],f); flen[f]=len(src.splitlines())
                ex=E.cov_for(f,cm)
                for ln in ex: exec_pairs.add((f,ln)); [execadj.add((f,ln+d)) for d in range(-2,3)]
                for ln in E.crash_frame_exec_lines(src,f,issue,ex): crash_pairs.add((f,ln))
                for ln in E.scored_exec_topk(src,f,issue,cctx,ex,30): scored_pairs.add((f,ln))
        except Exception: pass
        for f in {p[0] for p in base}:
            if f not in flen:
                try: flen[f]=len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines())
                except Exception: flen[f]=0
        inst.append(dict(iid=iid,gold=gold,base=base,crash=crash_pairs,scored=scored_pairs,
                         execp=exec_pairs,execadj=execadj,flen=flen))
    n=len(inst)

    def agg(fn):
        a=[];an=[];l=[]
        for x in inst:
            s=fn(x); sa,sn,sl=score_set(s,x["gold"],x["flen"]); a.append(sa);an.append(sn);l.append(sl)
        return 100*st.mean(a),100*st.mean(an),st.mean(l)
    def rank_by_exec(x, pool):
        def key(p):  # 执行=2, 邻近=1, 其他=0 (降序); 稳定
            return 2 if p in x["execp"] else (1 if p in x["execadj"] else 0)
        return sorted(pool, key=lambda p:-key(p))
    def soft_topN(x, pool, N):
        return set(rank_by_exec(x, pool)[:N]) if N<10**8 else set(pool)

    print(f"\n================  {tag}: execution 解耦叠加到自身基线 (crash·on-path, n={n})  ================")
    pts={}
    for name,fn in [("base(基线)",       lambda x:x["base"]),
                    ("+crash(纳入崩溃帧)", lambda x:x["base"]|x["crash"]),
                    ("+scored(纳入打分)",  lambda x:x["base"]|x["scored"]),
                    ("hard∩exec±2(硬过滤)",lambda x:x["base"]&x["execadj"]),
                    ("exec±2(纯信号)",     lambda x:x["execadj"]),
                    ("★(base∪scored)∩exec±2", lambda x:(x["base"]|x["scored"])&x["execadj"]),
                    ("★(base∪crash)∩exec±2",  lambda x:(x["base"]|x["crash"])&x["execadj"])]:
        a,an,l=agg(fn); pts[name]=(a,an,l)
        print(f"  {name:<22} superset={a:5.1f}  any={an:5.1f}  LoC={l:6.1f}")
    bl_s,bl_an,bl_l=pts["base(基线)"]
    def curve(name, poolfn):
        print(f"\n  [{name}] 软重排扫 top-N (superset-安全, 省LoC):")
        print(f"    {'N':>5}{'superset':>10}{'any':>7}{'LoC':>8}{'  vs基线':>10}")
        cur={}
        for N in NSWEEP:
            a,an,l=agg(lambda x,N=N: soft_topN(x, poolfn(x), N))
            cur[str(N)]=(a,an,l)
            tag2=''
            if l<=bl_l and a>=bl_s and (l<bl_l or a>bl_s): tag2='  <-- Pareto占优基线'
            NN='全量' if N>=10**8 else str(N)
            print(f"    {NN:>5}{a:>10.1f}{an:>7.1f}{l:>8.1f}{'':>10}{tag2}")
        return cur
    c_soft=curve("软过滤(base)", lambda x:x["base"])
    c_scored_soft=curve("上游+下游(base∪scored 再软过滤)", lambda x:x["base"]|x["scored"])

    out={"tag":tag,"n":n,"points":pts,"soft_base":c_soft,"soft_scored":c_scored_soft,
         "baseline":[bl_s,bl_an,bl_l]}
    of=args.out or f"agentless/cov_on_baseline_{tag}.json"
    json.dump(out, open(of,"w"), ensure_ascii=False, indent=1); print("\nwritten:",of)

if __name__=="__main__": main()
