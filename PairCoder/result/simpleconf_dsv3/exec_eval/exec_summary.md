# Execution-oracle summary: simpleconf

- Models: openai:deepseek-ai/DeepSeek-V3
- Tasks: 18; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 2 | 18 | 0.11 |
| B1_api_list | 18 | 18 | 1.00 |
| B2_raw_api_docs | 7 | 18 | 0.39 |
| B3_oracle_api_sequence | 4 | 18 | 0.22 |
| B4_gold_pair_rule | 18 | 18 | 1.00 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.00 | 0.00 | 0.00 | 0.67 | 0.00 |
| B1_api_list | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 0.33 | 0.00 | 1.00 | 1.00 | 0.25 |
| B3_oracle_api_sequence | 0.00 | 0.00 | 0.00 | 1.00 | 0.25 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.17 | 0.11 | 0.00 |
| B1_api_list | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 0.83 | 0.22 | 0.00 |
| B3_oracle_api_sequence | 0.50 | 0.11 | 0.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 |
