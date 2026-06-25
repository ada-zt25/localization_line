# RUN PLAN — ARISE-aligned line-localization experiments (handoff, self-contained)

You (a fresh Claude session) are to RUN and ANALYZE the experiment runlist below, then report
"us vs ARISE". All experiments run **locally** (Bash tool on the user's Windows machine, in this
`prelim_localization/` dir). The **model** is reached over an SSH tunnel to a remote AutoDL A800
serving **Qwen2.5-Coder-32B (AWQ-Int4)** via vLLM on `localhost:8000`. GitHub fetches work locally.

## GOAL
Beat **ARISE** (the static line-localization SOTA) on **SWE-bench Lite** with **Qwen2.5-Coder-32B**,
on instance-level **Line Recall@{1,5,10}**, end-to-end **file-not-given**.
- ARISE reference (Lite / Qwen2.5-Coder-32B / agentic): **line R@{1,5,10} = {41, 62, 74}**, file R@1 = 67.
- Prior result (DeepSeek-V3, n=288): line R@{1,5,10} = {36.1, 64.6, 71.9} → **wins R@5, LOSES R@1 & R@10**.
- Diagnosis (offline-proven): **R@1 = a RANKING problem** (gold is in the voted set ~85% but ranked #1
  only ~38%); **R@10 = a CEILING problem** (candidate set recall, ranking can't fix it). R@5 already wins.

## PREREQS (the user maintains these; verify before running)
1. AWQ model on the remote: `/root/autodl-tmp/qwen32b-awq`.
2. vLLM serving on the remote (note the torch-compile-disable fix, required for AWQ on this torch):
   ```
   TORCHDYNAMO_DISABLE=1 TORCH_COMPILE_DISABLE=1 vllm serve /root/autodl-tmp/qwen32b-awq \
     --served-model-name Qwen2.5-Coder-32B --quantization awq --enforce-eager \
     --port 8000 --max-model-len 16384 --gpu-memory-utilization 0.92
   ```
3. SSH tunnel (local Windows PowerShell, KEEP THE WINDOW OPEN):
   ```
   ssh -CN -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 8000:127.0.0.1:8000 -p 55162 root@connect.nma1.seetacloud.com
   ```
   If it drops mid-run, reconnect and re-launch the experiment (everything resumes — see below).

## COMMON ENV (prefix every experiment command)
```
SWEBENCH_DATASET=lite MODEL=Qwen2.5-Coder-32B OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=dummy
```
`--broad` = all of Lite (300 instances, 100% single-file — matches ARISE's set). `--workers 20` (AWQ has
a wide KV cache → high concurrency; raise if vLLM log shows headroom, lower on preemption).

## STEP 0 — verify the tunnel + model
```
python -c "import urllib.request,json; print([m['id'] for m in json.loads(urllib.request.urlopen('http://localhost:8000/v1/models',timeout=10).read())['data']])"
```
Expect `['Qwen2.5-Coder-32B']`. Then a 1-token smoke via /v1/chat/completions to confirm it generates.

## LONG-RUN HANDLING (important)
E1/E3 take ~20-30 min — longer than the Bash foreground timeout. Launch them with
`run_in_background: true`, then monitor: egl_e2e prints `[k/300] ...` to stderr and writes the `--out`
json incrementally. Poll the json's length / tail the process. egl_e2e is **resumable** (skips `done`
instances), so if the tunnel drops, just reconnect + re-run the same command.

## RUNLIST

### E1 — baseline (v0 ranker) + substrate dump   [GPU, ~20-30 min, background]
```
<ENV> python egl_e2e.py --broad --sample 300 --workers 20 --dump-substrate --out egl_e2e_awq.json
```
Produces: the headline **us(v0) vs ARISE** line R@{1,5,10} on full Lite, AND the per-file substrate
(region+freq+counts+gold) embedded in the json for the free offline ranking ablation.

### E2 — offline ranking ablation (pick the R@1 ranker)   [FREE, no GPU/LLM, minutes]
```
SWEBENCH_DATASET=lite python ablation_rank_sweep.py --substrate egl_e2e_awq.json
```
Compares the REAL production rankers `v0_rrf` / `counts_primary` / `vote_only` / `graph_only` + K-grid,
plus the rank-free **ORACLE** ceiling. Decide the R@1 winner = highest R@1 (without dropping R@5/R@10).
Report each variant's R@{1,5,10} and the oracle gap (oracle − best = ranking headroom remaining).

### E3 — top-N LLM final-pick (the strongest R@1 lever)   [GPU, ~20-30 min, background]
```
<ENV> python egl_e2e.py --broad --sample 300 --workers 20 --final-pick 8 --rank-mode <E2_WINNER> --out egl_e2e_awq_fp.json
```
`--final-pick 8` adds one focused LLM re-rank of the top-8 candidates per file (reorders the head, keeps
the R@10 tail). Compare its line R@{1,5,10} vs E1 and vs ARISE.

### E6 — Stage-B construct ablation ("去掉无用构件")   [GPU, ~15 min, background]
```
<ENV> python stageb_ablation.py --sample 60 --workers 16
```
File-given leave-one-out over 7 variants (full / no_element_sc / no_graph_backstop / no_module_lines /
no_small_bypass / no_temp_sched / k3_samples). Reports reg_ceiling / voted_recall / R@{1,5,10} +
delta_vs_full. Rule: a construct whose removal does NOT drop those is dead weight → recommend cutting it.

### E4 — R@10 recall bump   [CONDITIONAL: only if E1/E3 R@10 < 74]
R@10 is a ceiling (recall), not ranking. Try raising vote recall:
```
<ENV> python egl_e2e.py --broad --sample 300 --workers 20 --rank-mode <E2_WINNER> --k 8 --lines-cap 50 --out egl_e2e_awq_k8.json
```
(`--k` = vote self-consistency samples, `--lines-cap` = per-sample line cap.) Compare R@10 vs E1.

### E5 — final / lock
Pick the best config (ranker + final-pick + k/cap) by the joint R@{1,5,10} vs ARISE. Re-run once on
n=300 if needed for the definitive table + report. NOTE: bf16 final is BLOCKED (no AutoDL host with a
big enough disk to clone the 62GB bf16 model), so the final model is **AWQ-Int4** — which makes "we beat
ARISE" a STRONGER claim (a weaker quantized model still wins). Footnote the precision.

## REPORT FORMAT (what to hand back to the user)
A table: rows = {ARISE, E1 v0, E2 winner, E3 +final-pick, (E4 +recall)}, cols = line R@1 / R@5 / R@10 +
file R@{1,5,10}. State clearly: did we beat ARISE at ALL of R@1/5/10? Plus the E6 "which Stage-B
constructs to cut" recommendation. Keep raw jsons (egl_e2e_awq*.json, ablation_rank_sweep.json,
stageb_ablation.json).

## CODE REFERENCE (already implemented & tested; v0 default = shipped behavior, unchanged)
- `region_loc.py`: `_rank_v0` (shipped RRF), `_rank_counts` (consensus-primary, R@1 candidate),
  `llm_final_pick` (top-N LLM re-rank), `region_line_loc_ex` (one vote pass → ranked + substrate),
  cfg-threading for E6 toggles.
- `egl_e2e.py`: flags `--rank-mode v0|counts`, `--final-pick N`, `--dump-substrate`.
- `ablation_rank_sweep.py`: free offline ranker sweep (reads the e2e dump's substrate w/ counts).
- `stageb_ablation.py`: E6 leave-one-out driver.
- `p0_line_recall.py`: `SWEBENCH_DATASET=lite` loader; `GH_PROXY` env for GitHub (NOT needed locally).
