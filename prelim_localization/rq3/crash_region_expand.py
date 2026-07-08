#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""Can we raise R2 (traceback-funcs ∩ coverage, ~60%) toward R1 (coverage, 100%) without bloating?
The 40% R2 misses = gold in functions that EXECUTED but are OFF the crash call-stack (a helper called
by a traceback func that already returned). Fix: expand the region along the STATIC CALL GRAPH to the
EXECUTED callees of the traceback functions (1-hop, 2-hop). On-path crash subset, offline, no GPU.
  R2  = traceback funcs ∩ cov
  R4  = (traceback funcs + 1-hop executed callees) ∩ cov
  R5  = (+ 2-hop) ∩ cov
  Rallf = all executed functions in the file ∩ cov   (upper bound for 'restrict to executed funcs')"""
import ast, json, re, statistics as st
import p0_line_recall as p0

TB = re.compile(r"Traceback \(most recent call last\)"); FRAME2 = re.compile(r'File "[^"]+", line \d+')
FRAMEX = re.compile(r'File "[^"]+", line \d+, in (\S+)')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")
def is_crash(i, t): i = i or ""; return bool(TB.search(i)) or len(FRAME2.findall(i)) >= 2 or bool(RAISES.search(t or ""))

def func_table(src):
    """name -> (line set, called-function-names) for each function/method."""
    out = {}
    try: tree = ast.parse(src)
    except Exception: return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines = set(); calls = set()
            for c in ast.walk(node):
                if hasattr(c, "lineno"): lines.add(c.lineno)
                if isinstance(c, ast.Call):
                    fn = c.func
                    if isinstance(fn, ast.Name): calls.add(fn.id)
                    elif isinstance(fn, ast.Attribute): calls.add(fn.attr)
            out.setdefault(node.name, (set(), set()))
            out[node.name] = (out[node.name][0] | lines, out[node.name][1] | calls)
    return out

def expand(seed_names, ftab, hops):
    names = set(seed_names)
    for _ in range(hops):
        new = set()
        for n in list(names):
            if n in ftab:
                new |= ftab[n][1]                            # called names
        names |= (new & set(ftab))                           # keep only resolvable to a func in this file
    return names

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
cov = json.load(open("egl_cov_cache.json"))
def cov_for(f, cm):
    if f in cm: return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()

agg = {k: {"hit": 0, "sizes": []} for k in ("R2", "R4", "R5", "Rallf")}
n = 0
for iid, r in rows.items():
    if not is_crash(r.get("problem_statement"), r.get("test_patch")): continue
    cm = cov.get(iid)
    if not cm: continue
    tb = set(FRAMEX.findall(r.get("problem_statement") or ""))
    if not tb: continue
    gf = p0.parse_patch(r.get("patch") or "")
    for f in [x for x in gf if x.endswith(".py")]:
        gold = set(gf[f]["region"])
        if not gold: continue
        ex = cov_for(f, cm)
        if not (gold & ex): continue                         # on-path
        try: src = p0.fetch_file(r["repo"], r["base_commit"], f)
        except Exception: continue
        ftab = func_table(src)
        if not ftab: continue
        def region(names): return set().union(*[ftab[x][0] for x in names if x in ftab]) if any(x in ftab for x in names) else set()
        R2 = region(tb) & ex
        R4 = region(expand(tb, ftab, 1)) & ex
        R5 = region(expand(tb, ftab, 2)) & ex
        Rallf = set().union(*[ln for (ln, _) in ftab.values()]) & ex   # all func lines ∩ cov
        n += 1
        for key, R in (("R2", R2), ("R4", R4), ("R5", R5), ("Rallf", Rallf)):
            if R & gold: agg[key]["hit"] += 1
            agg[key]["sizes"].append(len(R))
        break

print(f"on-path 崩溃子集: n={n}\n")
print(f"{'区域':<34}{'金标recall%':>12}{'中位行数':>10}{'密度':>9}")
print("-" * 65)
for key, label in [("R2", "R2 traceback函数"), ("R4", "R4 +1-hop 执行callee"),
                   ("R5", "R5 +2-hop 执行callee"), ("Rallf", "Rallf 所有执行函数(上界)")]:
    a = agg[key]; rec = 100*a["hit"]/max(n,1); med = int(st.median(a["sizes"])) if a["sizes"] else 0
    print(f"{label:<34}{rec:>11.1f}{med:>10}{round(rec/max(med,1),2):>9}")
print("\n判读：若 R4/R5 的 recall 明显爬过 R2 的 ~60% 而中位行数没炸 → 沿调用图扩到 executed callee 能把离栈根因捞回来。")
