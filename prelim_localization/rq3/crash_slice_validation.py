#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""Offline validation (NO GPU) of the 'coverage-pruned backward slice' idea for crash bugs.
For the crash subset, on each gold file, compare 3 candidate REGIONS by (gold-recall, size):
  R1 = coverage            (all executed lines)                  — high recall, huge (the haystack)
  R2 = traceback-funcs ∩ coverage                               — the call-chain functions, executed
  R3 = (R2 + backward def-use slice) ∩ coverage                 — slice upstream along data flow
Hypothesis: R3 gold-recall > R2 (reaches the upstream root cause traceback misses) while
size(R3) << size(R1) (much narrower than raw coverage). All at base_commit (line numbers reliable)."""
import ast, json, re, statistics as st
import p0_line_recall as p0

TB = re.compile(r"Traceback \(most recent call last\)")
FRAME2 = re.compile(r'File "[^"]+", line \d+')
FRAMEX = re.compile(r'File "[^"]+", line \d+, in (\S+)')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")

def is_crash(issue, tp):
    issue = issue or ""
    return bool(TB.search(issue)) or len(FRAME2.findall(issue)) >= 2 or bool(RAISES.search(tp or ""))

def line_defuse(src):
    """per-line (defs, uses) variable names via AST (approximate: Name Store=def, Load=use; args=def)."""
    defs, uses = {}, {}
    try: tree = ast.parse(src)
    except Exception: return defs, uses
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and hasattr(node, "lineno"):
            (defs if isinstance(node.ctx, ast.Store) else uses).setdefault(node.lineno, set()).add(node.id)
        if isinstance(node, ast.arg) and hasattr(node, "lineno"):
            defs.setdefault(node.lineno, set()).add(node.arg)
    return defs, uses

def funcs_of(src):
    """name -> set(line range) for each function/method (for traceback-func region)."""
    out = {}
    try: tree = ast.parse(src)
    except Exception: return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lo, hi = node.lineno, max([node.lineno] + [getattr(c, "lineno", node.lineno) for c in ast.walk(node)])
            out.setdefault(node.name, set()).update(range(lo, hi + 1))
    return out

def backward_slice(seed_lines, defs, uses, exec_lines):
    """intraprocedural-ish backward slice over executed lines, seeded from uses at seed_lines."""
    needed = set()
    for ln in seed_lines: needed |= uses.get(ln, set())
    sl = set(seed_lines)
    for ln in sorted(exec_lines, reverse=True):
        d = defs.get(ln, set())
        if d & needed:
            sl.add(ln); needed = (needed - d) | uses.get(ln, set())
    return sl & exec_lines

rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
cov = json.load(open("egl_cov_cache.json"))

def cov_for(f, cmap):
    if f in cmap: return set(cmap[f])
    for cf, cl in cmap.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()

agg = {k: {"hit": 0, "sizes": []} for k in ("R1_cov", "R2_tbfunc", "R3_slice")}
n = 0
for iid, r in rows.items():
    if not is_crash(r.get("problem_statement"), r.get("test_patch")): continue
    cmap = cov.get(iid)
    if not cmap: continue
    tb_funcs = set(FRAMEX.findall(r.get("problem_statement") or ""))
    if not tb_funcs: continue
    gfiles = p0.parse_patch(r.get("patch") or "")
    used = False
    for f in [x for x in gfiles if x.endswith(".py")]:
        gold = set(gfiles[f]["region"])
        if not gold: continue
        ex = cov_for(f, cmap)
        if not ex: continue
        if not (gold & ex): continue                     # ON-PATH filter: gold must be executed
        try: src = p0.fetch_file(r["repo"], r["base_commit"], f)
        except Exception: continue
        defs, uses = line_defuse(src); fmap = funcs_of(src)
        R1 = ex
        tb_lines = set().union(*[fmap[fn] for fn in tb_funcs if fn in fmap]) if any(fn in fmap for fn in tb_funcs) else set()
        R2 = tb_lines & ex
        R3 = backward_slice(R2, defs, uses, ex) | R2 if R2 else set()
        if not R1: continue
        used = True
        for key, R in (("R1_cov", R1), ("R2_tbfunc", R2), ("R3_slice", R3)):
            if R & gold: agg[key]["hit"] += 1
            agg[key]["sizes"].append(len(R))
        break  # one gold file per instance
    if used: n += 1

print(f"crash 子集(有覆盖+traceback函数+金标): n={n}\n")
print(f"{'区域定义':<26}{'金标recall%':>12}{'中位行数':>10}{'均值行数':>10}{'recall/size 密度':>16}")
print("-" * 74)
for key, label in [("R1_cov", "R1 = 裸覆盖(执行行)"),
                   ("R2_tbfunc", "R2 = traceback函数∩覆盖"),
                   ("R3_slice", "R3 = 反向切片∩覆盖 ⭐")]:
    a = agg[key]; rec = 100*a["hit"]/max(n,1)
    med = int(st.median(a["sizes"])) if a["sizes"] else 0
    mean = int(st.mean(a["sizes"])) if a["sizes"] else 0
    dens = round(rec/max(med,1), 2)
    print(f"{label:<26}{rec:>11.1f}{med:>10}{mean:>10}{dens:>16}")
print("\n判读：R3 的『金标recall』≥ R2 且接近 R1(说明切片够到了 traceback 漏的上游根因)，")
print("     同时 R3 的『中位行数』≪ R1 259(说明比裸覆盖窄得多) → 切片在 recall 和精度上同时占优 = 假设成立。")
print("     『密度』(recall/size) 越高越好：R3 应显著高于 R1。")
