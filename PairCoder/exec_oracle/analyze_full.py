#!/usr/bin/env python3
"""Six-library full-run analysis: pass rates, B5_loop-B3* / gold-gap fill ratio,
and exact McNemar paired tests. Reads every result/<lib>_5model/exec_eval/
exec_results.csv. Pairs are (lib, model, task_id) [run-level].

    python analyze_full.py [--result-root ../result]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to GBK
except Exception:
    pass

LIBS = ["simplug", "diot", "simpleconf", "glom", "bidict", "sqlitedict"]
SHORT = {"B0_direct": "B0", "B1_api_list": "B1", "B2_raw_api_docs": "B2",
         "B3_oracle_api_sequence": "B3*", "B4_gold_pair_rule": "B4", "B5_loop": "B5_loop"}
ORDER = ["B0", "B1", "B2", "B3*", "B4", "B5_loop"]
PAIR_ORDER = ["param-dependency", "return-flow", "shared-receiver",
              "config-return-contract", "lifecycle", "completion-obligation"]


def load(result_root: Path):
    rows = []
    for lib in LIBS:
        p = result_root / f"{lib}_5model" / "exec_eval" / "exec_results.csv"
        if not p.exists():
            print(f"  [warn] missing {p}")
            continue
        for r in csv.DictReader(p.open(encoding="utf-8")):
            rows.append({"lib": lib, "model": r["model"], "task": r["task_id"],
                         "pair_type": r["pair_type"], "method": SHORT.get(r["method"], r["method"]),
                         "pass": r["exec_pass"] == "True"})
    return rows


def rate(rows, **filt):
    sel = [r for r in rows if all(r[k] == v for k, v in filt.items())]
    return (sum(r["pass"] for r in sel) / len(sel), len(sel)) if sel else (0.0, 0)


def paired(rows, a, b, **filt):
    """McNemar discordant counts over (lib,model,task): b=#(a pass,b fail), c=reverse."""
    by = defaultdict(dict)
    for r in rows:
        if all(r[k] == v for k, v in filt.items()):
            by[(r["lib"], r["model"], r["task"])][r["method"]] = r["pass"]
    nb = nc = 0
    for d in by.values():
        if a in d and b in d:
            if d[a] and not d[b]:
                nb += 1
            elif d[b] and not d[a]:
                nc += 1
    return nb, nc


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def fill(r_b5, r_b1, r_b4):
    denom = r_b4 - r_b1
    return (r_b5 - r_b1) / denom if denom > 0.01 else None


def fmt_p(p):
    return f"{p:.1e}" if p < 1e-3 else f"{p:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-root", default=str(Path(__file__).resolve().parent.parent / "result"))
    args = ap.parse_args()
    rows = load(Path(args.result_root))
    models = sorted({r["model"] for r in rows})
    print(f"# Six-library full-run analysis ({len(models)} models, run-level)\n")
    print(f"Total (model x task) generations per method: "
          f"{len({(r['lib'], r['model'], r['task']) for r in rows})}\n")

    # ---- Table 1: pass rate by method x library ----
    print("## 1. Pass rate by method x library\n")
    print("| lib | pairs | " + " | ".join(ORDER) + " |")
    print("|---|--:|" + "--:|" * len(ORDER))
    for lib in LIBS:
        cells = []
        n_pairs = len({(r["model"], r["task"]) for r in rows if r["lib"] == lib})
        for m in ORDER:
            rt, _ = rate(rows, lib=lib, method=m)
            cells.append(f"{rt:.2f}")
        print(f"| {lib} | {n_pairs} | " + " | ".join(cells) + " |")
    cells = [f"{rate(rows, method=m)[0]:.2f}" for m in ORDER]
    npar = len({(r['lib'], r['model'], r['task']) for r in rows})
    print(f"| **all** | {npar} | " + " | ".join(cells) + " |")

    # ---- Table 2: by pair_type ----
    print("\n## 2. By pair_type (pooled across libs)\n")
    print("| pair_type | pairs | B1 | B3* | B4 | B5_loop | B5_loop−B3* | fill=(B5−B1)/(B4−B1) | McNemar p (B5_loop vs B3*) |")
    print("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for pt in PAIR_ORDER:
        npar = len({(r["lib"], r["model"], r["task"]) for r in rows if r["pair_type"] == pt})
        if npar == 0:
            continue
        b1, _ = rate(rows, pair_type=pt, method="B1")
        b3, _ = rate(rows, pair_type=pt, method="B3*")
        b4, _ = rate(rows, pair_type=pt, method="B4")
        b5, _ = rate(rows, pair_type=pt, method="B5_loop")
        nb, nc = paired(rows, "B5_loop", "B3*", pair_type=pt)
        p = mcnemar_exact(nb, nc)
        fr = fill(b5, b1, b4)
        print(f"| {pt} | {npar} | {b1:.2f} | {b3:.2f} | {b4:.2f} | {b5:.2f} | "
              f"{b5-b3:+.2f} | {f'{fr:.0%}' if fr is not None else 'n/a'} | {fmt_p(p)} |")
    # overall row
    b1 = rate(rows, method="B1")[0]; b3 = rate(rows, method="B3*")[0]
    b4 = rate(rows, method="B4")[0]; b5 = rate(rows, method="B5_loop")[0]
    nb, nc = paired(rows, "B5_loop", "B3*")
    fr = fill(b5, b1, b4)
    npar = len({(r["lib"], r["model"], r["task"]) for r in rows})
    print(f"| **all** | {npar} | {b1:.2f} | {b3:.2f} | {b4:.2f} | {b5:.2f} | "
          f"{b5-b3:+.2f} | {f'{fr:.0%}' if fr is not None else 'n/a'} | {fmt_p(mcnemar_exact(nb, nc))} |")

    # ---- Table 3: McNemar paired tests (pooled) ----
    print("\n## 3. McNemar exact paired tests (pooled, two-sided)\n")
    print("| comparison A vs B | b (A>B) | c (B>A) | discordant | p |")
    print("|---|--:|--:|--:|--:|")
    for a, b in [("B5_loop", "B3*"), ("B5_loop", "B1"), ("B5_loop", "B4"), ("B4", "B3*")]:
        nb, nc = paired(rows, a, b)
        print(f"| {a} vs {b} | {nb} | {nc} | {nb+nc} | {fmt_p(mcnemar_exact(nb, nc))} |")


if __name__ == "__main__":
    main()
