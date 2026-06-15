# Execution-oracle summary: glom

- Models: qwen2.5:7b, qwen2.5-coder:7b
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 3 | 20 | 0.15 |
| B1_api_list | 12 | 20 | 0.60 |
| B2_raw_api_docs | 5 | 20 | 0.25 |
| B3_oracle_api_sequence | 14 | 20 | 0.70 |
| B4_gold_pair_rule | 17 | 20 | 0.85 |

## Pass rate by method x pair_type

| Method | config-return-contract | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|
| B0_direct | 0.00 | 0.50 | 0.17 | 0.00 |
| B1_api_list | 0.67 | 0.50 | 0.83 | 0.25 |
| B2_raw_api_docs | 0.50 | 0.00 | 0.33 | 0.00 |
| B3_oracle_api_sequence | 0.83 | 0.50 | 0.83 | 0.50 |
| B4_gold_pair_rule | 0.83 | 0.75 | 1.00 | 0.75 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.00 | 0.19 | - |
| B1_api_list | 0.75 | 0.56 | - |
| B2_raw_api_docs | 0.00 | 0.31 | - |
| B3_oracle_api_sequence | 0.50 | 0.75 | - |
| B4_gold_pair_rule | 1.00 | 0.81 | - |
