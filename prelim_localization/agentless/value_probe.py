#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""E1: 值注解识别探针 (诊断, 非方法). 配对测【值维度】能否撬开判别墙.
同一批【执行漏金标行】(模型看得到但没选=判别墙: C_infile_exec + infile_adj2), 两臂配对:
  arm0 (对照): 行上下文 + issue + 原始 traceback + "这行是不是修复?"  (= pointed_recognition)
  armV (值臂): 同上 + 从异常免费抽的【值/类型事实】前置 + 值流回溯框架.
差异 = 值事实抽取+前置+回溯框架. armV>>arm0 => 值维度能动判别(→ 值得造运行时取值 RQ4); armV≈arm0 => 免费值不够.
阳性对照: 同实例 base命中的金标(covered). 每(行,臂)一次 yes/no.
  MODEL=... OPENAI_BASE_URL/KEY=... SWEBENCH_DATASET=lite python agentless/value_probe.py --tag <tag> --workers 1
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

EXC=re.compile(r'^([A-Za-z_][\w.]*(?:Error|Exception|Warning|Exit)):?\s*(.*)$', re.M)
def value_facts(cctx):
    ms=EXC.findall(cctx or "")
    if not ms: return None
    t,m=ms[-1]
    return f"{t}: {m.strip()[:200]}"

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
PROMPT_VAL = """A failing test crashes. RUNTIME EVIDENCE captured from the actual failing execution:
    >>> {vfacts}
This is the concrete bad value / type / state that reached the crash. Trace that offending value/state BACKWARD along the data it flows from: where is it produced, passed through, or where should it be guarded?

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

### Source (▶ marks the line in question) — file: {file} ###
{context}

Question: Given the runtime evidence above, is the ▶-marked line (line {lineno} in {file}) where that bad value/state is produced, passed through, or where it must be guarded — i.e. part of the fix?
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

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True)
    ap.add_argument("--workers",type=int,default=1); ap.add_argument("--sample",type=int,default=0)
    ap.add_argument("--ctrl",type=int,default=3)
    a=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    cachef=f"agentless/valprobe_cache_{a.tag}.json"
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if a.sample: sub=sub[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    cache=json.loads(Path(cachef).read_text()) if Path(cachef).exists() else {}
    lock=threading.Lock()
    tasks=[]  # (iid,f,ln,cat,role,arm)
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su); missed=set(gold)-set(base)
        if not missed: continue
        ff=set(E.LOC[iid]["found_files"][:NB.TOP_N]); ec={}
        for (f,ln) in sorted(missed):
            if f not in ec: ec[f]=E.cov_for(f,cm) if f in ff else set()
            cat=cat_of(f,ln,ff,ec[f])
            if cat in ("C_infile_exec","infile_adj2"):        # 判别墙: 执行 & 在found_files
                for arm in ("ctrl","val"): tasks.append((iid,f,int(ln),cat,"missed",arm))
        covered=sorted(set(gold)&set(base))[:a.ctrl]
        for (f,ln) in covered:
            if f not in ec: ec[f]=E.cov_for(f,cm) if f in ff else set()
            cat=cat_of(f,ln,ff,ec[f])
            for arm in ("ctrl","val"): tasks.append((iid,f,int(ln),cat,"covered",arm))
    def work(t):
        iid,f,ln,cat,role,arm=t; key=f"{iid}|{f}|{ln}|{role}|{arm}"
        if key in cache: return None
        r=rows[iid]
        try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
        except Exception:
            with lock: cache[key]={"cat":cat,"role":role,"arm":arm,"ans":None,"vf":False}; return key
        issue=(r.get("problem_statement") or "")[:4000]; cctx=E._crash_ctx(r) or "(none)"
        vf=value_facts(cctx)
        if arm=="val" and vf:
            msg=PROMPT_VAL.format(vfacts=vf,problem_statement=issue,traceback=cctx,file=f,context=ctx_lines(src,ln),lineno=ln)
        else:
            msg=PROMPT_CTRL.format(problem_statement=issue,traceback=cctx,file=f,context=ctx_lines(src,ln),lineno=ln)
        try: o=R._llm_t(model,msg,temperature=0.0,timeout=120)
        except Exception: o=""
        m=re.search(r"\b(YES|NO)\b",(o or "").upper())
        with lock: cache[key]={"cat":cat,"role":role,"arm":arm,"ans":(m.group(1) if m else None),"vf":bool(vf)}; Path(cachef).write_text(json.dumps(cache))
        return key
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,t) for t in tasks]
        done=0
        for fut in as_completed(futs):
            if fut.result(): done+=1
            print(f"[{done}/{len(tasks)}] valprobe cached={len(cache)}",file=_sys.stderr); _sys.stderr.flush()
    # 汇总: 按 role×arm 识别率; 配对 (同一行 ctrl vs val)
    def yesrate(role,arm,cats=None):
        y=n=0
        for k,v in cache.items():
            if v["role"]!=role or v["arm"]!=arm: continue
            if cats and v["cat"] not in cats: continue
            n+=1; y+= (v["ans"]=="YES")
        return y,n
    # 配对: 收集每行 (ctrl_ans, val_ans, has_vf)
    byline=defaultdict(dict)
    for k,v in cache.items():
        iid,f,ln,role,arm=k.split("|")
        byline[(iid,f,ln,role)][arm]=(v["ans"],v["vf"],v["cat"])
    print(f"\n===== {model} 值注解探针 ({a.tag}) =====")
    for role in ["missed","covered"]:
        yc,nc=yesrate(role,"ctrl"); yv,nv=yesrate(role,"val")
        print(f"  [{role}] 对照臂 YES={yc}/{nc}={100*yc/max(nc,1):.0f}%   值臂 YES={yv}/{nv}={100*yv/max(nv,1):.0f}%")
    # 判别墙(missed)的配对 McNemar: 有值事实的行, val把NO翻成YES vs 反向
    b01=b10=0; both=0
    for (iid,f,ln,role),d in byline.items():
        if role!="missed" or "ctrl" not in d or "val" not in d: continue
        (ca,_,_),(va,vf,_)=d["ctrl"],d["val"]
        if not vf: continue                    # 只在真有值事实的行上比
        both+=1
        if ca=="NO" and va=="YES": b01+=1
        if ca=="YES" and va=="NO": b10+=1
    dn=b01+b10; kk=min(b01,b10)
    p=min(1.0, sum(comb(dn,i) for i in range(0,kk+1))*2/(2**dn)) if dn else 1.0
    print(f"  判别墙配对(有值事实的执行漏金标, n={both}): 值臂NO→YES翻转 b01={b01}, 反向 b10={b10}, exact p={p:.3f}")
    print(f"  => b01>>b10 且 p<0.05 = 值维度撬开判别墙; 否则免费traceback值不足(→运行时取值 或 backbone封顶)")

if __name__=="__main__": main()
