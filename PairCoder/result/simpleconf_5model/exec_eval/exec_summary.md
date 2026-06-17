# Execution-oracle summary: simpleconf

- Models: qwen2.5:7b, qwen2.5-coder:7b, llama3.1:8b, gemma2:9b, mistral:7b
- Tasks: 18; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 2 | 90 | 0.02 |
| B1_api_list | 29 | 90 | 0.32 |
| B2_raw_api_docs | 7 | 90 | 0.08 |
| B3_oracle_api_sequence | 9 | 90 | 0.10 |
| B4_gold_pair_rule | 48 | 90 | 0.53 |
| B5_loop | 50 | 90 | 0.56 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.00 | 0.00 | 0.10 | 0.07 | 0.00 |
| B1_api_list | 0.27 | 0.40 | 0.50 | 0.27 | 0.20 |
| B2_raw_api_docs | 0.13 | 0.00 | 0.00 | 0.27 | 0.05 |
| B3_oracle_api_sequence | 0.20 | 0.00 | 0.00 | 0.27 | 0.10 |
| B4_gold_pair_rule | 0.67 | 0.33 | 0.70 | 0.73 | 0.50 |
| B5_loop | 0.53 | 0.53 | 0.70 | 0.67 | 0.45 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.03 | 0.02 | 0.00 |
| B1_api_list | 0.27 | 0.33 | 0.40 |
| B2_raw_api_docs | 0.13 | 0.07 | 0.00 |
| B3_oracle_api_sequence | 0.20 | 0.07 | 0.00 |
| B4_gold_pair_rule | 0.53 | 0.58 | 0.40 |
| B5_loop | 0.60 | 0.56 | 0.47 |
