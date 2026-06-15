# PairCoder Simplug Model x Method Comparison

- Models: `qwen2.5:7b`, `qwen2.5-coder:7b`, `llama3.1:8b`, `gemma2:9b`, `mistral:7b`
- Methods: `B0_direct`, `B1_api_list`, `B2_raw_api_docs`, `B3_oracle_api_sequence`, `B4_gold_pair_rule`
- Tasks: 6 pair-critical simplug tasks
- Temperature: `0.2`
- Runs per condition: `3` (pair_pass uses majority vote across runs)
- Evaluation: AST-based checker for plugins_context parameter semantics, get_plugin return-flow, and disable -> hook call.

| Model | Method | Tasks | Runs | Static validity | Pair pass | Pair violation rate |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5:7b | B0_direct | 6 | 3 | 1.00 | 0 | 1.00 |
| qwen2.5:7b | B1_api_list | 6 | 3 | 1.00 | 1 | 0.83 |
| qwen2.5:7b | B2_raw_api_docs | 6 | 3 | 1.00 | 2 | 0.67 |
| qwen2.5:7b | B3_oracle_api_sequence | 6 | 3 | 0.94 | 1 | 0.83 |
| qwen2.5:7b | B4_gold_pair_rule | 6 | 3 | 1.00 | 5 | 0.17 |
| qwen2.5-coder:7b | B0_direct | 6 | 3 | 1.00 | 0 | 1.00 |
| qwen2.5-coder:7b | B1_api_list | 6 | 3 | 1.00 | 0 | 1.00 |
| qwen2.5-coder:7b | B2_raw_api_docs | 6 | 3 | 1.00 | 0 | 1.00 |
| qwen2.5-coder:7b | B3_oracle_api_sequence | 6 | 3 | 1.00 | 0 | 1.00 |
| qwen2.5-coder:7b | B4_gold_pair_rule | 6 | 3 | 1.00 | 6 | 0.00 |
| llama3.1:8b | B0_direct | 6 | 3 | 0.83 | 0 | 1.00 |
| llama3.1:8b | B1_api_list | 6 | 3 | 1.00 | 0 | 1.00 |
| llama3.1:8b | B2_raw_api_docs | 6 | 3 | 1.00 | 0 | 1.00 |
| llama3.1:8b | B3_oracle_api_sequence | 6 | 3 | 1.00 | 0 | 1.00 |
| llama3.1:8b | B4_gold_pair_rule | 6 | 3 | 1.00 | 5 | 0.17 |
| gemma2:9b | B0_direct | 6 | 3 | 1.00 | 0 | 1.00 |
| gemma2:9b | B1_api_list | 6 | 3 | 1.00 | 2 | 0.67 |
| gemma2:9b | B2_raw_api_docs | 6 | 3 | 1.00 | 3 | 0.50 |
| gemma2:9b | B3_oracle_api_sequence | 6 | 3 | 1.00 | 3 | 0.50 |
| gemma2:9b | B4_gold_pair_rule | 6 | 3 | 1.00 | 6 | 0.00 |
| mistral:7b | B0_direct | 6 | 3 | 1.00 | 0 | 1.00 |
| mistral:7b | B1_api_list | 6 | 3 | 0.94 | 0 | 1.00 |
| mistral:7b | B2_raw_api_docs | 6 | 3 | 1.00 | 0 | 1.00 |
| mistral:7b | B3_oracle_api_sequence | 6 | 3 | 1.00 | 3 | 0.50 |
| mistral:7b | B4_gold_pair_rule | 6 | 3 | 1.00 | 3 | 0.50 |

## Pair Violation Rate Matrix

| Method | qwen2.5:7b | qwen2.5-coder:7b | llama3.1:8b | gemma2:9b | mistral:7b |
|---|---:|---:|---:|---:|---:|
| B0_direct | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B1_api_list | 0.83 | 1.00 | 1.00 | 0.67 | 1.00 |
| B2_raw_api_docs | 0.67 | 1.00 | 1.00 | 0.50 | 1.00 |
| B3_oracle_api_sequence | 0.83 | 1.00 | 1.00 | 0.50 | 0.50 |
| B4_gold_pair_rule | 0.17 | 0.00 | 0.17 | 0.00 | 0.50 |

## Interpretation Guide

- `B3_oracle_api_sequence` gives the correct API order but does not state pair constraints.
- The problem-existence claim is supported when `B3_oracle_api_sequence` still has non-zero pair violations on a stronger model.
- `B4_gold_pair_rule` is an oracle upper-bound condition, not the final automatic PairCoder system.