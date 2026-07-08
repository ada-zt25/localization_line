#!/usr/bin/env python3
"""spine_multi_summary — one-command multi-backbone SPINE verdict table (NO endpoint).
For every runs/spine_behav132*.json it computes the assertion-rerank effect on line R@1 under THREE comparisons:
  - M5 vs M4         : rerank vs coverage-max (the original isolation; M4 can be coverage-handicapped)
  - M5 vs vote_only  : rerank vs the FAIR strongest coverage-free baseline (audit-endorsed headline)
  - M5vb vs vote_only: coverage-NEUTRAL SPINE (rerank applied to the vote list directly), if --spine-votebase was run
Each: McNemar (exact) + paired bootstrap 95% CI, on the de-noop+de-leak set. Prints a per-model table + a
generality tally, and (if --dump-ranks present) extracts promotion examples (gold rank>1 in vote -> rank 1 in M5).

Usage:  SWEBENCH_DATASET=lite python3 spine_multi_summary.py [--examples N]
"""
import json, sys, glob, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p0_line_recall as p0
import spine_paired_stats as sp

# filename tag -> (pretty name, dataset)
NAME = {
    "spine_behav132": ("DeepSeek-V3", "lite"),
    "spine_behav132_glm": ("GLM-4.5-Air", "lite"),
    "spine_behav132_qwen": ("Qwen3-Coder-30B", "lite"),
    "spine_behav132_hunyuan": ("Hunyuan-A13B", "lite"),
    "spine_behav132_ling": ("Ling-flash-2.0", "lite"),
    "spine_behav132_dsv32": ("DeepSeek-V3.2-Exp", "lite"),
    "spine_behav132_qwen72": ("Qwen2.5-72B", "lite"),
}

def cmp(recs, rows, a, b):
    """paired R@1 of arm a vs arm b on de-noop+de-leak set."""
    g = [r for r in recs if r.get("arms", {}).get(a) and r.get("arms", {}).get(b)
         and sp.fired(rows.get(r["instance_id"], {})) and not sp.leaks(rows.get(r["instance_id"], {}))]
    if not g:
        return None
    pairs = [(r["arms"][a]["R@1"], r["arms"][b]["R@1"]) for r in g]
    w, l, disc, p = sp.mcnemar(pairs)
    m, lo, hi = sp.boot_ci([x - y for x, y in pairs])
    ar = 100 * sum(x for x, _ in pairs) / len(pairs)
    br = 100 * sum(y for _, y in pairs) / len(pairs)
    return dict(n=len(g), a=round(ar, 1), b=round(br, 1), d=round(100 * m, 1),
                ci=[round(100 * lo, 1), round(100 * hi, 1)], w=w, l=l, disc=disc, p=round(p, 4),
                sig=(lo > 0 or hi < 0))

def promotions(recs, rows, limit=3):
    """instances where gold went from rank>1 in vote_only to rank 1 in ours_m5 (needs --dump-ranks)."""
    out = []
    for r in recs:
        ranks = r.get("ranks"); gold = {tuple(x) for x in r.get("gold_flat", [])}
        if not ranks or not gold:
            continue
        vote = [tuple(x) for x in ranks.get("vote_only", [])]
        m5 = [tuple(x) for x in ranks.get("ours_m5", [])]
        if not vote or not m5:
            continue
        vr = next((i + 1 for i, x in enumerate(vote) if x in gold), None)
        mr = next((i + 1 for i, x in enumerate(m5) if x in gold), None)
        if vr and mr == 1 and vr > 1:
            out.append((r["instance_id"], vr, m5[0]))
        if len(out) >= limit:
            break
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args()
    rowcache = {}
    def rows_for(ds):
        if ds not in rowcache:
            rowcache[ds] = {r["instance_id"]: r for r in p0.load_rows(500, ds)}
        return rowcache[ds]

    files = sorted(glob.glob(str(HERE / "runs" / "spine_behav132*.json")))
    print(f"{'model':17} | {'M5 vs M4':>22} | {'M5 vs vote(FAIR)':>24} | {'M5vb vs vote':>20}")
    print("-" * 92)
    sig_fair = 0; total = 0
    for fn in files:
        tag = Path(fn).stem
        if tag not in NAME:
            continue
        name, ds = NAME[tag]
        recs = json.load(open(fn)).get("results", [])
        if not recs or "ours_m5" not in (recs[0].get("arms", {}) if recs else {}):
            # find any rec with arms
            if not any("ours_m5" in r.get("arms", {}) for r in recs):
                continue
        rows = rows_for(ds)
        total += 1
        c_m4 = cmp(recs, rows, "ours_m5", "ours_dynamic_nofp")
        c_vt = cmp(recs, rows, "ours_m5", "vote_only")
        c_vb = cmp(recs, rows, "ours_m5_votebase", "vote_only")
        if c_vt and c_vt["sig"] and c_vt["d"] > 0:
            sig_fair += 1
        def fmt(c):
            if not c: return f"{'—':>20}"
            star = "*" if c["sig"] else " "
            return f"{c['d']:+5.1f}pp{star} p={c['p']:<6} {c['w']}/{c['l']}"
        print(f"{name:17} | {fmt(c_m4):>22} | {fmt(c_vt):>24} | {fmt(c_vb):>20}")
    print("-" * 92)
    print(f"GENERALITY (fair M5 vs vote_only, R@1 sig & positive): {sig_fair}/{total} backbones")

    print(f"\n=== promotion examples (gold rank>1 in vote -> rank 1 after SPINE; needs --dump-ranks) ===")
    for fn in files:
        tag = Path(fn).stem
        if tag not in NAME: continue
        recs = json.load(open(fn)).get("results", [])
        ex = promotions(recs, rows_for(NAME[tag][1]), args.examples)
        if ex:
            print(f"  [{NAME[tag][0]}]")
            for iid, vr, pick in ex:
                print(f"    {iid}: gold at vote-rank {vr} -> SPINE rank 1 ({pick[0]}:{pick[1]})")

if __name__ == "__main__":
    main()
