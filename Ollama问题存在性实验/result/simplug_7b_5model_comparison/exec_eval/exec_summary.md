# Execution-Oracle Re-evaluation (P1)

- Oracle: hidden tests executed against the REAL vendored simplug v0.5.7 (runtime behavior: hook results, enabled-set at call time, state restoration/persistence, runtime call traces). No AST patterns are consulted.
- Anchoring: see `anchor_report.json` -- canonical solutions and semantic variants pass; every documented pair-rule violation fails.
- Generations: 450 (re-evaluated from the original run, no new inference).
- A task counts as pass under the same >=50% majority vote across runs as the static pipeline.

## Main result: hidden-test violation rate (task-level majority)

| Model | Method | Tasks | Exec task pass | Exec violation rate | Static violation rate (old oracle) |
|---|---|---:|---:|---:|---:|
| qwen2.5:7b | B0_direct | 6 | 0 | 1.00 | 1.00 |
| qwen2.5:7b | B1_api_list | 6 | 1 | 0.83 | 0.83 |
| qwen2.5:7b | B2_raw_api_docs | 6 | 2 | 0.67 | 0.67 |
| qwen2.5:7b | B3_oracle_api_sequence | 6 | 1 | 0.83 | 0.83 |
| qwen2.5:7b | B4_gold_pair_rule | 6 | 5 | 0.17 | 0.17 |
| qwen2.5-coder:7b | B0_direct | 6 | 0 | 1.00 | 1.00 |
| qwen2.5-coder:7b | B1_api_list | 6 | 0 | 1.00 | 1.00 |
| qwen2.5-coder:7b | B2_raw_api_docs | 6 | 0 | 1.00 | 1.00 |
| qwen2.5-coder:7b | B3_oracle_api_sequence | 6 | 0 | 1.00 | 1.00 |
| qwen2.5-coder:7b | B4_gold_pair_rule | 6 | 5 | 0.17 | 0.00 |
| llama3.1:8b | B0_direct | 6 | 0 | 1.00 | 1.00 |
| llama3.1:8b | B1_api_list | 6 | 0 | 1.00 | 1.00 |
| llama3.1:8b | B2_raw_api_docs | 6 | 0 | 1.00 | 1.00 |
| llama3.1:8b | B3_oracle_api_sequence | 6 | 0 | 1.00 | 1.00 |
| llama3.1:8b | B4_gold_pair_rule | 6 | 2 | 0.67 | 0.17 |
| gemma2:9b | B0_direct | 6 | 0 | 1.00 | 1.00 |
| gemma2:9b | B1_api_list | 6 | 2 | 0.67 | 0.67 |
| gemma2:9b | B2_raw_api_docs | 6 | 3 | 0.50 | 0.50 |
| gemma2:9b | B3_oracle_api_sequence | 6 | 3 | 0.50 | 0.50 |
| gemma2:9b | B4_gold_pair_rule | 6 | 5 | 0.17 | 0.00 |
| mistral:7b | B0_direct | 6 | 0 | 1.00 | 1.00 |
| mistral:7b | B1_api_list | 6 | 0 | 1.00 | 1.00 |
| mistral:7b | B2_raw_api_docs | 6 | 0 | 1.00 | 1.00 |
| mistral:7b | B3_oracle_api_sequence | 6 | 3 | 0.50 | 0.50 |
| mistral:7b | B4_gold_pair_rule | 6 | 2 | 0.67 | 0.50 |

## Hidden-test violation rate matrix (execution oracle)

| Method | qwen2.5:7b | qwen2.5-coder:7b | llama3.1:8b | gemma2:9b | mistral:7b |
|---|---:|---:|---:|---:|---:|
| B0_direct | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B1_api_list | 0.83 | 1.00 | 1.00 | 0.67 | 1.00 |
| B2_raw_api_docs | 0.67 | 1.00 | 1.00 | 0.50 | 1.00 |
| B3_oracle_api_sequence | 0.83 | 1.00 | 1.00 | 0.50 | 0.50 |
| B4_gold_pair_rule | 0.17 | 0.17 | 0.67 | 0.17 | 0.67 |

## Failure breakdown (run-level, coarse classes)

| Model | Method | exec_error | wrong_behavior | pair_state_violation |
|---|---|---:|---:|---:|
| qwen2.5:7b | B0_direct | 18 | 0 | 0 |
| qwen2.5:7b | B1_api_list | 7 | 5 | 3 |
| qwen2.5:7b | B2_raw_api_docs | 12 | 0 | 0 |
| qwen2.5:7b | B3_oracle_api_sequence | 14 | 0 | 0 |
| qwen2.5:7b | B4_gold_pair_rule | 0 | 3 | 0 |
| qwen2.5-coder:7b | B0_direct | 18 | 0 | 0 |
| qwen2.5-coder:7b | B1_api_list | 6 | 12 | 0 |
| qwen2.5-coder:7b | B2_raw_api_docs | 12 | 6 | 0 |
| qwen2.5-coder:7b | B3_oracle_api_sequence | 18 | 0 | 0 |
| qwen2.5-coder:7b | B4_gold_pair_rule | 0 | 3 | 0 |
| llama3.1:8b | B0_direct | 11 | 7 | 0 |
| llama3.1:8b | B1_api_list | 13 | 4 | 0 |
| llama3.1:8b | B2_raw_api_docs | 18 | 0 | 0 |
| llama3.1:8b | B3_oracle_api_sequence | 18 | 0 | 0 |
| llama3.1:8b | B4_gold_pair_rule | 11 | 2 | 0 |
| gemma2:9b | B0_direct | 18 | 0 | 0 |
| gemma2:9b | B1_api_list | 12 | 0 | 0 |
| gemma2:9b | B2_raw_api_docs | 9 | 0 | 0 |
| gemma2:9b | B3_oracle_api_sequence | 6 | 2 | 0 |
| gemma2:9b | B4_gold_pair_rule | 0 | 3 | 0 |
| mistral:7b | B0_direct | 18 | 0 | 0 |
| mistral:7b | B1_api_list | 16 | 2 | 0 |
| mistral:7b | B2_raw_api_docs | 18 | 0 | 0 |
| mistral:7b | B3_oracle_api_sequence | 9 | 0 | 0 |
| mistral:7b | B4_gold_pair_rule | 7 | 5 | 1 |

## Static checker vs execution oracle (run-level)

- n = 450 generations with both verdicts

| | exec PASS | exec FAIL |
|---|---:|---:|
| static PASS | 99 | 25 |
| static FAIL | 4 | 322 |

- Agreement rate: **0.936**
- Cohen's kappa: **0.830**
- static PASS but exec FAIL (checker too lenient / runtime-only errors): 25
- static FAIL but exec PASS (checker false positives on semantic variants): 4
- Full disagreement listing: `disagreements.csv`

## Reading guide

- The problem-existence claim now rests on the EXECUTION oracle: B0-B3 violation rates stay high while B4 (gold pair rule) drops, under tests the injected rules never see.
- The static checker is demoted to a diagnostic role; its agreement/kappa against execution quantifies how trustworthy the earlier static numbers were.