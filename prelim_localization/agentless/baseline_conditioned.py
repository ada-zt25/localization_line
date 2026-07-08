#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""动态测试: Agentless 基线生成 + 【执行条件化】(标注执行行→ + traceback + 沿执行路径推理).
同为 Agentless 生成框架(4采样并集, 相同解析/并集/打分), 唯一变量 = prompt 里的执行 context.
=> 干净回答: 把执行信息作为 LLM 的语义 context, 能否让(弱)模型定位更准? (静态实验测不到)
对照: al_baseline_<tag>.json (无条件化基线).

  MODEL=... OPENAI_BASE_URL=... OPENAI_API_KEY=... SWEBENCH_DATASET=lite \
    python agentless/baseline_conditioned.py --workers 1 --tag <tag>
"""
import argparse, json, statistics as st, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import region_loc as R
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB
from agentless.util.postprocess_data import extract_code_blocks, extract_locs_for_files

# Agentless edit-loc prompt + 执行条件化 (标注→ / traceback / 沿执行路径推理). 其余与原生 prompt 同构.
PROMPT_COND = """
Please review the following GitHub problem description, the failing test traceback, and the relevant files, and provide a set of locations that need to be edited to fix the issue.
Lines executed by the failing test are marked with "→". The bug lies ON or NEAR the execution path leading to the failure: prioritize executed ("→") lines and their immediate neighbors.
The locations can be specified as class names, function or method names, or exact line numbers that require modification.

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

###
{file_contents}

###

Please provide the class name, function or method name, or the exact line numbers that need to be edited.
The possible location outputs should be either "class", "function" or "line".

### Examples:
```
full_path1/file1.py
line: 10
class: MyClass1
line: 51

full_path2/file2.py
function: my_function
line: 24
```

Return just the location(s) wrapped with ```.
"""

def numbered_lines(src, lineset, ex):
    lines=src.splitlines(); out=[]
    for ln in sorted(lineset):
        if 1<=ln<=len(lines):
            mark="→" if ln in ex else " "
            out.append(f"{mark} {ln}: {lines[ln-1]}")
    return "\n".join(out)

def build_cond(iid, r, cm, expand=True):
    L=E.LOC[iid]; ff=L["found_files"][:NB.TOP_N]; rel=L["found_related_locs"][:NB.TOP_N]
    issue=(r.get("problem_statement") or "")[:5000]; cctx=E._crash_ctx(r)
    parts=[]
    for i,rlocs in enumerate(rel):
        if i>=len(ff) or not rlocs or all(not x.strip() for x in rlocs): continue
        f=ff[i]
        try:
            src=p0.fetch_file(r["repo"],r["base_commit"],f)
            _,iv=E.transfer_arb_locs_to_locs(rlocs,None,f,NB.CTX,True,False,file_content=src)
        except Exception: continue
        ex=E.cov_for(f,cm)
        region=set(E.intervals_to_lines(iv))                  # Agentless 相关区域
        if expand:                                            # 上游: 执行行扩池, 抬 LLM 可选的候选天花板
            mode=_os.environ.get("EGL_EXPAND_MODE","scored30")
            try:
                if mode=="crashframe":  region|=set(E.crash_frame_exec_lines(src, f, issue, ex))  # 崩溃帧函数的全部执行行
                elif mode=="allexec":   region|=set(ex)                                            # 全部执行行
                else:                   region|=set(E.scored_exec_topk(src, f, issue, cctx, ex, 30))  # 打分top30(默认)
            except Exception: pass
        ctx=numbered_lines(src, region, ex)
        if ctx.strip(): parts.append(f"### File: {f} ###\n{ctx}")
    if not parts: return None, ff
    return PROMPT_COND.format(problem_statement=issue, traceback=(cctx or "(not available)"),
                              file_contents="\n".join(parts)), ff

def cond_edit_locs(model, iid, r, cm, cache, lock, expand=True):
    if iid in cache: return cache[iid]
    msg, ff = build_cond(iid, r, cm, expand)
    samples=[]
    if msg is not None:
        for s in range(NB.NUM_SAMPLES):
            try: out=R._llm_t(model, msg, temperature=NB.TEMP)
            except Exception: out=""
            res=extract_locs_for_files(extract_code_blocks(out or ""), ff)
            samples.append([res.get(ff[i], [""]) for i in range(len(ff))])
    with lock: cache[iid]=samples
    return samples

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tag",required=True); ap.add_argument("--workers",type=int,default=1)
    ap.add_argument("--sample",type=int,default=0); ap.add_argument("--expand",type=int,default=1)
    a=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    mode="upmid" if a.expand else "mid"   # upmid=上游扩池+中游条件化; mid=仅中游(基线区域)
    out=f"agentless/cov_{mode}_{a.tag}.json"; cachef=f"agentless/cov_{mode}_cache_{a.tag}.json"
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if a.sample: sub=sub[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    cache=json.loads(Path(cachef).read_text()) if Path(cachef).exists() else {}
    lock=threading.Lock()
    inst=[]
    def work(iid):
        r=rows.get(iid); cm=cov.get(iid)
        if not r or not cm or iid not in E.LOC: return None
        gold=E.gold_pairs(r)
        if not gold: return None
        samples=cond_edit_locs(model, iid, r, cm, cache, lock, bool(a.expand))
        with lock: Path(cachef).write_text(json.dumps(cache))
        pairs=NB.native_pairs(iid, r, samples)
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]
        try: flen={f:len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()) for f in {p[0] for p in pairs}|set(ff)}
        except Exception: flen={}
        return {"iid":iid,"gold":list(map(list,gold)),"pairs":list(map(list,pairs)),"flen":flen}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,iid) for iid in sub]
        for n,fut in enumerate(as_completed(futs),1):
            x=fut.result()
            if x: inst.append(x)
            print(f"[{n}/{len(sub)}] cond={len(inst)}", file=_sys.stderr); _sys.stderr.flush()
    A=[];AN=[];L=[]
    for x in inst:
        g=set(map(tuple,x["gold"])); S=set(map(tuple,x["pairs"]))  # framing-A: native_pairs 已±10, 不再 expand10 (修 ±20 双扩张)
        A.append(1 if g<=S else 0); AN.append(1 if g&S else 0); L.append(len(S))
    N=len(inst); s=100*st.mean(A) if N else 0; an=100*st.mean(AN) if N else 0; l=st.mean(L) if N else 0
    print(f"\n==== {model} 执行条件化基线生成 (crash·on-path, n={N}) ====")
    print(f"  条件化: superset={s:.1f}  any={an:.1f}  LoC={l:.0f}")
    base=f"agentless/al_baseline_{a.tag}.json"
    if Path(base).exists():
        b=json.load(open(base))["native_baseline"]
        print(f"  无条件化基线(对照): superset={b['superset']}  LoC={b['LoC']}   => Δsuperset={s-b['superset']:+.1f}, ΔLoC={l-b['LoC']:+.0f}")
    json.dump({"tag":a.tag,"model":model,"n":N,"conditioned":{"superset":round(s,1),"any":round(an,1),"LoC":round(l,1)},
               "per_instance_superset":A,"ids":[x["iid"] for x in inst]}, open(out,"w"))
    print("written:", out)

if __name__=="__main__": main()
