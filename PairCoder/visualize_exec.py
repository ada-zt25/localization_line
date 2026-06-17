#!/usr/bin/env python3
"""Visualize EXECUTION-oracle results for any PairCoder benchmark library.

Reads <result-dir>/exec_eval/exec_results.csv (written by benchlib_eval.py for
any of the six benchlib libraries) plus run_config.json, and renders figures
sliced by method x {model, pair_type, difficulty} -- the whole point of the
per-task pair_type/difficulty metadata.

Pure CSV/JSON + matplotlib: it does NOT import the vendored libraries, so run it
with whatever interpreter has matplotlib (e.g. conda's python), independent of
the experiment interpreter.

    python3 visualize_exec.py --result-dir result/glom_5model
    python3 visualize_exec.py --result-dir result/glom_5model --metric run

Outputs to <result-dir>/exec_eval/figs/:
  pass_by_method.png, heat_method_x_model.png, heat_method_x_pairtype.png,
  heat_method_x_difficulty.png, failure_reasons.png, charts_summary.md
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt

METHOD_ORDER = ["B0_direct", "B1_api_list", "B2_raw_api_docs", "B3_oracle_api_sequence", "B4_gold_pair_rule"]
METHOD_LABELS = {
    "B0_direct": "B0\ndirect",
    "B1_api_list": "B1\napi-list",
    "B2_raw_api_docs": "B2\nraw-docs",
    "B3_oracle_api_sequence": "B3\noracle-seq",
    "B4_gold_pair_rule": "B4\ngold-rule",
}
DIFF_ORDER = ["easy", "medium", "hard"]
REASON_COLORS = {
    "wrong_behavior": "#4C72B0",
    "pair_state_violation": "#C44E52",
    "exec_error": "#DD8452",
    "": "#55A868",  # passed
}


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def load(result_dir: Path):
    csv_path = result_dir / "exec_eval" / "exec_results.csv"
    if not csv_path.exists():
        raise SystemExit(f"missing {csv_path} -- run the eval step first")
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cfg_path = result_dir / "run_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    lib = cfg.get("lib", result_dir.name)
    methods = cfg.get("methods") or [m for m in METHOD_ORDER if any(r["method"] == m for r in rows)]
    methods = [m for m in METHOD_ORDER if m in methods] + [m for m in methods if m not in METHOD_ORDER]
    models = cfg.get("models") or sorted({r["model"] for r in rows})
    return rows, lib, methods, models


def pass_rate(rows, metric="task"):
    """metric='task': fraction of (model, task) groups passing by majority vote
    across runs. metric='run': fraction of individual runs passing."""
    if not rows:
        return None
    if metric == "run":
        flags = [_truthy(r["exec_pass"]) for r in rows]
        return sum(flags) / len(flags)
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["task_id"])].append(_truthy(r["exec_pass"]))
    groups = list(by.values())
    return sum(1 for g in groups if sum(g) / len(g) >= 0.5) / len(groups)


def _sel(rows, **kw):
    return [r for r in rows if all(r.get(k, "") == v for k, v in kw.items())]


def _heatmap(matrix, row_labels, col_labels, title, out, metric_rows):
    n_r, n_c = len(row_labels), len(col_labels)
    fig, ax = plt.subplots(figsize=(max(5, 1.1 * n_c + 2.5), max(3, 0.7 * n_r + 1.8)))
    data = [[(v if v is not None else float("nan")) for v in row] for row in matrix]
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(n_c)); ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(n_r)); ax.set_yticklabels(row_labels, fontsize=9)
    for i in range(n_r):
        for j in range(n_c):
            v = matrix[i][j]
            txt = "-" if v is None else f"{v:.0%}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=9,
                    color="black" if (v is None or 0.25 < v < 0.85) else "white")
    ax.set_title(title, fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="pass rate")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_pass_by_method(rows, lib, methods, metric, out_dir):
    rates = [pass_rate(_sel(rows, method=m), metric) for m in methods]
    fig, ax = plt.subplots(figsize=(max(6, 1.3 * len(methods) + 1), 5))
    xs = range(len(methods))
    bars = ax.bar(xs, [(r or 0) for r in rates], color="#4C72B0")
    for x, r in zip(xs, rates):
        ax.text(x, (r or 0) + 0.02, "-" if r is None else f"{r:.0%}", ha="center", fontsize=10)
    ax.set_xticks(list(xs)); ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in methods], fontsize=9)
    ax.set_ylim(0, 1.08); ax.set_ylabel("pass rate")
    ax.set_title(f"{lib}: execution pass rate by method ({metric}-level)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); out = out_dir / "pass_by_method.png"; fig.savefig(out, dpi=150); plt.close(fig)
    return out


def fig_failure_reasons(rows, lib, methods, out_dir):
    coarse = ["", "wrong_behavior", "pair_state_violation", "exec_error"]
    labels = {"": "pass", "wrong_behavior": "wrong behavior",
              "pair_state_violation": "pair/obligation violation", "exec_error": "exec error"}
    fig, ax = plt.subplots(figsize=(max(6, 1.3 * len(methods) + 1), 5))
    xs = range(len(methods))
    bottoms = [0.0] * len(methods)
    for c in coarse:
        fracs = []
        for m in methods:
            sel = _sel(rows, method=m)
            n = len(sel) or 1
            if c == "":
                k = sum(_truthy(r["exec_pass"]) for r in sel)
            else:
                k = sum((not _truthy(r["exec_pass"])) and r.get("exec_reason_coarse", "") == c for r in sel)
            fracs.append(k / n)
        ax.bar(xs, fracs, bottom=bottoms, label=labels[c], color=REASON_COLORS[c])
        bottoms = [b + f for b, f in zip(bottoms, fracs)]
    ax.set_xticks(list(xs)); ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in methods], fontsize=9)
    ax.set_ylim(0, 1.0); ax.set_ylabel("fraction of runs")
    ax.set_title(f"{lib}: outcome breakdown by method (run-level)")
    ax.legend(fontsize=8, loc="lower left", ncol=2)
    fig.tight_layout(); out = out_dir / "failure_reasons.png"; fig.savefig(out, dpi=150); plt.close(fig)
    return out


def write_summary(rows, lib, methods, models, metric, out_dir, figs):
    pair_types = sorted({r["pair_type"] for r in rows if r.get("pair_type")})
    diffs = [d for d in DIFF_ORDER if any(r.get("difficulty") == d for r in rows)]
    md = [f"# {lib}: execution-oracle charts ({metric}-level pass rate)", "",
          "Figures: " + ", ".join(f"`{p.name}`" for p in figs), "",
          "## Pass rate by method", "", "| " + " | ".join(METHOD_LABELS.get(m, m).replace(chr(10), " ") for m in methods) + " |",
          "|" + "---:|" * len(methods)]
    md.append("| " + " | ".join(f"{(pass_rate(_sel(rows, method=m), metric) or 0):.0%}" for m in methods) + " |")
    for axis_name, vals, key in [("pair_type", pair_types, "pair_type"), ("difficulty", diffs, "difficulty")]:
        md += ["", f"## Pass rate: method x {axis_name}", "",
               "| method | " + " | ".join(vals) + " |", "|---|" + "---:|" * len(vals)]
        for m in methods:
            cells = []
            for v in vals:
                r = pass_rate(_sel(rows, method=m, **{key: v}), metric)
                cells.append("-" if r is None else f"{r:.0%}")
            md.append(f"| {METHOD_LABELS.get(m, m).replace(chr(10), ' ')} | " + " | ".join(cells) + " |")
    out = out_dir / "charts_summary.md"; out.write_text("\n".join(md) + "\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="Visualize execution-oracle results (any library).")
    ap.add_argument("--result-dir", required=True)
    ap.add_argument("--metric", choices=["task", "run"], default="task",
                    help="task: per-(model,task) majority vote across runs (default); run: per individual run")
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()

    result_dir = Path(args.result_dir)
    rows, lib, methods, models = load(result_dir)
    out_dir = Path(args.out_dir) if args.out_dir else result_dir / "exec_eval" / "figs"
    out_dir.mkdir(parents=True, exist_ok=True)

    pair_types = sorted({r["pair_type"] for r in rows if r.get("pair_type")})
    diffs = [d for d in DIFF_ORDER if any(r.get("difficulty") == d for r in rows)]

    figs = [
        fig_pass_by_method(rows, lib, methods, args.metric, out_dir),
        _heatmap([[pass_rate(_sel(rows, method=m, model=mo), args.metric) for mo in models] for m in methods],
                 [METHOD_LABELS.get(m, m).replace("\n", " ") for m in methods], models,
                 f"{lib}: pass rate (method x model)", out_dir / "heat_method_x_model.png", methods),
        fig_failure_reasons(rows, lib, methods, out_dir),
    ]
    if pair_types:
        figs.append(_heatmap(
            [[pass_rate(_sel(rows, method=m, pair_type=pt), args.metric) for pt in pair_types] for m in methods],
            [METHOD_LABELS.get(m, m).replace("\n", " ") for m in methods], pair_types,
            f"{lib}: pass rate (method x pair_type)", out_dir / "heat_method_x_pairtype.png", methods))
    if diffs:
        figs.append(_heatmap(
            [[pass_rate(_sel(rows, method=m, difficulty=d), args.metric) for d in diffs] for m in methods],
            [METHOD_LABELS.get(m, m).replace("\n", " ") for m in methods], diffs,
            f"{lib}: pass rate (method x difficulty)", out_dir / "heat_method_x_difficulty.png", methods))

    md = write_summary(rows, lib, methods, models, args.metric, out_dir, figs)
    print(f"Wrote {len(figs)} figures + {md.name} to {out_dir}")
    for p in figs + [md]:
        print(f"  {p}")


if __name__ == "__main__":
    main()
