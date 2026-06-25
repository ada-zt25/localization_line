#!/usr/bin/env python3
"""ablation_rank_sweep — FREE offline ranking ablation over a persisted Stage-B substrate.

Reorders the ALREADY-VOTED line set (NO LLM, NO GPU) under different rankers to isolate where
Line R@1 / R@10 are lost: the candidate-SET ceiling vs the RANK. Tests the REAL production
rankers (region_loc._rank_v0 / _rank_counts), so a winner here ships unchanged.

Reads either substrate format:
  - egl_e2e --dump-substrate :  rec['substrate'][gf] = {region, freq, counts, gold, file_lines}
  - egl_headtohead.json      :  rec['files'][gf]     = {region, freq, ...}   (no counts; gold via patch)

  python ablation_rank_sweep.py --substrate egl_e2e.json
"""
from __future__ import annotations
import argparse, json, statistics as st
from pathlib import Path
import p0_line_recall as p0
import code_graph as cg
import region_loc as rl
from egl_headtohead import interleave, hitk

KS = (1, 5, 10)


def graph_scores(src, path, issue):
    g = cg.CodeGraph(src, path)
    return g.line_scores_v2(issue, use_coverage=False, graded=True) if g.ok else {}


def iter_files(rec, rows):
    """Yield (repo, commit, issue, gf, sub, gold) for either substrate format."""
    r = rows.get(rec.get("instance_id"))
    if not r:
        return
    issue = (r.get("problem_statement") or "")[:5000]
    repo, commit = r["repo"], r["base_commit"]
    if "substrate" in rec:                              # egl_e2e --dump-substrate
        for gf, sub in rec["substrate"].items():
            yield repo, commit, issue, gf, sub, set(sub.get("gold", []))
    elif "files" in rec:                                # egl_headtohead (gold from the patch)
        files = p0.parse_patch(r.get("patch") or "")
        for gf, sub in rec["files"].items():
            gold = files.get(gf, {}).get("region")
            if gold:
                yield repo, commit, issue, gf, sub, set(gold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--substrate", default="egl_e2e.json")
    ap.add_argument("--ks", default="1,5,10,20,30,60")
    ap.add_argument("--grow-depth", type=int, default=0, help="(Q3 offline GATE) simulate def-use SET-EXPANSION at this depth and report EXPANDED(set) ceiling vs ORACLE(set) — the FREE check of whether region_loc._expand_voted raises voted_ceiling, BEFORE any GPU run")
    ap.add_argument("--grow-cap", type=int, default=25)
    ap.add_argument("--arise-gold", action="store_true", help="(Lever 1) drop blank/comment lines from gold before scoring (matches egl_e2e --arise-gold)")
    args = ap.parse_args()
    Kgrid = [int(x) for x in args.ks.split(",")]
    data = json.load(open(args.substrate, encoding="utf-8"))
    recs = data["results"] if isinstance(data, dict) else data
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}

    # name -> ranker(freq, sc, counts) -> ordered line list
    variants = {
        "vote_only":      lambda f, s, c: sorted(f, key=lambda l: (-f[l], rl._tiebreak(l))),
        "graph_only":     lambda f, s, c: sorted(f, key=lambda l: (-s.get(l, 0.0), rl._tiebreak(l))),
        "v0_rrf":         lambda f, s, c: rl._rank_v0(dict(f), s, c),
        "counts_primary": lambda f, s, c: rl._rank_counts(dict(f), s, c),
    }
    for K in Kgrid:
        variants[f"rrf_K{K}"] = (lambda f, s, c, K=K: rl._rank_v0(dict(f), s, c, K=K))

    grow_names = ["v0_grow"] if args.grow_depth else []   # REALIZED rank of the expanded set
    hits = {v: {k: [] for k in KS} for v in list(variants) + grow_names}
    oracle = {k: [] for k in KS}; expanded = {k: [] for k in KS}
    n_used = 0
    for rec in recs:
        perfile = {v: [] for v in hits}
        goldflat = set(); exp_flat = set()
        used = False
        for repo, commit, issue, gf, sub, gold in iter_files(rec, rows):
            freq = {int(k): float(v) for k, v in sub.get("freq", {}).items()}
            counts = {int(k): int(v) for k, v in sub.get("counts", {}).items()}
            if not freq or not gold:
                continue
            try:
                src = p0.fetch_file(repo, commit, gf)
            except Exception:
                continue
            if args.arise_gold:
                gold = p0.clean_gold(gold, src.splitlines())
                if not gold:
                    continue
            g = cg.CodeGraph(src, gf)
            sc = g.line_scores_v2(issue, use_coverage=False, graded=True) if g.ok else {}
            grown = (rl._expand_voted(g, freq, set(sub.get("region", [])),
                                      depth=args.grow_depth, total_cap=args.grow_cap)
                     if (g.ok and args.grow_depth) else set())
            used = True
            goldflat |= {(gf, ln) for ln in gold}
            exp_flat |= {(gf, ln) for ln in (set(freq) | grown)}     # voted set + def-use growth
            for v, fn in variants.items():
                perfile[v].append([(gf, ln) for ln in fn(freq, sc, counts)])
            if grow_names:                                 # = exactly what live --grow-depth ranks
                ef = dict(freq); base = min(freq.values())
                for ln in grown: ef.setdefault(ln, base * 1e-3)
                perfile["v0_grow"].append([(gf, ln) for ln in rl._rank_v0(ef, sc, counts)])
        if not used:
            continue
        n_used += 1
        voted_flat = {(gf, ln) for L in perfile["vote_only"] for (gf, ln) in L}
        oc = 1 if (voted_flat & goldflat) else 0
        ec = 1 if (exp_flat & goldflat) else 0
        for k in KS:
            oracle[k].append(oc); expanded[k].append(ec)
        for v in hits:
            gl = interleave(perfile[v])
            for k in KS:
                hits[v][k].append(hitk(gl, goldflat, k))

    def Rk(xs):
        return round(100 * st.mean(xs), 1) if xs else None

    print(f"\n==== offline ranking ablation  (n={n_used}, substrate={Path(args.substrate).name}) ====")
    print(f"{'variant':16s} R@1    R@5    R@10")
    print(f"{'ORACLE(set)':16s} {Rk(oracle[1]):<6} {Rk(oracle[5]):<6} {Rk(oracle[10])}   <- rank-free ceiling (voted set)")
    if args.grow_depth:
        print(f"{'EXPANDED(set)':16s} {Rk(expanded[1]):<6} {Rk(expanded[5]):<6} {Rk(expanded[10])}"
              f"   <- voted set + def-use grow (depth={args.grow_depth}, cap={args.grow_cap}) = the Q3 GATE; "
              f"if not > ORACLE, expansion is dead")
    for v in hits:
        tag = "  <- REALIZED expanded rank (= live --grow-depth)" if v == "v0_grow" else ""
        print(f"{v:16s} {Rk(hits[v][1]):<6} {Rk(hits[v][5]):<6} {Rk(hits[v][10])}{tag}")
    print("\nARISE ref        41.0   62.0   74.0")
    out = {"n": n_used, "oracle": {k: Rk(oracle[k]) for k in KS},
           "expanded": ({k: Rk(expanded[k]) for k in KS} if args.grow_depth else None),
           "grow_depth": args.grow_depth, "grow_cap": args.grow_cap,
           "variants": {v: {f"R@{k}": Rk(hits[v][k]) for k in KS} for v in hits}}
    Path("ablation_rank_sweep.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
