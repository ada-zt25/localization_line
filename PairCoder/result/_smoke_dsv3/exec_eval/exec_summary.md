# Execution-oracle summary: glom

- Models: openai:deepseek-ai/DeepSeek-V3
- Tasks: 2; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 1 | 2 | 0.50 |
| B1_api_list | 2 | 2 | 1.00 |
| B4_gold_pair_rule | 2 | 2 | 1.00 |

## Pass rate by method x pair_type

| Method | param-dependency | shared-receiver |
|---|---:|---:|
| B0_direct | 0.00 | 1.00 |
| B1_api_list | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | - | 0.50 | - |
| B1_api_list | - | 1.00 | - |
| B4_gold_pair_rule | - | 1.00 | - |
