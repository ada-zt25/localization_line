import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _p=_os.path.dirname(_d); _sys.path[:0]=[_p]; _os.chdir(_p)
#!/usr/bin/env python3
"""newbench_scan — mine crash·on-path candidates from a SWE-bench dataset, using the EXACT
definition that produced the frozen n=57 (SWE-bench Lite). Two-stage so we spend Docker only where
needed:

  STAGE A (zero Docker): dataset -> single .py gold (len==1) -> code_gold non-empty ->
      is_crash  =>  crash single-file candidate pool  (needs source fetch, cached & cheap).
  STAGE B (Docker, separate script): collect failing-test coverage for the candidates, apply
      on-path (gold ∩ coverage != empty).

code_gold = p0.clean_gold: drop blank/comment/pure-punct lines from the patch region, keep only
REAL CODE lines. This is our own line-localization normalization (a non-code anchor is not "a line to
fix") and — critically — is the byte-identical operation that built the frozen 57, so benchmark2 stays
comparable to it. (Historical footnote: the cleaning rule was first aligned to ARISE; ARISE is no
longer a baseline and is not why we keep it.)

is_crash: the freeze_subsets.py variant (the canonical one that built rq3_subsets crash_onpath=57).
Validation gate: on --dataset lite this must recover the frozen 57 exactly before we trust Verified.
"""
import argparse, json, re
from collections import Counter
from pathlib import Path
import p0_line_recall as p0

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # prelim_localization (rq3_subsets.json, egl_cov_cache.json live here)

# ---- canonical is_crash (identical to rq4/freeze_subsets.py) ----
TB = re.compile(r"Traceback \(most recent call last\)")
FRAME2 = re.compile(r'File "[^"]+", line \d+')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")
def is_crash(problem_statement, test_patch):
    i = problem_statement or ""
    return bool(TB.search(i)) or len(FRAME2.findall(i)) >= 2 or bool(RAISES.search(test_patch or ""))

# ---- alt is_crash (datalevel_classifier variant) for cross-check ----
def is_crash_alt(problem_statement, test_patch):
    txt = problem_statement or ""; tp = test_patch or ""
    if "Traceback (most recent call last)" in txt:
        return True
    if re.search(r"\b\w+Error\b|\b\w+Exception\b", txt) and ("Traceback" in txt or "raise" in txt):
        return True
    if re.search(r"pytest\.raises|assertRaises|assert_raises", tp):
        return True
    return False


def single_py_gold(row):
    """Return (gold_file, region_set) if the patch touches exactly ONE .py gold file, else None.
    Matches cov_refine_eval.run_instance: len(gold_files)==1."""
    files = p0.parse_patch(row.get("patch") or "")
    gold_files = [f for f in files if f.endswith(".py")]
    if len(gold_files) != 1:
        return None
    gf = gold_files[0]
    return gf, files[gf]["region"]


def code_gold_nonempty(row, gf, region):
    """code_gold = p0.clean_gold (drop blank/comment/pure-punct, keep real code lines) non-empty.
    Needs source (cached fetch). Same call the frozen-57 pipeline uses -> byte-identical parity."""
    try:
        src = p0.fetch_file(row["repo"], row["base_commit"], gf)
    except Exception:
        return None  # unfetchable -> excluded (same as run_instance return None)
    lines = src.splitlines()
    gold = p0.clean_gold(region, lines)
    return gold if gold else None


def stage_a(dataset, n_pool, fetch=True):
    rows = p0.load_rows(n_pool, dataset=dataset)
    total = len(rows)
    single = crash = crash_alt = clean_ok = 0
    candidates = []          # dicts with instance_id/repo/base_commit/gold_file/gold_lines
    crash_no_cleanfetch = []
    for r in rows:
        iid = r["instance_id"]
        sp = single_py_gold(r)
        if not sp:
            continue
        single += 1
        gf, region = sp
        c = is_crash(r.get("problem_statement"), r.get("test_patch"))
        ca = is_crash_alt(r.get("problem_statement"), r.get("test_patch"))
        crash_alt += ca
        if not c:
            continue
        crash += 1
        if not fetch:
            candidates.append({"instance_id": iid, "repo": r["repo"],
                               "base_commit": r["base_commit"], "gold_file": gf})
            continue
        gold = code_gold_nonempty(r, gf, region)
        if gold is None:
            crash_no_cleanfetch.append(iid)
            continue
        clean_ok += 1
        candidates.append({"instance_id": iid, "repo": r["repo"], "base_commit": r["base_commit"],
                           "gold_file": gf, "gold_lines": sorted(gold), "n_gold": len(gold)})
    return {"dataset": dataset, "total": total, "single_py_gold": single,
            "crash_canonical": crash, "crash_alt": crash_alt,
            "clean_gold_ok": clean_ok, "crash_no_cleanfetch": crash_no_cleanfetch,
            "candidates": candidates}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="verified")
    ap.add_argument("--n-pool", type=int, default=500)
    ap.add_argument("--no-fetch", action="store_true", help="skip source fetch / clean_gold (counts only)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    res = stage_a(args.dataset, args.n_pool, fetch=not args.no_fetch)
    print(f"=== STAGE A: {args.dataset} (pool {res['total']}) ===")
    print(f"  single .py gold (len==1)      : {res['single_py_gold']}")
    print(f"  + is_crash (canonical)        : {res['crash_canonical']}")
    print(f"  + is_crash (alt/datalevel)    : {res['crash_alt']} (cross-check)")
    if not args.no_fetch:
        print(f"  + code_gold non-empty         : {res['clean_gold_ok']}  <-- coverage-candidate pool")
        print(f"    (dropped, unfetchable/empty : {len(res['crash_no_cleanfetch'])})")
    print(f"  repo mix (candidates): {dict(Counter(c['instance_id'].split('__')[0] for c in res['candidates']))}")

    # overlap with the frozen Lite crash·on-path 57 and with all Lite instances
    try:
        sub = json.load(open(ROOT / "rq3_subsets.json"))
        frozen57 = set(sub["crash_onpath"])
        lite_ids = {r["instance_id"] for r in p0.load_rows(500, dataset="lite")}
        cand_ids = {c["instance_id"] for c in res["candidates"]}
        print(f"\n  overlap w/ frozen Lite crash·on-path(57): {len(cand_ids & frozen57)}")
        print(f"  candidates already in Lite pool (any)   : {len(cand_ids & lite_ids)}")
        print(f"  NET-NEW candidates (not in Lite pool)   : {len(cand_ids - lite_ids)}")
    except Exception as e:
        print("  (overlap check skipped:", e, ")")

    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=1))
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
