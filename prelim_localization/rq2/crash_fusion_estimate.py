#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""Offline upper-bound estimate (NO GPU): on the crash subset, how much could traceback ADD to the
static method? Uses per-instance static line_R@k from existing egl_e2e runs + whether the issue
traceback reaches the gold (file/function). Key number = of the crash cases STATIC MISSES, what
fraction does the traceback recover → the headroom a static⊕traceback fusion could realize."""
import json, re
import p0_line_recall as p0
import code_graph as cg

TB = re.compile(r"Traceback \(most recent call last\)")
FRAME2 = re.compile(r'File "[^"]+", line \d+')
FRAMEX = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(|raises\(")

def is_crash(issue, test_patch):
    issue = issue or ""
    has_tb = bool(TB.search(issue)) or len(FRAME2.findall(issue)) >= 2
    return has_tb or bool(RAISES.search(test_patch or "")), has_tb

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}

def gold_lines(r):
    files = p0.parse_patch(r.get("patch") or "")
    return {f: set(files[f]["region"]) for f in files if f.endswith(".py")}

def tb_reaches_gold(r):
    """Does the issue traceback name the gold file / a function containing a gold line?"""
    frames = FRAMEX.findall(r.get("problem_statement") or "")
    if not frames: return False, False
    gl = gold_lines(r)
    tb_files = [p for (p, ln, fn) in frames]; tb_funcs = set(fn for (p, ln, fn) in frames)
    fhit = any(any(p.endswith(gf) or gf.endswith(p.split("/")[-1]) for p in tb_files) for gf in gl)
    fnhit = False
    try:
        for gf, g in gl.items():
            src = p0.fetch_file(r["repo"], r["base_commit"], gf); G = cg.CodeGraph(src, gf)
            if not getattr(G, "ok", False): continue
            for fdef in G.funcs:
                if fdef["name"] in tb_funcs and (set(range(fdef["start"], fdef["end"]+1)) & g):
                    fnhit = True; break
            if fnhit: break
    except Exception: pass
    return fhit, fnhit

# crash subset
crash = {}
for iid, r in rows.items():
    c, _ = is_crash(r.get("problem_statement"), r.get("test_patch"))
    if c: crash[iid] = r
print(f"crash 子集: {len(crash)} 题")

for static_file, tag in [("archive/egl_e2e_n288_v4pro_FINAL.json", "DeepSeek-V3"),
                         ("archive/egl_e2e_awq.json", "Qwen-32B AWQ")]:
    d = json.load(open(static_file)); res = d["results"] if isinstance(d, dict) else d
    byid = {x["instance_id"]: x for x in res}
    inst = [iid for iid in crash if iid in byid]
    if not inst: continue
    n = len(inst)
    sr = {k: sum(byid[i].get(f"line_R@{k}", 0) for i in inst)/n for k in (1,5,10)}
    # traceback reach on each crash instance
    reach = {i: tb_reaches_gold(crash[i]) for i in inst}
    tb_func = sum(1 for i in inst if reach[i][1]) / n
    # static MISS @10, of which traceback reaches (func-level)
    miss = [i for i in inst if not byid[i].get("line_R@10", 0)]
    miss_recover = sum(1 for i in miss if reach[i][1])
    # union ceiling @10 = static hit OR traceback func reaches
    union10 = sum(1 for i in inst if byid[i].get("line_R@10", 0) or reach[i][1]) / n
    print(f"\n===== {tag} · crash 子集 n={n} (end-to-end) =====")
    print(f"  静态 line R@1/5/10        : {sr[1]*100:.1f} / {sr[5]*100:.1f} / {sr[10]*100:.1f}")
    print(f"  traceback 函数级够到金标   : {tb_func*100:.0f}%")
    print(f"  静态 @10 漏掉的            : {len(miss)} 题")
    print(f"   └ 其中 traceback 能救回   : {miss_recover}/{len(miss)} = {(100*miss_recover//max(len(miss),1))}%  ← 互补性/可恢复 headroom")
    print(f"  并集上限 R@10 (静态∪traceback): {union10*100:.1f}%   (静态 {sr[10]*100:.1f}% → 上限 {union10*100:.1f}%, +{(union10-sr[10])*100:.1f}pp)")
print("\n注：这是端到端、且是『traceback 够到金标函数』的上限（实际融合 + 函数内还要排到 top-k，会打折）；")
print("    但若『静态漏的里 traceback 能救回』比例高 → 说明两信号互补、融合值得做。SBFL 未计入（需通过覆盖，P1）。")
