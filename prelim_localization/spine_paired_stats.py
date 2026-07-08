#!/usr/bin/env python3
"""spine_paired_stats — the offline verdict for the SPINE decisive run (NO endpoint).
Reads an egl_e2e.py --assert-rerank output JSON and computes the ONLY honest SPINE test:
   M5 (arm 'ours_m5', assertion-rerank)  vs  M4 (arm 'ours_dynamic_nofp', coverage-aware, SAME pool).
Both arms come from the SAME run on identical inputs, so the delta is the assertion signal alone
(never M5-minus-M0, which conflates coverage-narrowing).

Excludes, from the PRIMARY analysis:
  - no-op instances (SPINE did not fire: the test_patch '+' lines carry no assertion keyword -> rerank == input)
  - leak instances (evidence quotes a gold source line verbatim -> a crash 'win' could be answer-leak, not discrimination)
Reports McNemar (exact binomial) + paired bootstrap 95% CI on R@1/R@5/R@10, on ALL / de-noop / de-noop+de-leak sets,
and grades against the pre-set green-light: n>=60, R@1 CI excludes 0, McNemar discordant>=8 & p<0.05.

Usage:  python3 spine_paired_stats.py runs/spine_behav132.json --dataset lite [--seeds runs/spine_behav132_seed*.json]
"""
import json, sys, argparse, math, random
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p0_line_recall as p0
import test_evidence as te
from spine_offline_probe import gold_source_lines

M5, M4 = "ours_m5", "ours_dynamic_nofp"
KS = [1, 5, 10]

def fired(row):
    added = [ln[1:] for ln in (row.get("test_patch") or "").splitlines()
             if ln.startswith("+") and not ln.startswith("+++") and ln[1:].strip()]
    return any(te._KEY.search(l) for l in added)

def leaks(row):
    _, gtexts = gold_source_lines(row)
    if not gtexts:
        return False
    ev = te.extract_test_evidence(row)
    return bool(ev) and any(t in ev for t in gtexts)

def mcnemar(pairs):  # pairs: list of (m5, m4) in {0,1}
    wins = sum(1 for a, b in pairs if a == 1 and b == 0)
    loss = sum(1 for a, b in pairs if a == 0 and b == 1)
    disc = wins + loss
    # exact two-sided binomial p on discordant pairs (H0: p=0.5)
    if disc == 0:
        p = 1.0
    else:
        k = min(wins, loss)
        p = min(1.0, 2 * sum(math.comb(disc, i) for i in range(0, k + 1)) / (2 ** disc))
    return wins, loss, disc, p

def boot_ci(deltas, n=5000, seed=0):
    if not deltas:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    m = sum(deltas) / len(deltas)
    means = []
    for _ in range(n):
        s = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        means.append(sum(s) / len(s))
    means.sort()
    return (round(m, 4), round(means[int(0.025 * n)], 4), round(means[int(0.975 * n)], 4))

def analyze(recs, rows, label):
    usable = [r for r in recs if r.get("arms", {}).get(M5) and r.get("arms", {}).get(M4)]
    def subset(pred):
        return [r for r in usable if pred(rows.get(r["instance_id"], {}))]
    groups = {
        "ALL": usable,
        "de-noop": subset(fired),
        "de-noop+de-leak": [r for r in subset(fired) if not leaks(rows.get(r["instance_id"], {}))],
    }
    print(f"\n########## {label}  (usable pairs: {len(usable)}/{len(recs)}) ##########")
    verdict = {}
    for gname, g in groups.items():
        print(f"\n--- {gname}  (n={len(g)}) ---")
        gv = {}
        for k in KS:
            pairs = [(r["arms"][M5][f"R@{k}"], r["arms"][M4][f"R@{k}"]) for r in g]
            deltas = [a - b for a, b in pairs]
            w, l, d, p = mcnemar(pairs)
            m, lo, hi = boot_ci(deltas)
            m5r = round(100 * sum(a for a, _ in pairs) / len(pairs), 1) if pairs else None
            m4r = round(100 * sum(b for _, b in pairs) / len(pairs), 1) if pairs else None
            sig = (lo > 0 or hi < 0)
            gv[f"R@{k}"] = dict(m5=m5r, m4=m4r, delta_pp=round(100 * m, 1), ci=[round(100*lo,1), round(100*hi,1)],
                                mcnemar=dict(w=w, l=l, disc=d, p=round(p, 4)), sig=sig)
            flag = "  <== SIG" if sig else ""
            print(f"  R@{k}: M5={m5r}  M4={m4r}  Δ={round(100*m,1):+}pp  CI[{round(100*lo,1)},{round(100*hi,1)}]  "
                  f"McNemar {w}W/{l}L disc={d} p={round(p,3)}{flag}")
        verdict[gname] = gv
    # green-light grade on the de-noop+de-leak primary group, R@1
    prim = verdict["de-noop+de-leak"]["R@1"]
    n_prim = len(groups["de-noop+de-leak"])
    green = (n_prim >= 60 and prim["sig"] and prim["ci"][0] > 0
             and prim["mcnemar"]["disc"] >= 8 and prim["mcnemar"]["p"] < 0.05)
    grade = ("GREEN — scale it" if green else
             "RED — real null (adequate discordance, CI includes 0)" if (prim["mcnemar"]["disc"] >= 8 and not prim["sig"])
             else "AMBER — underpowered (discordant<8); n or effect too small to conclude")
    print(f"\n>>> PRIMARY (de-noop+de-leak, R@1, n={n_prim}): {grade}")
    print(f"    criteria: n>=60={n_prim>=60}  CI-excl-0={prim['sig'] and prim['ci'][0]>0}  "
          f"disc>=8={prim['mcnemar']['disc']>=8}  p<0.05={prim['mcnemar']['p']<0.05}")
    return verdict

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="egl_e2e --assert-rerank output JSON")
    ap.add_argument("--dataset", default="lite", choices=["lite", "verified"])
    ap.add_argument("--seeds", nargs="*", default=[], help="additional seed run JSONs; checks R@1 delta sign stability")
    args = ap.parse_args()
    rows = {r["instance_id"]: r for r in p0.load_rows(500, args.dataset)}
    recs = json.load(open(args.run)).get("results", [])
    v = analyze(recs, rows, Path(args.run).name)
    if args.seeds:
        signs = []
        for sp in [args.run] + args.seeds:
            rc = json.load(open(sp)).get("results", [])
            g = [r for r in rc if r.get("arms", {}).get(M5) and r.get("arms", {}).get(M4) and fired(rows.get(r["instance_id"], {})) and not leaks(rows.get(r["instance_id"], {}))]
            d = sum(r["arms"][M5]["R@1"] - r["arms"][M4]["R@1"] for r in g)
            signs.append((Path(sp).name, d))
        print("\n=== seed sign-stability (R@1 net wins, de-noop+de-leak) ===")
        for nm, d in signs:
            print(f"    {nm}: {d:+d}")
        allpos = all(d > 0 for _, d in signs); allneg = all(d < 0 for _, d in signs)
        print(f"    sign stable across {len(signs)} seeds: {allpos or allneg}  ({'positive' if allpos else 'negative' if allneg else 'FLIPS'})")

if __name__ == "__main__":
    main()
