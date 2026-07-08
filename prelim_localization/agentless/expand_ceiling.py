#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_sys.path[:0]=[_os.path.join(_ROOT,"agentless_vendor","repo"), _ROOT]; _os.chdir(_ROOT)
"""Offline ceiling test: can 'selective coverage expansion' raise the region Contains-all ceiling
from Agentless's 64.9% toward the 75.4% exec-union ceiling, at controlled LoC? No LLM."""
import json, statistics as st
import agentless.al_vote_eval as E
import p0_line_recall as p0, code_graph as cg
from agentless.util.preprocess_data import transfer_arb_locs_to_locs
rows={r['instance_id']:r for r in p0.load_rows(500,dataset='lite')}
cov=json.load(open('egl_cov_cache.json'))
sub=json.load(open('rq3_subsets.json'))['crash_onpath']

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

_GCACHE={}
def graph(r,f):
    key=(r['repo'],r['base_commit'],f)
    if key not in _GCACHE:
        try: _GCACHE[key]=cg.CodeGraph(p0.fetch_file(*key), f)
        except Exception: _GCACHE[key]=None
    return _GCACHE[key]

def crash_funcs_exec(iid,r,cm,adj):
    L=E.LOC[iid]; ff=L['found_files']; issue=r.get('problem_statement') or ''; add=set()
    for f in ff:
        g=graph(r,f)
        if not g or not g.ok: continue
        ex=E.cov_for(f,cm); seeds=g.seed_from_traceback(issue)
        fis={g.line_func.get(s) for s in seeds if g.line_func.get(s) is not None}
        for fi in fis:
            fn=g.funcs[fi]
            for ln in range(fn['start'],fn['end']+1):
                if ln in ex:
                    for d in range(-adj,adj+1): add.add((f,ln+d))
    return add

def frontier_all(iid,r,cm,adj):
    add=set()
    for f in E.LOC[iid]['found_files']:
        for ln in E.cov_for(f,cm):
            for d in range(-adj,adj+1): add.add((f,ln+d))
    return add

def main():
    V={"V0 region(base)":[], "V1 +crash-frame func exec±2":[], "V2 region∩none, +frontier exec±2":[],
       "V3 crash-func-exec ∪ region∩frontier":[]}
    L={k:[] for k in V}
    n=0
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid)
        if not r or not cm or iid not in E.LOC: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        n+=1
        region=region_of(iid,r); cf=crash_funcs_exec(iid,r,cm,2); fr=frontier_all(iid,r,cm,2)
        pools={"V0 region(base)":region, "V1 +crash-frame func exec±2":region|cf,
               "V2 region∩none, +frontier exec±2":region|fr,
               "V3 crash-func-exec ∪ region∩frontier":cf|(region&fr)}
        for k,S in pools.items():
            V[k].append(1 if gold<=S else 0); L[k].append(len(S))
        print(f"  ..{n} {iid}", file=_sys.stderr)
    print(f"\n选择性扩展 · 区域 Contains-all 天花板 (crash·on-path n={n})\n")
    print(f"  {'variant':<38}{'Contains-all':>13}{'avgLoC':>9}")
    for k in V:
        print(f"  {k:<38}{100*st.mean(V[k]):>13.1f}{st.mean(L[k]):>9.0f}")
    print(f"\n  对照: AL realized 61.4 @ ~340; 区域∪全部exec(无±) 75.4 @ 1589; frontier天花板 70.2")

if __name__=="__main__": main()
