import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _p=_os.path.dirname(_d); _sys.path[:0]=[_p]; _os.chdir(_p)
#!/usr/bin/env python3
"""make_bundle — dump FULL evidence (problem_statement + test_patch + gold-file patch hunk) for the
Verified crash-half candidates, so an offline audit needs no network. Also embeds, for calibration,
the frozen Lite-57 records processed by the identical predicate."""
import json
from pathlib import Path
import p0_line_recall as p0
import newbench.audit_candidates as A   # reuse the EXACT predicate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def gold_hunk(patch, gf):
    """Extract the diff hunk(s) touching the gold file, for eyeballing the fix."""
    out, cur = [], False
    for ln in (patch or "").split("\n"):
        if ln.startswith("diff --git"):
            cur = (gf in ln)
        if cur:
            out.append(ln)
    return "\n".join(out)[:4000]

def build(dataset):
    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset=dataset)}
    recs = A.select(dataset, 500)
    bundle = {}
    for r in recs:
        if not r["strict_crash_half"]:
            continue
        row = rows[r["instance_id"]]
        bundle[r["instance_id"]] = {
            "repo": r["repo"], "crash_rule": r["crash_rule"], "crash_evidence": r["crash_evidence"],
            "is_crash_alt": r["is_crash_alt"], "gold_file": r["gold_file"],
            "n_py_gold": r["n_py_gold"], "n_all_gold": r["n_all_gold"],
            "non_py_gold": r["non_py_gold"], "n_clean_gold": r["n_clean_gold"],
            "problem_statement": (row.get("problem_statement") or ""),
            "test_patch": (row.get("test_patch") or ""),
            "gold_hunk": gold_hunk(row.get("patch"), r["gold_file"]),
            "FAIL_TO_PASS": row.get("FAIL_TO_PASS"), "PASS_TO_PASS_n": len(json.loads(row.get("PASS_TO_PASS") or "[]")) if isinstance(row.get("PASS_TO_PASS"), str) else None,
        }
    return bundle

def main():
    sub = json.load(open(ROOT / "rq3_subsets.json"))
    frozen57 = set(sub["crash_onpath"])
    lite_ids = {r["instance_id"] for r in p0.load_rows(500, dataset="lite")}
    ver = build("verified")
    net_new = {k: v for k, v in ver.items() if k not in lite_ids and k not in frozen57}
    lite = build("lite")
    calib57 = {k: v for k, v in lite.items() if k in frozen57}
    out = {"verified_crash_half": ver, "verified_net_new": net_new,
           "calibration_lite57": calib57,
           "counts": {"verified_strict": len(ver), "net_new": len(net_new), "calib57": len(calib57)}}
    (HERE / "audit_bundle.json").write_text(json.dumps(out, indent=1))
    print("counts:", out["counts"])
    print("wrote", HERE / "audit_bundle.json")

if __name__ == "__main__":
    main()
