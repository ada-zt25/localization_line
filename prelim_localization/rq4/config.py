#!/usr/bin/env python3
"""RQ4 frozen configuration (anti-drift). All hyperparameters live here; run_all.py reads ONLY this.
Editing arms/metrics/backbone here counts as changing the contract — update RQ4_SPEC §changelog too."""
import os

# ---- backbone (LOCKED: ARISE-matched) ----
MODEL      = os.environ.get("MODEL", "Qwen2.5-Coder-32B")   # = vLLM --served-model-name (memory §5.1; weights are the -Instruct 32B)
BASE_URL   = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")   # local vLLM on the A800 box

# ---- eval口径 (LOCKED) ----
K          = 5            # self-consistency vote samples
TOPK       = 10           # candidate files kept
ARISE_GOLD = True         # ARISE-aligned gold (drop blank/comment anchors) — apply to ALL arms
BOOT_N     = 10000        # bootstrap resamples for CIs

# ---- parallelism (A800-80G: vLLM batches; tune to GPU throughput / disk) ----
WORKERS     = int(os.environ.get("RQ4_WORKERS", 24))    # concurrent instances hitting vLLM (LLM half)
COV_WORKERS = int(os.environ.get("RQ4_COV_WORKERS", 6)) # parallel Docker coverage workers (only if cache miss)

# ---- paths ----
HERE     = os.path.dirname(os.path.abspath(__file__))
FROZEN   = os.path.join(HERE, "frozen_subsets.json")
RESULTS  = os.environ.get("RQ4_RESULTS") or os.path.join(HERE, "results")   # per-model dir for T2 cross-backbone
S1_IDS   = os.path.join(RESULTS, "S1_ids.json")          # flat id list written from FROZEN by run_all
ORACLE_REUSE = os.path.join(RESULTS, "oracle_files_S1.json")  # file-given: each S1 inst -> ranked_files=[gold_file]
GIT_SHA  = os.environ.get("RQ4_GIT_SHA", "uncommitted")

# ---- Task 1 (OPTIONAL, NOT in the RQ4 critical path; file-given口径 needs no file-loc — changelog v2) ----
# file-loc sweep (n=300), pick first config that hits ARISE (R@1>=67 & R@3>=82). Run only via `--task fileloc`.
# Each = (name, [extra egl_e2e flags]). Cheap→expensive; stop at first passing.
FILELOC_SWEEP = [
    ("agentless",          ["--file-loc", "agentless"]),
    ("agentless_rerank",   ["--file-loc", "agentless", "--file-rerank", "10"]),
    ("arise_agentic",      ["--file-loc", "arise", "--arise-turns", "8"]),
    # ("swerank",          ["--file-loc", "swerank"]),   # STRETCH ≥90: needs swerank_loc.py + SweRankEmbed-Large served (see PARALLEL.md §patches)
]
FILELOC_TARGET = {"R@1": 67.0, "R@3": 82.0}              # ARISE parity bar
FILELOC_FROZEN = ""                                       # <-- run_all writes the winning result json path here after the sweep

# ---- Task 2 (RQ4): the two GPU passes on S1 (each derives several arms; M1 derived offline) ----
# Both reuse ONE frozen file-loc run so file-loc is held constant across arms.
RQ4_PASSES = {
    # PASS_A normal region + coverage + substrate dump → gives M0(ours_static), M3(ours_dynamic), anchors;
    #        M1(filter) derived offline from the dumped substrate ∩ coverage.
    "passA_normal":   ["--coverage", "--dump-substrate"],
    # PASS_B coverage-narrowed vote (M2): region = executed lines only → vote_only/ours arms ARE M2/M4.
    "passB_covnarrow":["--cov-narrow", "--dump-substrate"],
    # PASS_C M5: cov-narrowed vote + ASSERTION-grounded rerank (target R@1/R@5; the signal orthogonal to coverage).
    "passC_m5":       ["--cov-narrow", "--dump-substrate", "--assert-rerank", "10"],
}
# T2 cross-backbone: optionally run only a subset of passes (e.g. skip passC_m5 / M5). Env-gated → default unchanged.
_only = os.environ.get("RQ4_PASSES_ONLY")
if _only:
    RQ4_PASSES = {k: v for k, v in RQ4_PASSES.items() if k in _only.split(",")}

# arm → which (pass, egl_e2e arm name) realizes it
RQ4_ARM_MAP = {
    "M0_ours_static":      ("passA_normal",    "ours_static"),
    "M3_ours_dynamic":     ("passA_normal",    "ours_dynamic"),
    "M2_covnarrow_static": ("passB_covnarrow", "ours_static"),
    "M4_coverage_max":     ("passB_covnarrow", "ours_dynamic"),
    "M5_assert_rerank":    ("passC_m5",        "ours_m5"),
    "anchor_arise_static": ("passA_normal",    "arise_static"),
    "anchor_vote_only":    ("passA_normal",    "vote_only"),
}
PRIMARY_DELTA = ("M4_coverage_max", "M0_ours_static")    # the RQ4 headline: M4 − M0 on S1
# M5 secondary headline: M5 − M4 (does assertion-reasoning add discrimination on top of coverage-narrowing?)

# ---- external reference (NOT a baseline; different口径, all-300 agentic) ----
ARISE_REF = {"line_R@1": 41, "line_R@5": 62, "line_R@10": 74, "file_R@1": 67, "file_R@3": 82}

# ---- offline ceiling (already established, lineloc_offline.json) ----
OFFLINE_FILTER_CEILING = {"S1_line_R@10": 43.9, "delta_vs_static_pp": 14.0, "ci95": [3.5, 24.6], "sig": True}

def env_banner():
    return (f"MODEL={MODEL} BASE_URL={BASE_URL} K={K} TOPK={TOPK} WORKERS={WORKERS} "
            f"COV_WORKERS={COV_WORKERS} ARISE_GOLD={ARISE_GOLD} GIT_SHA={GIT_SHA}")
