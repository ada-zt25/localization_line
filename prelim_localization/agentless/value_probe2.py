#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""E2: 付费值探针 (诊断). 配对测【真实运行时值】能否撬开判别墙.
两臂 (同一批执行漏金标行 + covered对照):
  ctrl: 行上下文 + issue + traceback + "是不是修复?"
  real: 同上 + 该行(及附近执行行)的【真实运行时值快照】(value_cache, sys.settrace抓的) + 值流回溯框架.
仅在【该行有抓到运行时值】的行上做 real vs ctrl 配对 (否则 real=ctrl 无意义).
对照 E1(免费异常值, valprobe_cache): real >> free >> ctrl = 付费值维度有效.
  MODEL=... SWEBENCH_DATASET=lite python agentless/value_probe2.py --tag <tag> --workers 1
"""
import argparse, json, re, threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import comb
from pathlib import Path
import p0_line_recall as p0
import region_loc as R
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

PROMPT_CTRL = """A failing test crashes with the traceback below. I am pointing you at ONE specific source line (marked ▶). Decide whether THAT line is part of the code that must be edited to fix the described issue.

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

### Source (▶ marks the line in question) — file: {file} ###
{context}

Question: Is the ▶-marked line (line {lineno} in {file}) part of the fix for this issue (it must be edited, or is immediately adjacent to lines that must be edited)?
Answer with exactly one word on the first line: YES or NO. Then one sentence of justification.
"""
PROMPT_REAL = """A failing test crashes with the traceback below. I captured the ACTUAL RUNTIME VALUES of local variables as the failing test executed (via a line tracer). Use these concrete values to reason about where the bad value/state originates or must be guarded.

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

### RUNTIME VALUES captured on the executed path (file:line -> locals at that moment) ###
{values}

### Source (▶ marks the line in question) — file: {file} ###
{context}

Question: Given the concrete runtime values above, is the ▶-marked line (line {lineno} in {file}) where the bad value/state is produced, passed through, or where it must be guarded — i.e. part of the fix?
Answer with exactly one word on the first line: YES or NO. Then one sentence of justification.
"""

def ctx_lines(src, ln, w=15):
    lines=src.splitlines(); out=[]
    for i in range(max(1,ln-w), min(len(lines),ln+w)+1):
        out.append(f"{'▶' if i==ln else ' '} {i}: {lines[i-1]}")
    return "\n".join(out)

def cat_of(f, ln, ff, ex):
    if f not in ff: return "D_outfile"
    if ln in ex: return "C_infile_exec"
    if any((ln+d) in ex for d in (-2,-1,1,2)): return "infile_adj2"
    return "infile_far"

def val_block(vcache_i, f, ln, span=8, maxlines=14):
    """该行及附近(±span)执行行的真实值快照, 作数据流上下文."""
    fv=vcache_i.get(f, {})
    picks=[]
    for d in range(-span, span+1):
        key=str(ln+d)
        if key in fv:
            snap=fv[key]
            s=", ".join(f"{k}={v}" for k,v in list(snap.items())[:8])
            picks.append((ln+d, f"{f}:{ln+d} -> {s}"))
    picks.sort()
    if not picks: return None
    return "\n".join(p[1] for p in picks[:maxlines])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True)
    ap.add_argument("--workers",type=int,default=1); ap.add_argument("--sample",type=int,default=0)
    ap.add_argument("--ctrl",type=int,default=3); ap.add_argument("--valcache",default="value_cache.json")
    a=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    cachef=f"agentless/valprobe2_cache_{a.tag}.json"
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    vcache=json.load(open(a.valcache))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if a.sample: sub=sub[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    cache=json.loads(Path(cachef).read_text()) if Path(cachef).exists() else {}
    lock=threading.Lock()
    tasks=[]  # (iid,f,ln,cat,role,arm,hasval)
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su); missed=set(gold)-set(base)
        if not missed: continue
        vci=vcache.get(iid) or {}
        ff=set(E.LOC[iid]["found_files"][:NB.TOP_N]); ec={}
        def add(f,ln,role):
            hv=bool(val_block(vci,f,int(ln)))
            for arm in ("ctrl","real"): tasks.append((iid,f,int(ln),cat_of(f,int(ln),ff,ec.get(f,set())),role,arm,hv))
        for (f,ln) in sorted(missed):
            if f not in ec: ec[f]=E.cov_for(f,cm) if f in ff else set()
            if cat_of(f,ln,ff,ec[f]) in ("C_infile_exec","infile_adj2"): add(f,ln,"missed")
        for (f,ln) in sorted(set(gold)&set(base))[:a.ctrl]:
            if f not in ec: ec[f]=E.cov_for(f,cm) if f in ff else set()
            add(f,ln,"covered")
    def work(t):
        iid,f,ln,cat,role,arm,hv=t; key=f"{iid}|{f}|{ln}|{role}|{arm}"
        if key in cache: return None
        r=rows[iid]
        try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
        except Exception:
            with lock: cache[key]={"cat":cat,"role":role,"arm":arm,"ans":None,"hv":hv}; return key
        issue=(r.get("problem_statement") or "")[:4000]; cctx=E._crash_ctx(r) or "(none)"
        vb=val_block(vcache.get(iid) or {}, f, ln)
        if arm=="real" and vb:
            msg=PROMPT_REAL.format(problem_statement=issue,traceback=cctx,values=vb,file=f,context=ctx_lines(src,ln),lineno=ln)
        else:
            msg=PROMPT_CTRL.format(problem_statement=issue,traceback=cctx,file=f,context=ctx_lines(src,ln),lineno=ln)
        try: o=R._llm_t(model,msg,temperature=0.0,timeout=120)
        except Exception: o=""
        m=re.search(r"\b(YES|NO)\b",(o or "").upper())
        with lock: cache[key]={"cat":cat,"role":role,"arm":arm,"ans":(m.group(1) if m else None),"hv":hv}; Path(cachef).write_text(json.dumps(cache))
        return key
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,t) for t in tasks]
        done=0
        for fut in as_completed(futs):
            if fut.result(): done+=1
            print(f"[{done}/{len(tasks)}] valprobe2 cached={len(cache)}",file=_sys.stderr); _sys.stderr.flush()
    # 汇总 + 配对 (只在 hv=有真实值 的行)
    byline=defaultdict(dict)
    for k,v in cache.items():
        iid,f,ln,role,arm=k.split("|"); byline[(iid,f,ln,role)][arm]=(v["ans"],v.get("hv",False),v["cat"])
    def rate(role,arm,needhv):
        y=n=0
        for (iid,f,ln,r2),d in byline.items():
            if r2!=role or arm not in d: continue
            ans,hv,cat=d[arm]
            if needhv and not hv: continue
            n+=1; y+=(ans=="YES")
        return y,n
    print(f"\n===== {model} 付费值探针 E2 ({a.tag}) =====")
    for role in ["missed","covered"]:
        yc,nc=rate(role,"ctrl",True); yr,nr=rate(role,"real",True)
        print(f"  [{role}] (有真实值的行) 对照臂 YES={yc}/{nc}={100*yc/max(nc,1):.0f}%   真值臂 YES={yr}/{nr}={100*yr/max(nr,1):.0f}%")
    b01=b10=nn=0
    for (iid,f,ln,role),d in byline.items():
        if role!="missed" or "ctrl" not in d or "real" not in d: continue
        (ca,hv,_),(ra,_,_)=d["ctrl"],d["real"]
        if not hv: continue
        nn+=1
        if ca=="NO" and ra=="YES": b01+=1
        if ca=="YES" and ra=="NO": b10+=1
    dn=b01+b10; kk=min(b01,b10); p=min(1.0,sum(comb(dn,i) for i in range(0,kk+1))*2/(2**dn)) if dn else 1.0
    print(f"  判别墙配对(有真实值, n={nn}): 真值臂NO→YES b01={b01}, 反向b10={b10}, exact p={p:.3f}")

if __name__=="__main__": main()
