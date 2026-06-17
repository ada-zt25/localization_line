#!/usr/bin/env python3
r"""RQ1: extraction-quality evaluation for the test-free pair-rule extractor (B5).

Scores pair_extractor.Phi against a hand-annotated gold of the typed pairwise
constraints each library exhibits.  Reports, per library and overall:

  * precision / recall / F1 of emitted typed rules,
  * the relation confusion matrix (edge-type accuracy),
  * the precision-coverage operating curve over the calibrated confidence theta,
  * the calibration check  precision(theta) ~ E[c | c>=theta] >= theta.

Calibration is fit LEAVE-ONE-LIBRARY-OUT: a library's confidences come from a
Platt model trained only on the OTHER libraries' (score, correct?) pairs, so the
precision floor is reported under genuine cross-library transfer (no leakage).

GOLD below is the annotator's ground truth -- the set of typed constraints in
the benchmark's hand-written gold rules, reduced to the *salient API tokens* that
count as recovering each constraint.  The extractor never reads this; it reads
only library source / signatures / docstrings / doc snippets.

    python eval_extraction.py                       # print summary
    python eval_extraction.py --emit result/extraction_eval
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import pair_extractor as px

# ---------------------------------------------------------------------------
# GOLD: typed constraints per library, as (relation, {salient tokens that count
# as recovering it}).  Tokens are matched case-insensitively against the tokens
# of an extracted rule's anchors.  Drawn from each lib's GOLD_PAIR_RULES, reduced
# to API-level salient tokens (NOT example data fields like 'items').
# ---------------------------------------------------------------------------
GOLD = {
    "glom": [
        ("return-flow",             {"path", "dotted", "navigate", "chain", "tuple"}),
        ("config-return-contract",  {"shape", "spec", "list", "dict", "output"}),
        ("param-dependency",        {"default", "coalesce"}),
        ("shared-receiver",         {"assign"}),
    ],
    "diot": [
        ("param-dependency",        {"diot_transform", "transform", "camel", "snake"}),
        ("config-return-contract",  {"diot_nest", "nest", "to_dict"}),
        ("return-flow",             {"nested", "chain"}),
        ("shared-receiver",         {"same"}),
        ("lifecycle",               {"thaw", "diot_frozen", "frozendiot", "frozen"}),
    ],
    "simpleconf": [
        ("param-dependency",        {"order", "override", "precedence", "merge"}),
        ("config-return-contract",  {"profile", "profiles", "diot"}),
        ("return-flow",             {"load", "access"}),
        ("shared-receiver",         {"use_profile", "same"}),
        ("lifecycle",               {"with_profile", "revert", "temporarily", "temporary"}),
    ],
    "bidict": [
        ("param-dependency",        {"forceput", "put"}),
        ("config-return-contract",  {"inv", "inverse"}),
        ("return-flow",             {"inv", "inverse"}),
        ("shared-receiver",         {"inv", "inverse"}),
        ("lifecycle",               {"putall", "frozenbidict", "atomic"}),
    ],
    "simplug": [
        ("param-dependency",        {"names", "string", "strings"}),       # names-as-strings
        ("config-return-contract",  {"result", "first", "last", "spec"}),  # result mode -> shape
        ("return-flow",             {"get_plugin", "wrapper"}),
        ("shared-receiver",         {"disable", "same"}),
        ("lifecycle",               {"plugins_context", "persistent", "context"}),
    ],
    "sqlitedict": [
        ("completion-obligation",   {"commit", "durable", "persist"}),
    ],
}

LIBS = list(GOLD)


def _toks(*strings) -> set:
    out = set()
    for s in strings:
        out |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(s).lower()))
    return out


def _rule_tokens(rule: dict) -> set:
    return _toks(*rule["anchors"])


def _match_gold(rule: dict, lib: str):
    """Return the matched gold relation for an extracted rule, or None.

    A rule matches a gold entry iff the relation is identical AND their salient
    tokens overlap.  Used for precision/recall.  For the confusion matrix we also
    expose _covering_gold (token overlap ignoring relation)."""
    tk = _rule_tokens(rule)
    for rel, accept in GOLD[lib]:
        if rel == rule["relation"] and (tk & accept):
            return rel
    return None


def _covering_gold(rule: dict, lib: str):
    """The gold relation whose salient tokens this rule's tokens hit (any
    relation) -- the 'true' relation for the edge-type confusion matrix."""
    tk = _rule_tokens(rule)
    best, best_overlap = None, 0
    for rel, accept in GOLD[lib]:
        ov = len(tk & accept)
        if ov > best_overlap:
            best, best_overlap = rel, ov
    return best


# ---------------------------------------------------------------------------
# Leave-one-library-out Platt calibration of the raw discriminative score.
# ---------------------------------------------------------------------------
def calibrate_lolo(raw: dict):
    """raw: {lib: [rule dicts with 'score']}. Adds 'label' and 'confidence'
    (LOLO-calibrated) to every rule. Returns the same dict."""
    # label each rule: 1 if it matches a gold of the same relation, else 0.
    for lib, rules in raw.items():
        for r in rules:
            r["label"] = 1 if _match_gold(r, lib) else 0

    for held in LIBS:
        train_s, train_y = [], []
        for lib in LIBS:
            if lib == held:
                continue
            for r in raw[lib]:
                train_s.append(r["score"])
                train_y.append(r["label"])
        alpha, beta = px.fit_platt(train_s, train_y)
        for r in raw[held]:
            r["confidence"] = round(px._sigmoid(alpha * r["score"] + beta), 4)
            r["platt"] = [round(alpha, 4), round(beta, 4)]
    return raw


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def prf_at(rules_by_lib: dict, theta: float):
    """Pooled precision / recall / F1 over all libs at confidence >= theta."""
    tp = emitted = 0
    recovered = defaultdict(set)   # lib -> set of gold relations recovered
    gold_total = sum(len(GOLD[l]) for l in rules_by_lib)
    for lib, rules in rules_by_lib.items():
        gold_rels = [rel for rel, _ in GOLD[lib]]
        for r in rules:
            if r["confidence"] < theta:
                continue
            emitted += 1
            if r["label"]:
                tp += 1
                recovered[lib].add(_match_gold(r, lib))
    rec_count = sum(len(s) for s in recovered.values())
    precision = tp / emitted if emitted else 0.0
    recall = rec_count / gold_total if gold_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, emitted, tp


def precision_coverage_curve(rules_by_lib: dict, steps=21):
    rows = []
    for i in range(steps):
        theta = i / (steps - 1)
        p, r, f, n, tp = prf_at(rules_by_lib, theta)
        # mean confidence of emitted (the calibration estimate of precision)
        cs = [ru["confidence"] for rs in rules_by_lib.values() for ru in rs
              if ru["confidence"] >= theta]
        est = sum(cs) / len(cs) if cs else 0.0
        rows.append({"theta": round(theta, 3), "precision": round(p, 3),
                     "recall": round(r, 3), "f1": round(f, 3),
                     "emitted": n, "tp": tp, "E[c|c>=theta]": round(est, 3)})
    return rows


def confusion(rules_by_lib: dict):
    rels = px.RELATIONS
    mat = {a: {b: 0 for b in rels} for a in rels}      # true (cover) -> predicted
    no_gold = defaultdict(int)
    for lib, rules in rules_by_lib.items():
        for r in rules:
            true = _covering_gold(r, lib)
            if true is None:
                no_gold[r["relation"]] += 1
            else:
                mat[true][r["relation"]] += 1
    return mat, no_gold


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", help="write extraction_eval artifacts under this dir")
    ap.add_argument("--theta-star", type=float, default=None,
                    help="report P/R/F1 at this theta (default: smallest theta meeting --target-precision)")
    ap.add_argument("--target-precision", type=float, default=0.6,
                    help="high-precision operating target for theta* selection")
    args = ap.parse_args()

    raw = {lib: px.extract_library(lib, platt=None) for lib in LIBS}
    calibrate_lolo(raw)

    curve = precision_coverage_curve(raw)
    # choose theta* = smallest theta achieving precision >= 0.8 (else best-F1)
    if args.theta_star is not None:
        theta_star = args.theta_star
    else:
        hit = [row for row in curve if row["precision"] >= args.target_precision and row["emitted"] > 0]
        emitted_rows = [r for r in curve if r["emitted"] > 0]
        theta_star = (hit[0]["theta"] if hit else
                      max(emitted_rows, key=lambda r: (r["precision"], r["recall"]))["theta"])

    print("# RQ1  Test-free pair-rule extraction quality\n")
    print(f"Libraries: {', '.join(LIBS)}   |   gold typed rules: "
          f"{sum(len(GOLD[l]) for l in LIBS)}\n")

    print("## Per-library (all emitted, theta=0)")
    print("| lib | gold | emitted | TP | precision | recall | F1 |")
    print("|---|--:|--:|--:|--:|--:|--:|")
    for lib in LIBS:
        p, r, f, n, tp = prf_at({lib: raw[lib]}, 0.0)
        print(f"| {lib} | {len(GOLD[lib])} | {n} | {tp} | {p:.2f} | {r:.2f} | {f:.2f} |")
    p, r, f, n, tp = prf_at(raw, 0.0)
    print(f"| **all** | {sum(len(GOLD[l]) for l in LIBS)} | {n} | {tp} | {p:.2f} | {r:.2f} | {f:.2f} |")

    print(f"\n## At theta* = {theta_star} (LOLO-calibrated confidence)")
    p, r, f, n, tp = prf_at(raw, theta_star)
    print(f"precision={p:.2f}  recall={r:.2f}  F1={f:.2f}  (emitted={n}, TP={tp})")

    print("\n## Precision-coverage curve (calibration check: precision >= E[c|c>=theta] target)")
    print("| theta | precision | recall | F1 | emitted | E[c|c>=theta] |")
    print("|--:|--:|--:|--:|--:|--:|")
    for row in curve[::2]:
        print(f"| {row['theta']} | {row['precision']} | {row['recall']} | "
              f"{row['f1']} | {row['emitted']} | {row['E[c|c>=theta]']} |")

    print("\n## Relation confusion (true cover -> predicted), edge-type accuracy")
    mat, no_gold = confusion(raw)
    diag = sum(mat[r][r] for r in px.RELATIONS)
    tot = sum(sum(mat[a].values()) for a in px.RELATIONS)
    print(f"edge-type accuracy (on token-covered rules) = {diag}/{tot} = "
          f"{diag/tot:.2f}" if tot else "no covered rules")
    short = {"param-dependency": "param", "return-flow": "return", "shared-receiver": "shared",
             "config-return-contract": "config", "lifecycle": "lifecyc"}
    hdr = "| true\\pred | " + " | ".join(short[r] for r in px.RELATIONS) + " |"
    print(hdr)
    print("|---|" + "--:|" * len(px.RELATIONS))
    for a in px.RELATIONS:
        if sum(mat[a].values()) == 0:
            continue
        print(f"| {short[a]} | " + " | ".join(str(mat[a][b]) for b in px.RELATIONS) + " |")
    if no_gold:
        print(f"\nFalse positives with no token-covered gold (pure precision misses): "
              f"{dict(no_gold)}")

    if args.emit:
        out = Path(args.emit)
        out.mkdir(parents=True, exist_ok=True)
        for lib in LIBS:
            (out / f"extracted_{lib}.json").write_text(
                json.dumps(raw[lib], indent=2, ensure_ascii=False), encoding="utf-8")
        with (out / "precision_coverage.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(curve[0].keys()))
            w.writeheader()
            w.writerows(curve)
        print(f"\nwrote artifacts to {out}")


if __name__ == "__main__":
    main()
