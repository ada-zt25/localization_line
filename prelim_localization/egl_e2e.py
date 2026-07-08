#!/usr/bin/env python3
"""egl_e2e — end-to-end file-NOT-given line localization, ARISE-aligned:
    STRONG file retrieval front-end (file_localize)  x  TUNED region line localization (region_loc)
on the SINGLE+MULTI mixed pool (ARISE/SWE-bench-Lite style, not multi-file-only). Replaces the weak
ReAct file-finder (egl_agentic, file_recall 0.47) with a strong retrieval front-end so the end-to-end
shows "strong file-finding x our strong line-loc". No Docker (file-not-given via repo tree + fetch).

Reports, ARISE-口径:
  - File Recall@k    (instance-level: top-k candidate files contain >=1 gold file) + gold-file recall
  - Line Recall@k    (instance-level: top-k predicted lines, round-robin interleaved across files)
  - line fraction-recall (global + conditional on found gold files = the line-loc step isolated)
  - paired vs a whole-file (no-narrowing) baseline + bootstrap CIs

    OPENAI_BASE_URL=... MODEL=deepseek-ai/DeepSeek-V3 python egl_e2e.py --sample 50 --k 5 --topk 10
"""
from __future__ import annotations
import argparse, json, os, sys, random, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import p1_realistic as p1
import region_loc as rl
import file_localize as fl
import code_graph as cg
import test_evidence as te
import statistics as st
from hybrid_loop import _llm, RANK_PROMPT, parse_ranked

HERE = Path(__file__).resolve().parent
PY = {"astropy/astropy", "scikit-learn/scikit-learn", "pydata/xarray",
      "psf/requests", "matplotlib/matplotlib", "pallets/flask"}
KS = (1, 5, 10)
AKS = (1, 3, 5, 10)                              # richer k-grid for the per-arm line-loc decomposition
# The 5 line-loc arms, ALL produced from ONE LLM vote pass per file (+1 final-pick on the headline):
#   arise_static     = ARISE's pure static def-use-slice ranking over the file (no vote, no coverage) = the baseline
#   vote_only        = our LLM self-consistency vote, ranked by vote-mass only (no graph, no coverage)
#   ours_static      = vote + STATIC graph(def-use slice) + consensus, NO coverage (our static half)
#   ours_dynamic_nofp= vote + COVERAGE-aware graph + consensus (our full static+dynamic, before final-pick)
#   ours_dynamic     = ours_dynamic_nofp + LLM final-pick head re-rank (the shipped headline)
ARMS = ["arise_static", "vote_only", "ours_static", "ours_dynamic_nofp", "ours_dynamic"]
BASELINE_MAXLINES = 4000


def _arm_metrics(per_file, goldflat, tot_gold):
    """line R@{1,3,5,10} + recall/precision/F1 + raw hits for one arm's interleaved (file,line) ranking."""
    gl = interleave(per_file)
    hits = len(set(gl) & goldflat)
    n_pred = sum(len(L) for L in per_file)
    R = hits / tot_gold if tot_gold else 0.0
    P = hits / n_pred if n_pred else 0.0
    m = {f"R@{kk}": hitk(gl, goldflat, kk) for kk in AKS}
    m.update({"recall": round(R, 3), "precision": round(P, 3),
              "f1": round(2 * P * R / (P + R), 3) if (P + R) else 0.0, "n_pred": n_pred, "hits": hits})
    return m


def select_pool_mixed(sample, broad=False):
    """SINGLE+MULTI mixed pool (ARISE/Lite-style): PY-repo instances whose gold edits are ALL Python
    (1 OR MORE files) with a FAIL_TO_PASS. (broad=all repos.) Random(0)-shuffled, first `sample`."""
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    cands = []
    for iid, r in rows.items():
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if not py or len(py) != len([f for f in files if f.endswith(".py")]):
            continue                                   # skip non-Python edits
        if (broad or r["repo"] in PY) and r.get("FAIL_TO_PASS"):
            cands.append(iid)                          # NOTE: len(py)>=1 -> single AND multi-file
    random.Random(0).shuffle(cands)
    return rows, cands[:sample]


def interleave(per_file):
    out = []; i = 0
    while any(i < len(L) for L in per_file):
        for L in per_file:
            if i < len(L): out.append(L[i])
        i += 1
    return out

def hitk(gl, gold, k): return 1 if (set(gl[:k]) & gold) else 0

def boot_ci(xs, nboot=5000):
    if not xs: return (None, None)
    if len(xs) == 1: return (round(xs[0], 3), round(xs[0], 3))
    rng = random.Random(12345); n = len(xs)
    means = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(nboot))
    return (round(means[int(0.025 * nboot)], 3), round(means[int(0.975 * nboot)], 3))

def paired_delta(a, b):
    d = [x - y for x, y in zip(a, b)]
    if not d: return None
    n = len(d); mean = sum(d) / n
    if n == 1: return {"mean": round(mean, 3), "ci": [round(mean, 3)] * 2, "p_gt0": 1.0 if mean > 0 else 0.0, "sig": False, "n": 1}
    rng = random.Random(777)
    means = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(5000))
    lo, hi = means[int(0.025 * 5000)], means[int(0.975 * 5000)]
    return {"mean": round(mean, 3), "ci": [round(lo, 3), round(hi, 3)],
            "p_gt0": round(sum(1 for m in means if m > 0) / 5000, 3), "sig": bool(lo > 0 or hi < 0), "n": n}


class FatalAPIError(Exception):
    """Account balance / auth failure — stop the whole run (don't churn)."""


def process_instance(model, r, topk, k, lines_cap, baseline, rank_mode="v0", final_pick=0, dump=False,
                     cov_cache=None, file_rerank=0, file_loc="agentless", arise_turns=8, reuse_files=None,
                     cfg=None, arise_gold=False, assert_rerank=0, dump_ranks=False, spine_votebase=False):
    """All work for ONE instance (strong file-find + tuned region line-loc + optional baseline).
    Thread-safe: only reads shared state, returns its own rec. Raises FatalAPIError on 403/balance.
    rank_mode/final_pick select the Stage-B ranker (R@1 ablation); dump persists the per-file
    substrate (region+freq+counts+gold) into rec for free offline ranking sweeps.
    cov_cache (the DYNAMIC half): {iid: {file: [executed lines]}} from failing-test Docker coverage;
    when present its lines are threaded into region_line_loc_ex -> the delta*covered graph term, the
    rank_functions '+1.5 executed' boost, and the module-line coverage boost all fire (un-dormants Q3).
    file_rerank>0: LLM listwise re-rank of the top-N candidate files for ARISE-parity file R@1."""
    iid = r["instance_id"]; files = p0.parse_patch(r.get("patch") or "")
    gold_files = [f for f in files if f.endswith(".py")]
    gold = {f: files[f]["region"] for f in gold_files}
    if arise_gold:                                       # Lever 1: ARISE-aligned gold (drop blank/comment anchors)
        for f in gold_files:
            try: gold[f] = p0.clean_gold(gold[f], p0.fetch_file(r["repo"], r["base_commit"], f).splitlines())
            except Exception: pass
    tot_gold = sum(len(v) for v in gold.values())
    issue = (r.get("problem_statement") or "")[:5000]
    cov_map = {f: set(v) for f, v in (cov_cache or {}).get(iid, {}).items()}
    rec = {"instance_id": iid, "repo": r["repo"], "n_gold_files": len(gold_files), "tot_gold": tot_gold,
           "has_cov": bool(cov_map)}
    try:
        if reuse_files is not None and reuse_files.get(iid):   # reuse a prior run's file-loc (coverage-independent)
            ranked_files = reuse_files[iid]
        else:                                                  # Agentless single-shot (+ optional LLM rerank)
            ranked_files = fl.localize_files(model, r["repo"], r["base_commit"], issue, topk=topk)
            if file_rerank and ranked_files:                   # ARISE-parity file R@1 lever
                try:
                    ranked_files = fl.llm_file_rerank(model, r["repo"], r["base_commit"], issue,
                                                      ranked_files, top_n=file_rerank)
                except Exception:
                    pass
    except Exception as e:
        msg = repr(e)
        if "403" in msg or "balance" in msg.lower() or "401" in msg:
            raise FatalAPIError(msg)
        rec["error"] = f"filefind:{msg}"[:140]; return rec     # NOT done -> re-runs
    found = [f for f in gold_files if f in ranked_files]
    rec["ranked_files"] = ranked_files[:topk]
    rec["file_recall"] = round(len(found) / len(gold_files), 3) if gold_files else 0.0
    rec.update({f"file_R@{kk}": (1 if set(ranked_files[:kk]) & set(gold_files) else 0) for kk in KS})
    LCAP = 60                                                  # per-file cap for the rank-only arms
    arm_per = {a: [] for a in ARMS}
    whole_per = []; whole_hit = 0
    gold_in_found = sum(len(gold[f]) for f in found)
    reg_ceils = []; voted_ceils = []; cov_gold_hits = 0; cov_gold_tot = 0
    found_sizes = []; nbypass = 0; cov_files_found = 0
    m5_per = []                                                # M5: assertion-grounded rerank of the cov-narrowed ranking
    m5v_per = []                                               # M5-votebase: SAME rerank on the coverage-FREE vote list (isolates the assertion signal from coverage)
    rank_dump = {}                                             # per-arm (file,line) rankings for auditability (--dump-ranks)
    ev = te.extract_test_evidence(r) if assert_rerank else ""  # the signal orthogonal to coverage
    for f in found:
        try: src = p0.fetch_file(r["repo"], r["base_commit"], f)
        except Exception: continue
        flines = src.splitlines(); found_sizes.append(len(flines))
        gf = gold.get(f, set())
        cl = cov_map.get(f); cl_set = set(cl) if cl else set()
        if cl_set: cov_files_found += 1
        # ONE LLM vote pass (coverage-aware) -> the dynamic-pre-finalpick ranking + the substrate
        rp, sub = rl.region_line_loc_ex(model, issue, src, f, coverage_lines=(sorted(cl_set) if cl_set else None),
                                        k_samples=k, lines_cap=lines_cap, rank_mode="v0", cfg=cfg)
        if dump and sub is not None:
            sub["gold"] = sorted(gf); sub["file_lines"] = len(flines)
            rec.setdefault("substrate", {})[f] = sub
        if sub is None:                                        # graph unparseable -> skip this file
            continue
        freq = {int(x): float(v) for x, v in sub["freq"].items()}
        counts = {int(x): int(v) for x, v in sub["counts"].items()}
        region = set(sub["region"])
        g = cg.CodeGraph(src, f)
        gstat = g.line_scores_v2(issue, graded=True, use_coverage=False) if g.ok else {}
        gcov = (g.line_scores_v2(issue, coverage_lines=sorted(cl_set), graded=True, use_coverage=True)
                if (g.ok and cl_set) else gstat)
        # 5 arms — all FREE given the vote; only ours_dynamic spends 1 final-pick call
        a_arise = sorted(gstat, key=lambda l: (-gstat[l], rl._tiebreak(l)))[:LCAP]   # ARISE pure static slice
        a_vote = sorted(freq, key=lambda l: (-freq[l], rl._tiebreak(l))) if freq else []
        a_ourstat = rl._rank_v0(dict(freq), gstat, counts) if freq else []
        a_dynnofp = rp                                         # = _rank_v0(freq, gcov, counts)
        a_dyn = (rl.llm_final_pick(model, issue, f, flines, a_dynnofp, top_n=final_pick)
                 if (final_pick and a_dynnofp) else a_dynnofp)
        for a, ranked in zip(ARMS, [a_arise, a_vote, a_ourstat, a_dynnofp, a_dyn]):
            arm_per[a].append([(f, ln) for ln in ranked])
        a_m5 = a_m5v = []                                      # reset per file (avoid stale carry-over on multi-file instances)
        if assert_rerank and a_dynnofp:                        # M5 = rerank the cov-aware ranking by test evidence
            a_m5 = rl.assertion_rerank(model, issue, f, flines, a_dynnofp, ev, top_n=assert_rerank)
            m5_per.append([(f, ln) for ln in a_m5])
        if assert_rerank and spine_votebase and a_vote:        # M5-votebase = SAME rerank on the coverage-FREE vote list
            a_m5v = rl.assertion_rerank(model, issue, f, flines, a_vote, ev, top_n=assert_rerank)
            m5v_per.append([(f, ln) for ln in a_m5v])
        if dump_ranks:                                         # persist the actual head rankings (audit rank-1 pick vs gold/evidence)
            for a, ranked in (("arise_static", a_arise), ("vote_only", a_vote), ("ours_static", a_ourstat),
                              ("ours_dynamic_nofp", a_dynnofp), ("ours_m5", a_m5), ("ours_m5_votebase", a_m5v)):
                if ranked:
                    rank_dump.setdefault(a, []).extend([[f, int(ln)] for ln in ranked[:15]])
        if gf:
            reg_ceils.append(len(gf & region) / len(gf))
            voted_ceils.append(len(gf & set(freq)) / len(gf))
            cov_gold_hits += len(gf & cl_set); cov_gold_tot += len(gf)
        if len(flines) <= 500: nbypass += 1
        if baseline:                                           # optional whole-file (no-narrowing) arm
            if len(flines) <= BASELINE_MAXLINES:
                numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(flines))
                try: wp = parse_ranked(_llm(model, RANK_PROMPT.format(issue=issue, path=f, numbered=numbered), timeout=120, retries=2))
                except Exception: wp = []
            else: wp = []
            whole_per.append([(f, ln) for ln in wp]); whole_hit += len(set(wp) & gf)
    goldflat = {(f, ln) for f in gold_files for ln in gold[f]}
    rec["arms"] = {a: _arm_metrics(arm_per[a], goldflat, tot_gold) for a in ARMS}
    if assert_rerank and m5_per:                               # M5 arm (only present when --assert-rerank set)
        rec["arms"]["ours_m5"] = _arm_metrics(m5_per, goldflat, tot_gold)
    if assert_rerank and spine_votebase and m5v_per:           # coverage-neutral SPINE arm (rerank of vote_only)
        rec["arms"]["ours_m5_votebase"] = _arm_metrics(m5v_per, goldflat, tot_gold)
    if dump_ranks and rank_dump:
        rec["ranks"] = rank_dump; rec["gold_flat"] = sorted([f, int(ln)] for f, ln in goldflat)
    dyn = rec["arms"]["ours_dynamic"]                          # headline = full dynamic+static method
    rec["line_recall"] = dyn["recall"]; rec["line_precision"] = dyn["precision"]
    rec["line_f1"] = dyn["f1"]; rec["n_pred"] = dyn["n_pred"]
    rec["line_recall_given_found"] = round(dyn["hits"] / gold_in_found, 3) if gold_in_found else 0.0
    rec.update({f"line_R@{kk}": dyn[f"R@{kk}"] for kk in KS})  # legacy fields for monitoring/back-compat
    # diagnostics for post-run method reflection
    rec["n_found"] = len(found); rec["found_file_lines"] = found_sizes
    rec["cov_files_found"] = cov_files_found; rec["small_bypass_files"] = nbypass
    rec["reg_ceiling"] = round(st.mean(reg_ceils), 3) if reg_ceils else None
    rec["voted_ceiling"] = round(st.mean(voted_ceils), 3) if voted_ceils else None
    rec["cov_on_gold_recall"] = round(cov_gold_hits / cov_gold_tot, 3) if cov_gold_tot else None
    if baseline:
        rec["whole_line_recall"] = round(whole_hit / tot_gold, 3) if tot_gold else 0.0
        rec.update({f"whole_line_R@{kk}": hitk(interleave(whole_per), goldflat, kk) for kk in KS})
    rec["done"] = True
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--k", type=int, default=5, help="region_loc self-consistency samples (Stage-B tuned)")
    ap.add_argument("--lines-cap", type=int, default=30, help="max lines per vote sample (Stage-B tuned)")
    ap.add_argument("--topk", type=int, default=10, help="candidate files kept from the file-finder")
    ap.add_argument("--workers", type=int, default=8, help="parallel instances (API calls are I/O-bound)")
    ap.add_argument("--baseline", action="store_true", help="paired whole-file (no-narrowing) baseline")
    ap.add_argument("--broad", action="store_true")
    ap.add_argument("--rank-mode", default="v0", choices=["v0", "counts"], help="Stage-B ranker (R@1 ablation)")
    ap.add_argument("--final-pick", type=int, default=0, help="top-N LLM final re-rank for R@1 (0=off)")
    ap.add_argument("--dump-substrate", action="store_true", help="persist region+freq+counts+gold per file for free offline ranking sweeps")
    ap.add_argument("--coverage", action="store_true", help="ACTIVATE the DYNAMIC half: collect failing-test execution coverage (Docker) and thread it into line-loc (un-dormants the Q3 coverage signal)")
    ap.add_argument("--cov-workers", type=int, default=4, help="parallel Docker workers for the coverage pre-pass (peak disk ~= this many SWE-bench images; raise if disk+bandwidth allow)")
    ap.add_argument("--prefetch-coverage", action="store_true", help="ONLY run the Docker coverage pre-pass (populate egl_cov_cache.json) then exit — run this in parallel with a no-coverage LLM run to overlap Docker(本机) with GPU(tunnel); the later --coverage run then finds all coverage cached")
    ap.add_argument("--file-loc", default="agentless", choices=["agentless"], help="file-finder front-end: 'agentless' (single-shot LLM + optional --file-rerank). [The blind ARISE reimpl front-end was retired 2026-07-08 — ARISE is now open-source (github.com/FARD-Lab/ARISE); use the official repo for the ARISE baseline.]")
    ap.add_argument("--arise-turns", type=int, default=8, help="(arise file-loc) max agent turns per instance — lower = fewer LLM calls = faster (default 8; the agent usually localizes in 3-6)")
    ap.add_argument("--file-rerank", type=int, default=0, help="(agentless only) LLM listwise re-rank of the top-N candidate files for ARISE-parity file R@1 (0=off)")
    ap.add_argument("--reuse-files", default="", help="path to a prior egl_e2e output json; reuse its per-instance ranked_files and SKIP the file-finder (file-loc is coverage-independent, so the static & dynamic ablation arms share ONE ARISE-agent file-loc run)")
    ap.add_argument("--grow-depth", type=int, default=0, help="(Q3 line-loc) def-use slice EXPANSION depth of the voted set (0=off); grows the candidate set with data-flow neighbors of voted lines to raise voted_ceiling (the diagnosed bottleneck). VALIDATE OFFLINE FIRST via ablation_rank_sweep.py --grow-depth before trusting.")
    ap.add_argument("--grow-cap", type=int, default=25, help="(Q3) max grown lines added per file by --grow-depth")
    ap.add_argument("--vote-unfiltered", action="store_true", help="(Q3 line-loc) admit in-FILE votes just outside the shown region (off-by-a-few neighbors) into the candidate set")
    ap.add_argument("--arise-gold", action="store_true", help="(Lever 1) ARISE-aligned gold: drop blank/comment insertion-anchor lines from the gold set — raises the region ceiling 0.795->~0.90 AND matches ARISE's口径 (it excludes blank lines) instead of grading ourselves harder. Apply to ALL arms; report with/without.")
    ap.add_argument("--small-file", type=int, default=500, help="(Lever 2) whole-file (no narrowing) threshold; raise (e.g. 1800) so most files use the whole executable file as the region -> code-gold region recall ~1.0 (narrowing was costing ~10pts)")
    ap.add_argument("--max-region", type=int, default=0, help="(Lever 2) override max region lines (0=keep 900); raise so whole-file regions aren't truncated by graph score")
    ap.add_argument("--all-module-lines", action="store_true", help="(Lever 2) include EVERY module-level code line in the region (recovers the module-level gold -- imports/class-body/decorators, ~1 in 11 gold lines -- the top-12 heuristic misses)")
    ap.add_argument("--out", default=str(HERE / "egl_e2e.json"))
    ap.add_argument("--instances", default="", help="(RQ4) path to a JSON list of instance_ids OR a comma list; "
                    "overrides the --sample pool so a run targets the FROZEN subset (e.g. rq4 S1 crash·on-path)")
    ap.add_argument("--cov-narrow", action="store_true", help="(RQ4 M2) restrict the region shown to the LLM vote "
                    "to EXECUTED lines only (coverage-narrowed vote) — the one untested lever vs the offline filter ceiling")
    ap.add_argument("--assert-rerank", type=int, default=0, help="(RQ4 M5) assertion-grounded rerank of the top-N "
                    "cov-narrowed candidates: reason BACKWARD from the failing test's expected-vs-observed evidence "
                    "(the signal orthogonal to coverage) to pinpoint the root-cause line (targets R@1/R@5). 0=off")
    ap.add_argument("--spine-votebase", action="store_true", help="also emit 'ours_m5_votebase': the SAME assertion "
                    "rerank applied to the coverage-FREE vote_only list — isolates the assertion signal from coverage "
                    "(the fair-baseline SPINE effect; requires --assert-rerank)")
    ap.add_argument("--dump-ranks", action="store_true", help="persist per-instance head (file,line) rankings for each "
                    "arm + gold_flat, so the actual rank-1 pick can be audited vs gold/evidence offline")
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    rows, pool = select_pool_mixed(args.sample, args.broad)
    if args.instances:                                   # RQ4: target an explicit frozen instance list
        rows = {r["instance_id"]: r for r in p0.load_rows(500)}
        if args.instances.endswith(".json"):
            doc = json.loads(Path(args.instances).read_text())
            ids = doc if isinstance(doc, list) else doc.get("instances", [])
        else:
            ids = [s for s in args.instances.split(",") if s]
        pool = [iid for iid in ids if iid in rows]
        print(f"[instances] frozen pool: {len(pool)} instances from {args.instances}", file=sys.stderr)
    if args.cov_narrow:
        args.coverage = True                             # M2 needs coverage; force the DYNAMIC half on
    out = Path(args.out)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    by_id = {r["instance_id"]: r for r in results}
    todo = [iid for iid in pool if not by_id.get(iid, {}).get("done")]
    print(f"[e2e] {len(pool)} mixed instances ({len(todo)} to run); k={args.k} cap={args.lines_cap} "
          f"topk={args.topk} workers={args.workers} file_loc={args.file_loc} coverage={args.coverage} "
          f"file_rerank={args.file_rerank}", file=sys.stderr)

    # DYNAMIC half: PARALLEL Docker coverage pre-pass -> egl_cov_cache.json (so the LLM run below only
    # does thread-safe cache READS). run_coverage cleans up its image+container per instance (finally:
    # rm+rmi), so peak disk = ~cov_workers images. Cache written after every completion = crash-resumable.
    cov_cache = {}
    if args.coverage or args.prefetch_coverage:
        import cov_collect as cc                              # repo-aware (django runtests.py + pytest)
        cov_path = HERE / "egl_cov_cache.json"
        cov_cache = json.loads(cov_path.read_text()) if cov_path.exists() else {}
        miss = [iid for iid in todo if not cov_cache.get(iid)]   # re-try empties (old pytest-only failures)
        print(f"[cov] pre-pass: {len(miss)} instances needing coverage x {args.cov_workers} Docker workers "
              f"(DYNAMIC half; cache={cov_path.name})", file=sys.stderr)
        def _collect(iid):
            try:
                exec_lines = cc.collect(iid, rows[iid])
                return iid, {f: sorted(v) for f, v in exec_lines.items()}
            except Exception as e:
                return iid, ("ERR", repr(e)[:80])
        if miss:
            clock = threading.Lock(); cdone = [0]
            with ThreadPoolExecutor(max_workers=args.cov_workers) as cex:
                for fut in as_completed([cex.submit(_collect, iid) for iid in miss]):
                    iid, res = fut.result()
                    with clock:
                        cdone[0] += 1
                        if isinstance(res, dict):
                            cov_cache[iid] = res
                        cov_path.write_text(json.dumps(cov_cache, indent=2), encoding="utf-8")
                        nf = len(res) if isinstance(res, dict) else 0
                        nl = sum(len(v) for v in res.values()) if isinstance(res, dict) else 0
                        print(f"[cov {cdone[0]}/{len(miss)}] {iid:30s} files={nf} exec_lines={nl}"
                              + ("" if isinstance(res, dict) else f" {res}"), file=sys.stderr); sys.stderr.flush()
        ncov = sum(1 for iid in pool if cov_cache.get(iid))
        print(f"[cov] DYNAMIC half ON: {ncov}/{len(pool)} instances have failing-test coverage", file=sys.stderr)
        if args.prefetch_coverage:
            print(f"[cov] prefetch-only complete ({ncov}/{len(pool)} cached); skipping LLM run.", file=sys.stderr)
            return
    else:
        print("[WARN] --coverage OFF: the DYNAMIC half is DORMANT — this is a STATIC-only run, NOT the "
              "full dynamic+static method. Pass --coverage for the real method.", file=sys.stderr)

    reuse_files = None
    if args.reuse_files:
        rf = json.loads(Path(args.reuse_files).read_text())
        reuse_files = {r["instance_id"]: r["ranked_files"] for r in rf.get("results", []) if r.get("ranked_files")}
        print(f"[reuse] loaded file-loc for {len(reuse_files)} instances from "
              f"{Path(args.reuse_files).name} (file-finder skipped where available)", file=sys.stderr)

    cfg = {}                                            # Q3 line-loc set-expansion + region knobs (default OFF)
    if args.grow_depth:
        cfg["grow_depth"] = args.grow_depth; cfg["grow_cap"] = args.grow_cap
    if args.vote_unfiltered:
        cfg["vote_unfiltered"] = True
    if args.small_file != 500:                          # Lever 2: bigger whole-file region
        cfg["small_file"] = args.small_file
    if args.max_region:
        cfg["max_region_lines"] = args.max_region
    if args.all_module_lines:
        cfg["all_module"] = True
    if args.cov_narrow:                                  # RQ4 M2: coverage-narrowed vote region
        cfg["cov_narrow"] = True
    if cfg:
        print(f"[Q3] line-loc knobs ON (cfg={cfg}) — validate offline first via ablation_rank_sweep.py!", file=sys.stderr)
    if args.arise_gold:
        print("[Lever1] ARISE-aligned gold ON (blank/comment anchors dropped from gold set)", file=sys.stderr)

    lock = threading.Lock(); progress = [len(pool) - len(todo)]
    ex = ThreadPoolExecutor(max_workers=args.workers)
    futs = {ex.submit(process_instance, model, rows[iid], args.topk, args.k, args.lines_cap, args.baseline,
                      args.rank_mode, args.final_pick, args.dump_substrate, cov_cache, args.file_rerank,
                      args.file_loc, args.arise_turns, reuse_files, cfg, args.arise_gold, args.assert_rerank,
                      args.dump_ranks, args.spine_votebase): iid
            for iid in todo}
    try:
        for fut in as_completed(futs):
            iid = futs[fut]
            try:
                rec = fut.result()
            except FatalAPIError as e:
                print(f"\nABORT: API balance/auth error ({repr(e)[:60]}) — top up, then re-run (resumes).", file=sys.stderr)
                ex.shutdown(wait=False, cancel_futures=True); break
            except Exception as e:
                rec = {"instance_id": iid, "repo": rows[iid]["repo"], "error": repr(e)[:140]}
            with lock:
                by_id[iid] = rec; progress[0] += 1
                out.write_text(json.dumps({"results": list(by_id.values())}, indent=2), encoding="utf-8")
                _a = (rec.get("arms") or {})
                print(f"[{progress[0]}/{len(pool)}] {iid:30s} file_rec={rec.get('file_recall')} "
                      f"cov={1 if rec.get('has_cov') else 0} line_R@5 "
                      f"arise={_a.get('arise_static', {}).get('R@5')} ours={_a.get('ours_dynamic', {}).get('R@5')}",
                      file=sys.stderr); sys.stderr.flush()
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    summarize(list(by_id.values()), out, args.baseline)


def summarize(results, out, baseline):
    import statistics as st
    ok = [r for r in results if r.get("done") and "line_recall" in r]
    def m(k): xs = [r[k] for r in ok if r.get(k) is not None]; return round(st.mean(xs), 3) if xs else None
    def Rk(k): xs = [r[k] for r in ok if r.get(k) is not None]; return round(100 * st.mean(xs), 1) if xs else None
    summary = {
        "n": len(ok),
        "n_with_coverage": sum(1 for r in ok if r.get("has_cov")),   # DYNAMIC half activation (0 => coverage dormant)
        "file_recall_gold": m("file_recall"), "file_R@k": {k: Rk(f"file_R@{k}") for k in KS},
        "line_recall": m("line_recall"), "line_recall_ci": boot_ci([r["line_recall"] for r in ok]),
        "line_recall_given_found_files": m("line_recall_given_found"),
        "line_precision": m("line_precision"), "line_precision_ci": boot_ci([r.get("line_precision", 0) for r in ok]),
        "line_f1": m("line_f1"), "n_pred_mean": m("n_pred"),
        "line_R@k": {k: Rk(f"line_R@{k}") for k in KS},
        "swe_contextbench_ref": {"gpt5_prometheus_recall": ">0.60", "precision": "<0.35", "f1": "<0.40"},
        "arise_ref_line_R@k": {1: 41, 5: 62, 10: 74},
        "arise_ref_file_R@1": 67,
    }
    if baseline and any("whole_line_recall" in r for r in ok):
        summary["whole_line_recall"] = m("whole_line_recall")
        summary["whole_line_R@k"] = {k: Rk(f"whole_line_R@{k}") for k in KS}
        summary["region_minus_whole_recall_paired"] = paired_delta(
            [r["line_recall"] for r in ok if "whole_line_recall" in r],
            [r["whole_line_recall"] for r in ok if "whole_line_recall" in r])

    # ---- line-loc ARM DECOMPOSITION (the headline: ARISE-static vs our dynamic, same file-loc) ----
    okA = [r for r in ok if r.get("arms")]
    if okA:
        def aRk(a, k): xs = [r["arms"][a][f"R@{k}"] for r in okA]; return round(100 * st.mean(xs), 1) if xs else None
        def aM(a, key): xs = [r["arms"][a][key] for r in okA]; return round(st.mean(xs), 3) if xs else None
        def pdelta(a, b):                                      # per-instance paired delta a-b on line R@{1,5,10}
            return {k: paired_delta([r["arms"][a][f"R@{k}"] for r in okA],
                                    [r["arms"][b][f"R@{k}"] for r in okA]) for k in KS}
        summary["line_loc_arms"] = {a: {**{f"R@{k}": aRk(a, k) for k in AKS},
                                        "recall": aM(a, "recall"), "precision": aM(a, "precision"), "f1": aM(a, "f1")}
                                    for a in ARMS}
        summary["headline_us_vs_arise"] = {
            "ours_dynamic_line_R@k": {k: aRk("ours_dynamic", k) for k in KS},
            "arise_static_line_R@k": {k: aRk("arise_static", k) for k in KS},
            "arise_ref_line_R@k": {1: 41, 5: 62, 10: 74},
            "delta_ours_minus_arise_static": pdelta("ours_dynamic", "arise_static"),
        }
        summary["ablation_paired_deltas_R@k"] = {
            "coverage_effect__dyn_minus_ourstatic": pdelta("ours_dynamic_nofp", "ours_static"),
            "finalpick_effect__dyn_minus_dynnofp": pdelta("ours_dynamic", "ours_dynamic_nofp"),
            "vote+graph_vs_ariseStatic__ourstatic_minus_arise": pdelta("ours_static", "arise_static"),
            "vote_vs_ariseStatic__voteonly_minus_arise": pdelta("vote_only", "arise_static"),
        }
        flines_all = [x for r in okA for x in (r.get("found_file_lines") or [])]
        summary["diagnostics"] = {
            "reg_ceiling": m("reg_ceiling"), "voted_ceiling": m("voted_ceiling"),
            "cov_on_gold_recall": m("cov_on_gold_recall"),
            "cov_files_found_mean": m("cov_files_found"), "n_found_mean": m("n_found"),
            "small_bypass_files_mean": m("small_bypass_files"),
            "found_file_lines_median": round(st.median(flines_all), 1) if flines_all else None,
        }
    d = json.loads(out.read_text()); d["summary"] = summary
    out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== E2E SUMMARY (file-NOT-given, ARISE-aligned) ====\n" +
          json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
