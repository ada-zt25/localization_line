#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""中游: 聚焦重判别 pass (LLM 二次判别, 脱离覆盖率评分).
上游: region = Agentless相关 ∪ 全部执行行 (端上漏掉的执行金标 C). 中游: 给模型【它自己的基线预测】+【执行代码(→标注)】,
问"哪些 OTHER 执行行也是故障?" -> 救回 A(看见没选)+C(新端上来的). 输出=额外定位, 与基线并入, 下游软过滤缩LoC.

  MODEL=... OPENAI_BASE_URL=... OPENAI_API_KEY=... SWEBENCH_DATASET=lite \
    python agentless/rediscriminate.py --tag <tag> --base-cache agentless/al_baseline_cache_<tag>.json
"""
import argparse, json, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import region_loc as R
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB
from agentless.util.postprocess_data import extract_code_blocks, extract_locs_for_files

PROMPT = """
Lines executed by the FAILING test are marked "→". A fix's edit locations lie ON or NEAR this executed path.

### GitHub Problem Description ###
{problem_statement}

### Failing Test Traceback ###
{traceback}

### Executed code (→ = executed by the failing test) ###
{file_contents}

### Locations a first pass already identified ###
{baseline_locs}

The first pass likely MISSED some executed (→) lines that are also part of the fix. Carefully reason from the failure along the executed path, and list ADDITIONAL locations (class / function / line) that are also part of the fix — do NOT repeat the already-identified ones.

You MUST prefix every location group with its full file path on its own line (exactly as shown in the code headers above), otherwise the location is unusable. Format:

### Examples:
```
full_path1/file1.py
line: 10
class: MyClass1

full_path2/file2.py
function: my_function
line: 24
```

Return just the additional location(s) wrapped with ```.
"""
CAP=450   # 渲染执行区域的行数上限 (防超长 prompt)

def numbered(src, lineset, ex):
    lines=src.splitlines(); out=[]
    for ln in sorted(lineset):
        if 1<=ln<=len(lines):
            out.append(f"{'→' if ln in ex else ' '} {ln}: {lines[ln-1]}")
    return "\n".join(out)

def build(iid, r, cm):
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
        region=set(E.intervals_to_lines(iv))                 # Agentless 相关
        for ln in ex:                                        # 上游: 全部执行行 ± 2 context
            for d in range(-2,3): region.add(ln+d)
        region={ln for ln in region if ln in ex or ln in region}
        if len(region)>CAP:                                  # 超长: 只留执行行±1
            region={ln for ln in ex}
            reg2=set()
            for ln in ex:
                for d in range(-1,2): reg2.add(ln+d)
            region=reg2
        ctx=numbered(src, region, ex)
        if ctx.strip(): parts.append(f"### File: {f} ###\n{ctx}")
    if not parts: return None, ff
    return issue, cctx, "\n".join(parts), ff

def base_locstr(iid):
    """基线预测的 loc 串 (给模型看它已选了什么)."""
    samples=json.load(open(_os.environ["EGL_BASE_CACHE"]))[iid] if _os.environ.get("EGL_BASE_CACHE") else None
    return samples

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tag",required=True); ap.add_argument("--base-cache",required=True)
    ap.add_argument("--workers",type=int,default=1); ap.add_argument("--sample",type=int,default=0)
    a=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    out=f"agentless/rediscr_{a.tag}.json"; cachef=f"agentless/rediscr_cache_{a.tag}.json"
    basec=json.load(open(a.base_cache))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if a.sample: sub=sub[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    cache=json.loads(Path(cachef).read_text()) if Path(cachef).exists() else {}
    lock=threading.Lock()
    def work(iid):
        if iid in cache: return None
        r=rows.get(iid); cm=cov.get(iid); su=basec.get(iid)
        if not r or not cm or iid not in E.LOC or not su: return None
        b=build(iid, r, cm)
        if b[0] is None:
            with lock: cache[iid]=[]; Path(cachef).write_text(json.dumps(cache)); return iid
        issue,cctx,fc,ff=b
        # 基线已选的 loc 串 (su=采样列表; 跨采样按文件聚合)
        perfile={}
        for s in su:
            for i in range(min(len(s),len(ff))):
                for x in (s[i] or []):
                    for ln in str(x).split("\n"):
                        if ln.strip(): perfile.setdefault(ff[i],set()).add(ln.strip())
        blocs="\n".join(f"{f}\n"+"\n".join(sorted(v)) for f,v in perfile.items() if v)  # 纯路径(无###), 让模型照抄成可解析格式
        msg=PROMPT.format(problem_statement=issue, traceback=(cctx or "(none)"), file_contents=fc, baseline_locs=blocs or "(none)")
        try: o=R._llm_t(model, msg, temperature=0.0, timeout=180)
        except Exception: o=""
        res=extract_locs_for_files(extract_code_blocks(o or ""), ff)
        add=[res.get(ff[i],[""]) for i in range(len(ff))]
        with lock: cache[iid]=add; Path(cachef).write_text(json.dumps(cache))
        return iid
    n=0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,iid) for iid in sub]
        for f in as_completed(futs):
            if f.result(): n+=1
            print(f"[{n+len(cache)-n}/{len(sub)}] rediscr done={sum(1 for v in cache.values())}",file=_sys.stderr); _sys.stderr.flush()
    json.dump({"tag":a.tag,"n":len(cache)}, open(out,"w"))
    print("written cache:",cachef)

if __name__=="__main__": main()
