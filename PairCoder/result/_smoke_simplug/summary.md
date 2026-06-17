# PairCoder Simplug Model x Method Comparison

- Models: `qwen2.5:7b`
- Methods: `B0_direct`
- Tasks: 1 pair-critical simplug tasks
- Temperature: `0.2`
- Runs per condition: `1` (pair_pass uses majority vote across runs)
- Evaluation: AST-based checker for plugins_context parameter semantics, get_plugin return-flow, and disable -> hook call.

| Model | Method | Tasks | Runs | Static validity | Pair pass | Pair violation rate |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5:7b | B0_direct | 1 | 1 | 1.00 | 0 | 1.00 |

## Pair Violation Rate Matrix

| Method | qwen2.5:7b |
|---|---:|
| B0_direct | 1.00 |

## Interpretation Guide

- `B3_oracle_api_sequence` gives the correct API order but does not state pair constraints.
- The problem-existence claim is supported when `B3_oracle_api_sequence` still has non-zero pair violations on a stronger model.
- `B4_gold_pair_rule` is an oracle upper-bound condition, not the final automatic PairCoder system.