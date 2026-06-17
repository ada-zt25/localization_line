#!/usr/bin/env python3
"""Visualize the PairCoder multi-model x method comparison results.

Designed to stay readable with FIVE (or more) models. Instead of cramming
25 grouped bars into one axis, the model x method violation rates are shown as:

  fig1_violation_heatmap.png
      A model x method heatmap (green = low violation = good, red = high = bad),
      every cell annotated with its percentage. This is the clean primary view
      and scales to any number of models.

  fig2_violation_trend.png
      A line chart: x = injection method (B0 -> B4), one line per model. Makes
      the narrative obvious -- violations stay high through B0-B3 (the problem
      region) and collapse only at B4 (gold pair rule).

  fig3_error_breakdown.png
      Horizontal stacked bars per model: what error types dominate under the
      no-gold-rule conditions (B0-B3).

  fig4_task_method_grid_<model>.png
      One per-model task x method pass/partial/fail grid.

  charts_summary.md
      The violation-rate matrix as a markdown table.

Usage:
  python3 visualize_results.py --result-dir result/<run_name>
  python3 visualize_results.py --result-dir result/<run_name> --out-dir figs
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
from matplotlib.colors import ListedColormap

# Methods that inject NO gold pair rule -- where the problem must show up.
NO_GOLD_METHODS = ["B0_direct", "B1_api_list", "B2_raw_api_docs", "B3_oracle_api_sequence"]

# Short axis labels.
METHOD_LABELS = {
    "B0_direct": "B0\ndirect",
    "B1_api_list": "B1\napi-list",
    "B2_raw_api_docs": "B2\nraw-docs",
    "B3_oracle_api_sequence": "B3\noracle-seq",
    "B4_gold_pair_rule": "B4\ngold-rule",
}
METHOD_LABELS_FLAT = {k: v.replace("\n", " ") for k, v in METHOD_LABELS.items()}

# Distinct line markers so models stay distinguishable even in grayscale print.
LINE_MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]

ERROR_TYPE_COLORS = {
    "missing API call": "#4C72B0",
    "wrong parameter semantics": "#DD8452",
    "wrong API pattern": "#8172B3",
    "broken data flow": "#C44E52",
    "syntax_error": "#937860",
    "empty_generation": "#999999",
    "experiment_error": "#000000",
}


def load_artifacts(result_dir: Path):
    config_path = result_dir / "run_config.json"
    summary_path = result_dir / "summary.json"
    csv_path = result_dir / "pair_violation_results.csv"

    for p in (summary_path, csv_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing expected artifact: {p}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        models = config.get("models") or list(summary.keys())
        methods = config.get("methods") or _methods_from_summary(summary)
    else:
        models = list(summary.keys())
        methods = _methods_from_summary(summary)

    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    return summary, models, methods, rows


def _methods_from_summary(summary: dict) -> list[str]:
    seen: list[str] = []
    for model_block in summary.values():
        for method in model_block:
            if method not in seen:
                seen.append(method)
    return seen


def _violation_rate(summary: dict, model: str, method: str) -> float:
    block = summary.get(model, {}).get(method, {})
    return float(block.get("pair_violation_rate", 0.0))


def _runs_per_task(summary: dict) -> int:
    for model_block in summary.values():
        for stats in model_block.values():
            return int(stats.get("runs_per_task", 1))
    return 1


# --------------------------------------------------------------------------- #
# Figure 1: model x method violation-rate heatmap (clean primary view)
# --------------------------------------------------------------------------- #
def plot_violation_heatmap(summary, models, methods, out_dir: Path) -> Path:
    grid = [[_violation_rate(summary, m, meth) for meth in methods] for m in models]

    fig, ax = plt.subplots(
        figsize=(max(7, 1.5 * len(methods) + 2), max(3.5, 0.7 * len(models) + 2))
    )
    im = ax.imshow(grid, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in methods])
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)

    for i in range(len(models)):
        for j in range(len(methods)):
            rate = grid[i][j]
            ax.text(
                j, i, f"{rate:.0%}",
                ha="center", va="center",
                color="white" if (rate < 0.25 or rate > 0.75) else "black",
                fontsize=10, fontweight="bold",
            )

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Pair-violation rate (green = better)")
    ax.set_title(
        "API-pair composition failure across models x knowledge-injection methods\n"
        "(B0-B3 stay red: API knowledge alone is not enough; B4 gold rule turns green)"
    )
    fig.tight_layout()
    out = out_dir / "fig1_violation_heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Figure 2: violation-rate trend lines (one line per model)
# --------------------------------------------------------------------------- #
def plot_violation_trend(summary, models, methods, out_dir: Path) -> Path:
    cmap = plt.get_cmap("tab10")
    x = list(range(len(methods)))

    fig, ax = plt.subplots(figsize=(max(7, 1.5 * len(methods) + 2), 5.5))

    for mi, model in enumerate(models):
        rates = [_violation_rate(summary, model, meth) for meth in methods]
        ax.plot(
            x, rates,
            marker=LINE_MARKERS[mi % len(LINE_MARKERS)],
            markersize=7, linewidth=2,
            color=cmap(mi % 10), label=model,
        )

    # Shade the no-gold-rule "problem region".
    gold_idx = [i for i, m in enumerate(methods) if m not in NO_GOLD_METHODS]
    if gold_idx:
        ax.axvspan(-0.4, min(gold_idx) - 0.5, color="#F2C14E", alpha=0.10, zorder=0)
        ax.text(
            (min(gold_idx) - 1) / 2, 1.06,
            "no explicit pair rule -> problem region",
            ha="center", va="top", fontsize=9, color="#8a6d00",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in methods])
    ax.set_ylabel("Pair-violation rate (lower = better)")
    ax.set_ylim(-0.05, 1.12)
    ax.set_xlim(-0.4, len(methods) - 0.6)
    ax.set_title("Pair-violation rate vs knowledge-injection method, per model")
    ax.legend(title="model", frameon=False, fontsize=9, loc="lower left")
    ax.grid(axis="y", ls=":", lw=0.5, alpha=0.6)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = out_dir / "fig2_violation_trend.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Figure 3: error-type breakdown under no-gold-rule conditions (horizontal)
# --------------------------------------------------------------------------- #
def plot_error_breakdown(rows, models, methods, out_dir: Path) -> Path:
    active_no_gold = [m for m in NO_GOLD_METHODS if m in methods]

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_types: list[str] = []
    for r in rows:
        if r["method"] not in active_no_gold:
            continue
        if str(r["pair_pass"]) == "True":
            continue
        raw = (r.get("error_types") or "").strip()
        types = [t.strip() for t in raw.split(";") if t.strip()] or ["unknown"]
        for t in types:
            counts[r["model"]][t] += 1
            if t not in all_types:
                all_types.append(t)

    fig, ax = plt.subplots(figsize=(9, max(3, 0.7 * len(models) + 2)))
    y = list(range(len(models)))
    lefts = [0.0] * len(models)
    for t in all_types:
        widths = [counts[model].get(t, 0) for model in models]
        ax.barh(
            y, widths, left=lefts, label=t,
            color=ERROR_TYPE_COLORS.get(t, None), edgecolor="white",
        )
        lefts = [b + w for b, w in zip(lefts, widths)]

    for yi, total in zip(y, lefts):
        if total > 0:
            ax.text(total + 0.2, yi, f"{int(total)}", va="center", fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels(models)
    ax.invert_yaxis()
    ax.set_xlabel("Error-tag count (failing rows, B0-B3)")
    ax.set_title("What kind of pair errors dominate without a pair rule")
    ax.legend(title="error type", frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = out_dir / "fig3_error_breakdown.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Figure 4: per-model task x method pass/partial/fail grids
# --------------------------------------------------------------------------- #
def plot_task_method_grids(rows, models, methods, out_dir: Path) -> list[Path]:
    task_ids = sorted({r["task_id"] for r in rows})

    agg: dict[str, dict[tuple[str, str], list[bool]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        agg[r["model"]][(r["task_id"], r["method"])].append(str(r["pair_pass"]) == "True")

    cmap = ListedColormap(["#C44E52", "#FFE08A", "#55A868"])  # fail / partial / pass
    outputs: list[Path] = []

    for model in models:
        grid = []
        for t in task_ids:
            row_vals = []
            for m in methods:
                passes = agg[model].get((t, m), [])
                if not passes:
                    row_vals.append(float("nan"))
                else:
                    frac = sum(passes) / len(passes)
                    row_vals.append(0.0 if frac == 0 else (1.0 if frac == 1 else 0.5))
            grid.append(row_vals)

        fig, ax = plt.subplots(
            figsize=(max(6, 1.2 * len(methods) + 2), max(4, 0.6 * len(task_ids) + 2))
        )
        ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(methods)))
        ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in methods], fontsize=9)
        ax.set_yticks(range(len(task_ids)))
        ax.set_yticklabels(task_ids, fontsize=9)
        ax.set_title(f"Pass(green)/Partial(yellow)/Fail(red): {model}")

        for i in range(len(task_ids)):
            for j in range(len(methods)):
                v = grid[i][j]
                label = "?" if v != v else ("PASS" if v == 1 else ("~" if v == 0.5 else "FAIL"))
                ax.text(j, i, label, ha="center", va="center", fontsize=7,
                        color="black" if v == 0.5 else "white")

        fig.tight_layout()
        safe = model.replace(":", "_").replace("/", "_")
        out = out_dir / f"fig4_task_method_grid_{safe}.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)
        outputs.append(out)

    return outputs


# --------------------------------------------------------------------------- #
# Markdown table mirror
# --------------------------------------------------------------------------- #
def write_markdown(summary, models, methods, out_dir: Path) -> Path:
    runs = _runs_per_task(summary)
    lines = [
        "# Pair-violation rate matrix",
        "",
        f"- Models: {len(models)} | Methods: {len(methods)} | Runs/condition: {runs} (majority vote)",
        "",
        "| Model | " + " | ".join(METHOD_LABELS_FLAT.get(m, m) for m in methods) + " |",
        "|---" + "|---:" * len(methods) + "|",
    ]
    for model in models:
        cells = [f"{_violation_rate(summary, model, meth):.0%}" for meth in methods]
        lines.append(f"| {model} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "_Lower is better. Non-zero violations under B0-B3 (no explicit pair rule)",
        "across all models support the problem-existence claim; B4 (gold rule) is the",
        "oracle upper bound showing the problem is solvable once pair knowledge is given._",
    ]
    out = out_dir / "charts_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize PairCoder multi-model comparison results.")
    parser.add_argument("--result-dir", required=True, help="Directory with summary.json + pair_violation_results.csv")
    parser.add_argument("--out-dir", default="", help="Where to write figures (default: <result-dir>/figs)")
    args = parser.parse_args()

    result_dir = Path(args.result_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else result_dir / "figs"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary, models, methods, rows = load_artifacts(result_dir)

    produced = [
        plot_violation_heatmap(summary, models, methods, out_dir),
        plot_violation_trend(summary, models, methods, out_dir),
        plot_error_breakdown(rows, models, methods, out_dir),
        *plot_task_method_grids(rows, models, methods, out_dir),
        write_markdown(summary, models, methods, out_dir),
    ]

    print("Wrote:")
    for p in produced:
        print(f"  {p}")


if __name__ == "__main__":
    main()
