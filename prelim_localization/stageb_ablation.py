#!/usr/bin/env python3
"""stageb_ablation (E6) — LEAVE-ONE-OUT ablation of the Stage-B CONSTRUCTS, to decide which earn
their keep for line recall and which are dead weight ("去掉无用构件"). FILE-GIVEN (the gold file is
handed in) so it isolates Stage-B from the file-finder. Each variant turns ONE construct off from
the full config; a construct whose removal does NOT drop region-ceiling / voted-recall / R@k is
removable.

Metrics per variant:
  reg_ceiling  = |gold ∩ region| / |gold|   (Stage-1: did the construct keep gold IN the region)
  voted_recall = |gold ∩ voted|  / |gold|   (Stage-2: did the construct get gold VOTED)
  R@{1,5,10}   = top-k ranked contains a gold line (downstream effect)

Online (each toggle re-votes) -> run on the FAST AWQ server, moderate n:
  SWEBENCH_DATASET=lite MODEL=Qwen2.5-Coder-32B OPENAI_BASE_URL=http://localhost:8000/v1 \
      OPENAI_API_KEY=dummy python stageb_ablation.py --sample 60 --workers 16
"""
from __future__ import annotations
import argparse, json, os, random, sys, threading
import statistics as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import region_loc as rl

HERE = Path(__file__).resolve().parent
KS = (1, 5, 10)

# Each variant = the FULL Stage-B with ONE construct toggled OFF.
VARIANTS = {
    "full":              {},                       # all constructs on (the shipped Stage-B)
    "no_element_sc":     {"n_elem": 1},            # single element pass (no self-consistency)
    "no_graph_backstop": {"graph_backstop": 0},    # drop graph/coverage function backstop
    "no_module_lines":   {"module_lines": 0},      # drop module-level suspect lines
    "no_small_bypass":   {"small_file": 0},        # always narrow (never hand back the whole small file)
    "no_temp_sched":     {"temp_sched": False},    # all vote samples greedy (kill diversity)
    "k3_samples":        {"k_samples": 3},         # fewer self-consistency samples (5 -> 3)
}
_FIELDS = ["reg_ceiling", "voted_recall"] + [f"R@{k}" for k in KS]


def select_pool(sample):
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    cands = []
    for iid, r in rows.items():
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if not py or len(py) != len([f for f in files if f.endswith(".py")]):
            continue
        if r.get("FAIL_TO_PASS"):
            cands.append(iid)
    random.Random(0).shuffle(cands)
    return rows, cands[:sample]


def hitk(ranked, gold, k):
    return 1 if (set(ranked[:k]) & gold) else 0


def process(model, r):
    """Run every variant on this instance's gold file(s), file-given. Returns {variant: {field: [vals]}}."""
    files = p0.parse_patch(r.get("patch") or "")
    issue = (r.get("problem_statement") or "")[:5000]
    out = {v: {f: [] for f in _FIELDS} for v in VARIANTS}
    for gf in [f for f in files if f.endswith(".py")]:
        gold = files[gf]["region"]
        if not gold:
            continue
        try:
            src = p0.fetch_file(r["repo"], r["base_commit"], gf)
        except Exception:
            continue
        for v, cfg in VARIANTS.items():
            ranked, sub = rl.region_line_loc_ex(model, issue, src, gf, cfg=cfg)
            if sub is None:
                continue
            region = set(sub["region"]); voted = {int(k) for k in sub["freq"]}
            out[v]["reg_ceiling"].append(len(gold & region) / len(gold))
            out[v]["voted_recall"].append(len(gold & voted) / len(gold))
            for k in KS:
                out[v][f"R@{k}"].append(hitk(ranked, gold, k))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--workers", type=int, default=16, help="AWQ has wide KV cache -> push concurrency")
    ap.add_argument("--out", default=str(HERE / "stageb_ablation.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "Qwen2.5-Coder-32B")
    rows, pool = select_pool(args.sample)
    print(f"[E6] {len(pool)} instances x {len(VARIANTS)} variants (file-given, model={model})", file=sys.stderr)

    agg = {v: {f: [] for f in _FIELDS} for v in VARIANTS}
    lock = threading.Lock(); done = [0]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, model, rows[iid]): iid for iid in pool}
        for fut in as_completed(futs):
            try:
                res = fut.result()
            except Exception as e:
                print("ERR", repr(e)[:100], file=sys.stderr); continue
            with lock:
                for v in VARIANTS:
                    for f in _FIELDS:
                        agg[v][f].extend(res[v][f])
                done[0] += 1
                print(f"[{done[0]}/{len(pool)}] {futs[fut]}", file=sys.stderr); sys.stderr.flush()

    def m(xs):
        return round(st.mean(xs), 3) if xs else None
    summary = {v: {f: m(agg[v][f]) for f in _FIELDS} for v in VARIANTS}
    base = summary["full"]
    for v in VARIANTS:
        if v == "full":
            continue
        summary[v]["delta_vs_full"] = {f: (round(summary[v][f] - base[f], 3)
                                       if summary[v][f] is not None and base[f] is not None else None)
                                       for f in _FIELDS}
    Path(args.out).write_text(json.dumps({"n": len(pool), "summary": summary}, indent=2), encoding="utf-8")

    print("\n==== E6 Stage-B construct ablation (file-given) ====", file=sys.stderr)
    print(f"{'variant':18s} regCeil voteRec  R@1    R@5    R@10", file=sys.stderr)
    for v in VARIANTS:
        s = summary[v]
        print(f"{v:18s} {str(s['reg_ceiling']):<7} {str(s['voted_recall']):<7} "
              f"{str(s['R@1']):<6} {str(s['R@5']):<6} {s['R@10']}", file=sys.stderr)
    print("\nRule: delta_vs_full < 0 on regCeil/voteRec/R@k => the removed construct WAS helping (keep);"
          "\n      delta >= 0 => removing it didn't hurt => DEAD WEIGHT, cut it (and save its LLM cost).", file=sys.stderr)


if __name__ == "__main__":
    main()
