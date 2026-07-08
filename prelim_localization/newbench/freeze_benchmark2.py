import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _p=_os.path.dirname(_d); _sys.path[:0]=[_p]; _os.chdir(_p)
#!/usr/bin/env python3
"""freeze_benchmark2 — build benchmark2 = SWE-bench-Verified crash·on-path, STRICTLY matching the
frozen-57 (Lite) definition. An instance is admitted ONLY if it passes ALL of:
   crash (is_crash canonical)  ∧  single .py gold  ∧  code_gold non-empty   [already audited]
   ∧  on-path:  code_gold ∩ coverage(failing test) != empty                  [decided HERE]
on-path uses the SAME rule the 57's experiment (cov_refine_eval) used: gold = p0.clean_gold(region),
coverage matched to the gold file by cov_for (endswith), admit iff the intersection is non-empty.

No off-path / no-coverage instance can leak in — they are routed to the transparency breakdown, never
into benchmark2_crash_onpath.

  python newbench/freeze_benchmark2.py            # after coverage collection
"""
import argparse, json
from collections import Counter
from pathlib import Path
import p0_line_recall as p0

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUDIT = HERE / "audit_crash_half.json"
COV = HERE / "verified_cov_cache.json"
OUT = HERE / "benchmark2.json"


def cov_for(f, cm):
    """endswith file matching — byte-identical to freeze_subsets.py / cov_refine_eval.py."""
    if f in cm:
        return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]):
            return set(cl)
    return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="net_new", choices=["net_new", "all_strict"])
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    audit = json.load(open(AUDIT))
    curated = HERE / "benchmark2_crash_half.json"
    if args.which == "net_new" and curated.exists():
        cand_ids = json.load(open(curated))["confirmed"]      # 75 = audit-curated (django-9296 excluded)
    else:
        key = "verified_net_new" if args.which == "net_new" else "verified_strict_crash_half"
        cand_ids = audit[key]
    records = audit["records"]
    if not COV.exists():
        raise SystemExit(f"missing {COV} — run collect_verified_cov.py first")
    covcache = json.load(open(COV))
    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="verified")}

    onpath, offpath, nocov = [], [], []
    for iid in cand_ids:
        rec = records[iid]
        gf = rec["gold_file"]
        gold = set(rec.get("clean_gold") or [])          # code_gold (== clean_gold), the audited gold
        cm = covcache.get(iid)
        if not cm:                                        # coverage never collected / empty
            nocov.append(iid); continue
        ex = cov_for(gf, cm)
        if not ex:
            nocov.append(iid); continue
        inter = gold & ex
        entry = {"instance_id": iid, "repo": rec["repo"],
                 "base_commit": rows[iid]["base_commit"], "gold_file": gf,
                 "gold_lines": sorted(gold), "exec_lines": sorted(ex),
                 "n_gold": len(gold), "n_exec": len(ex), "n_gold_executed": len(inter),
                 "crash_rule": rec.get("crash_rule")}
        (onpath if inter else offpath).append(entry)

    meta = {
        "name": "benchmark2",
        "definition": "crash (is_crash canonical) AND single .py gold AND code_gold non-empty AND "
                      "on-path (code_gold ∩ failing-test coverage != empty)",
        "byte_identical_to": "frozen-57 SWE-bench-Lite crash·on-path (rq3_subsets.json crash_onpath)",
        "source_dataset": "SWE-bench_Verified (princeton-nlp/SWE-bench_Verified, 500)",
        "scope": args.which + " (disjoint from SWE-bench-Lite / the frozen 57)",
        "code_gold": "p0.clean_gold: drop blank/comment/pure-punct, keep real code lines "
                     "(historical footnote: rule first aligned to ARISE; ARISE is not a baseline here)",
        "coverage_source": "cov_collect.collect (official SWE-bench Docker image, failing test under coverage)",
        "counts": {"candidates": len(cand_ids), "crash_onpath": len(onpath),
                   "crash_offpath": len(offpath), "crash_nocov": len(nocov)},
        "repo_mix": dict(Counter(e["instance_id"].split("__")[0] for e in onpath)),
        "crash_rule_mix": dict(Counter(e["crash_rule"] for e in onpath)),
    }
    out = {"meta": meta,
           "benchmark2_crash_onpath": onpath,
           "_crash_offpath": [e["instance_id"] for e in offpath],
           "_crash_nocov": nocov}
    Path(args.out).write_text(json.dumps(out, indent=1))

    print("=== benchmark2 freeze ===")
    for k, v in meta["counts"].items():
        print(f"  {k:16s}: {v}")
    print(f"  repo mix (on-path): {meta['repo_mix']}")
    print(f"  crash-rule mix    : {meta['crash_rule_mix']}")
    print(f"  wrote {args.out}")
    print("\n  merged with frozen-57 -> combined crash·on-path n =",
          57 + len(onpath), "(benchmark1 57 + benchmark2", len(onpath), ")")


if __name__ == "__main__":
    main()
