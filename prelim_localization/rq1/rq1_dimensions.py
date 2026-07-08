#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""RQ1 (offline): WHICH factors most depress line-level localization recall? Stratify per-instance
line recall by multiple dimensions, using the end-to-end run egl_e2e_ARISE_static.json (Qwen2.5-Coder-32B,
n=300, SWE-bench-Lite; dataset pinned to 'lite' so this reproduces with no env var). Two metrics:
line_R@10 (end-to-end) and line_recall_given_found (isolates the LINE step from file-loc).
Dimensions: #gold files, #gold lines, gold-file size, bug type, code domain, file-found."""
import json, re, statistics as st
import p0_line_recall as p0

TB = re.compile(r"Traceback \(most recent call last\)"); FRAME2 = re.compile(r'File "[^"]+", line \d+')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")
def is_crash(i, t): i = i or ""; return bool(TB.search(i)) or len(FRAME2.findall(i)) >= 2 or bool(RAISES.search(t or ""))

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
res = json.load(open("egl_e2e_ARISE_static.json"))["results"]   # Qwen-32B, Lite n=300 (full match w/ lite rows)

# gold-file size (cached fetch)
def gold_file_lines(r):
    gf = p0.parse_patch(r.get("patch") or "")
    pyf = [f for f in gf if f.endswith(".py") and gf[f]["region"]]
    if not pyf: return None
    try: return len(p0.fetch_file(r["repo"], r["base_commit"], pyf[0]).splitlines())
    except Exception: return None

recs = []
for x in res:
    r = rows.get(x["instance_id"])
    if not r: continue
    recs.append({
        "lr10": x.get("line_R@10", 0),
        "lrgf": x.get("line_recall_given_found", 0.0),
        "found": 1 if x.get("file_recall", 0) > 0 else 0,
        "ngold_files": x.get("n_gold_files", 1),
        "tot_gold": x.get("tot_gold", 1),
        "crash": is_crash(r.get("problem_statement"), r.get("test_patch")),
        "fsize": gold_file_lines(r),
        "repo": r["repo"].split("/")[-1],
    })
n = len(recs)
print(f"RQ1 多维度（Qwen2.5-Coder-32B n={n}，SWE-bench-Lite，端到端，egl_e2e_ARISE_static）\n")

def strat(name, bucket_fn, order=None):
    g = {}
    for d in recs:
        b = bucket_fn(d)
        if b is None: continue
        g.setdefault(b, []).append(d)
    keys = order or sorted(g)
    print(f"— 维度：{name} —")
    print(f"   {'分桶':<16}{'n':>5}{'line_R@10':>11}{'line_rec|found':>15}{'file找到%':>10}")
    for k in keys:
        if k not in g: continue
        b = g[k]; m = len(b)
        print(f"   {str(k):<16}{m:>5}{100*st.mean([d['lr10'] for d in b]):>10.1f}%"
              f"{100*st.mean([d['lrgf'] for d in b]):>14.1f}%{100*st.mean([d['found'] for d in b]):>9.0f}%")
    print()

strat("文件已找到", lambda d: "found" if d["found"] else "NOT-found", ["found", "NOT-found"])
strat("# gold 文件（多文件难度）", lambda d: "1 文件" if d["ngold_files"] == 1 else "≥2 文件", ["1 文件", "≥2 文件"])
strat("# gold 行（多行修复）", lambda d: "1 行" if d["tot_gold"] <= 1 else ("2–3 行" if d["tot_gold"] <= 3 else "≥4 行"),
      ["1 行", "2–3 行", "≥4 行"])
strat("gold 文件规模（行数）", lambda d: None if d["fsize"] is None else
      ("≤200" if d["fsize"] <= 200 else ("200–1000" if d["fsize"] <= 1000 else (">1000–3000" if d["fsize"] <= 3000 else ">3000"))),
      ["≤200", "200–1000", ">1000–3000", ">3000"])
strat("bug 类型", lambda d: "崩溃类" if d["crash"] else "行为类", ["崩溃类", "行为类"])
# top repos by count
from collections import Counter
top = [r for r, _ in Counter(d["repo"] for d in recs).most_common(6)]
strat("仓库（top6）", lambda d: d["repo"] if d["repo"] in top else None, top)
print("判读：看哪个维度内 line_R@10 / line_rec|found 的跌幅最大 → 那是最压低行级 recall 的因素。")
