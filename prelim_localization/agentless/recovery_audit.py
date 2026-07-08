#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""救回审计 (no-expand10): 对每个基线漏金标实例, 看二次判别 additions 是否碰到漏掉的金标.
  flip      = base∪radd ⊇ gold 而 base ⊉ gold (superset 翻转)
  touched   = radd 覆盖到 至少一个 base 漏掉的金标行
  recoverable = 漏金标全部 in-file 且 执行/±2 (miss_decompose 口径)
=> 区分 '模型没给出能覆盖金标的定位' vs '给了但仍差(D类/远执行)'.
"""
import argparse, json
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); a=ap.parse_args()
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    red=json.load(open(f"agentless/rediscr_cache_{a.tag}.json"))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    miss=0; have_red=0; touched=0; flip=0; recoverable=0; recov_and_flip=0; recov_touched=0
    rows_pr=[]
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid); ra=red.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su)
        missed=set(gold)-set(base)
        if not missed: continue
        miss+=1
        ff=set(E.LOC[iid]["found_files"][:NB.TOP_N])
        ec={f:E.cov_for(f,cm) for f in ff}
        recov = all((f in ff) and (ln in ec[f] or any((ln+d) in ec[f] for d in (-2,-1,1,2))) for (f,ln) in missed)
        if recov: recoverable+=1
        radd=NB.native_pairs(iid,r,[ra]) if ra else set()
        if radd-base: have_red+=1
        tched = bool(missed & radd)
        if tched: touched+=1
        fl = set(gold)<=(base|radd) and not (set(gold)<=base)
        if fl: flip+=1
        if recov and tched: recov_touched+=1
        if recov and fl: recov_and_flip+=1
        if recov: rows_pr.append((iid, len(missed), tched, fl))
    print(f"\n===== {a.tag}  二次判别救回审计 (no-expand10) =====")
    print(f"  基线漏金标实例: {miss}   其中理论可救(in-file&exec/±2): {recoverable}")
    print(f"  二次判别产出新additions的实例: {have_red}")
    print(f"  additions 碰到漏掉金标(touched): {touched}/{miss}   其中理论可救内: {recov_touched}/{recoverable}")
    print(f"  superset 翻转(flip): {flip}/{miss}   其中理论可救内: {recov_and_flip}/{recoverable}")
    print(f"  --- 理论可救实例逐条 (iid, #漏金标, touched, flip) ---")
    for iid,nm,t,f in rows_pr:
        print(f"    {iid:<32} miss={nm:<3} touched={'Y' if t else '.'} flip={'Y' if f else '.'}")

if __name__=="__main__": main()
