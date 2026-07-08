#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""RQ2 P0 (offline): (1) crash-vs-behavioral split of SWE-bench-Lite + per-repo; (2) is execution
coverage a localization signal ON CRASH bugs — stratified gold-executed rate + narrowing, crash vs
behavioral. Pure offline: SWE-bench metadata + cached failing-test coverage (egl_cov_cache.json).
NO GPU/LLM (the static-vs-static+coverage Recall@k comparison is the later GPU phase P3)."""
import json, re, statistics as st
import p0_line_recall as p0

# ---- classifier (offline proxy) ----
TB = re.compile(r"Traceback \(most recent call last\)")
FRAME = re.compile(r'File "[^"]+", line \d+')
EXC = re.compile(r"\b[A-Z][A-Za-z]*(?:Error|Exception)\b")
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(|raises\(")

def classify(issue, test_patch):
    issue = issue or ""; test_patch = test_patch or ""
    has_tb = bool(TB.search(issue)) or len(FRAME.findall(issue)) >= 2   # a real traceback block in the report
    exc = bool(EXC.search(issue))                                       # a named exception mentioned
    test_raises = bool(RAISES.search(test_patch))                       # the failing test expects an exception
    crash_strict = has_tb                                               # most reliable: report pasted a traceback
    crash_loose = has_tb or test_raises                                 # + tests that assert on an exception
    return {"has_tb": has_tb, "exc": exc, "test_raises": test_raises,
            "crash_strict": crash_strict, "crash_loose": crash_loose}

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
cov = json.load(open("egl_cov_cache.json"))

cls = {}
for iid, r in rows.items():
    cls[iid] = classify(r.get("problem_statement"), r.get("test_patch"))

n = len(rows)
strict = sum(c["crash_strict"] for c in cls.values())
loose = sum(c["crash_loose"] for c in cls.values())
print(f"=== SWE-bench-Lite 崩溃类占比 (n={n}) ===")
print(f"  crash_strict (issue 含 Traceback): {strict}/{n} = {100*strict//n}%")
print(f"  crash_loose  (+ 测试 pytest.raises): {loose}/{n} = {100*loose//n}%")

# per-repo
print("\n=== 每库崩溃占比 (strict / loose / 总数) ===")
byrepo = {}
for iid, r in rows.items():
    repo = r["repo"].split("/")[-1]
    byrepo.setdefault(repo, []).append(cls[iid])
for repo in sorted(byrepo, key=lambda x: -len(byrepo[x])):
    cs = byrepo[repo]; ns = len(cs)
    s = sum(c["crash_strict"] for c in cs); l = sum(c["crash_loose"] for c in cs)
    print(f"  {repo:28} {s:2}/{l:2}/{ns:2}  ({100*l//ns:3}% loose)")

# ---- coverage signal, stratified by crash vs behavioral ----
def gold_lines(r):
    files = p0.parse_patch(r.get("patch") or "")
    return {f: set(files[f]["region"]) for f in files if f.endswith(".py")}

def cov_for(iid, f, cmap):
    if f in cmap: return set(cmap[f])
    for cf, cl in cmap.items():                      # suffix match
        if cf.endswith(f) or f.endswith(cf): return set(cl)
    return set()

def stratum_stats(pred_crash):
    rec_gold, any_gold, n_exec, file_lines_n, ninst = [], 0, [], [], 0
    for iid, r in rows.items():
        if cls[iid]["crash_loose"] != pred_crash: continue
        cmap = cov.get(iid)
        if not cmap: continue
        for f, g in gold_lines(r).items():
            if not g: continue
            ex = cov_for(iid, f, cmap)
            if not ex: continue
            ninst += 1
            rec_gold.append(len(g & ex) / len(g))
            n_exec.append(len(ex))
            if g & ex: any_gold += 1
    if not ninst: return None
    return {"n": ninst,
            "gold_exec_rate": round(100*st.mean(rec_gold), 1),
            "any_gold_rate": round(100*any_gold/ninst, 1),
            "exec_median": int(st.median(n_exec))}

print("\n=== coverage 信号：金标行是否被执行 (按崩溃 vs 行为分层) ===")
print(f"{'子集':<12}{'(题数)':>7}{'金标被执行%':>13}{'≥1金标被执行%':>15}{'执行集中位行数':>15}")
for label, isc in [("崩溃类(loose)", True), ("行为类", False)]:
    s = stratum_stats(isc)
    if s:
        print(f"{label:<12}{s['n']:>7}{s['gold_exec_rate']:>13}{s['any_gold_rate']:>15}{s['exec_median']:>15}")
print("\n判读：若崩溃类的『≥1金标被执行%』明显高于行为类 → coverage 在崩溃类上确实含答案（有定位信号）；")
print("     执行集中位行数越小 → 覆盖收窄越强、对行级越有用。完整『coverage 提升 recall 多少』= P3 需 GPU 跑 静态 vs 静态+覆盖。")

# ---- traceback signal (精确信号): does the issue's pasted traceback point at the gold file/region? ----
FRAMEX = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')
def tb_frames(issue):
    return FRAMEX.findall(issue or "")   # list of (path, lineno, func)

print("\n=== traceback 精确信号 (仅 crash_strict：issue 真含 traceback) ===")
file_hit = func_hit = both0 = ninst = ntb_frames = 0
deepest_file_hit = 0
for iid, r in rows.items():
    if not cls[iid]["crash_strict"]: continue
    frames = tb_frames(r.get("problem_statement"))
    if not frames: continue
    gl = gold_lines(r)
    if not gl: continue
    ninst += 1; ntb_frames += len(frames)
    tb_files = [p for (p, ln, fn) in frames]
    tb_funcs = set(fn for (p, ln, fn) in frames)
    # 文件级：traceback 任一帧文件后缀匹配某个金标文件
    fhit = any(any(p.endswith(gf) or gf.endswith(p.split("/")[-1]) for p in tb_files) for gf in gl)
    # 最深帧(异常抛出处)文件 == 金标文件
    deep = frames[-1][0]
    dhit = any(deep.endswith(gf) or gf.endswith(deep.split("/")[-1]) for gf in gl)
    # 函数级：金标行落在 traceback 点名的某函数内（用 code_graph）
    fnhit = False
    try:
        import code_graph as cg
        for gf, g in gl.items():
            src = p0.fetch_file(r["repo"], r["base_commit"], gf)
            G = cg.CodeGraph(src, gf)
            if not getattr(G, "ok", False): continue
            for fdef in G.funcs:
                if fdef["name"] in tb_funcs and (set(range(fdef["start"], fdef["end"]+1)) & g):
                    fnhit = True; break
            if fnhit: break
    except Exception:
        pass
    file_hit += fhit; deepest_file_hit += dhit; func_hit += fnhit
    if not fhit and not fnhit: both0 += 1
if ninst:
    print(f"  样本(有traceback且有金标): {ninst} 题，平均 {ntb_frames/ninst:.1f} 帧/题")
    print(f"  traceback 命中金标文件(任一帧):  {file_hit}/{ninst} = {100*file_hit//ninst}%")
    print(f"  最深帧(抛异常处)==金标文件:      {deepest_file_hit}/{ninst} = {100*deepest_file_hit//ninst}%")
    print(f"  traceback 点名的函数含金标行:    {func_hit}/{ninst} = {100*func_hit//ninst}%  ← 这是崩溃类执行信号的真正强度")
    print(f"  traceback 文件/函数都不含金标:   {both0}/{ninst} = {100*both0//ninst}%")
print("\n>>> 结论看：① raw coverage(259行) 对崩溃类只小幅有用；② 真正的精确信号是 traceback 的『函数级命中』。")
print(">>> 若『函数级含金标』高 → 方法应是 traceback/SBFL 当强先验，不是 raw coverage。这决定 7 方法里哪几个是主角。")
