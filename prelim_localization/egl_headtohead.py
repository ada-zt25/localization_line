#!/usr/bin/env python3
"""egl_headtohead — the MAKE-OR-BREAK equal-recall head-to-head (RP next-step #1), rebuilt to
the adversarial-review spec (every ranker scores the byte-identical RR-voted set drawn once,
ARISE is steelmanned and coverage-clean, and every verdict is a PAIRED per-instance bootstrap).

Two phases:
  VOTE  (LLM, once, resumable): per (instance, gold file) build Stage-A region + ONE RR-vote
        (region_loc.region_substrate) + the whole-file baseline ranked list; PERSIST all of it.
  RERANK (offline, recomputed every run from the persisted substrate — NO LLM): apply six
        orderings/prunings of the identical voted set and score them with honest paired stats.

Orderings of the IDENTICAL voted set (so set-recall is provably equal; only ORDER differs):
  vote_only : voted set by RR-vote mass alone        (does the LLM vote ALONE rank well?)
  arise     : voted set by a COVERAGE-FREE, GRADED ARISE def-use-slice score (line_scores_v2,
              use_coverage=False) — the steelmanned static slice, NO LLM vote.
  v0 (ours) : RRF(vote_rank, graph_rank) where graph = line_scores_v2 (+coverage when --exec).
              V0 = vote ⊕ ARISE-signal, so it is the FUSION; the scientific test is vote_only
              vs arise (does the vote beat the slice?), with V0 shown to do >= both.
Different-set baselines (NOT equal-recall — recall differs by construction):
  arise_std : standalone ARISE — rank the WHOLE FILE by the graded static score, top |v0|
              (its OWN candidate selection, no LLM vote): what the static slice recalls alone.
  sieve_fn  : V0 hard-filtered to lines whose enclosing function was EXECUTED (lenient).
  sieve_ln  : V0 hard-filtered to EXECUTED STATEMENTS only (strict line-level coverage prune).

Honest metrics (review fixes): global R@k by ROUND-ROBIN interleave across gold files (not
first-file-dominated concat); EFFECTIVE recall denominator (only files actually scored); PAIRED
per-instance delta bootstrap (CI + P(d>0)) for every verdict — "wins" only when the paired CI
excludes 0; the non-degradation GATE compares V0 against the whole-file baseline on the PAIRED
subset of files where a baseline exists (files >4000 lines are excluded from BOTH, and counted).

    OPENAI_BASE_URL=https://api.siliconflow.com/v1 MODEL=deepseek-ai/DeepSeek-V3 \
        python egl_headtohead.py --sample 13 --k 3            # vote + V0/vote/ARISE + gate (no Docker)
        python egl_headtohead.py --sample 13 --k 3 --exec     # + SieveFL (Docker coverage, cached)
        python egl_headtohead.py --sample 13 --rerank-only    # re-score from persisted substrate, no LLM
"""
from __future__ import annotations
import argparse, json, os, sys, random
from pathlib import Path
import p0_line_recall as p0
import code_graph as cg
import region_loc as rl
from hybrid_loop import _llm, RANK_PROMPT, parse_ranked

HERE = Path(__file__).resolve().parent
PY = {"astropy/astropy", "scikit-learn/scikit-learn", "pydata/xarray",
      "psf/requests", "matplotlib/matplotlib", "pallets/flask"}
KS = (1, 5, 10)
EQUAL_RECALL = ["v0", "vote_only", "arise"]          # share the voted set => identical recall
DIFF_SET = ["arise_std", "sieve_fn", "sieve_ln"]     # different set => recall differs
VARIANTS = EQUAL_RECALL + DIFF_SET
BASELINE_MAXLINES = 4000
COV_CACHE = HERE / "egl_cov_cache.json"


def select_pool(sample, broad=False, min_file_lines=0):
    """IDENTICAL selection to region_loc.main (same instances as region_loc_v0.json):
    PY-repo multi-file Python edits with FAIL_TO_PASS, Random(0)-shuffled, first `sample`."""
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    cands = []
    for iid, r in rows.items():
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if not py or len(py) != len([f for f in files if f.endswith(".py")]):
            continue
        if broad:
            cands.append(iid)
        elif r["repo"] in PY and len(py) >= 2 and r.get("FAIL_TO_PASS"):
            cands.append(iid)
    random.Random(0).shuffle(cands)
    if min_file_lines:
        kept = []
        for iid in cands:
            r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
            for gf in [f for f in files if f.endswith(".py")]:
                try:
                    if len(p0.fetch_file(r["repo"], r["base_commit"], gf).splitlines()) > min_file_lines:
                        kept.append(iid); break
                except Exception:
                    pass
            if len(kept) >= sample:
                break
        cands = kept
    return rows, cands[:sample]


def load_cov(iid, r, want_exec):
    """Per-file executed lines from Docker coverage (cached in egl_cov_cache.json)."""
    cache = json.loads(COV_CACHE.read_text()) if COV_CACHE.exists() else {}
    if iid in cache:
        return {f: set(v) for f, v in cache[iid].items()}
    if not want_exec:
        return {}
    import hybrid_loop_v2 as v2
    _called, exec_lines = v2.run_coverage(iid, r, [])
    cache[iid] = {f: sorted(v) for f, v in exec_lines.items()}
    COV_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return exec_lines


# ----------------------------- offline rankers -------------------------------

def _tiebreak(ln):
    """Deterministic, line-POSITION-decorrelated tiebreak (Knuth multiplicative hash) so
    zero-score voted lines aren't ordered by an arbitrary ascending line index — the review's
    'arise tie-break by line number flatters V0' artifact."""
    return (ln * 2654435761) % (2 ** 32)


def _rrf(freq, scores, K=30):
    voted = list(freq)
    vr = {ln: i for i, ln in enumerate(sorted(voted, key=lambda k: (-freq[k], _tiebreak(k))))}
    gr = {ln: i for i, ln in enumerate(sorted(voted, key=lambda k: (-scores.get(k, 0.0), _tiebreak(k))))}
    return sorted(voted, key=lambda ln: -(1.0 / (K + vr[ln]) + 1.0 / (K + gr[ln])))


def rank_all(g, issue, freq, region, cov):
    """Six orderings/prunings of the voted set (offline; no LLM). `cov` = executed line set."""
    freq = {int(k): v for k, v in freq.items()}
    voted = list(freq)
    sc_static = g.line_scores_v2(issue, use_coverage=False, graded=True)            # ARISE: pure static
    sc_v0 = g.line_scores_v2(issue, coverage_lines=cov, use_coverage=bool(cov), graded=True)  # V0 graph(+cov)
    vote_only = sorted(voted, key=lambda l: (-freq[l], _tiebreak(l)))
    arise = sorted(voted, key=lambda l: (-sc_static.get(l, 0.0), _tiebreak(l)))
    v0 = _rrf(freq, sc_v0) if freq else []
    arise_std = sorted(sc_static.keys(), key=lambda l: (-sc_static[l], _tiebreak(l)))[:max(1, len(v0))]
    exec_funcs = {i for i, f in enumerate(g.funcs) if cov & set(range(f["start"], f["end"] + 1))}
    def _fn_exec(ln):
        fi = g.line_func.get(ln); return (fi in exec_funcs) or (ln in cov)
    if cov:
        sieve_fn = [l for l in v0 if _fn_exec(l)]
        sieve_ln = [l for l in v0 if l in cov]
    else:                                          # no coverage -> sieve is a no-op (== v0 set)
        sieve_fn = sieve_ln = list(v0)
    n_zero = sum(1 for l in voted if sc_static.get(l, 0.0) == 0.0)
    return ({"v0": v0, "vote_only": vote_only, "arise": arise, "arise_std": arise_std,
             "sieve_fn": sieve_fn, "sieve_ln": sieve_ln},
            {"n_voted": len(voted), "n_zero_score_voted": n_zero})


def interleave(per_file):
    """Round-robin merge of per-file ranked (gf, line) lists, so global top-k spans files
    instead of being dominated by whichever gold file parse_patch emitted first."""
    out = []; i = 0
    while any(i < len(L) for L in per_file):
        for L in per_file:
            if i < len(L):
                out.append(L[i])
        i += 1
    return out


def hitk(global_list, goldflat, k):
    return 1 if (set(global_list[:k]) & goldflat) else 0


# ----------------------------- statistics ------------------------------------

def boot_ci(xs, nboot=5000):
    if not xs: return (None, None)
    if len(xs) == 1: return (round(xs[0], 3), round(xs[0], 3))
    rng = random.Random(12345); n = len(xs)
    means = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(nboot))
    return (round(means[int(0.025 * nboot)], 3), round(means[int(0.975 * nboot)], 3))


def paired_delta(a, b, nboot=5000):
    """PAIRED bootstrap of mean(a_i - b_i): the honest test (uses pairing, not two marginal
    CIs). 'sig' True iff the 95% CI excludes 0."""
    d = [x - y for x, y in zip(a, b)]
    if not d: return None
    n = len(d); mean = sum(d) / n
    if n == 1:
        return {"mean": round(mean, 3), "ci": [round(mean, 3), round(mean, 3)],
                "p_gt0": 1.0 if mean > 0 else 0.0, "sig": False, "n": 1}
    rng = random.Random(777)
    means = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(nboot))
    lo, hi = means[int(0.025 * nboot)], means[int(0.975 * nboot)]
    return {"mean": round(mean, 3), "ci": [round(lo, 3), round(hi, 3)],
            "p_gt0": round(sum(1 for m in means if m > 0) / nboot, 3),
            "sig": bool(lo > 0 or hi < 0), "n": n}


# ----------------------------- driver ----------------------------------------

def vote_phase(rows, pool, model, k, want_exec, want_baseline, out, results, by_id):
    """Ensure every instance has its persisted LLM substrate (region + freq + baseline)."""
    for idx, iid in enumerate(pool):
        rec = by_id.get(iid)
        if rec and rec.get("substrate_done"):
            print(f"{iid} substrate cached", file=sys.stderr); continue
        r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
        gold_files = [f for f in files if f.endswith(".py")]
        issue = (r.get("problem_statement") or "")[:5000]
        rec = {"instance_id": iid, "repo": r["repo"], "n_gold_files": len(gold_files), "files": {}}
        for gf in gold_files:
            try: src = p0.fetch_file(r["repo"], r["base_commit"], gf)
            except Exception: continue
            lines = src.splitlines()
            sub = rl.region_substrate(model, issue, src, gf, k_samples=k)
            if sub is None: continue               # unparseable file
            wp = []
            if want_baseline and len(lines) <= BASELINE_MAXLINES:
                numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))
                try: wp = parse_ranked(_llm(model, RANK_PROMPT.format(issue=issue, path=gf, numbered=numbered)))
                except Exception: wp = []
            rec["files"][gf] = {"n_gold": len(files[gf]["region"]), "file_lines": len(lines),
                                "region": sub["region"], "freq": sub["freq"], "baseline_wp": wp,
                                "baseline_skipped": len(lines) > BASELINE_MAXLINES}
        rec["substrate_done"] = True; by_id[iid] = rec; results[:] = list(by_id.values())
        out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
        print(f"[vote {idx+1}/{len(pool)}] {iid:30s} files={len(rec['files'])}", file=sys.stderr); sys.stderr.flush()


def rerank_phase(rows, results, want_exec):
    """Recompute every metric from the persisted substrate (offline; no LLM)."""
    per = {iid: {} for iid in [r["instance_id"] for r in results]}
    for rec in results:
        iid = rec["instance_id"]; r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
        issue = (r.get("problem_statement") or "")[:5000]
        cov_map = load_cov(iid, r, want_exec)
        rec["has_cov"] = bool(cov_map)
        gold_files = [f for f in files if f.endswith(".py")]
        scored_gold = 0; ceil_sum = 0.0; n_scored_files = 0
        eq_ok = True; n_zero = 0; n_voted = 0
        perfile = {v: [] for v in VARIANTS}; base_perfile = []; v0_gate_perfile = []
        goldflat = set(); goldflat_base = set()
        n_base_skip = 0; gold_in_skip = 0
        sieve_drop_fn = sieve_drop_ln = 0; covered_gold = 0
        for gf in gold_files:
            sub = rec["files"].get(gf)
            if not sub:                            # file was skipped in vote phase
                continue
            gf_gold = files[gf]["region"]
            try: src = p0.fetch_file(r["repo"], r["base_commit"], gf)
            except Exception: continue
            g = cg.CodeGraph(src, gf)
            if not g.ok: continue
            cov = set(cov_map.get(gf, set()))
            ranked, diag = rank_all(g, issue, sub["freq"], set(sub["region"]), cov)
            n_scored_files += 1; scored_gold += len(gf_gold)
            ceil_sum += (len(set(sub["region"]) & gf_gold) / len(gf_gold)) if gf_gold else 0.0
            n_voted += diag["n_voted"]; n_zero += diag["n_zero_score_voted"]
            # equal-recall invariant (per file): the three EQUAL_RECALL sets must be identical
            if not (set(ranked["v0"]) == set(ranked["vote_only"]) == set(ranked["arise"])):
                eq_ok = False
            for v in VARIANTS:
                perfile[v].append([(gf, ln) for ln in ranked[v]])
            goldflat |= {(gf, ln) for ln in gf_gold}
            # SieveFL recall loss (only on covered files, against the v0 set)
            if cov:
                v0set = set(ranked["v0"])
                sieve_drop_fn += len((v0set - set(ranked["sieve_fn"])) & gf_gold)
                sieve_drop_ln += len((v0set - set(ranked["sieve_ln"])) & gf_gold)
                covered_gold += len(v0set & gf_gold)
            # whole-file baseline (paired subset: only files with a real baseline)
            if not sub.get("baseline_skipped"):
                base_perfile.append([(gf, ln) for ln in sub.get("baseline_wp", [])])
                v0_gate_perfile.append([(gf, ln) for ln in ranked["v0"]])
                goldflat_base |= {(gf, ln) for ln in gf_gold}
            else:
                n_base_skip += 1; gold_in_skip += len(gf_gold)
        if n_scored_files == 0:
            per[iid] = None; continue
        m = {}
        for v in VARIANTS:
            gl = interleave(perfile[v])
            # recall = predicted gold lines / scored gold (effective denominator)
            pred_gold = sum(len({ln for (gf2, ln) in L if (gf2, ln) in goldflat}) for L in perfile[v])
            m[v] = {"recall": round(pred_gold / scored_gold, 4) if scored_gold else 0.0,
                    **{f"R@{k}": hitk(gl, goldflat, k) for k in KS}}
        # gate metrics on the baseline-present subset
        base_gl = interleave(base_perfile); v0_gate_gl = interleave(v0_gate_perfile)
        base_pred = sum(len({ln for (gf2, ln) in L if (gf2, ln) in goldflat_base}) for L in base_perfile)
        v0g_pred = sum(len({ln for (gf2, ln) in L if (gf2, ln) in goldflat_base}) for L in v0_gate_perfile)
        gate = {"n_base_skip": n_base_skip, "gold_in_skip": gold_in_skip,
                "whole_recall": round(base_pred / max(1, sum(len(files[gf]['region']) for gf in gold_files
                                       if rec['files'].get(gf) and not rec['files'][gf].get('baseline_skipped'))), 4),
                "v0_recall": round(v0g_pred / max(1, sum(len(files[gf]['region']) for gf in gold_files
                                   if rec['files'].get(gf) and not rec['files'][gf].get('baseline_skipped'))), 4),
                **{f"whole_R@{k}": hitk(base_gl, goldflat_base, k) for k in KS},
                **{f"v0gate_R@{k}": hitk(v0_gate_gl, goldflat_base, k) for k in KS}}
        rec["metrics"] = {"scored_gold": scored_gold, "n_scored_files": n_scored_files,
                          "region_ceiling": round(ceil_sum / n_scored_files, 3),
                          "equal_recall_ok": eq_ok, "n_voted": n_voted, "n_zero_score_voted": n_zero,
                          "variants": m, "gate": gate,
                          "sieve_drop_fn": sieve_drop_fn, "sieve_drop_ln": sieve_drop_ln,
                          "covered_gold": covered_gold}
        per[iid] = rec["metrics"]
    return per


def summarize(results, out, want_baseline):
    import statistics as st
    ok = [r for r in results if r.get("metrics")]
    M = {r["instance_id"]: r["metrics"] for r in ok}
    cov_ids = [r["instance_id"] for r in ok if r.get("has_cov")]
    def col(v, key, ids=None):
        ids = ids or list(M)
        return [M[i]["variants"][v][key] for i in ids if v in M[i]["variants"]]
    def mean(xs): return round(st.mean(xs), 3) if xs else None
    table = {}
    for v in VARIANTS:
        ids = cov_ids if v in ("sieve_fn", "sieve_ln") else list(M)
        rec = col(v, "recall", ids)
        table[v] = {"n": len(ids), "recall": mean(rec), "recall_ci95": boot_ci(rec),
                    "R@k": {k: (round(100 * st.mean(col(v, f"R@{k}", ids)), 1) if col(v, f"R@{k}", ids) else None) for k in KS}}
    # ---- PAIRED delta verdicts (the only honest comparison) ----
    def pair(va, vb, ids):
        out_p = {"recall": paired_delta(col(va, "recall", ids), col(vb, "recall", ids))}
        for k in KS:
            out_p[f"R@{k}"] = paired_delta(col(va, f"R@{k}", ids), col(vb, f"R@{k}", ids))
        return out_p
    allids = list(M)
    paired = {
        "vote_only_minus_arise": pair("vote_only", "arise", allids),   # does the LLM vote beat the static slice?
        "v0_minus_arise": pair("v0", "arise", allids),                 # fusion vs static (partly mechanical)
        "v0_minus_vote_only": pair("v0", "vote_only", allids),         # does graph add over vote alone?
    }
    if cov_ids:
        paired["v0_minus_sieve_ln"] = pair("v0", "sieve_ln", cov_ids)  # re-rank vs strict hard-filter
        paired["v0_minus_sieve_fn"] = pair("v0", "sieve_fn", cov_ids)  # re-rank vs lenient hard-filter
    eq_all = all(M[i]["equal_recall_ok"] for i in M)
    summary = {"n": len(ok), "n_with_cov": len(cov_ids),
               "equal_recall_invariant_holds": eq_all,
               "region_ceiling": mean([M[i]["region_ceiling"] for i in M]),
               "n_voted_mean": round(st.mean([M[i]["n_voted"] for i in M]), 1) if M else None,
               "zero_score_voted_frac": round(sum(M[i]["n_zero_score_voted"] for i in M) /
                                              max(1, sum(M[i]["n_voted"] for i in M)), 3),
               "variants": table, "paired": paired}
    if cov_ids:
        cg_ = [M[i] for i in cov_ids]
        summary["sieve"] = {
            "n_with_cov": len(cov_ids),
            "covered_gold_total": sum(m["covered_gold"] for m in cg_),
            "sieve_ln_gold_dropped": sum(m["sieve_drop_ln"] for m in cg_),
            "sieve_fn_gold_dropped": sum(m["sieve_drop_fn"] for m in cg_),
            "sieve_ln_recall": table["sieve_ln"]["recall"], "sieve_fn_recall": table["sieve_fn"]["recall"],
            "v0_recall_on_cov": mean(col("v0", "recall", cov_ids))}
    if want_baseline:
        gates = [M[i]["gate"] for i in M]
        wr = [g["whole_recall"] for g in gates]; vr = [g["v0_recall"] for g in gates]
        summary["gate"] = {
            "n_files_baseline_skipped": sum(g["n_base_skip"] for g in gates),
            "gold_in_skipped_files": sum(g["gold_in_skip"] for g in gates),
            "whole_recall_paired": mean(wr), "v0_recall_paired": mean(vr),
            "v0_minus_whole_recall_paired": paired_delta(vr, wr),
            "whole_R@k": {k: round(100 * st.mean([g[f"whole_R@{k}"] for g in gates]), 1) for k in KS},
            "v0_R@k_on_baseline_subset": {k: round(100 * st.mean([g[f"v0gate_R@{k}"] for g in gates]), 1) for k in KS},
            "v0_minus_whole_R@k_paired": {k: paired_delta([g[f"v0gate_R@{k}"] for g in gates],
                                                          [g[f"whole_R@{k}"] for g in gates]) for k in KS}}
    d = json.loads(out.read_text()); d["summary"] = summary
    out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== HEAD-TO-HEAD SUMMARY (LINE recall, file given) ====\n" +
          json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=13)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--exec", dest="want_exec", action="store_true", help="Docker coverage for SieveFL")
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("--rerank-only", action="store_true", help="recompute metrics from substrate, no LLM")
    ap.add_argument("--broad", action="store_true")
    ap.add_argument("--min-file-lines", type=int, default=0)
    ap.add_argument("--out", default=str(HERE / "egl_headtohead.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    rows, pool = select_pool(args.sample, args.broad, args.min_file_lines)
    out = Path(args.out)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    by_id = {r["instance_id"]: r for r in results}
    print(f"[h2h] {len(pool)} instances; k={args.k} exec={args.want_exec} "
          f"baseline={not args.no_baseline} rerank_only={args.rerank_only}", file=sys.stderr)
    if not args.rerank_only:
        vote_phase(rows, pool, model, args.k, args.want_exec, not args.no_baseline, out, results, by_id)
    results = list(by_id.values())
    rerank_phase(rows, results, args.want_exec)
    by_id = {r["instance_id"]: r for r in results}
    out.write_text(json.dumps({"results": list(by_id.values())}, indent=2), encoding="utf-8")
    summarize(list(by_id.values()), out, not args.no_baseline)


if __name__ == "__main__":
    main()
