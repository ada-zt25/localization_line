# Execution-oracle summary: sqlitedict

- Models: openai:deepseek-ai/DeepSeek-V3
- Tasks: 3; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 3 | 3 | 1.00 |
| B1_api_list | 3 | 3 | 1.00 |
| B2_raw_api_docs | 3 | 3 | 1.00 |
| B3_oracle_api_sequence | 3 | 3 | 1.00 |
| B4_gold_pair_rule | 2 | 3 | 0.67 |

## Pass rate by method x pair_type

| Method | completion-obligation |
|---|---:|
| B0_direct | 1.00 |
| B1_api_list | 1.00 |
| B2_raw_api_docs | 1.00 |
| B3_oracle_api_sequence | 1.00 |
| B4_gold_pair_rule | 0.67 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 1.00 | 1.00 | - |
| B1_api_list | 1.00 | 1.00 | - |
| B2_raw_api_docs | 1.00 | 1.00 | - |
| B3_oracle_api_sequence | 1.00 | 1.00 | - |
| B4_gold_pair_rule | 1.00 | 0.50 | - |
