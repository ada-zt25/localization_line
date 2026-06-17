# Execution-oracle summary: diot

- Models: openai:deepseek-ai/DeepSeek-V3
- Tasks: 12; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 10 | 12 | 0.83 |
| B1_api_list | 10 | 12 | 0.83 |
| B2_raw_api_docs | 12 | 12 | 1.00 |
| B3_oracle_api_sequence | 10 | 12 | 0.83 |
| B4_gold_pair_rule | 12 | 12 | 1.00 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 |
| B1_api_list | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 |
| B2_raw_api_docs | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B3_oracle_api_sequence | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 1.00 | 0.75 | 1.00 |
| B1_api_list | 1.00 | 0.75 | 1.00 |
| B2_raw_api_docs | 1.00 | 1.00 | 1.00 |
| B3_oracle_api_sequence | 1.00 | 0.75 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 |
