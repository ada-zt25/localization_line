# Execution-oracle summary: diot

- Models: qwen2.5:7b, qwen2.5-coder:7b
- Tasks: 12; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 17 | 24 | 0.71 |
| B1_api_list | 20 | 24 | 0.83 |
| B2_raw_api_docs | 20 | 24 | 0.83 |
| B3_oracle_api_sequence | 24 | 24 | 1.00 |
| B4_gold_pair_rule | 24 | 24 | 1.00 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.67 | 0.75 | 0.33 | 1.00 | 1.00 |
| B1_api_list | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 |
| B2_raw_api_docs | 0.83 | 0.50 | 1.00 | 0.75 | 1.00 |
| B3_oracle_api_sequence | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 1.00 | 0.56 | 1.00 |
| B1_api_list | 1.00 | 0.75 | 1.00 |
| B2_raw_api_docs | 1.00 | 0.88 | 0.00 |
| B3_oracle_api_sequence | 1.00 | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 1.00 |
