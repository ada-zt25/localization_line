#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""AL vs AL+vote vs AL+vote+cov-frontier on crash·on-path, scored with Agentless's metric.

Shared upstream = Agentless's file + related-element localization (from the released GPT-4o artifact).
Only the EDIT-LOCATION stage varies:
  AL              : Agentless native 4-sample edit locs (±10 expanded)                     [baseline]
  AL+vote         : OUR k-sample self-consistency vote on Agentless's related-element region,
                    top-N voted lines (±10 expanded)                                        [vote half]
  AL+vote+cov-fr  : the voted lines FRONTIER-filtered to executed±2 first, then top-N (±10) [+coverage]
Metric = Agentless Contains-GT (superset & any) + Avg LoC. We sweep top-N -> Pareto curve, and report
the LoC-matched operating point vs AL.

  SWEBENCH_DATASET=lite OPENAI_BASE_URL=https://api.siliconflow.cn/v1 OPENAI_API_KEY=... \
    MODEL=deepseek-ai/DeepSeek-V3 python agentless/al_vote_eval.py --k 10 --workers 4
"""
import argparse, json, statistics as st, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import p0_line_recall as p0
import region_loc as R
import code_graph as cg
from agentless.util.preprocess_data import transfer_arb_locs_to_locs

LOC={json.loads(l)["instance_id"]:json.loads(l) for l in open(_os.environ.get("EGL_LOC_FILE", _os.path.join(_VEND,"agentless_gpt4o_lite_loc_outputs.jsonl")))}
NSWEEP=[1,2,3,4,5,6,8,10,15,25,40,60,100,150,200]

def crash_frame_exec_lines(src, f, issue, ex):
    """V1 selective expansion: executed lines of functions named in the traceback frames.
    Recovers on-path gold that Agentless's element-selection dropped from the region, cheaply."""
    add=set()
    try: g=cg.CodeGraph(src, f)
    except Exception: return add
    if not g.ok: return add
    seeds=g.seed_from_traceback(issue or "")
    for s in seeds:
        fi=g.line_func.get(s)
        if fi is None: continue
        fn=g.funcs[fi]
        for ln in range(fn["start"], fn["end"]+1):
            if ln in ex: add.add(ln)
    return add

def cov_for(f,cm):
    if f in cm: return set(cm[f])
    for cf,cl in cm.items():
        if cf==f or cf.endswith('/'+f) or f.endswith('/'+cf): return set(cl)  # 路径边界匹配, 不用裸basename(修 sym_expr.py↔expr.py 误配)
    return set()

def expand10(pairs, flen):
    out=set()
    for (f,ln) in pairs:
        n=flen.get(f, ln+10)
        for k in range(max(1,ln-10), min(n,ln+10)+1): out.add((f,k))
    return out

def intervals_to_lines(iv):
    s=set()
    for a,b in iv:
        for ln in range(a,b+1): s.add(ln)
    return s

def al_native_pairs(iid, r):
    L=LOC[iid]; ff=L["found_files"]; merged=set()
    for s in L["found_edit_locs"]:
        for i,locs in enumerate(s):
            if i>=len(ff) or not locs or all(not x.strip() for x in locs): continue
            f=ff[i]
            try:
                src=p0.fetch_file(r["repo"],r["base_commit"],f); _,iv=transfer_arb_locs_to_locs(locs,None,f,10,True,False,file_content=src)
            except Exception: continue
            for ln in intervals_to_lines(iv): merged.add((f,ln))
    return merged

def gold_pairs(r, clean=False):
    files=p0.parse_patch(r.get("patch") or ""); out=set()
    for f in files:
        if not f.endswith(".py"): continue
        try: lines=p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()
        except Exception: lines=[]
        g=p0.clean_gold(files[f]["region"],lines) if (clean and lines) else files[f]["region"]
        for ln in g: out.add((f,ln))
    return out

import re as _re
def _crash_ctx(r, cap=1600):
    ps=r.get("problem_statement") or ""
    m=_re.search(r"Traceback \(most recent call last\)", ps)
    if m: return ps[m.start():m.start()+cap]
    fr=_re.findall(r'File "[^"]+", line \d+[^\n]*', ps)
    return ("\n".join(fr[:20])[:cap]) if fr else ps[-1200:]

def scored_exec_topk(src, f, issue, fail, ex, K):
    """V2 selective expansion: top-K executed lines ranked by line_scores_v2 (issue relevance +
    def-use-from-traceback + coverage). Raises the ±10 region ceiling 68.4->75.4 at K=30 (saturates)."""
    try: g=cg.CodeGraph(src, f)
    except Exception: return set()
    if not g.ok: return set()
    sc=g.line_scores_v2(issue, failure=fail, coverage_lines=ex, graded=True, use_coverage=True)
    return set(sorted((l for l in sc if l in ex), key=lambda l:-sc[l])[:K])

def do_vote(model, iid, r, k, lines_cap, cache, lock, cm=None, cov_annot=False, expand=False, expand_topk=30):
    """Return {(file,line): freq} from voting on Agentless's related-element region (cached).
    cov_annot (channel ①): mark executed lines + prepend crash traceback in the vote prompt.
    expand (V2): union top-K issue+crash-scored executed lines into the region (raise the ceiling)."""
    if iid in cache: return {tuple(json.loads(kk)):v for kk,v in cache[iid].items()}
    L=LOC[iid]; ff=L["found_files"]; rel=L["found_related_locs"]
    issue=(r.get("problem_statement") or "")[:5000]
    cctx=_crash_ctx(r)
    voted={}
    for i, rlocs in enumerate(rel):
        if i>=len(ff) or not rlocs or all(not x.strip() for x in rlocs): continue
        f=ff[i]
        try:
            src=p0.fetch_file(r["repo"],r["base_commit"],f); lines=src.splitlines()
            _,iv=transfer_arb_locs_to_locs(rlocs,None,f,10,True,False,file_content=src)
        except Exception: continue
        region={ln for ln in intervals_to_lines(iv) if 1<=ln<=len(lines)}
        if expand and cm:
            region |= {ln for ln in scored_exec_topk(src, f, issue, cctx, cov_for(f, cm), expand_topk) if 1<=ln<=len(lines)}
        if not region: continue
        annot = cov_for(f, cm) if (cov_annot and cm) else None
        try:
            freq,_=R._vote(model, issue, f, lines, region, k, lines_cap, cov_annot=annot, crash_ctx=(cctx if cov_annot else None))
        except Exception:
            freq={}
        for ln,fr in freq.items(): voted[(f,int(ln))]=fr
    with lock:
        cache[iid]={json.dumps(list(kk)):v for kk,v in voted.items()}
    return voted

def topN(voted, N):
    return [p for p,_ in sorted(voted.items(), key=lambda x:-x[1])[:N]]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--k",type=int,default=10); ap.add_argument("--workers",type=int,default=4)
    ap.add_argument("--lines-cap",type=int,default=30); ap.add_argument("--sample",type=int,default=0)
    ap.add_argument("--adj",type=int,default=2)
    ap.add_argument("--cov-annot",action="store_true",help="channel ①: coverage-annotated + crash-context vote (use a SEPARATE --cache)")
    ap.add_argument("--expand",action="store_true",help="V2: union top-K issue+crash-scored executed lines into the vote region")
    ap.add_argument("--expand-topk",type=int,default=30,help="K for scored-exec expansion (saturates ~30)")
    ap.add_argument("--out",default=_os.path.join(_HERE,"al_vote_result.json"))
    ap.add_argument("--cache",default=_os.path.join(_HERE,"al_vote_cache.json"))
    args=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    sub=json.load(open("rq3_subsets.json"))["crash_onpath"]
    if args.sample: sub=sub[:args.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
    cov=json.load(open("egl_cov_cache.json"))
    from pathlib import Path
    cache=json.loads(Path(args.cache).read_text()) if Path(args.cache).exists() else {}
    lock=threading.Lock()

    inst=[]  # per-instance materialized data
    def work(iid):
        r=rows.get(iid); cm=cov.get(iid)
        if not r or not cm or iid not in LOC: return None
        gold=gold_pairs(r);
        if not gold: return None
        voted=do_vote(model, iid, r, args.k, args.lines_cap, cache, lock, cm=cm, cov_annot=args.cov_annot, expand=args.expand, expand_topk=args.expand_topk)
        with lock: Path(args.cache).write_text(json.dumps(cache))
        AL=al_native_pairs(iid, r)
        try: flen={f:len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()) for f in {p[0] for p in voted}|{p[0] for p in AL}}
        except Exception: flen={}
        ff=LOC[iid]["found_files"]
        execset={(f,ln) for f in ff for ln in cov_for(f,cm)}
        exec_adj=set(execset)
        for f in ff:
            for ln in cov_for(f,cm):
                for d in range(-args.adj,args.adj+1): exec_adj.add((f,ln+d))
        voted_fr={p:voted[p] for p in voted if p in exec_adj}
        return {"iid":iid,"gold":list(map(list,gold)),"AL":list(map(list,AL)),
                "voted":{json.dumps(list(k)):v for k,v in voted.items()},
                "voted_fr":{json.dumps(list(k)):v for k,v in voted_fr.items()},
                "flen":flen}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs=[ex.submit(work,iid) for iid in sub]
        for n,fut in enumerate(as_completed(futs),1):
            r=fut.result()
            if r: inst.append(r)
            print(f"[{n}/{len(sub)}] voted={len(inst)}", file=_sys.stderr); _sys.stderr.flush()

    def score(pairs_list_fn):
        allc=[]; anyc=[]; loc=[]
        for x in inst:
            gold=set(map(tuple,x["gold"])); flen={f:l for f,l in x["flen"].items()}
            S=expand10(pairs_list_fn(x), flen)
            allc.append(1 if gold<=S else 0); anyc.append(1 if gold&S else 0); loc.append(len(S))
        return 100*st.mean(allc),100*st.mean(anyc),st.mean(loc)
    def voted_of(x,key): return {tuple(json.loads(k)):v for k,v in x[key].items()}

    N=len(inst)
    print(f"\n==== AL vs AL+vote vs AL+vote+cov-frontier  (crash·on-path, Agentless metric)  n={N} k={args.k} ====")
    a,an,l=score(lambda x:set(map(tuple,x["AL"])))
    print(f"AL (Agentless native)          Contains-all={a:.1f}  any={an:.1f}  LoC={l:.0f}")
    print("\nAL+vote  (top-N voted, ±10):")
    print(f"{'N':>4}{'Contains-all':>14}{'any':>8}{'LoC':>8}")
    curve_v={}
    for Nn in NSWEEP:
        a2,an2,l2=score(lambda x,Nn=Nn: topN(voted_of(x,'voted'),Nn))
        curve_v[Nn]=(a2,an2,l2); print(f"{Nn:>4}{a2:>14.1f}{an2:>8.1f}{l2:>8.0f}")
    print("\nAL+vote+cov-frontier  (voted∩exec±{}, top-N, ±10):".format(args.adj))
    print(f"{'N':>4}{'Contains-all':>14}{'any':>8}{'LoC':>8}")
    curve_c={}
    for Nn in NSWEEP:
        a3,an3,l3=score(lambda x,Nn=Nn: topN(voted_of(x,'voted_fr'),Nn))
        curve_c[Nn]=(a3,an3,l3); print(f"{Nn:>4}{a3:>14.1f}{an3:>8.1f}{l3:>8.0f}")
    # LoC-matched operating point vs AL
    def matched(curve):
        best=min(curve.items(), key=lambda kv: abs(kv[1][2]-l))
        return best
    print(f"\nLoC-matched to AL (~{l:.0f}):")
    for name,c in [("AL+vote",curve_v),("AL+vote+cov-fr",curve_c)]:
        Nn,(a2,an2,l2)=matched(c); print(f"  {name}: N={Nn} Contains-all={a2:.1f} any={an2:.1f} LoC={l2:.0f}  (Δall vs AL {a2-a:+.1f})")
    json.dump({"n":N,"k":args.k,"AL":[a,an,l],"vote":curve_v,"vote_cov":curve_c}, open(args.out,"w"), indent=1)
    print("written:",args.out)

if __name__=="__main__":
    main()
