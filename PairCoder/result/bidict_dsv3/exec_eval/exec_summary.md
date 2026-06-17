# Execution-oracle summary: bidict

- Models: openai:deepseek-ai/DeepSeek-V3
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 9 | 10 | 0.90 |
| B1_api_list | 10 | 10 | 1.00 |
| B2_raw_api_docs | 9 | 10 | 0.90 |
| B3_oracle_api_sequence | 8 | 10 | 0.80 |
| B4_gold_pair_rule | 10 | 10 | 1.00 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 |
| B1_api_list | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 |
| B3_oracle_api_sequence | 0.50 | 0.50 | 1.00 | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 1.00 | 0.86 | 1.00 |
| B1_api_list | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 1.00 | 1.00 | 0.00 |
| B3_oracle_api_sequence | 1.00 | 0.86 | 0.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 |
