# Execution-oracle summary: simplug

- Models: openai:deepseek-ai/DeepSeek-V3
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 2 | 10 | 0.20 |
| B1_api_list | 6 | 10 | 0.60 |
| B2_raw_api_docs | 6 | 10 | 0.60 |
| B3_oracle_api_sequence | 3 | 10 | 0.30 |
| B4_gold_pair_rule | 9 | 10 | 0.90 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| B1_api_list | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| B3_oracle_api_sequence | 1.00 | 0.00 | 0.00 | 0.50 | 0.00 |
| B4_gold_pair_rule | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.33 | 0.25 | 0.00 |
| B1_api_list | 0.67 | 0.75 | 0.33 |
| B2_raw_api_docs | 0.67 | 0.75 | 0.33 |
| B3_oracle_api_sequence | 0.33 | 0.25 | 0.33 |
| B4_gold_pair_rule | 1.00 | 1.00 | 0.67 |
