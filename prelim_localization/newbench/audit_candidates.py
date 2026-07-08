import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _p=_os.path.dirname(_d); _sys.path[:0]=[_p]; _os.chdir(_p)
#!/usr/bin/env python3
"""audit_candidates — prove the Verified crash candidates match the EXACT selection predicate that
produced the frozen Lite crash·on-path n=57 (the CRASH half; on-path is measured later by coverage).

For every candidate we RE-DERIVE from the raw row (never trust the scan's json):
  1. crash_canonical  : is_crash (freeze_subsets variant) + WHICH rule fired + the matched evidence
  2. crash_alt        : datalevel_classifier variant (cross-check; must also be True for strictness)
  3. single_py_gold   : exactly one .py gold file  (len(gold_files)==1)
  4. code_gold        : p0.clean_gold(region, src) non-empty (drop blank/comment/punct, keep
                        real code lines; the byte-identical op that built the 57. ARISE is a
                        historical footnote, not our rationale.)
  5. net_new          : not in Lite pool AND not in the frozen 57
  6. wellformed       : row has patch, test_patch, problem_statement, base_commit, repo

REGRESSION GATE: the SAME predicate, run over Lite, must re-select all 57. If it doesn't, the code has
drifted and the audit is invalid. We assert this before trusting the Verified numbers.
"""
import json, re
from pathlib import Path
import p0_line_recall as p0

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# ---------- canonical is_crash (BYTE-IDENTICAL to rq4/freeze_subsets.py) ----------
TB = re.compile(r"Traceback \(most recent call last\)")
FRAME2 = re.compile(r'File "[^"]+", line \d+')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")

def crash_evidence(problem_statement, test_patch):
    """Return (is_crash, rule, evidence) with the SAME truth value as freeze_subsets.is_crash."""
    i = problem_statement or ""; t = test_patch or ""
    if TB.search(i):
        m = TB.search(i); return True, "traceback", i[m.start():m.start()+80]
    frames = FRAME2.findall(i)
    if len(frames) >= 2:
        return True, "frames>=2", " | ".join(frames[:3])
    if RAISES.search(t):
        m = RAISES.search(t); return True, "raises", t[max(0, m.start()-20):m.start()+40].strip()
    return False, "none", ""

# ---------- alt is_crash (datalevel_classifier variant) ----------
def is_crash_alt(problem_statement, test_patch):
    txt = problem_statement or ""; tp = test_patch or ""
    if "Traceback (most recent call last)" in txt:
        return True
    if re.search(r"\b\w+Error\b|\b\w+Exception\b", txt) and ("Traceback" in txt or "raise" in txt):
        return True
    if re.search(r"pytest\.raises|assertRaises|assert_raises", tp):
        return True
    return False

# ---------- the FULL crash-half predicate (== the 57's selection, minus on-path) ----------
def crash_half(row):
    """Return dict of predicate results, or reason it fails. Mirrors cov_refine_eval.run_instance
    (single .py gold, code_gold non-empty) + freeze is_crash."""
    files = p0.parse_patch(row.get("patch") or "")
    py_gold = [f for f in files if f.endswith(".py")]
    all_gold = list(files.keys())
    is_c, rule, ev = crash_evidence(row.get("problem_statement"), row.get("test_patch"))
    is_ca = is_crash_alt(row.get("problem_statement"), row.get("test_patch"))
    rec = {"instance_id": row["instance_id"], "repo": row["repo"],
           "n_py_gold": len(py_gold), "n_all_gold": len(all_gold),
           "py_gold": py_gold, "non_py_gold": [f for f in all_gold if not f.endswith(".py")],
           "is_crash": is_c, "crash_rule": rule, "crash_evidence": ev, "is_crash_alt": is_ca,
           "wellformed": all(bool(row.get(k)) for k in ("patch", "test_patch",
                             "problem_statement", "base_commit", "repo"))}
    if len(py_gold) == 1:
        gf = py_gold[0]; region = files[gf]["region"]
        try:
            src = p0.fetch_file(row["repo"], row["base_commit"], gf)
            clean = p0.clean_gold(region, src.splitlines())
            rec.update({"gold_file": gf, "n_region": len(region), "n_clean_gold": len(clean),
                        "code_gold_ok": bool(clean), "clean_gold": sorted(clean)})
        except Exception as e:
            rec.update({"gold_file": gf, "code_gold_ok": None, "fetch_error": repr(e)[:100]})
    else:
        rec.update({"gold_file": None, "code_gold_ok": False})
    # strict-match = crash(canonical) AND single .py gold AND code_gold non-empty
    rec["strict_crash_half"] = bool(is_c and len(py_gold) == 1 and rec.get("code_gold_ok"))
    return rec


def select(dataset, n_pool):
    rows = p0.load_rows(n_pool, dataset=dataset)
    return [crash_half(r) for r in rows]


def main():
    # ---- REGRESSION GATE: re-select Lite, must recover the frozen 57 ----
    sub = json.load(open(ROOT / "rq3_subsets.json"))
    frozen57 = set(sub["crash_onpath"])
    lite_recs = select("lite", 500)
    lite_ids = {r["instance_id"] for r in lite_recs}
    lite_crashhalf = {r["instance_id"] for r in lite_recs if r["strict_crash_half"]}
    missed = frozen57 - lite_crashhalf
    print("=== REGRESSION GATE (Lite) ===")
    print(f"  frozen 57 all pass crash-half predicate: {len(frozen57 & lite_crashhalf)}/57"
          + ("  OK" if not missed else f"  !! MISSED {missed}"))
    assert not missed, f"predicate drift: {missed} of the 57 no longer pass"

    # ---- Verified candidates ----
    ver_recs = select("verified", 500)
    strict = [r for r in ver_recs if r["strict_crash_half"]]
    net_new = [r for r in strict if r["instance_id"] not in lite_ids and r["instance_id"] not in frozen57]
    print("\n=== VERIFIED crash-half audit ===")
    print(f"  strict crash-half candidates : {len(strict)}")
    print(f"  net-new (not in Lite / 57)   : {len(net_new)}")
    # strictness cross-checks
    only_canon = [r for r in strict if not r["is_crash_alt"]]
    borderline = [r for r in strict if r["crash_rule"] == "frames>=2"]
    print(f"  pass canonical but NOT alt   : {len(only_canon)}  {[r['instance_id'] for r in only_canon]}")
    print(f"  crash rule = frames>=2 (weakest signal): {len(borderline)} {[r['instance_id'] for r in borderline]}")
    from collections import Counter
    print(f"  crash-rule mix: {dict(Counter(r['crash_rule'] for r in strict))}")
    print(f"  repo mix (net-new): {dict(Counter(r['instance_id'].split('__')[0] for r in net_new))}")

    out = {"regression_gate": {"frozen57_recovered": len(frozen57 & lite_crashhalf), "missed": sorted(missed)},
           "verified_strict_crash_half": [r["instance_id"] for r in strict],
           "verified_net_new": [r["instance_id"] for r in net_new],
           "records": {r["instance_id"]: r for r in strict}}
    (HERE / "audit_crash_half.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {HERE / 'audit_crash_half.json'}")

    # per-instance evidence table
    print("\n=== per-instance crash evidence (net-new) ===")
    for r in net_new:
        print(f"  {r['instance_id']:34s} [{r['crash_rule']:9s}] gold={r['gold_file']}"
              f" clean={r['n_clean_gold']} :: {r['crash_evidence'][:70]}")


if __name__ == "__main__":
    main()
