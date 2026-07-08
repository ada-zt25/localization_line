#!/usr/bin/env python3
"""
B4 — dataset-level control-flow-distinct vs. data-level proportion (approximate).

Strengthens the §7 claim ("SWE-bench faults are predominantly data-level")
beyond the n=9 SBFL differential (Table 3) using a patch-structure proxy.

The coverage-based ground-truth label (gold line in the failing-only spectrum)
requires passing+failing coverage, collected for only 9 instances. As a scalable
proxy we classify each instance's GOLD PATCH:

  control-flow-distinct (CF)  <=>  the fix ADDS a branch (if/elif/else) whose
      body is *substantial* -- it reroutes execution to an alternative
      computation (both arms do real work), so the failing input drives a
      genuinely different path and the gold appears in failing-only coverage.

  data-level (DL)  <=>  everything else: a value/expression change on an existing
      executed line (wrong value that passing tests also run), a guard/early-return
      insertion, or a pure code insertion (the fix is off the executed path).

This proxy is *calibrated and reported* against the 9 SBFL ground-truth labels;
we report its agreement and treat the dataset number as approximate.
"""
import json, re, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / "cache" / "swebench_lite_pool_300.json"

# SBFL coverage-based ground truth (Table 3): gold in failing-only => CF, else DL
GROUND_TRUTH = {
    "matplotlib__matplotlib-22711": "CF", "matplotlib__matplotlib-22835": "CF",
    "matplotlib__matplotlib-23299": "CF",
    "astropy__astropy-14182": "DL", "astropy__astropy-14365": "DL",
    "astropy__astropy-7746": "DL", "astropy__astropy-14995": "DL",
    "scikit-learn__scikit-learn-10508": "DL", "mwaskom__seaborn-3010": "DL",
}

CTRL_HEAD = re.compile(r"^(if|elif|else|for|while|try|except|with|match|case)\b")
CTRL_XFER = re.compile(r"^(return|raise|break|continue|pass|yield)\b")


def added_content(patch):
    """Return list of (indent, text) for '+' content lines (skip +++ headers, blanks, comments)."""
    out = []
    for ln in patch.splitlines():
        if ln.startswith("+++") or not ln.startswith("+"):
            continue
        body = ln[1:]
        text = body.strip()
        if not text or text.startswith("#"):
            continue
        indent = len(body) - len(body.lstrip())
        out.append((indent, text))
    return out


def classify(patch, rule="substantial"):
    """CF vs DL from patch structure.
    rule='substantial' (calibrated): CF iff the patch adds an if/elif/else header
        whose body reroutes to a real computation (>= one non-control-transfer
        statement); guard/early-return insertions stay DL, matching the paper's
        insertion-is-data-level mechanism.
    rule='naive' (ablation): CF iff the patch adds ANY if/elif/else header. This
        is the un-tuned baseline; the gap between the two exposes how load-bearing
        the substantial-body carve-out is."""
    added = added_content(patch)
    for i, (ind, txt) in enumerate(added):
        if not re.match(r"^(if|elif|else)\b", txt):
            continue
        if rule == "naive":
            return "CF"
        body = []
        for ind2, txt2 in added[i + 1:]:
            if ind2 <= ind:
                break
            body.append(txt2)
        if any(not CTRL_XFER.match(b) for b in body):   # substantial body => reroute
            return "CF"
    return "DL"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (round(100 * (center - half), 1), round(100 * (center + half), 1))


def is_crash(inst):
    """Regex crash proxy matching rq2/crash_coverage_analysis.py (traceback / raises)."""
    txt = (inst.get("problem_statement") or "")
    tp = (inst.get("test_patch") or "")
    if "Traceback (most recent call last)" in txt:
        return True
    if re.search(r"\b\w+Error\b|\b\w+Exception\b", txt) and ("Traceback" in txt or "raise" in txt):
        return True
    if re.search(r"pytest\.raises|assertRaises|assert_raises", tp):
        return True
    return False


def main():
    pool = {p["instance_id"]: p for p in json.load(open(POOL))}

    # ---- IN-SAMPLE calibration on the 9 SBFL instances (no held-out set exists) ----
    print("=== IN-SAMPLE calibration on n=9 SBFL ground truth ===")
    cal = {}
    for rule in ("substantial", "naive"):
        ok = 0
        rows = []
        for iid, gt in GROUND_TRUTH.items():
            pred = classify(pool[iid]["patch"], rule=rule)
            hit = pred == gt
            ok += hit
            rows.append({"instance": iid, "gt": gt, "pred": pred, "agree": hit})
        cal[rule] = {"agree": ok, "rows": rows}
        print(f"  rule={rule:12s} in-sample agreement {ok}/9")
    print()

    # ---- apply to populations, under BOTH rules (knob-sensitivity is explicit) ----
    def summarize(ids, name, rule):
        dl = sum(classify(pool[i]["patch"], rule=rule) == "DL" for i in ids)
        n = len(ids)
        lo, hi = wilson(dl, n)
        return {"population": name, "rule": rule, "n": n, "data_level": dl,
                "data_level_pct": round(100 * dl / n, 1), "wilson95_sampling_only": [lo, hi]}

    all_ids = list(pool.keys())
    crash_ids = [i for i in all_ids if is_crash(pool[i])]
    print("=== dataset-level data-level proportion (patch proxy; both rules) ===")
    pops = []
    for rule in ("substantial", "naive"):
        for ids, nm in [(all_ids, "all SWE-bench-Lite"), (crash_ids, "crash-loose subset")]:
            r = summarize(ids, nm, rule)
            pops.append(r)
            print(f"  {nm:22s} rule={rule:12s} n={r['n']:4d}  "
                  f"data-level={r['data_level']:4d} ({r['data_level_pct']}%)  "
                  f"Wilson95(sampling-only)={r['wilson95_sampling_only']}")

    out = {
        "config": "B4 dataset-level data-level proportion (patch-structure proxy)",
        "proxy": "CF iff patch adds if/else branch with substantial body; else data-level",
        "calibration_in_sample": {"n": 9, "note": "rule designed on these 9; NOT held-out",
                                  "substantial_agree": cal["substantial"]["agree"],
                                  "naive_agree": cal["naive"]["agree"],
                                  "rows": cal["substantial"]["rows"]},
        "populations": pops,
        "note": ("APPROXIMATE and IN-SAMPLE: the classification rule was designed on the same "
                 "n=9 coverage-based SBFL instances it is scored against (in-sample agreement "
                 "{}/9; naive branch-adding rule only {}/9). The estimate is knob-sensitive: "
                 "the substantial-body carve-out (guards/insertions counted data-level, per the "
                 "paper's mechanism) moves the all-300 number from ~49% (naive) to ~66%. The "
                 "Wilson interval reflects sampling only, NOT classifier error (~11%) or rule "
                 "choice. Read as an indicative extrapolation, not an independent measurement."
                 .format(cal["substantial"]["agree"], cal["naive"]["agree"])),
    }
    outpath = HERE.parent / "rq4" / "results" / "datalevel_scale.json"
    json.dump(out, open(outpath, "w"), indent=2)
    print(f"\nwrote {outpath}")
    return out


if __name__ == "__main__":
    main()
