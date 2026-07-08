#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""诊断探针 (非方法!): 把金标行直接指给模型看, 问"这行是不是修复的一部分?".
剥离 判别(discrimination) vs 生成/排序(generation).  两个对照维度:
  (1) 阳性对照: 同时问 base命中的金标(covered) 与 base漏掉的金标(missed).
       - covered YES高 & missed YES低 => 探针有判别力, 负结果(漏金标救不回)为真.
       - covered 也低 => 问法太保守, 结果无效.
  (2) 粒度对照: --gran line|func.  func = "包含该行的函数是否属于修复?" 排除'多行修复中单行含糊'的伪负.
按类别分层. 用金标做输入 => 诊断非定位器. 每(行,粒度)一次 yes/no.
  MODEL=... OPENAI_BASE_URL/KEY=... SWEBENCH_DATASET=lite python agentless/pointed_recognition.py --tag <tag> --gran line --workers 1
"""
import argparse, json, re, threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import region_loc as R
import code_graph as cg
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

PROMPT_LINE = """A failing test crashes with the traceback below. I am pointing you at ONE specific source line (marked ▶). Decide whether THAT line is part of the code that must be edited to fix the described issue.

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

### Source (▶ marks the line in question) — file: {file} ###
{context}

Question: Is the ▶-marked line (line {lineno} in {file}) part of the fix for this issue (i.e. it must be edited, or it is immediately adjacent to lines that must be edited)?
Answer with exactly one word on the first line: YES or NO. Then one sentence of justification.
"""
PROMPT_FUNC = """A failing test crashes with the traceback below. I am pointing you at ONE function/region (its body shown, the anchor line marked ▶). Decide whether code inside THIS function must be edited to fix the described issue.

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

### Source region — file: {file} ###
{context}

Question: Must some line inside the shown function/region (around line {lineno} in {file}) be edited to fix this issue?
Answer with exactly one word on the first line: YES or NO. Then one sentence of justification.
"""

def ctx_lines(src, ln, w=15):
    lines=src.splitlines(); out=[]
    for i in range(max(1,ln-w), min(len(lines),ln+w)+1):
        out.append(f"{'▶' if i==ln else ' '} {i}: {lines[i-1]}")
    return "\n".join(out)

def ctx_func(src, ln):
    """区域框架: 锚点行 ±25 窗口 (func 措辞由 PROMPT_FUNC 承担)."""
    return ctx_lines(src, ln, 25)

def cat_of(f, ln, ff, ex):
    if f not in ff: return "D_outfile"
    if ln in ex: return "C_infile_exec"
    if any((ln+d) in ex for d in (-2,-1,1,2)): return "infile_adj2"
    return "infile_far"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True)
    ap.add_argument("--gran",choices=["line","func"],default="line")
    ap.add_argument("--workers",type=int,default=1); ap.add_argument("--sample",type=int,default=0)
    ap.add_argument("--ctrl",type=int,default=3,help="每实例阳性对照(covered金标)上限")
    a=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    PROMPT=PROMPT_LINE if a.gran=="line" else PROMPT_FUNC
    cachef=f"agentless/recog_cache_{a.tag}_{a.gran}.json"
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if a.sample: sub=sub[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    cache=json.loads(Path(cachef).read_text()) if Path(cachef).exists() else {}
    lock=threading.Lock()
    tasks=[]  # (iid,f,ln,cat,role)  role: missed / covered
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
            tasks.append((iid,f,int(ln),cat_of(f,ln,ff,ec[f]),"missed"))
        covered=sorted(set(gold)&set(base))[:a.ctrl]   # 阳性对照: 同实例 base命中的金标
        for (f,ln) in covered:
            if f not in ec: ec[f]=E.cov_for(f,cm) if f in ff else set()
            tasks.append((iid,f,int(ln),cat_of(f,ln,ff,ec[f]),"covered"))
    def work(t):
        iid,f,ln,cat,role=t; key=f"{iid}|{f}|{ln}|{role}"
        if key in cache: return None
        r=rows[iid]
        try: src=p0.fetch_file(r["repo"],r["base_commit"],f)
        except Exception:
            with lock: cache[key]={"cat":cat,"role":role,"ans":None}; return key
        issue=(r.get("problem_statement") or "")[:4000]; cctx=E._crash_ctx(r) or "(none)"
        context=ctx_lines(src,ln) if a.gran=="line" else ctx_func(src,ln)
        msg=PROMPT.format(problem_statement=issue,traceback=cctx,file=f,context=context,lineno=ln)
        try: o=R._llm_t(model,msg,temperature=0.0,timeout=120)
        except Exception: o=""
        m=re.search(r"\b(YES|NO)\b",(o or "").upper())
        with lock: cache[key]={"cat":cat,"role":role,"ans":(m.group(1) if m else None)}; Path(cachef).write_text(json.dumps(cache))
        return key
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,t) for t in tasks]
        done=0
        for fut in as_completed(futs):
            if fut.result(): done+=1
            print(f"[{done}/{len(tasks)}] recog({a.gran}) cached={len(cache)}",file=_sys.stderr); _sys.stderr.flush()
    yes=defaultdict(int); tot=defaultdict(int)   # key=(role,cat)
    for k,v in cache.items():
        rk=(v["role"],v["cat"]); tot[rk]+=1
        if v["ans"]=="YES": yes[rk]+=1
    print(f"\n===== {model} 指向式识别 gran={a.gran} ({a.tag}) =====")
    for role in ["missed","covered"]:
        ry=sum(yes[(role,c)] for c in ["C_infile_exec","infile_adj2","infile_far","D_outfile"])
        rn=sum(tot[(role,c)] for c in ["C_infile_exec","infile_adj2","infile_far","D_outfile"])
        print(f"  [{role}] 合计 YES={ry}/{rn} = {100*ry/max(rn,1):.0f}%")
        for c in ["C_infile_exec","infile_adj2","infile_far","D_outfile"]:
            if tot[(role,c)]: print(f"      {c:>16}: {yes[(role,c)]:>3}/{tot[(role,c)]:<3} = {100*yes[(role,c)]/tot[(role,c)]:.0f}%")

if __name__=="__main__": main()
