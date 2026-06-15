# Execution-oracle summary: pyparam

- Models: qwen2.5:7b, qwen2.5-coder:7b
- Tasks: 12; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 0 | 24 | 0.00 |
| B1_api_list | 24 | 24 | 1.00 |
| B2_raw_api_docs | 12 | 24 | 0.50 |
| B3_oracle_api_sequence | 19 | 24 | 0.79 |
| B4_gold_pair_rule | 24 | 24 | 1.00 |

## Pass rate by method x pair_type

| Method | config-return-contract | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|
| B0_direct | 0.00 | 0.00 | 0.00 | 0.00 |
| B1_api_list | 1.00 | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 0.50 | 0.67 | 0.50 | 0.25 |
| B3_oracle_api_sequence | 0.88 | 0.67 | 0.83 | 0.75 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.00 | 0.00 | - |
| B1_api_list | 1.00 | 1.00 | - |
| B2_raw_api_docs | 0.50 | 0.50 | - |
| B3_oracle_api_sequence | 0.88 | 0.75 | - |
| B4_gold_pair_rule | 1.00 | 1.00 | - |
