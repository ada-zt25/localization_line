#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_sys.path[:0]=[_os.path.join(_ROOT,"agentless_vendor","repo"), _ROOT]; _os.chdir(_ROOT)
"""Selective E4: instead of ALL issue-token executed lines (ceiling 82.5 but pool 3338), add only the
top-K executed lines ranked by line_scores_v2 (issue relevance + def-use-from-traceback + coverage).
Goal: keep the 82.5-ish ceiling at a fraction of the pool -> a realizable, LoC-cheap superset win.
Report ±10 (metric-realizable) Contains-all ceiling + ±10 pool LoC, for K per file."""
import json, re, statistics as st
import agentless.al_vote_eval as E
import p0_line_recall as p0, code_graph as cg
from agentless.util.preprocess_data import transfer_arb_locs_to_locs
rows={r['instance_id']:r for r in p0.load_rows(500,dataset='lite')}
cov=json.load(open('egl_cov_cache.json'))
sub=json.load(open('rq3_subsets.json'))['crash_onpath']
KS=[15,30,60,120]
def crash_ctx(r):
    ps=r.get('problem_statement') or ''; m=re.search(r"Traceback \(most recent call last\)",ps)
    return ps[m.start():m.start()+1600] if m else ps[:1600]
def region_of(iid,r):
    L=E.LOC[iid]; ff=L['found_files']; reg=set()
    for i,rl in enumerate(L['found_related_locs']):
        if i>=len(ff) or not rl or all(not x.strip() for x in rl): continue
        f=ff[i]
        try: src=p0.fetch_file(r['repo'],r['base_commit'],f); _,iv=transfer_arb_locs_to_locs(rl,None,f,10,True,False,file_content=src)
        except Exception: continue
        for a,b in iv:
            for ln in range(a,b+1): reg.add((f,ln))
    return reg
def topk_scored_exec(iid,r,cm,K):
    """top-K executed lines per file by line_scores_v2(issue+traceback-slice+coverage)."""
    L=E.LOC[iid]; ff=L['found_files']; issue=(r.get('problem_statement') or '')[:5000]; fail=crash_ctx(r); add=set()
    for f in ff:
        try: src=p0.fetch_file(r['repo'],r['base_commit'],f); g=cg.CodeGraph(src,f)
        except Exception: continue
        if not g.ok: continue
        ex=E.cov_for(f,cm)
        sc=g.line_scores_v2(issue,failure=fail,coverage_lines=ex,graded=True,use_coverage=True)
        exec_scored=sorted((ln for ln in sc if ln in ex), key=lambda l:-sc[l])[:K]
        for ln in exec_scored: add.add((f,ln))
    return add
def main():
    order=['region']+[f'+top{K} scored-exec' for K in KS]
    ca={k:[] for k in order}; loc={k:[] for k in order}
    n=0
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid)
        if not r or not cm or iid not in E.LOC: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        n+=1
        reg=region_of(iid,r); ff=E.LOC[iid]['found_files']
        try: flen={f:len(p0.fetch_file(r['repo'],r['base_commit'],f).splitlines()) for f in ff}
        except Exception: flen={}
        pools={'region':reg}
        for K in KS: pools[f'+top{K} scored-exec']=reg|topk_scored_exec(iid,r,cm,K)
        for k,S in pools.items():
            S10=E.expand10(S,flen); ca[k].append(1 if gold<=S10 else 0); loc[k].append(len(S10))
        print(f"  ..{n} {iid}",file=_sys.stderr)
    print(f"\nselective-E4 · ±10 可realize Contains-all 天花板 + 池 (crash·on-path n={n})\n")
    print(f"  {'pool':<26}{'±10 CA':>9}{'±10 LoC':>9}")
    for k in order:
        print(f"  {k:<26}{100*st.mean(ca[k]):>9.1f}{st.mean(loc[k]):>9.0f}")
    print(f"\n  对照: region 68.4 @677;  E4-all 82.5 @3338;  AL realized 66.7 @341;  当前 al_vote 68.4 @290")
if __name__=='__main__': main()
