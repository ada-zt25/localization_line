#!/usr/bin/env python3
"""Execution-based re-evaluation of the simplug existence experiment (P1).

Replaces the circular static AST oracle with execution-based hidden tests:

  1. ANCHORING (--anchors-only, and always run first): canonical solutions,
     semantically-equivalent variants (which the static checker wrongly
     rejects) and constraint-violating solutions are executed against the
     hidden tests; the suite must behave exactly as documented before any
     model output is judged.
  2. EVALUATION: every saved generation from the original run is executed
     in an isolated subprocess and judged by the hidden tests.
  3. COMPARISON: run-level confusion matrix static-vs-execution, agreement
     rate, Cohen's kappa, and a disagreement listing for error analysis.

Usage:
    python3 run_exec_eval.py                  # anchors + full evaluation
    python3 run_exec_eval.py --anchors-only   # just the anchoring suite
    python3 run_exec_eval.py --result-dir ../result/simplug_7b_5model_comparison
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "exec_runner.py"
DEFAULT_RESULT_DIR = HERE.parent / "result" / "simplug_7b_5model_comparison"
TIMEOUT_SEC = 60


def safe_name(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace(",", "__")


def run_one(task_id: str, gen_path: Path, out_path: Path) -> dict:
    """Invoke exec_runner.py in a subprocess; return its verdict dict."""
    cmd = [
        sys.executable,
        str(RUNNER),
        "--task",
        task_id,
        "--gen",
        str(gen_path),
        "--out",
        str(out_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(HERE),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return {
            "exec_pass": False,
            "reason": "timeout",
            "reason_coarse": "exec_error",
            "detail": f"no verdict within {TIMEOUT_SEC}s",
            "per_value": [],
        }
    if out_path.exists():
        try:
            return json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "exec_pass": False,
        "reason": "harness_error",
        "reason_coarse": "exec_error",
        "detail": (
            f"runner exited {proc.returncode} without verdict; "
            f"stderr: {proc.stderr.decode('utf-8', 'replace')[-400:]}"
        ),
        "per_value": [],
    }


# ---------------------------------------------------------------------------
# Anchoring suite
# ---------------------------------------------------------------------------


def run_anchors(verbose: bool = True) -> bool:
    from anchor_solutions import ANCHORS

    tmp = Path(tempfile.mkdtemp(prefix="paircoder_anchors_"))
    rows, ok_all = [], True
    for task_id, cases in sorted(ANCHORS.items()):
        for name, code, expectation in cases:
            gen = tmp / f"{task_id}__{name}.py"
            gen.write_text(code, encoding="utf-8")
            verdict = run_one(task_id, gen, tmp / f"{task_id}__{name}.json")
            if expectation is True:
                ok = verdict["exec_pass"]
                expected_str = "PASS"
            else:
                ok = (not verdict["exec_pass"]) and verdict["reason"] in expectation
                expected_str = f"FAIL({'|'.join(sorted(expectation))})"
            got_str = "PASS" if verdict["exec_pass"] else f"FAIL({verdict['reason']})"
            ok_all &= ok
            rows.append((task_id, name, expected_str, got_str, ok, verdict["detail"]))

    if verbose:
        width = max(len(r[1]) for r in rows)
        print("\n== Anchoring suite (oracle validity) ==")
        for task_id, name, exp, got, ok, detail in rows:
            mark = "ok " if ok else "XXX"
            print(f"  [{mark}] {task_id}  {name:<{width}}  expected={exp:<28} got={got}")
            if not ok:
                print(f"        detail: {detail}")
        n_ok = sum(1 for r in rows if r[4])
        print(f"  -> {n_ok}/{len(rows)} anchor cases behave as documented\n")

    (HERE / "anchor_report.json").write_text(
        json.dumps(
            [
                {
                    "task_id": t,
                    "case": n,
                    "expected": e,
                    "got": g,
                    "ok": o,
                    "detail": d,
                }
                for t, n, e, g, o, d in rows
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return ok_all


# ---------------------------------------------------------------------------
# Full evaluation of saved generations
# ---------------------------------------------------------------------------


def load_static_results(result_dir: Path) -> dict:
    static = {}
    csv_path = result_dir / "pair_violation_results.csv"
    if not csv_path.exists():
        return static
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (
                row["model"],
                row["task_id"],
                row["method"],
                int(row.get("run_idx", 1) or 1),
            )
            static[key] = row
    return static


def evaluate_all(result_dir: Path, jobs: int) -> list[dict]:
    config = json.loads((result_dir / "run_config.json").read_text(encoding="utf-8"))
    models, methods = config["models"], config["methods"]
    task_ids, runs = config["tasks"], config.get("runs", 1)
    task_meta = config.get("task_meta", {})
    static = load_static_results(result_dir)

    out_dir = result_dir / "exec_eval"
    (out_dir / "verdicts").mkdir(parents=True, exist_ok=True)

    items = []
    for run_idx in range(1, runs + 1):
        suffix = "" if runs == 1 else f"_run{run_idx}"
        for model in models:
            for task_id in task_ids:
                for method in methods:
                    gen_name = f"{safe_name(model)}__{task_id}__{method}{suffix}"
                    gen_path = result_dir / "generations" / f"{gen_name}.py"
                    items.append((run_idx, model, task_id, method, gen_name, gen_path))

    rows: list[dict] = [None] * len(items)  # type: ignore[list-item]
    t0 = time.time()

    def work(i_item):
        i, (run_idx, model, task_id, method, gen_name, gen_path) = i_item
        if not gen_path.exists():
            verdict = {
                "exec_pass": False,
                "reason": "harness_error",
                "reason_coarse": "exec_error",
                "detail": f"missing generation file {gen_path.name}",
            }
        else:
            verdict = run_one(
                task_id, gen_path, out_dir / "verdicts" / f"{gen_name}.json"
            )
        srow = static.get((model, task_id, method, run_idx), {})
        meta = task_meta.get(task_id, {})
        rows[i] = {
            "run_idx": run_idx,
            "model": model,
            "task_id": task_id,
            "pair_type": meta.get("pair_type", ""),
            "difficulty": meta.get("difficulty", ""),
            "method": method,
            "exec_pass": verdict["exec_pass"],
            "exec_reason": verdict["reason"],
            "exec_reason_coarse": verdict["reason_coarse"],
            "exec_detail": verdict["detail"],
            "static_pair_pass": srow.get("pair_pass", ""),
            "static_violations": srow.get("violations", ""),
            "static_error_types": srow.get("error_types", ""),
            "generation_path": str(gen_path),
        }

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        done = 0
        for _ in pool.map(work, enumerate(items)):
            done += 1
            if done % 50 == 0:
                print(f"  evaluated {done}/{len(items)} ({time.time()-t0:.0f}s)")

    with (out_dir / "exec_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {out_dir / 'exec_results.csv'} ({len(rows)} rows)")
    return rows


# ---------------------------------------------------------------------------
# Aggregation: summary tables + static-vs-exec comparison
# ---------------------------------------------------------------------------


def majority_pass(flags: list[bool]) -> bool:
    return sum(flags) / len(flags) >= 0.5 if flags else False


def aggregate(rows: list[dict], result_dir: Path) -> None:
    config = json.loads((result_dir / "run_config.json").read_text(encoding="utf-8"))
    models, methods = config["models"], config["methods"]
    out_dir = result_dir / "exec_eval"

    # ---- per (model, method): task-level majority vote + run-level rate ----
    summary: dict = {}
    for model in models:
        summary[model] = {}
        for method in methods:
            sel = [r for r in rows if r["model"] == model and r["method"] == method]
            by_task: dict[str, list[bool]] = {}
            for r in sel:
                by_task.setdefault(r["task_id"], []).append(bool(r["exec_pass"]))
            n_tasks = len(by_task)
            task_pass = sum(majority_pass(v) for v in by_task.values())
            run_pass = sum(bool(r["exec_pass"]) for r in sel)
            reasons: dict[str, int] = {}
            for r in sel:
                if not r["exec_pass"]:
                    reasons[r["exec_reason_coarse"]] = (
                        reasons.get(r["exec_reason_coarse"], 0) + 1
                    )
            summary[model][method] = {
                "n_tasks": n_tasks,
                "total_rows": len(sel),
                "exec_task_pass": task_pass,
                "exec_task_violation_rate": (
                    1 - task_pass / n_tasks if n_tasks else 0
                ),
                "exec_run_pass": run_pass,
                "exec_run_pass_rate": run_pass / len(sel) if sel else 0,
                "fail_reasons_coarse": reasons,
            }

    # ---- run-level confusion matrix static vs exec ----
    judged = [r for r in rows if r["static_pair_pass"] in ("True", "False")]
    tp = sum(
        1 for r in judged if r["static_pair_pass"] == "True" and r["exec_pass"]
    )
    tn = sum(
        1
        for r in judged
        if r["static_pair_pass"] == "False" and not r["exec_pass"]
    )
    fp = sum(  # static says pass, execution fails
        1 for r in judged if r["static_pair_pass"] == "True" and not r["exec_pass"]
    )
    fn = sum(  # static says fail, execution passes
        1 for r in judged if r["static_pair_pass"] == "False" and r["exec_pass"]
    )
    n = len(judged)
    po = (tp + tn) / n if n else 0
    p_yes = ((tp + fp) / n) * ((tp + fn) / n) if n else 0
    p_no = ((tn + fn) / n) * ((tn + fp) / n) if n else 0
    pe = p_yes + p_no
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0

    disagreements = [
        r
        for r in judged
        if (r["static_pair_pass"] == "True") != bool(r["exec_pass"])
    ]
    with (out_dir / "disagreements.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "task_id",
                "method",
                "run_idx",
                "static_pair_pass",
                "exec_pass",
                "exec_reason",
                "exec_detail",
                "static_violations",
                "generation_path",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(disagreements)

    comparison = {
        "n_run_level": n,
        "both_pass": tp,
        "both_fail": tn,
        "static_pass_exec_fail": fp,
        "static_fail_exec_pass": fn,
        "agreement_rate": po,
        "cohens_kappa": kappa,
    }
    (out_dir / "exec_summary.json").write_text(
        json.dumps(
            {"summary": summary, "static_vs_exec": comparison},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ---- markdown report ----
    md = [
        "# Execution-Oracle Re-evaluation (P1)",
        "",
        "- Oracle: hidden tests executed against the REAL vendored simplug "
        "v0.5.7 (runtime behavior: hook results, enabled-set at call time, "
        "state restoration/persistence, runtime call traces). No AST "
        "patterns are consulted.",
        "- Anchoring: see `anchor_report.json` -- canonical solutions and "
        "semantic variants pass; every documented pair-rule violation fails.",
        f"- Generations: {len(rows)} (re-evaluated from the original run, "
        "no new inference).",
        "- A task counts as pass under the same >=50% majority vote across "
        "runs as the static pipeline.",
        "",
        "## Main result: hidden-test violation rate (task-level majority)",
        "",
        "| Model | Method | Tasks | Exec task pass | Exec violation rate | "
        "Static violation rate (old oracle) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    static_summary_path = result_dir / "summary.json"
    static_summary = (
        json.loads(static_summary_path.read_text(encoding="utf-8"))
        if static_summary_path.exists()
        else {}
    )
    for model in models:
        for method in methods:
            s = summary[model][method]
            st = static_summary.get(model, {}).get(method, {})
            st_rate = (
                f"{st.get('pair_violation_rate'):.2f}"
                if st.get("pair_violation_rate") is not None
                else "-"
            )
            md.append(
                f"| {model} | {method} | {s['n_tasks']} | "
                f"{s['exec_task_pass']} | {s['exec_task_violation_rate']:.2f} | "
                f"{st_rate} |"
            )

    md += [
        "",
        "## Hidden-test violation rate matrix (execution oracle)",
        "",
        "| Method | " + " | ".join(models) + " |",
        "|---" + "|---:" * len(models) + "|",
    ]
    for method in methods:
        cells = [
            f"{summary[m][method]['exec_task_violation_rate']:.2f}" for m in models
        ]
        md.append("| " + method + " | " + " | ".join(cells) + " |")

    md += [
        "",
        "## Failure breakdown (run-level, coarse classes)",
        "",
        "| Model | Method | exec_error | wrong_behavior | pair_state_violation |",
        "|---|---|---:|---:|---:|",
    ]
    for model in models:
        for method in methods:
            reasons = summary[model][method]["fail_reasons_coarse"]
            md.append(
                f"| {model} | {method} | {reasons.get('exec_error', 0)} | "
                f"{reasons.get('wrong_behavior', 0)} | "
                f"{reasons.get('pair_state_violation', 0)} |"
            )

    md += [
        "",
        "## Static checker vs execution oracle (run-level)",
        "",
        f"- n = {n} generations with both verdicts",
        "",
        "| | exec PASS | exec FAIL |",
        "|---|---:|---:|",
        f"| static PASS | {tp} | {fp} |",
        f"| static FAIL | {fn} | {tn} |",
        "",
        f"- Agreement rate: **{po:.3f}**",
        f"- Cohen's kappa: **{kappa:.3f}**",
        f"- static PASS but exec FAIL (checker too lenient / runtime-only "
        f"errors): {fp}",
        f"- static FAIL but exec PASS (checker false positives on semantic "
        f"variants): {fn}",
        "- Full disagreement listing: `disagreements.csv`",
        "",
        "## Reading guide",
        "",
        "- The problem-existence claim now rests on the EXECUTION oracle: "
        "B0-B3 violation rates stay high while B4 (gold pair rule) drops, "
        "under tests the injected rules never see.",
        "- The static checker is demoted to a diagnostic role; its "
        "agreement/kappa against execution quantifies how trustworthy the "
        "earlier static numbers were.",
    ]
    (out_dir / "exec_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  wrote {out_dir / 'exec_summary.md'}")
    print(json.dumps(comparison, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--anchors-only", action="store_true")
    ap.add_argument(
        "--skip-anchors",
        action="store_true",
        help="not recommended; anchors gate the oracle's validity",
    )
    args = ap.parse_args()

    if not args.skip_anchors:
        if not run_anchors():
            print("Anchoring suite FAILED -- the oracle is not trustworthy; "
                  "fix hidden tests/fixture before evaluating models.")
            sys.exit(2)
        if args.anchors_only:
            return
    elif args.anchors_only:
        return

    result_dir = Path(args.result_dir).resolve()
    print(f"== Evaluating saved generations in {result_dir} ==")
    rows = evaluate_all(result_dir, jobs=args.jobs)
    aggregate(rows, result_dir)


if __name__ == "__main__":
    main()
