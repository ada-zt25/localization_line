#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_sys.path[:0]=[_os.path.join(_ROOT,"agentless_vendor","repo"), _ROOT]; _os.chdir(_ROOT)
"""Offline ablation: which TARGETED coverage expansion recovers the most region Contains-all gold
at the least pool size? All additions restricted to EXECUTED lines (on-path). No LLM.
  E1 crash-frame funcs        (traceback frames' functions, exec)              [= current V1]
  E2 + 1-hop callees          (functions the crash-frame funcs CALL, exec)     [the helper]
  E3 + def-use slice          (backward/both slice from crash seeds, exec)     [root-cause def]
  E4 + issue-token exec lines (executed lines overlapping issue symbols)       [issue-relevant]
  E5 + 1-hop callers          (functions that CALL the crash-frame funcs, exec)[up the stack]
Report cumulative region∪(E1..Ek) Contains-all + pool LoC, vs base region and the exec±2 ceiling.
"""
import json, statistics as st
import agentless.al_vote_eval as E
import p0_line_recall as p0, code_graph as cg
from agentless.util.preprocess_data import transfer_arb_locs_to_locs
rows={r['instance_id']:r for r in p0.load_rows(500,dataset='lite')}
cov=json.load(open('egl_cov_cache.json'))
sub=json.load(open('rq3_subsets.json'))['crash_onpath']

_G={}
def graph(r,f):
    k=(r['repo'],r['base_commit'],f)
    if k not in _G:
        try: _G[k]=cg.CodeGraph(p0.fetch_file(*k),f)
        except Exception: _G[k]=None
    return _G[k]

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

def func_exec_lines(g,fi,ex):
    fn=g.funcs[fi]; return {ln for ln in range(fn['start'],fn['end']+1) if ln in ex}

def expansions(iid,r,cm):
    """Return dict name->set((file,line)) for E1..E5, all exec-restricted."""
    L=E.LOC[iid]; ff=L['found_files']; issue=r.get('problem_statement') or ''
    out={k:set() for k in ('E1','E2','E3','E4','E5')}
    for f in ff:
        g=graph(r,f)
        if not g or not g.ok: continue
        ex=E.cov_for(f,cm)
        seeds=g.seed_from_traceback(issue)
        crash_fis={g.line_func.get(s) for s in seeds if g.line_func.get(s) is not None}
        # E1 crash-frame functions
        for fi in crash_fis: out['E1']|={(f,ln) for ln in func_exec_lines(g,fi,ex)}
        # E2 1-hop callees
        for fi in crash_fis:
            for callee in g.funcs[fi].get('calls',()):
                for cfi in g.name2func.get(callee,[]):
                    out['E2']|={(f,ln) for ln in func_exec_lines(g,cfi,ex)}
        # E3 def-use slice from crash seeds
        try:
            sl=g.dataflow_slice(set(seeds),'both',depth=2,cap=120)
            for s in sl:
                end=g._stmt_end(s) if hasattr(g,'_stmt_end') else s
                for ln in range(s,end+1):
                    if ln in ex: out['E3'].add((f,ln))
        except Exception: pass
        # E4 issue-token overlapping executed lines
        try:
            itok=set(cg.tokenize(issue)); lines=g.lines if hasattr(g,'lines') else p0.fetch_file(r['repo'],r['base_commit'],f).splitlines()
            for ln in ex:
                if 1<=ln<=len(lines) and (set(cg.tokenize(lines[ln-1])) & itok): out['E4'].add((f,ln))
        except Exception: pass
        # E5 1-hop callers
        crash_names={g.funcs[fi]['name'] for fi in crash_fis if fi is not None}
        for j,fn in enumerate(g.funcs):
            if crash_names & set(fn.get('calls',())):
                out['E5']|={(f,ln) for ln in func_exec_lines(g,j,ex)}
    return out

def frontier(iid,cm,adj=2):
    add=set()
    for f in E.LOC[iid]['found_files']:
        for ln in E.cov_for(f,cm):
            for d in range(-adj,adj+1): add.add((f,ln+d))
    return add

def main():
    order=['region','+E1','+E1E2','+E1E2E3','+E4(issue-only)','+E1E2E3E4','+E1E2E3E4E5','region∪exec±2(ceiling)']
    ca={k:[] for k in order}; loc={k:[] for k in order}      # raw-pool ceiling
    ca10={k:[] for k in order}; loc10={k:[] for k in order}  # ±10-expanded (metric-realizable) ceiling
    n=0
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid)
        if not r or not cm or iid not in E.LOC: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        n+=1
        reg=region_of(iid,r); ex=expansions(iid,r,cm); fr=frontier(iid,cm)
        ff=E.LOC[iid]['found_files']
        try: flen={f:len(p0.fetch_file(r['repo'],r['base_commit'],f).splitlines()) for f in ff}
        except Exception: flen={}
        pools={
            'region':reg,
            '+E1':reg|ex['E1'],
            '+E1E2':reg|ex['E1']|ex['E2'],
            '+E1E2E3':reg|ex['E1']|ex['E2']|ex['E3'],
            '+E4(issue-only)':reg|ex['E4'],
            '+E1E2E3E4':reg|ex['E1']|ex['E2']|ex['E3']|ex['E4'],
            '+E1E2E3E4E5':reg|ex['E1']|ex['E2']|ex['E3']|ex['E4']|ex['E5'],
            'region∪exec±2(ceiling)':reg|fr,
        }
        for k,S in pools.items():
            ca[k].append(1 if gold<=S else 0); loc[k].append(len(S))
            S10=E.expand10(S,flen)
            ca10[k].append(1 if gold<=S10 else 0); loc10[k].append(len(S10))
        print(f"  ..{n} {iid}", file=_sys.stderr)
    print(f"\n定向扩展消融 · 区域 Contains-all 天花板 (crash·on-path n={n})")
    print(f"  裸池 = gold⊆pool;  ±10 = gold⊆(pool±10展开)=真实指标可realize上限\n")
    print(f"  {'pool':<26}{'裸池 CA':>9}{'裸池LoC':>9}{'±10 CA':>9}{'±10 LoC':>9}")
    for k in order:
        print(f"  {k:<26}{100*st.mean(ca[k]):>9.1f}{st.mean(loc[k]):>9.0f}{100*st.mean(ca10[k]):>9.1f}{st.mean(loc10[k]):>9.0f}")
    print(f"\n  对照: AL realized superset 66.7 @ LoC 341;  当前 al_vote(+E1) realized 68.4 @ 290")

if __name__=='__main__': main()
