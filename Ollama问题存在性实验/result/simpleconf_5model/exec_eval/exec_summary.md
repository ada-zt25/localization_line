# Execution-oracle summary: simpleconf

- Models: qwen2.5:7b, qwen2.5-coder:7b
- Tasks: 18; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 1 | 36 | 0.03 |
| B1_api_list | 16 | 36 | 0.44 |
| B2_raw_api_docs | 4 | 36 | 0.11 |
| B3_oracle_api_sequence | 8 | 36 | 0.22 |
| B4_gold_pair_rule | 25 | 36 | 0.69 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.00 | 0.00 | 0.25 | 0.00 | 0.00 |
| B1_api_list | 0.33 | 0.42 | 0.75 | 0.33 | 0.50 |
| B2_raw_api_docs | 0.00 | 0.00 | 0.25 | 0.33 | 0.12 |
| B3_oracle_api_sequence | 0.33 | 0.00 | 0.75 | 0.50 | 0.00 |
| B4_gold_pair_rule | 0.83 | 0.42 | 0.75 | 1.00 | 0.75 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.08 | 0.00 | 0.00 |
| B1_api_list | 0.42 | 0.56 | 0.17 |
| B2_raw_api_docs | 0.17 | 0.11 | 0.00 |
| B3_oracle_api_sequence | 0.33 | 0.22 | 0.00 |
| B4_gold_pair_rule | 0.75 | 0.72 | 0.50 |
