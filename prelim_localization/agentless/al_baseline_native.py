#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""模型自身的 Agentless 原生 edit-location 基线（crash·on-path），用于 WITHIN-MODEL 对比。

严格保真 & 零泄漏:
  - prompt        = Agentless 原生 obtain_relevant_code_combine_top_n_prompt (逐字复制自 vendor FL.py)
  - 输出解析      = Agentless 自己的 extract_code_blocks + extract_locs_for_files (直接 import vendor)
  - loc->行解析   = transfer_arb_locs_to_locs (Agentless 自己的函数, 和 GPT-4o AL 用的同一个)
  - 上游         = GPT-4o 的 found_files+found_related_locs (三臂共享, 仅隔离 edit-loc 阶段)
  - 采样         = top_n=3 文件, num_samples=4, temperature=0.8, 带行号 (= Agentless-lite / GPT-4o artifact 口径)
  - 打分         = 并集 4 采样 -> ±10 (expand10) -> superset/LoC, 和 al_native_pairs 对 GPT-4o 逐字一致
  - 不掺入: 覆盖率 / 扩区 / crash-context / k=10 投票 / 金标. 也不 sandbag (用它自己的解析器).

  SWEBENCH_DATASET=lite OPENAI_BASE_URL=... OPENAI_API_KEY=... MODEL=... \
    python agentless/al_baseline_native.py --workers 1 \
      --out agentless/al_baseline_<tag>.json --cache agentless/al_baseline_cache_<tag>.json
"""
import argparse, json, statistics as st, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import region_loc as R
import agentless.al_vote_eval as E                     # LOC, expand10, gold_pairs, intervals_to_lines, transfer_arb_locs_to_locs
from agentless.util.postprocess_data import extract_code_blocks, extract_locs_for_files

TOP_N=3; NUM_SAMPLES=4; TEMP=0.8; CTX=10               # Agentless-lite edit-loc 口径

# --- Agentless 原生 edit-location prompt (逐字复制自 agentless_vendor/repo/agentless/fl/FL.py:88) ---
PROMPT = """
Please review the following GitHub problem description and relevant files, and provide a set of locations that need to be edited to fix the issue.
The locations can be specified as class names, function or method names, or exact line numbers that require modification.

### GitHub Problem Description ###
{problem_statement}

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
function: MyClass2.my_method
line: 12

full_path3/file3.py
function: my_function
line: 24
line: 156
```

Return just the location(s) wrapped with ```.
"""

def numbered_context(src, iv):
    """把 related-locs 解析出的行区间渲染成带行号的窄化上下文 (no_line_number=False, no sticky/add_space)."""
    lines=src.splitlines(); out=[]; seen=set()
    for a,b in iv:
        for ln in range(a, b+1):
            if 1<=ln<=len(lines) and ln not in seen:
                seen.add(ln); out.append(f"{ln}: {lines[ln-1]}")
    return "\n".join(out)

def build_message(iid, r):
    """构造 Agentless edit-loc 单条 (多文件合并) 提示: GPT-4o 的 found_files[:3]+related_locs, 各文件窄化带行号."""
    L=E.LOC[iid]; ff=L["found_files"][:TOP_N]; rel=L["found_related_locs"][:TOP_N]
    issue=(r.get("problem_statement") or "")[:5000]
    parts=[]
    for i,rlocs in enumerate(rel):
        if i>=len(ff) or not rlocs or all(not x.strip() for x in rlocs): continue
        f=ff[i]
        try:
            src=p0.fetch_file(r["repo"],r["base_commit"],f)
            _,iv=E.transfer_arb_locs_to_locs(rlocs,None,f,CTX,True,False,file_content=src)
        except Exception: continue
        ctx=numbered_context(src, iv)
        if ctx.strip(): parts.append(f"### File: {f} ###\n{ctx}")
    if not parts: return None, ff
    return PROMPT.format(problem_statement=issue, file_contents="\n".join(parts)), ff

def native_edit_locs(model, iid, r, cache, lock):
    """返回 found_edit_locs 格式: [样本][文件序号]->loc串列表 (与 GPT-4o artifact 完全同构)."""
    if iid in cache: return cache[iid]
    msg, ff = build_message(iid, r)
    samples=[]
    if msg is not None:
        for s in range(NUM_SAMPLES):
            try: out=R._llm_t(model, msg, temperature=TEMP)
            except Exception: out=""
            res=extract_locs_for_files(extract_code_blocks(out or ""), ff)   # {fn:[joined]}
            samples.append([res.get(ff[i], [""]) for i in range(len(ff))])   # 对齐 found_files 顺序
    with lock: cache[iid]=samples
    return samples

def native_pairs(iid, r, samples):
    """并集 4 采样 -> {(file,line)}, 逐字镜像 al_vote_eval.al_native_pairs 对 GPT-4o 的处理."""
    L=E.LOC[iid]; ff=L["found_files"][:TOP_N]; merged=set()
    for s in samples:
        for i,locs in enumerate(s):
            if i>=len(ff) or not locs or all(not x.strip() for x in locs): continue
            f=ff[i]
            try:
                src=p0.fetch_file(r["repo"],r["base_commit"],f)
                _,iv=E.transfer_arb_locs_to_locs(locs,None,f,CTX,True,False,file_content=src)
            except Exception: continue
            for ln in E.intervals_to_lines(iv): merged.add((f,int(ln)))
    return merged

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workers",type=int,default=1)
    ap.add_argument("--sample",type=int,default=0)
    ap.add_argument("--out",default=_os.path.join(_HERE,"al_baseline_native.json"))
    ap.add_argument("--cache",default=_os.path.join(_HERE,"al_baseline_cache.json"))
    ap.add_argument("--vote-result",default="",help="对应模型的 al_vote_*_v2.json, 用于 within-model 对比打印")
    args=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if args.sample: sub=sub[:args.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cache=json.loads(Path(args.cache).read_text()) if Path(args.cache).exists() else {}
    lock=threading.Lock()

    inst=[]
    def work(iid):
        r=rows.get(iid)
        if not r or iid not in E.LOC: return None
        gold=E.gold_pairs(r)
        if not gold: return None
        samples=native_edit_locs(model, iid, r, cache, lock)
        with lock: Path(args.cache).write_text(json.dumps(cache))
        base=native_pairs(iid, r, samples)
        ff=E.LOC[iid]["found_files"][:TOP_N]
        try: flen={f:len(p0.fetch_file(r["repo"],r["base_commit"],f).splitlines()) for f in {p[0] for p in base}|set(ff)}
        except Exception: flen={}
        return {"iid":iid,"gold":list(map(list,gold)),"base":list(map(list,base)),"flen":flen}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs=[ex.submit(work,iid) for iid in sub]
        for n,fut in enumerate(as_completed(futs),1):
            x=fut.result()
            if x: inst.append(x)
            print(f"[{n}/{len(sub)}] base={len(inst)}",file=_sys.stderr); _sys.stderr.flush()

    # 打分: superset(gold⊆展开集) / any / 平均LoC — 和 al_vote_eval.score 逐字一致 (expand10 ±10)
    allc=[]; anyc=[]; loc=[]
    for x in inst:
        gold=set(map(tuple,x["gold"])); flen={f:l for f,l in x["flen"].items()}
        S=E.expand10(set(map(tuple,x["base"])), flen)
        allc.append(1 if gold<=S else 0); anyc.append(1 if gold&S else 0); loc.append(len(S))
    N=len(inst)
    a,an,l=(100*st.mean(allc),100*st.mean(anyc),st.mean(loc)) if N else (0,0,0)
    print(f"\n==== {model}  原生 Agentless edit-loc 基线 (crash·on-path, n={N}, top_n={TOP_N}, {NUM_SAMPLES}采样@T{TEMP}) ====")
    print(f"模型自身基线: superset={a:.1f}  any={an:.1f}  LoC={l:.0f}")
    out={"model":model,"n":N,"top_n":TOP_N,"num_samples":NUM_SAMPLES,"temp":TEMP,
         "native_baseline":{"superset":round(a,1),"any":round(an,1),"LoC":round(l,1)},
         "per_instance_superset":allc,"ids":[x["iid"] for x in inst]}
    if args.vote_result and Path(args.vote_result).exists():
        v=json.load(open(args.vote_result))
        print(f"\n对比 GPT-4o 基线: superset={v['AL'][0]:.1f}  LoC={v['AL'][2]:.0f}")
        print("模型自身 vote+cov 曲线 (within-model 真正对比):")
        print(f"{'N':>4}{'superset':>10}{'LoC':>8}")
        for Nn in ['10','25','40','60','100','200']:
            if Nn in v.get('vote_cov',{}): a2,an2,l2=v['vote_cov'][Nn]; print(f"{Nn:>4}{a2:>10.1f}{l2:>8.0f}")
        out["gpt4o_baseline"]=v["AL"]; out["vote_cov"]=v["vote_cov"]; out["vote"]=v["vote"]
    json.dump(out, open(args.out,"w"), indent=1)
    print("written:", args.out)

if __name__=="__main__": main()
