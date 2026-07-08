#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""Early signal (0 GPU): apply execution-coverage filter to Agentless's OWN GPT-4o edit-location set,
on crash·on-path, scored with Agentless's Contains-GT + LoC. Isolates the COVERAGE half of A3 (voting
half needs our backbone). Tests the superset-vs-filter tension (plan 5.2).
Result 2026-07-05 (n=56): AL all62.5/any85.7/LoC299; +hard all25.0/any83.9/LoC89; +frontier all57.1/any83.9/LoC180.
Run:  python agentless/cov_filter_on_agentless.py
"""
import json, statistics as st
import p0_line_recall as p0
from agentless.util.preprocess_data import transfer_arb_locs_to_locs

loc={json.loads(l)["instance_id"]:json.loads(l) for l in open(_os.path.join(_VEND,"agentless_gpt4o_lite_loc_outputs.jsonl"))}
rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}
cov=json.load(open("egl_cov_cache.json"))
def cov_for(f,cm):
    if f in cm: return set(cm[f])
    for cf,cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split('/')[-1]): return set(cl)
    return set()
def al_pairs(iid):
    L=loc[iid]; r=rows[iid]; ff=L["found_files"]; merged=set()
    for s in L["found_edit_locs"]:
        for i,locs in enumerate(s):
            if i>=len(ff) or not locs or all(not x.strip() for x in locs): continue
            f=ff[i]
            try:
                src=p0.fetch_file(r["repo"],r["base_commit"],f); _,iv=transfer_arb_locs_to_locs(locs,None,f,10,True,False,file_content=src)
            except Exception: continue
            for a,b in iv:
                for ln in range(a,b+1): merged.add((f,ln))
    return merged,ff
def gold_pairs(iid,clean=False):
    r=rows[iid]; files=p0.parse_patch(r.get("patch") or ""); out=set()
    for f in files:
        if not f.endswith(".py"): continue
        try: lines=p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()
        except Exception: lines=[]
        g=p0.clean_gold(files[f]["region"],lines) if (clean and lines) else files[f]["region"]
        for ln in g: out.add((f,ln))
    return out

def main(subset="crash_onpath", adj=2):
    sub=json.load(open("rq3_subsets.json"))[subset]
    arms={a:{"all":[],"any":[],"loc":[]} for a in ["AL","AL+cov","AL+cov_frontier"]}
    n=0
    for iid in sub:
        if iid not in loc or iid not in cov: continue
        cm=cov[iid]; AL,ff=al_pairs(iid); gold=gold_pairs(iid)
        if not gold or not AL: continue
        n+=1
        execset={(f,ln) for f in ff for ln in cov_for(f,cm)}
        exec_adj=set(execset)
        for f in ff:
            for ln in cov_for(f,cm):
                for d in range(-adj,adj+1): exec_adj.add((f,ln+d))
        for a,S in {"AL":AL,"AL+cov":AL&execset,"AL+cov_frontier":AL&exec_adj}.items():
            arms[a]["all"].append(1 if gold<=S else 0); arms[a]["any"].append(1 if gold&S else 0); arms[a]["loc"].append(len(S))
    print(f"Agentless GPT-4o artifact on {subset}  n={n}  (frontier=exec±{adj})\n")
    print(f"{'arm':<18}{'Contains-all%':>14}{'Contains-any%':>14}{'avgLoC':>9}")
    for a in ["AL","AL+cov","AL+cov_frontier"]:
        d=arms[a]; print(f"{a:<18}{100*st.mean(d['all']):>14.1f}{100*st.mean(d['any']):>14.1f}{st.mean(d['loc']):>9.0f}")

if __name__=="__main__":
    main()
