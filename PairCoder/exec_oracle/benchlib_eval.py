#!/usr/bin/env python3
"""Generic execution-oracle evaluation for a benchmark library.

Reads a result dir produced by benchlib_generate.py, runs the anchor suite
first (refuses to score models unless the oracle is green), then judges every
saved generation in an isolated subprocess (benchlib_runner.py). Writes
exec_results.csv and a summary sliced by method x pair_type x difficulty.

    python3 benchlib_eval.py --result-dir result/glom_5model
    python3 benchlib_eval.py --result-dir ... --skip-anchors
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import benchlib

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "benchlib_runner.py"


def safe_name(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace(",", "__")


def run_one(lib_name, task_id, gen_path, out_path):
    if not gen_path.exists():
        return {"exec_pass": False, "reason": "harness_error",
                "reason_coarse": "exec_error", "detail": f"missing {gen_path.name}"}
    cmd = [sys.executable, str(RUNNER), "--lib", lib_name, "--task", task_id,
           "--gen", str(gen_path), "--out", str(out_path)]
    try:
        proc = subprocess.run(cmd, cwd=str(HERE), stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, timeout=60)
    except subprocess.TimeoutExpired:
        return {"exec_pass": False, "reason": "timeout",
                "reason_coarse": "exec_error", "detail": "no verdict within 60s"}
    if out_path.exists():
        try:
            return json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"exec_pass": False, "reason": "harness_error", "reason_coarse": "exec_error",
            "detail": f"runner exited {proc.returncode}; stderr: {proc.stderr.decode('utf-8','replace')[-300:]}"}


def majority(flags):
    return (sum(flags) / len(flags) >= 0.5) if flags else False


def evaluate(result_dir: Path, jobs: int):
    config_path = result_dir / "run_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing {config_path}. Generation likely failed before run_config.json was written."
        )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lib_name = config["lib"]
    models, methods = config["models"], config["methods"]
    task_ids, runs = config["tasks"], config.get("runs", 1)
    meta = config.get("task_meta", {})

    out_dir = result_dir / "exec_eval"
    (out_dir / "verdicts").mkdir(parents=True, exist_ok=True)

    items = []
    for run_idx in range(1, runs + 1):
        suffix = "" if runs == 1 else f"_run{run_idx}"
        for model in models:
            for task_id in task_ids:
                for method in methods:
                    name = f"{safe_name(model)}__{task_id}__{method}{suffix}"
                    items.append((run_idx, model, task_id, method, name))

    rows = [None] * len(items)

    def work(idx_item):
        i, (run_idx, model, task_id, method, name) = idx_item
        gen = result_dir / "generations" / f"{name}.py"
        v = run_one(lib_name, task_id, gen, out_dir / "verdicts" / f"{name}.json")
        m = meta.get(task_id, {})
        rows[i] = {
            "run_idx": run_idx, "model": model, "task_id": task_id,
            "pair_type": m.get("pair_type", ""), "difficulty": m.get("difficulty", ""),
            "method": method, "exec_pass": v["exec_pass"],
            "exec_reason": v["reason"], "exec_reason_coarse": v["reason_coarse"],
            "exec_detail": v["detail"], "generation_path": str(gen),
        }

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(work, enumerate(items)))

    with (out_dir / "exec_results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {out_dir/'exec_results.csv'} ({len(rows)} rows)")
    return rows, config


def _rate(rows):
    """task-level majority-vote pass rate over (model, task) groups."""
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["task_id"])].append(bool(r["exec_pass"]))
    groups = list(by.values())
    passed = sum(majority(g) for g in groups)
    return passed, len(groups)


def aggregate(rows, config, result_dir: Path):
    methods = config["methods"]
    out_dir = result_dir / "exec_eval"
    pair_types = sorted({r["pair_type"] for r in rows if r["pair_type"]})
    diffs = ["easy", "medium", "hard"]

    md = [f"# Execution-oracle summary: {config['lib']}", "",
          f"- Models: {', '.join(config['models'])}",
          f"- Tasks: {len(config['tasks'])}; runs/condition: {config.get('runs',1)}",
          "- Pass rate = task-level majority vote across runs, averaged over models.",
          "", "## Pass rate by method", "",
          "| Method | pass | total | rate |", "|---|---:|---:|---:|"]
    for method in methods:
        p, n = _rate([r for r in rows if r["method"] == method])
        md.append(f"| {method} | {p} | {n} | {p/n:.2f} |" if n else f"| {method} | - | 0 | - |")

    md += ["", "## Pass rate by method x pair_type", "",
           "| Method | " + " | ".join(pair_types) + " |",
           "|---|" + "---:|" * len(pair_types)]
    for method in methods:
        cells = []
        for pt in pair_types:
            p, n = _rate([r for r in rows if r["method"] == method and r["pair_type"] == pt])
            cells.append(f"{p/n:.2f}" if n else "-")
        md.append(f"| {method} | " + " | ".join(cells) + " |")

    md += ["", "## Pass rate by method x difficulty", "",
           "| Method | " + " | ".join(diffs) + " |",
           "|---|" + "---:|" * len(diffs)]
    for method in methods:
        cells = []
        for d in diffs:
            p, n = _rate([r for r in rows if r["method"] == method and r["difficulty"] == d])
            cells.append(f"{p/n:.2f}" if n else "-")
        md.append(f"| {method} | " + " | ".join(cells) + " |")

    (out_dir / "exec_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"  wrote {out_dir/'exec_summary.md'}")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-dir", required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--skip-anchors", action="store_true")
    args = ap.parse_args()

    result_dir = Path(args.result_dir).expanduser().resolve()
    config_path = result_dir / "run_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing {config_path}. Run benchlib_generate.py first, or check that the generation step completed."
        )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lib_name = config["lib"]

    if not args.skip_anchors:
        print(f"== anchor suite for {lib_name} (oracle trustworthiness gate) ==")
        if not benchlib.run_anchors(lib_name):
            print("ANCHORS NOT GREEN -- refusing to score models. Fix the oracle first.")
            raise SystemExit(1)
        print()

    print("== evaluating generations ==")
    rows, config = evaluate(result_dir, args.jobs)
    aggregate(rows, config, result_dir)


if __name__ == "__main__":
    main()
