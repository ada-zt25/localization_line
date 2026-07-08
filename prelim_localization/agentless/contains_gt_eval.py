#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""P0 gate: reproduce Agentless Table 2 (Contains-GT + LoC) on its released GPT-4o Lite artifact,
using Agentless's OWN transfer_arb_locs_to_locs (context_window=10, function/class->span).
PASSED 2026-07-05: file-contains 82.7% (paper 81.7), merged LoC 336 (342), per-sample LoC 179 (165-213).
Run:  python agentless/contains_gt_eval.py [limit]
"""
import json, statistics as st
import p0_line_recall as p0
from agentless.util.preprocess_data import transfer_arb_locs_to_locs

LOC=_os.path.join(_VEND,"agentless_gpt4o_lite_loc_outputs.jsonl")
loc={json.loads(l)["instance_id"]:json.loads(l) for l in open(LOC)}
rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="lite")}

def cand_pairs_for_sample(sample_locs, found_files, r):
    pairs=set()
    for i, locs in enumerate(sample_locs):
        if i>=len(found_files): break
        f=found_files[i]
        if not locs or all(not x.strip() for x in locs): continue
        try:
            src=p0.fetch_file(r["repo"], r["base_commit"], f)
            _, iv = transfer_arb_locs_to_locs(locs, None, f, 10, True, False, file_content=src)
        except Exception:
            continue
        for a,b in iv:
            for ln in range(a,b+1): pairs.add((f,ln))
    return pairs

def gold_pairs(r, clean):
    files=p0.parse_patch(r.get("patch") or ""); out=set()
    for f in files:
        if not f.endswith(".py"): continue
        try: lines=p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()
        except Exception: lines=[]
        g=p0.clean_gold(files[f]["region"],lines) if (clean and lines) else files[f]["region"]
        for ln in g: out.add((f,ln))
    return out

def run(clean, limit=None):
    ps_all=[]; ps_any=[]; ps_loc=[]; m_all=[]; m_any=[]; m_loc=[]; fc=[]
    ids=list(loc)[:limit] if limit else list(loc)
    for iid in ids:
        r=rows.get(iid)
        if not r: continue
        L=loc[iid]; ff=L["found_files"]; gold=gold_pairs(r,clean)
        if not gold: continue
        fc.append(1 if {f for f,_ in gold}<=set(ff) else 0)
        merged=set(); sa=[]; sy=[]; sl=[]
        for s in L["found_edit_locs"]:
            cp=cand_pairs_for_sample(s,ff,r); merged|=cp
            sa.append(1 if gold<=cp else 0); sy.append(1 if gold&cp else 0); sl.append(len(cp))
        ps_all.append(st.mean(sa)); ps_any.append(st.mean(sy)); ps_loc.append(st.mean(sl))
        m_all.append(1 if gold<=merged else 0); m_any.append(1 if gold&merged else 0); m_loc.append(len(merged))
    n=len(ps_loc)
    print(f"  gold={'ARISE-clean' if clean else 'raw-patch'}  n={n}")
    print(f"  file-contains-GT: {100*st.mean(fc):.1f}%  (paper 81.7)")
    print(f"  per-sample: all={100*st.mean(ps_all):.1f}% any={100*st.mean(ps_any):.1f}% LoC={st.mean(ps_loc):.0f}  (paper 51-53% @165-213)")
    print(f"  merged(4):  all={100*st.mean(m_all):.1f}% any={100*st.mean(m_any):.1f}% LoC={st.mean(m_loc):.0f}  (paper ~59% @342)")

if __name__=="__main__":
    lim=int(_sys.argv[1]) if len(_sys.argv)>1 else None
    print("=== RAW patch gold ==="); run(False,lim)
    print("=== ARISE-clean gold ==="); run(True,lim)
