#!/usr/bin/env python3
"""arise_eval_adapter — score OUR localization (SPINE / baseline arms, or an end-to-end run) with the
OFFICIAL ARISE evaluation口径, so our numbers are byte-for-byte comparable to a real ARISE run_eval.

Bridges two things:
  (1) our per-instance ranked lines  ->  ARISE prediction format = ranked [(file, function, line), ...]
  (2) scoring                        ->  arise.eval.metrics.compute_all_metrics with arise.eval.gold.parse_gold

Works on ANY egl_e2e run that has the per-instance `ranks` dump (--dump-ranks): file-given now, and the
future de-oracle end-to-end run later (same adapter, so SPINE-vs-ARISE is one shared scorer).

Usage:
  # table of all arms under official ARISE gold, for one or more runs:
  SWEBENCH_DATASET=lite python3 arise_eval_adapter.py runs/basecmp_dsv3.json [runs/basecmp_qwen30.json ...]
  # or point at an end-to-end preds run later.
"""
import sys, json, math, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "vendor" / "ARISE" / "src"))
import p0_line_recall as p0
from arise.eval import gold as ag          # official ARISE gold.py
from arise.eval import metrics as am       # official ARISE metrics.py

ARMS = ["arise_static", "vote_only", "ours_static", "ours_dynamic_nofp", "ours_m5", "ours_m5_votebase"]
ARM_LABEL = {"arise_static": "ARISE-static(proxy)", "vote_only": "vote(self-consist)",
             "ours_static": "ours-static", "ours_dynamic_nofp": "cov-max(M4)",
             "ours_m5": "SPINE(M5)", "ours_m5_votebase": "SPINE-votebase"}


def _func_map(row, path, cache):
    key = (row["instance_id"], path)
    if key not in cache:
        try:
            cache[key] = p0.line_to_func(p0.fetch_file(row["repo"], row["base_commit"], path))
        except Exception:
            cache[key] = {}
    return cache[key]


def arm_preds(run_recs, rows, arm, topn, fcache):
    """{iid: [(file, function, line), ...]} for one arm, from the run's `ranks` dump, rank order."""
    out = {}
    for r in run_recs:
        ranks = r.get("ranks")
        if not ranks or arm not in ranks:
            continue
        iid = r["instance_id"]; row = rows.get(iid)
        if not row:
            continue
        preds = []
        for f, ln in ranks[arm][:topn]:
            func = _func_map(row, f, fcache).get(int(ln), "")
            preds.append((f, func, int(ln)))
        out[iid] = preds
    return out


def golds_for(iids, rows):
    return {iid: ag.parse_gold(rows[iid].get("patch") or "") for iid in iids if iid in rows}


def _mcnemar(pairs):  # pairs of (a_hit, b_hit)
    w = sum(1 for a, b in pairs if a and not b); l = sum(1 for a, b in pairs if b and not a); d = w + l
    p = 1.0 if d == 0 else min(1.0, 2 * sum(math.comb(d, i) for i in range(min(w, l) + 1)) / (2 ** d))
    return w, l, d, round(p, 4)


def line_hit(pred, gold, k):
    """official line_recall_at_k for one instance (1/0)."""
    return int(am.line_recall_at_k(pred, gold, k))


def score_run(run_json, dataset, topn=10):
    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset)}
    recs = [r for r in json.load(open(run_json)).get("results", []) if r.get("ranks")]
    fcache = {}
    name = Path(run_json).stem.replace("basecmp_", "").replace("spine_behav132_", "")
    print(f"\n########## {name}  (n_with_dumps={len(recs)}) — OFFICIAL ARISE gold口径 ##########")
    # per-arm official metrics
    per_arm_preds = {a: arm_preds(recs, rows, a, topn, fcache) for a in ARMS}
    common = set.intersection(*[set(p) for p in per_arm_preds.values() if p]) if any(per_arm_preds.values()) else set()
    golds = golds_for(list(common), rows)
    print(f"{'arm':22} {'lineR@1':>8} {'lineR@5':>8} {'lineR@10':>9} {'fileR@1':>8} {'funcR@1':>8}")
    m5_line1 = {}
    for a in ARMS:
        preds = {iid: per_arm_preds[a][iid] for iid in common if iid in per_arm_preds[a]}
        if not preds:
            continue
        res = am.compute_all_metrics(preds, golds)
        print(f"{ARM_LABEL[a]:22} {100*res['line_recall@1']:8.1f} {100*res['line_recall@5']:8.1f} "
              f"{100*res['line_recall@10']:9.1f} {100*res['file_recall@1']:8.1f} {100*res['func_recall@1']:8.1f}")
        if a == "ours_m5":
            m5_line1 = {iid: line_hit(preds[iid], golds[iid], 1) for iid in preds}
    # paired SPINE vs each baseline on line R@1
    print(f"  -- SPINE(M5) vs baseline, paired line R@1 (n={len(common)}) --")
    for base in ("vote_only", "arise_static"):
        bpreds = {iid: per_arm_preds[base][iid] for iid in common if iid in per_arm_preds[base]}
        pairs = [(m5_line1[iid], line_hit(bpreds[iid], golds[iid], 1)) for iid in bpreds if iid in m5_line1]
        if not pairs:
            print(f"     SPINE vs {ARM_LABEL[base]:20}: (arm not in this run's dump — skipped)"); continue
        w, l, d, pv = _mcnemar(pairs)
        m5r = 100 * sum(a for a, _ in pairs) / len(pairs); br = 100 * sum(b for _, b in pairs) / len(pairs)
        print(f"     SPINE vs {ARM_LABEL[base]:20}: {m5r:.1f} vs {br:.1f}  Δ={m5r-br:+.1f}pp  {w}W/{l}L p={pv}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="egl_e2e run json(s) with --dump-ranks")
    ap.add_argument("--dataset", default="lite")
    ap.add_argument("--topn", type=int, default=10)
    args = ap.parse_args()
    for rj in args.runs:
        if Path(rj).exists():
            score_run(rj, args.dataset, args.topn)
        else:
            print(f"(skip missing {rj})")


if __name__ == "__main__":
    main()
