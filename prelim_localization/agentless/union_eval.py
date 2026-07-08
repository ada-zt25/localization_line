#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_sys.path[:0]=[_os.path.join(_ROOT,"agentless_vendor","repo"), _ROOT]; _os.chdir(_ROOT)
"""『并入 Agentless 预测』(union) arm, scored with Agentless's superset + LoC (NO any, NO LLM).
Instead of REPLACING Agentless's edit locations with our vote, UNION them:
  final = Agentless_native_edit_locs  ∪  topN(our vote)          [+ optional ∩ frontier(exec±2)]
Uses the RECOMMENDED vote = 投票+打分扩区域 (top-30 scored-exec expansion + channel①),
cached in agentless/al_vote_cache_v2.json. Sweeps N; reports superset + LoC per operating point.
  python agentless/union_eval.py            (crash·on-path, DeepSeek-V3 cached votes)
"""
import json, statistics as st
import agentless.al_vote_eval as E
import p0_line_recall as p0

CACHES={  # label -> cache file (both = 扩区域 + channel① 投票, only the expansion differs)
    "V1 崩溃帧扩区+投票": "al_vote_cache_expand.json",
    "V2 打分扩区+投票":   "al_vote_cache_v2.json",
}
NSWEEP=[10,25,40,60,100,150,200]

def main():
    which=_sys.argv[1] if len(_sys.argv)>1 else None      # optional single label
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
    cov=json.load(open("egl_cov_cache.json"))
    labels=[which] if which in CACHES else list(CACHES)
    for lab in labels:
        run_one(lab, _os.path.join(_HERE, CACHES[lab]), rows, cov)

def run_one(LABEL, CACHE, rows, cov):
    cache=json.load(open(CACHE))
    sub=json.load(open("rq3_subsets.json"))["crash_onpath"]
    inst=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); vc=cache.get(iid)
        if not r or not cm or iid not in E.LOC or not vc: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        voted={tuple(json.loads(k)):v for k,v in vc.items()}
        AL=E.al_native_pairs(iid,r); ff=E.LOC[iid]["found_files"]
        try: flen={f:len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()) for f in {p[0] for p in voted}|{p[0] for p in AL}}
        except Exception: flen={}
        fr=set()
        for f in ff:
            for ln in E.cov_for(f,cm):
                for d in range(-2,3): fr.add((f,ln+d))
        inst.append(dict(gold=gold,AL=AL,voted=voted,flen=flen,fr=fr))
    n=len(inst)
    def sc(fn):
        a=[];l=[]
        for x in inst:
            S=E.expand10(fn(x),x["flen"]); a.append(1 if x["gold"]<=S else 0); l.append(len(S))
        return 100*st.mean(a), st.mean(l)
    al_s,al_l=sc(lambda x:set(x["AL"]))
    out={"n":n,"model":"deepseek-ai/DeepSeek-V3","subset":"crash_onpath","vote":LABEL,
         "AL":{"superset":round(al_s,1),"LoC":round(al_l)},"union":{},"union_frontier":{}}
    print(f"\n================  {LABEL}  ================")
    print(f"n={n}   Agentless 基线: superset={al_s:.1f}  LoC={al_l:.0f}\n")
    print(f"并入 Agentless 预测 = Agentless ∪ ({LABEL}, top-N)   [左=纯并集, 右=并集∩frontier]")
    print(f"{'N':>4} | {'纯并集 superset/LoC':>22} | {'并集∩frontier superset/LoC':>26}")
    for N in NSWEEP:
        u_s,u_l=sc(lambda x,N=N:set(x["AL"])|set(E.topN(x["voted"],N)))
        f_s,f_l=sc(lambda x,N=N:(set(x["AL"])|set(E.topN(x["voted"],N)))&x["fr"])
        out["union"][N]={"superset":round(u_s,1),"LoC":round(u_l)}
        out["union_frontier"][N]={"superset":round(f_s,1),"LoC":round(f_l)}
        print(f"{N:>4} | {u_s:>8.1f}({u_s-al_s:+.1f}) {u_l:>5.0f}({100*(u_l/al_l-1):+.0f}%) | "
              f"{f_s:>8.1f}({f_s-al_s:+.1f}) {f_l:>5.0f}({100*(f_l/al_l-1):+.0f}%)")
    fn=_os.path.join(_HERE, "union_result_"+("v1" if "V1" in LABEL else "v2")+".json")
    json.dump(out, open(fn,"w"), ensure_ascii=False, indent=1)
    print("written:", _os.path.basename(fn))

if __name__=="__main__": main()
