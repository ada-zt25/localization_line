# Execution-Oracle Re-evaluation (P1)

- Oracle: hidden tests executed against the REAL vendored simplug v0.5.7 (runtime behavior: hook results, enabled-set at call time, state restoration/persistence, runtime call traces). No AST patterns are consulted.
- Anchoring: see `anchor_report.json` -- canonical solutions and semantic variants pass; every documented pair-rule violation fails.
- Generations: 750 (re-evaluated from the original run, no new inference).
- A task counts as pass under the same >=50% majority vote across runs as the static pipeline.

## Main result: hidden-test violation rate (task-level majority)

| Model | Method | Tasks | Exec task pass | Exec violation rate | Static violation rate (old oracle) |
|---|---|---:|---:|---:|---:|
| qwen2.5:7b | B0_direct | 10 | 1 | 0.90 | - |
| qwen2.5:7b | B1_api_list | 10 | 4 | 0.60 | - |
| qwen2.5:7b | B2_raw_api_docs | 10 | 4 | 0.60 | - |
| qwen2.5:7b | B3_oracle_api_sequence | 10 | 3 | 0.70 | - |
| qwen2.5:7b | B4_gold_pair_rule | 10 | 9 | 0.10 | - |
| qwen2.5-coder:7b | B0_direct | 10 | 2 | 0.80 | - |
| qwen2.5-coder:7b | B1_api_list | 10 | 2 | 0.80 | - |
| qwen2.5-coder:7b | B2_raw_api_docs | 10 | 4 | 0.60 | - |
| qwen2.5-coder:7b | B3_oracle_api_sequence | 10 | 2 | 0.80 | - |
| qwen2.5-coder:7b | B4_gold_pair_rule | 10 | 8 | 0.20 | - |
| llama3.1:8b | B0_direct | 10 | 0 | 1.00 | - |
| llama3.1:8b | B1_api_list | 10 | 0 | 1.00 | - |
| llama3.1:8b | B2_raw_api_docs | 10 | 1 | 0.90 | - |
| llama3.1:8b | B3_oracle_api_sequence | 10 | 0 | 1.00 | - |
| llama3.1:8b | B4_gold_pair_rule | 10 | 2 | 0.80 | - |
| gemma2:9b | B0_direct | 10 | 0 | 1.00 | - |
| gemma2:9b | B1_api_list | 10 | 0 | 1.00 | - |
| gemma2:9b | B2_raw_api_docs | 10 | 0 | 1.00 | - |
| gemma2:9b | B3_oracle_api_sequence | 10 | 0 | 1.00 | - |
| gemma2:9b | B4_gold_pair_rule | 10 | 0 | 1.00 | - |
| mistral:7b | B0_direct | 10 | 0 | 1.00 | - |
| mistral:7b | B1_api_list | 10 | 0 | 1.00 | - |
| mistral:7b | B2_raw_api_docs | 10 | 0 | 1.00 | - |
| mistral:7b | B3_oracle_api_sequence | 10 | 0 | 1.00 | - |
| mistral:7b | B4_gold_pair_rule | 10 | 0 | 1.00 | - |

## Hidden-test violation rate matrix (execution oracle)

| Method | qwen2.5:7b | qwen2.5-coder:7b | llama3.1:8b | gemma2:9b | mistral:7b |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.90 | 0.80 | 1.00 | 1.00 | 1.00 |
| B1_api_list | 0.60 | 0.80 | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 0.60 | 0.60 | 0.90 | 1.00 | 1.00 |
| B3_oracle_api_sequence | 0.70 | 0.80 | 1.00 | 1.00 | 1.00 |
| B4_gold_pair_rule | 0.10 | 0.20 | 0.80 | 1.00 | 1.00 |

## Failure breakdown (run-level, coarse classes)

| Model | Method | exec_error | wrong_behavior | pair_state_violation |
|---|---|---:|---:|---:|
| qwen2.5:7b | B0_direct | 26 | 1 | 0 |
| qwen2.5:7b | B1_api_list | 18 | 3 | 1 |
| qwen2.5:7b | B2_raw_api_docs | 17 | 4 | 0 |
| qwen2.5:7b | B3_oracle_api_sequence | 24 | 0 | 0 |
| qwen2.5:7b | B4_gold_pair_rule | 12 | 0 | 0 |
| qwen2.5-coder:7b | B0_direct | 26 | 0 | 0 |
| qwen2.5-coder:7b | B1_api_list | 17 | 8 | 0 |
| qwen2.5-coder:7b | B2_raw_api_docs | 18 | 4 | 0 |
| qwen2.5-coder:7b | B3_oracle_api_sequence | 26 | 0 | 0 |
| qwen2.5-coder:7b | B4_gold_pair_rule | 13 | 0 | 0 |
| llama3.1:8b | B0_direct | 24 | 4 | 0 |
| llama3.1:8b | B1_api_list | 22 | 4 | 0 |
| llama3.1:8b | B2_raw_api_docs | 25 | 0 | 0 |
| llama3.1:8b | B3_oracle_api_sequence | 28 | 0 | 0 |
| llama3.1:8b | B4_gold_pair_rule | 20 | 0 | 0 |
| gemma2:9b | B0_direct | 28 | 0 | 0 |
| gemma2:9b | B1_api_list | 22 | 2 | 0 |
| gemma2:9b | B2_raw_api_docs | 25 | 0 | 0 |
| gemma2:9b | B3_oracle_api_sequence | 22 | 2 | 0 |
| gemma2:9b | B4_gold_pair_rule | 20 | 2 | 0 |
| mistral:7b | B0_direct | 27 | 1 | 0 |
| mistral:7b | B1_api_list | 29 | 1 | 0 |
| mistral:7b | B2_raw_api_docs | 30 | 0 | 0 |
| mistral:7b | B3_oracle_api_sequence | 23 | 0 | 0 |
| mistral:7b | B4_gold_pair_rule | 21 | 3 | 1 |

## Static checker vs execution oracle (run-level)

- n = 0 generations with both verdicts

| | exec PASS | exec FAIL |
|---|---:|---:|
| static PASS | 0 | 0 |
| static FAIL | 0 | 0 |

- Agreement rate: **0.000**
- Cohen's kappa: **0.000**
- static PASS but exec FAIL (checker too lenient / runtime-only errors): 0
- static FAIL but exec PASS (checker false positives on semantic variants): 0
- Full disagreement listing: `disagreements.csv`

## Reading guide

- The problem-existence claim now rests on the EXECUTION oracle: B0-B3 violation rates stay high while B4 (gold pair rule) drops, under tests the injected rules never see.
- The static checker is demoted to a diagnostic role; its agreement/kappa against execution quantifies how trustworthy the earlier static numbers were.