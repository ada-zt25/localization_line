# Execution-oracle summary: bidict

- Models: qwen2.5:7b, qwen2.5-coder:7b
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 17 | 20 | 0.85 |
| B1_api_list | 18 | 20 | 0.90 |
| B2_raw_api_docs | 15 | 20 | 0.75 |
| B3_oracle_api_sequence | 20 | 20 | 1.00 |
| B4_gold_pair_rule | 17 | 20 | 0.85 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.75 | 1.00 | 0.75 | 1.00 | 0.75 |
| B1_api_list | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 |
| B2_raw_api_docs | 1.00 | 0.50 | 0.75 | 0.75 | 0.75 |
| B3_oracle_api_sequence | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 1.00 | 0.25 | 1.00 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.75 | 0.86 | 1.00 |
| B1_api_list | 1.00 | 1.00 | 0.00 |
| B2_raw_api_docs | 1.00 | 0.79 | 0.00 |
| B3_oracle_api_sequence | 1.00 | 1.00 | 1.00 |
| B4_gold_pair_rule | 1.00 | 0.79 | 1.00 |
