#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""RQ3 coverage-REFINE experiment (LLM pipeline, crash·on-path, file-given, ARISE-gold).

Question: off-path is OUT OF SCOPE. On-path the gold line is ALWAYS executed, so a hard
coverage filter is SAFE (no −45 catastrophe) and already strong (RQ3-E1 offline +14pp). The
open question this run answers: on top of the hard filter, can the finer coverage CHANNELS push
the gold line HIGHER inside the executed set (better R@1/R@5) and can conditioning GENERATION on
coverage recover votes a blind vote misses?

Arms (all file-given, same region, ARISE-gold; coverage is the ONLY thing that varies):
  A0 base        : no coverage. Shipped V0 rank on a coverage-BLIND self-consistency vote.
  A1 filter      : A0's ranked list, then HARD-filter to executed lines (the RQ3-E1 +14pp move).
                   >> the baseline the optimized method must beat.
  A2 graded      : filter to executed, then re-rank the survivors by the graded coverage ARM
                   (channel ③ crash-frame proximity + ⑤ cross-sample agreement) instead of V0 order.
  A3 annot       : channel ① — the VOTE prompt marks executed lines (`>`) + prepends the crash
                   traceback (conditions GENERATION), then filter + graded rank.
  A4 revote      : channel ④ — after the annotated vote, narrow to executed top-N and RE-VOTE on
                   that small pool, merge (re-ranked executed head + A3 tail = recall floor).

A2/A3/A4 keep the SAME executed survivor SET as A1 (so R@∞ is identical) — the whole game is
ranking the gold higher WITHIN it, plus (A3/A4) generating better candidates.

Metrics: Line R@{1,5,10} + MRR per arm; paired bootstrap 95% CI of Δ(Ai−A0) and Δ(Ai−A1);
McNemar exact on the discordant pairs; per-arm exec-set gold retention (on-path assumption check);
LLM call count. Per-instance raw hits persisted for recomputation. Resumable vote cache.

  SWEBENCH_DATASET=lite OPENAI_BASE_URL=https://api.siliconflow.cn/v1 \
    OPENAI_API_KEY=... MODEL=deepseek-ai/DeepSeek-V3 \
    python rq3/cov_refine_eval.py --sample 6 --k 5           # smoke
    python rq3/cov_refine_eval.py --k 5                       # full crash_onpath (n=57)
"""
import argparse, json, math, os, re, sys, time
from pathlib import Path
import p0_line_recall as p0
import code_graph as cg
import region_loc as R

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ARMS = ["A0_base", "A1_filter", "A2_graded", "A3_annot", "A4_revote"]
KS = (1, 5, 10)

def crash_context(row, cap=1600):
    """Display traceback for the vote prompt: the Traceback block if present, else the File/line
    frames, else the issue tail. seed_from_traceback is fed the FULL problem_statement separately."""
    ps = row.get("problem_statement") or ""
    m = re.search(r"Traceback \(most recent call last\)", ps)
    if m:
        return ps[m.start():m.start() + cap]
    frames = re.findall(r'File "[^"]+", line \d+[^\n]*', ps)
    if frames:
        return "\n".join(frames[:20])[:cap]
    return ps[-1200:]

def cov_for(f, cm):
    if f in cm: return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()

def hit(rk, gold, k): return 1 if (set(rk[:k]) & gold) else 0
def rr(rk, gold):
    for i, l in enumerate(rk, 1):
        if l in gold: return 1.0 / i
    return 0.0

def frame_lines_of(g, seeds):
    out = set()
    for s in seeds:
        fi = g.line_func.get(s)
        if fi is not None:
            f = g.funcs[fi]; out |= set(range(f["start"], f["end"] + 1))
    return out

def run_instance(model, iid, row, cm, k, lines_cap, cache, calls, lock=None):
    """Return {arm: ranked_lines}, gold, meta — or None to skip."""
    import contextlib
    _lk = lock if lock is not None else contextlib.nullcontext()
    files = p0.parse_patch(row.get("patch") or "")
    gold_files = [f for f in files if f.endswith(".py")]
    if len(gold_files) != 1:
        return None
    gf = gold_files[0]
    try:
        src = p0.fetch_file(row["repo"], row["base_commit"], gf)
    except Exception:
        return None
    lines = src.splitlines()
    gold = p0.clean_gold(files[gf]["region"], lines)      # ARISE-gold
    if not gold:
        return None
    ex = cov_for(gf, cm)
    if not ex:
        return None
    g = cg.CodeGraph(src, gf)
    if not g.ok:
        return None
    issue = (row.get("problem_statement") or "")[:5000]
    crash_ctx = crash_context(row)
    seeds = g.seed_from_traceback(row.get("problem_statement") or "")
    frame_lines = frame_lines_of(g, seeds)
    region = R._make_region(model, issue, src, gf, g, lines, coverage_lines=None, failure="")
    # static graph arm (constant across arms; coverage enters only via the explicit channels)
    scores = g.line_scores_v2(issue, failure="", coverage_lines=None, graded=True, use_coverage=False)

    c = cache.setdefault(iid, {})
    def blind_vote():
        if "blind" not in c:
            f0, ct0 = R._vote(model, issue, gf, lines, region, k, lines_cap)
            with _lk: calls[0] += k
            c["blind"] = {"freq": {int(a): b for a, b in f0.items()},
                          "counts": {int(a): b for a, b in ct0.items()}}
        d = c["blind"]; return {int(a): b for a, b in d["freq"].items()}, {int(a): b for a, b in d["counts"].items()}
    def annot_vote():
        if "annot" not in c:
            f1, ct1 = R._vote(model, issue, gf, lines, region, k, lines_cap,
                              cov_annot=ex, crash_ctx=crash_ctx)
            with _lk: calls[0] += k
            c["annot"] = {"freq": {int(a): b for a, b in f1.items()},
                          "counts": {int(a): b for a, b in ct1.items()}}
        d = c["annot"]; return {int(a): b for a, b in d["freq"].items()}, {int(a): b for a, b in d["counts"].items()}

    out = {}
    # A0 / A1 / A2 share the blind vote
    freq0, counts0 = blind_vote()
    if freq0:
        v0 = R._rank_v0(freq0, scores, counts0)
        out["A0_base"] = v0
        out["A1_filter"] = [l for l in v0 if l in ex]
        freq0_ex = {l: freq0[l] for l in freq0 if l in ex}
        out["A2_graded"] = R._rank_cov(freq0_ex, scores, counts0, ex, frame_lines) if freq0_ex else []
    else:
        out["A0_base"] = out["A1_filter"] = out["A2_graded"] = []
    # A3 annotated vote (channel ①) + filter + graded
    freq1, counts1 = annot_vote()
    if freq1:
        freq1_ex = {l: freq1[l] for l in freq1 if l in ex}
        out["A3_annot"] = R._rank_cov(freq1_ex, scores, counts1, ex, frame_lines) if freq1_ex else []
    else:
        freq1_ex = {}; out["A3_annot"] = []
    # A4 revote (channel ④): narrow to executed top-N of the annotated vote, RE-VOTE on that pool
    if freq1_ex:
        pool = sorted(freq1_ex, key=lambda l: -freq1_ex[l])[:max(8, min(40, len(freq1_ex)))]
        pool_region = set(pool)
        if "revote" not in c:
            f2, ct2 = R._vote(model, issue, gf, lines, pool_region, k, lines_cap,
                              cov_annot=ex, crash_ctx=crash_ctx)
            with _lk: calls[0] += k
            c["revote"] = {"freq": {int(a): b for a, b in f2.items()},
                           "counts": {int(a): b for a, b in ct2.items()}}
        d = c["revote"]; f2 = {int(a): b for a, b in d["freq"].items()}; ct2 = {int(a): b for a, b in d["counts"].items()}
        if f2:
            # RECALL-SAFE fusion: the 2nd-round vote only REWEIGHTS A3's executed survivors (pool ⊆
            # freq1_ex), then rank_cov re-orders the SAME set -> A4 set == A3 set, so R@10 can only
            # move up, never drop (the head+tail replacement could push a survivor past k = a recall
            # regression seen at n=8 on django-11583/astropy-7746; fusion fixes it).
            fused = dict(freq1_ex)
            for l, v in f2.items():
                if l in fused: fused[l] += v
            fused_counts = {l: counts1.get(l, 0) + ct2.get(l, 0) for l in fused}
            out["A4_revote"] = R._rank_cov(fused, scores, fused_counts, ex, frame_lines)
        else:
            out["A4_revote"] = out["A3_annot"]
    else:
        out["A4_revote"] = out["A3_annot"]

    meta = {"gold_in_region": int(bool(gold & region)), "gold_executed": int(bool(gold & ex)),
            "n_region": len(region), "n_exec_in_region": len(region & ex),
            "n_gold": len(gold), "file_lines": len(lines), "n_frame": len(frame_lines)}
    return out, gold, meta

# ------------------------------- stats ----------------------------------------

def bootstrap_ci(deltas, iters=3000):
    if not deltas: return (0.0, 0.0, 0.0)
    import random
    rnd = random.Random(0); n = len(deltas); means = []
    for _ in range(iters):
        s = sum(deltas[rnd.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    return (sum(deltas) / n, means[int(0.025 * iters)], means[int(0.975 * iters)])

def mcnemar(a_hits, b_hits):
    """b beats a discordant counts + exact two-sided binomial p (a=baseline, b=treatment)."""
    b01 = sum(1 for a, b in zip(a_hits, b_hits) if a == 0 and b == 1)   # baseline miss, treatment hit
    b10 = sum(1 for a, b in zip(a_hits, b_hits) if a == 1 and b == 0)
    n = b01 + b10
    if n == 0: return b01, b10, 1.0
    kk = min(b01, b10)
    p = sum(math.comb(n, i) for i in range(kk + 1)) / (2 ** n) * 2
    return b01, b10, min(1.0, p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="first N of crash_onpath (0 = all)")
    ap.add_argument("--workers", type=int, default=1, help="concurrent instances (1 = serial). Instances are independent; cache writes/calls counter are locked.")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--lines-cap", type=int, default=30)
    ap.add_argument("--subset", default="crash_onpath")
    ap.add_argument("--out", default=str(HERE / "cov_refine_result.json"))
    ap.add_argument("--cache", default=str(HERE / "cov_refine_cache.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    base = os.environ.get("OPENAI_BASE_URL", "?")
    subset = json.load(open(ROOT / "rq3_subsets.json"))[args.subset]
    if args.sample: subset = subset[:args.sample]
    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
    cm_all = json.load(open(ROOT / "egl_cov_cache.json"))
    cache = json.loads(Path(args.cache).read_text()) if Path(args.cache).exists() else {}

    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    per = []            # per-instance {iid, meta, hits{arm:{k:0/1}}, rr{arm}}
    calls = [0]
    lock = threading.Lock()
    t0 = time.time()
    done = [0]

    def work(n, iid):
        row = rows.get(iid); cm = cm_all.get(iid)
        if not row or not cm:
            return ("skip", n, iid, "no row/cov")
        try:
            r = run_instance(model, iid, row, cm, args.k, args.lines_cap, cache, calls, lock)
        except Exception as e:
            return ("error", n, iid, f"{type(e).__name__}: {str(e)[:120]}")
        if r is None:
            return ("skip", n, iid, "gold/cov")
        out, gold, meta = r
        rec = {"instance_id": iid, "meta": meta, "hits": {}, "rr": {}}
        for arm in ARMS:
            rk = out.get(arm, [])
            rec["hits"][arm] = {k: hit(rk, gold, k) for k in KS}
            rec["rr"][arm] = round(rr(rk, gold), 4)
        with lock:
            per.append(rec)
            Path(args.cache).write_text(json.dumps(cache))     # resumable
            done[0] += 1
        return ("ok", n, iid, rec)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(work, n, iid) for n, iid in enumerate(subset, 1)]
        for fut in as_completed(futs):
            status, n, iid, payload = fut.result()
            if status == "ok":
                a1 = payload["hits"]["A1_filter"]; a4 = payload["hits"]["A4_revote"]; m = payload["meta"]
                print(f"[{done[0]}/{len(subset)}] {iid:32s} A1@1/5/10={a1[1]}{a1[5]}{a1[10]} "
                      f"A4@1/5/10={a4[1]}{a4[5]}{a4[10]} | region={m['n_region']} exec={m['n_exec_in_region']} "
                      f"calls={calls[0]} {int(time.time()-t0)}s", file=sys.stderr)
            else:
                print(f"[--] {iid}  {status.upper()} ({payload})", file=sys.stderr)
            sys.stderr.flush()

    # ---- aggregate ----
    N = len(per)
    def rate(arm, k): return round(100 * sum(x["hits"][arm][k] for x in per) / N, 1) if N else 0.0
    def mrr(arm): return round(sum(x["rr"][arm] for x in per) / N, 3) if N else 0.0
    summary = {"model": model, "base_url": base, "subset": args.subset, "n": N, "k": args.k,
               "llm_calls": calls[0], "arms": {}}
    for arm in ARMS:
        summary["arms"][arm] = {**{f"R@{k}": rate(arm, k) for k in KS}, "MRR": mrr(arm),
                                "exec_retention": round(100 * sum(
                                    1 for x in per if x["hits"][arm][10] or not x["meta"]["gold_executed"]) / N, 1) if N else 0}
    # paired deltas + CI + McNemar vs A0 and vs A1
    comps = {}
    for base_arm in ("A0_base", "A1_filter"):
        for arm in ARMS:
            if arm == base_arm: continue
            for k in KS:
                d = [x["hits"][arm][k] - x["hits"][base_arm][k] for x in per]
                mean, lo, hi = bootstrap_ci(d)
                b01, b10, pmc = mcnemar([x["hits"][base_arm][k] for x in per],
                                        [x["hits"][arm][k] for x in per])
                comps[f"{arm}−{base_arm}@{k}"] = {"delta_pp": round(100 * mean, 1),
                    "CI95": [round(100 * lo, 1), round(100 * hi, 1)], "sig": (lo > 0 or hi < 0),
                    "mcnemar": {"base_miss_treat_hit": b01, "base_hit_treat_miss": b10, "p": round(pmc, 4)}}
    summary["paired"] = comps
    Path(args.out).write_text(json.dumps({"summary": summary, "per_instance": per}, indent=2), encoding="utf-8")

    print("\n==== COVERAGE-REFINE (crash·on-path, file-given, ARISE-gold) ====")
    print(f"model={model}  n={N}  k={args.k}  llm_calls={summary['llm_calls']}")
    hdr = f"{'arm':<12}{'R@1':>7}{'R@5':>7}{'R@10':>7}{'MRR':>8}"
    print(hdr); print("-" * len(hdr))
    for arm in ARMS:
        a = summary["arms"][arm]
        print(f"{arm:<12}{a['R@1']:>7}{a['R@5']:>7}{a['R@10']:>7}{a['MRR']:>8}")
    print("\nΔ vs A1_filter (does the finer method beat the naive on-path filter?)  * = CI excludes 0")
    for arm in ("A2_graded", "A3_annot", "A4_revote"):
        for k in KS:
            c = comps[f"{arm}−A1_filter@{k}"]
            star = " *" if c["sig"] else ""
            print(f"  {arm}@{k}: {c['delta_pp']:+.1f}pp  CI{c['CI95']}  McNemar p={c['mcnemar']['p']}"
                  f" ({c['mcnemar']['base_miss_treat_hit']}↑/{c['mcnemar']['base_hit_treat_miss']}↓){star}")
    print("\nΔ vs A0_base (does coverage help the full LLM pipeline at all — RQ3-E4)")
    for arm in ("A1_filter", "A4_revote"):
        for k in KS:
            c = comps[f"{arm}−A0_base@{k}"]; star = " *" if c["sig"] else ""
            print(f"  {arm}@{k}: {c['delta_pp']:+.1f}pp  CI{c['CI95']}{star}")
    print(f"\nwritten: {args.out}")

if __name__ == "__main__":
    main()
