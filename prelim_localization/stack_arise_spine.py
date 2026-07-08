#!/usr/bin/env python3
"""stack_arise_spine — THE decisive experiment: does SPINE STACK on a strong baseline (ARISE)?

Feed a baseline's per-instance ranked (file,function,line) top-k; rerank its #1 file's line order by
SPINE's assertion signal (recall-safe head-only reorder); score baseline vs baseline+SPINE vs
baseline+RANDOM (control) under the OFFICIAL ARISE metrics (arise.eval); paired McNemar on line R@1.

INPUT --preds JSON = {iid: [[file, function, line], ...]}  (rank order, most-suspicious first):
  - REAL ARISE:  python -c "from evaluation.parse_preds import load_predictions_from_dir as L; import json; \
                   json.dump({k:[list(t) for t in v] for k,v in L('outputs/condfull-fl').items()}, open('arise_preds.json','w'))"
  - PROXY (validation): build from an egl_e2e run's ranks dump — see --from-run below.

SAME-MODEL is load-bearing: run ARISE and this rerank with the SAME backbone (MODEL env), else a gain
is 'bigger reranker' not 'assertion signal'. Endpoint via OPENAI_BASE_URL/OPENAI_API_KEY. No GPU, no Docker.

OUTCOME (green-light): baseline+SPINE line R@1 - baseline >= +? with McNemar p<.05, discordant>=8,
AND baseline+SPINE > baseline+random (proves it's the assertion signal, not any reshuffle).
"""
import sys, json, math, argparse, random, os, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "vendor" / "ARISE" / "src"))
import p0_line_recall as p0
import test_evidence as te
import region_loc as rl
from arise.eval import gold as ag
from arise.eval import metrics as am


def build_proxy_from_run(run_json, arm, out_json):
    """Make an ARISE-format preds file {iid:[[file,func,line],...]} from an egl_e2e --dump-ranks run's arm."""
    preds = {}
    for r in json.load(open(run_json)).get("results", []):
        ranks = r.get("ranks")
        if ranks and arm in ranks:
            preds[r["instance_id"]] = [[f, "", int(ln)] for f, ln in ranks[arm]]
    json.dump(preds, open(out_json, "w"))
    return len(preds)


def _files_in_order(triples):
    seen, out = set(), []
    for f, _, _ in triples:
        if f not in seen:
            seen.add(f); out.append(f)
    return out


def rerank(triples, mode, model, issue, row, top_n):
    """mode: none (baseline, unchanged) | spine (assertion rerank of #1 file's head) | random (shuffle #1 head)."""
    if mode == "none" or not triples:
        return [(f, fn, int(ln)) for f, fn, ln in triples]
    files = _files_in_order(triples)
    top_file = files[0]
    head_lines = [int(ln) for f, _, ln in triples if f == top_file]           # #1 file's lines, rank order
    other = [(f, fn, int(ln)) for f, fn, ln in triples if f != top_file]      # keep tail as-is
    func_of = {(f, int(ln)): fn for f, fn, ln in triples}
    if mode == "random":
        h, rest = head_lines[:top_n], head_lines[top_n:]
        seed = int.from_bytes(hashlib.md5(row["instance_id"].encode()).digest()[:4], "big")  # reproducible
        rng = random.Random(seed); h = h[:]; rng.shuffle(h)
        new_head = h + rest
    else:  # spine
        try:
            lines = p0.fetch_file(row["repo"], row["base_commit"], top_file).splitlines()
        except Exception:
            return [(f, fn, int(ln)) for f, fn, ln in triples]
        ev = te.extract_test_evidence(row)
        new_head = rl.assertion_rerank(model, issue, top_file, lines, head_lines, ev, top_n=top_n)
    return [(top_file, func_of.get((top_file, ln), ""), ln) for ln in new_head] + other


def mcnemar(pairs):
    w = sum(1 for a, b in pairs if a and not b); l = sum(1 for a, b in pairs if b and not a); d = w + l
    p = 1.0 if d == 0 else min(1.0, 2 * sum(math.comb(d, i) for i in range(min(w, l) + 1)) / (2 ** d))
    return w, l, d, round(p, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", help="ARISE-format {iid:[[file,func,line],...]} baseline top-k")
    ap.add_argument("--from-run", help="build proxy preds from this egl_e2e --dump-ranks run instead")
    ap.add_argument("--arm", default="vote_only", help="which arm to use as proxy baseline (with --from-run)")
    ap.add_argument("--dataset", default="lite")
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(HERE / "runs" / "stack_arise_spine.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")

    preds_path = args.preds
    if args.from_run:
        preds_path = str(HERE / "runs" / f"proxy_{args.arm}.json")
        n = build_proxy_from_run(args.from_run, args.arm, preds_path)
        print(f"[proxy] built {n} baseline preds from {Path(args.from_run).name} arm={args.arm}", file=sys.stderr)
    preds = json.load(open(preds_path))
    rows = {r["instance_id"]: r for r in p0.load_rows(500, args.dataset)}
    ids = [i for i in preds if i in rows]
    if args.limit:
        ids = ids[:args.limit]
    golds = {i: ag.parse_gold(rows[i].get("patch") or "") for i in ids}

    from concurrent.futures import ThreadPoolExecutor
    ARMS = {"baseline": "none", "baseline+SPINE": "spine", "baseline+random": "random"}
    scored = {a: {} for a in ARMS}

    def work(iid):
        row = rows[iid]; issue = row.get("problem_statement") or ""
        base = [(t[0], t[1] if len(t) > 2 else "", int(t[-1])) for t in preds[iid]]
        return iid, {a: rerank(base, m, model, issue, row, args.top_n) for a, m in ARMS.items()}

    Path(args.out).parent.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        done = 0
        for iid, arms in ex.map(work, ids):
            for a in ARMS:
                scored[a][iid] = arms[a]
            done += 1
            if done % 20 == 0:
                print(f"  reranked {done}/{len(ids)}", file=sys.stderr)
    json.dump({"model": model, "scored_ids": ids}, open(args.out, "w"), indent=1)

    print(f"\nn={len(golds)}  model={model}  top_n={args.top_n}")
    print(f"{'arm':18} {'lineR@1':>8} {'lineR@5':>8} {'lineR@10':>9}")
    hit1 = {}
    for a in ARMS:
        pr = {i: scored[a][i] for i in golds if i in scored[a]}
        res = am.compute_all_metrics(pr, {i: golds[i] for i in pr})
        print(f"{a:18} {100*res['line_recall@1']:8.1f} {100*res['line_recall@5']:8.1f} {100*res['line_recall@10']:9.1f}")
        hit1[a] = {i: int(am.line_recall_at_k(pr[i], golds[i], 1)) for i in pr}
    print("  -- paired line R@1 --")
    for base in ("baseline", "baseline+random"):
        pairs = [(hit1["baseline+SPINE"][i], hit1[base][i]) for i in hit1["baseline+SPINE"] if i in hit1[base]]
        w, l, d, pv = mcnemar(pairs)
        dl = 100 * (sum(a for a, _ in pairs) - sum(b for _, b in pairs)) / len(pairs)
        print(f"  SPINE vs {base:16}: Δ={dl:+.1f}pp  {w}W/{l}L disc={d} p={pv}")


if __name__ == "__main__":
    main()
