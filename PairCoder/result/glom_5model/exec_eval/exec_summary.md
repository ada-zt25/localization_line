# Execution-oracle summary: glom

- Models: qwen2.5:7b, qwen2.5-coder:7b, llama3.1:8b, gemma2:9b, mistral:7b
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 6 | 50 | 0.12 |
| B1_api_list | 20 | 50 | 0.40 |
| B2_raw_api_docs | 9 | 50 | 0.18 |
| B3_oracle_api_sequence | 6 | 50 | 0.12 |
| B4_gold_pair_rule | 35 | 50 | 0.70 |
| B5_loop | 26 | 50 | 0.52 |

## Pass rate by method x pair_type

| Method | config-return-contract | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|
| B0_direct | 0.00 | 0.30 | 0.20 | 0.00 |
| B1_api_list | 0.33 | 0.40 | 0.47 | 0.40 |
| B2_raw_api_docs | 0.27 | 0.10 | 0.27 | 0.00 |
| B3_oracle_api_sequence | 0.07 | 0.10 | 0.20 | 0.10 |
| B4_gold_pair_rule | 0.73 | 0.50 | 0.73 | 0.80 |
| B5_loop | 0.40 | 0.40 | 0.60 | 0.70 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.20 | 0.10 | - |
| B1_api_list | 0.50 | 0.38 | - |
| B2_raw_api_docs | 0.00 | 0.23 | - |
| B3_oracle_api_sequence | 0.10 | 0.12 | - |
| B4_gold_pair_rule | 0.80 | 0.68 | - |
| B5_loop | 0.40 | 0.55 | - |
