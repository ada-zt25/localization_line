#!/usr/bin/env python3
"""spine_offline_probe — endpoint-FREE reconnaissance for the SPINE decisive run.
Answers, WITHOUT any LLM call:
  (A) coverage-cache availability per subset (can SPINE run with zero Docker?)
  (B) real SPINE 'fire' rate: does extract_test_evidence yield keyword-matched assertions,
      or would it degenerate to head-only no-op?  (has_tev is trivially ~100%; the real gate
      is whether the '+' lines carry an assertion the judge can reason over.)
  (C) crash-observed vs assertion-only split (traceback present = real expected-vs-observed;
      absent = expected-only) per subset -> tests the audit's 'behavioral = degenerate' claim.
  (D) LEAK check: does the test-evidence text ever quote a GOLD SOURCE line verbatim?
Runs on cached rows/coverage/gold only. No network if caches are warm.
"""
import json, os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p0_line_recall as p0
import test_evidence as te

_KEY = te._KEY
_TB  = te._TB

def load_ids():
    rq3 = json.load(open(HERE / "rq3_subsets.json"))          # lite bench1 splits
    b2  = json.load(open(HERE / "newbench" / "benchmark2_ids.json"))  # verified crash 61
    return {
        "crash_onpath_lite":  rq3["crash_onpath"],   # 57
        "behav_onpath_lite":  rq3["behav_onpath"],   # 132  <- SPINE home turf
        "crash_bench2_verif": list(b2),              # 61
    }

def load_cov():
    cov = json.load(open(HERE / "egl_cov_cache.json"))
    vpath = HERE / "newbench" / "verified_cov_cache.json"
    if vpath.exists():
        cov2 = json.load(open(vpath))
        for k, v in cov2.items():
            cov.setdefault(k, v)
    return cov

def gold_source_lines(row):
    """gold SOURCE line TEXT (stripped, len>=4) for the first .py gold file, using cached file."""
    patch = row.get("patch") or ""
    files = p0.parse_patch(patch)
    pyf = next((f for f in files if f.endswith(".py")), None)
    if not pyf:
        return None, set()
    try:
        src = p0.fetch_file(row["repo"], row["base_commit"], pyf)   # cached
    except Exception:
        return pyf, None
    flines = src.splitlines()
    gold = p0.clean_gold(files[pyf]["region"], flines)
    texts = set()
    for ln in gold:
        if 1 <= ln <= len(flines):
            t = flines[ln - 1].strip()
            if len(t) >= 4:
                texts.add(t)
    return pyf, texts

def probe(ids, rows, cov):
    n = len(ids)
    have_cov = have_gold = fire = tb = leak = missing_row = 0
    leak_examples = []
    for iid in ids:
        r = rows.get(iid)
        if r is None:
            missing_row += 1
            continue
        if iid in cov:
            have_cov += 1
        ev = te.extract_test_evidence(r)
        # would SPINE 'fire'? = there is at least one '+' assertion line matching the key regex
        added = [ln[1:] for ln in (r.get("test_patch") or "").splitlines()
                 if ln.startswith("+") and not ln.startswith("+++") and ln[1:].strip()]
        if any(_KEY.search(l) for l in added):
            fire += 1
        if _TB.search(r.get("problem_statement") or ""):
            tb += 1
        pyf, gtexts = gold_source_lines(r)
        if gtexts is not None:
            have_gold += 1
            if gtexts and ev:
                hit = [t for t in gtexts if t in ev]
                if hit:
                    leak += 1
                    if len(leak_examples) < 4:
                        leak_examples.append((iid, hit[0][:80]))
    return {
        "n": n, "missing_row": missing_row,
        "cov_cached": have_cov, "cov_pct": round(100 * have_cov / n, 1),
        "gold_file_cached": have_gold,
        "spine_fires": fire, "fire_pct": round(100 * fire / n, 1),
        "traceback_present": tb, "tb_pct": round(100 * tb / n, 1),
        "gold_line_leak": leak, "leak_examples": leak_examples,
    }

def main():
    idsets = load_ids()
    cov = load_cov()
    lite = {r["instance_id"]: r for r in p0.load_rows(500, "lite")}
    verif = {r["instance_id"]: r for r in p0.load_rows(500, "verified")}
    rowmaps = {"crash_onpath_lite": lite, "behav_onpath_lite": lite, "crash_bench2_verif": verif}
    print(f"cov cache entries: {len(cov)}  | lite rows: {len(lite)}  verif rows: {len(verif)}\n")
    out = {}
    for name, ids in idsets.items():
        rows = rowmaps[name]
        res = probe(ids, rows, cov)
        out[name] = res
        print(f"=== {name}  (n={res['n']}) ===")
        print(f"  coverage cached      : {res['cov_cached']}/{res['n']}  ({res['cov_pct']}%)   <- zero-Docker feasibility")
        print(f"  gold file cached     : {res['gold_file_cached']}/{res['n']}")
        print(f"  SPINE fires (assert) : {res['spine_fires']}/{res['n']}  ({res['fire_pct']}%)   <- real non-no-op rate")
        print(f"  traceback present    : {res['traceback_present']}/{res['n']}  ({res['tb_pct']}%)  <- crash=real counterfactual; behav=expected-only")
        print(f"  gold-line LEAK       : {res['gold_line_leak']}/{res['n']}  (evidence quotes a gold source line verbatim)")
        for iid, ex in res["leak_examples"]:
            print(f"        leak e.g. {iid}: {ex!r}")
        print()
    json.dump(out, open(HERE / "spine_offline_probe.json", "w"), indent=2)
    print("wrote spine_offline_probe.json")

if __name__ == "__main__":
    main()
