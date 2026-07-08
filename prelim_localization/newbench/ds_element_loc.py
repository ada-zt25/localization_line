#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""benchmark2 上游 (file-given): 文件 = oracle gold_file; 区域 = DeepSeek-V3 在 gold_file 上做 Agentless 元素定位.
输出 newbench/benchmark2_loc.jsonl, 每行与 GPT-4o artifact 同格式 {instance_id, found_files, found_related_locs},
供 al_baseline_native / baseline_conditioned 复用 (EGL_LOC_FILE 指向它).  无 clone, 只 fetch gold_file.
"""
import json, argparse, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import region_loc as R
from agentless.util.postprocess_data import extract_code_blocks, extract_locs_for_files

# Agentless 元素定位 prompt (raw files), 逐字复制自 vendor FL.py:189
PROMPT = """
Please look through the following GitHub Problem Description and Relevant Files.
Identify all locations that need inspection or editing to fix the problem, including directly related areas as well as any potentially related global variables, functions, and classes.
For each location you provide, either give the name of the class, the name of a method in a class, the name of a function, or the name of a global variable.

### GitHub Problem Description ###
{problem_statement}

### Relevant Files ###
{file_contents}

###

Please provide the complete set of locations as either a class name, a function name, or a variable name.
Note that if you include a class, you do not need to list its specific methods.
You can include either the entire class or don't include the class name and instead include specific methods in the class.
### Examples:
```
full_path1/file1.py
function: my_function_1
class: MyClass1
function: MyClass2.my_method

full_path2/file2.py
variable: my_var
function: MyClass3.my_method

full_path3/file3.py
function: my_function_2
function: my_function_3
function: MyClass4.my_method_1
class: MyClass5
```

Return just the locations wrapped with ```.
"""

def element_loc(model, gold_file, issue, src):
    fc = f"### File: {gold_file} ###\n{src}"
    msg = PROMPT.format(problem_statement=issue[:8000], file_contents=fc)
    try: out = R._llm_t(model, msg, temperature=0.0, timeout=180)
    except Exception: out = ""
    res = extract_locs_for_files(extract_code_blocks(out or ""), [gold_file])
    return res.get(gold_file, [""])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workers",type=int,default=1); ap.add_argument("--sample",type=int,default=0)
    a=ap.parse_args()
    model=_os.environ.get("MODEL","deepseek-ai/DeepSeek-V3")
    co=json.load(open("newbench/benchmark2.json"))["benchmark2_crash_onpath"]
    if a.sample: co=co[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset="verified")}
    outp=Path("newbench/benchmark2_loc.jsonl")
    done={json.loads(l)["instance_id"] for l in open(outp)} if outp.exists() else set()
    lock=threading.Lock()
    def work(x):
        iid=x["instance_id"]
        if iid in done: return None
        r=rows.get(iid)
        if not r: return None
        gf=x["gold_file"]
        try: src=p0.fetch_file(r["repo"],r["base_commit"],gf)
        except Exception: return None
        rel=element_loc(model, gf, r.get("problem_statement") or "", src)
        rec={"instance_id":iid,"found_files":[gf],"found_related_locs":[rel]}
        with lock:
            with open(outp,"a") as fo: fo.write(json.dumps(rec)+"\n")
        return iid
    n=0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,x) for x in co]
        for f in as_completed(futs):
            if f.result(): n+=1
            print(f"[{n+len(done)}/{len(co)}] element-loc done", file=_sys.stderr); _sys.stderr.flush()
    print(f"written {outp} ; total lines now:", sum(1 for _ in open(outp)))

if __name__=="__main__": main()
