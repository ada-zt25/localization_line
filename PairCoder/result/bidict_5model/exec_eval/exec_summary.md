# Execution-oracle summary: bidict

- Models: qwen2.5:7b, qwen2.5-coder:7b, llama3.1:8b, gemma2:9b, mistral:7b
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 30 | 50 | 0.60 |
| B1_api_list | 31 | 50 | 0.62 |
| B2_raw_api_docs | 20 | 50 | 0.40 |
| B3_oracle_api_sequence | 36 | 50 | 0.72 |
| B4_gold_pair_rule | 38 | 50 | 0.76 |
| B5_loop | 41 | 50 | 0.82 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.50 | 0.50 | 0.40 | 0.90 | 0.70 |
| B1_api_list | 0.80 | 0.40 | 0.40 | 0.70 | 0.80 |
| B2_raw_api_docs | 0.50 | 0.20 | 0.40 | 0.40 | 0.50 |
| B3_oracle_api_sequence | 0.80 | 0.40 | 0.50 | 0.90 | 1.00 |
| B4_gold_pair_rule | 0.90 | 0.70 | 0.50 | 0.80 | 0.90 |
| B5_loop | 0.90 | 0.60 | 0.70 | 0.90 | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.60 | 0.63 | 0.40 |
| B1_api_list | 0.80 | 0.66 | 0.00 |
| B2_raw_api_docs | 0.50 | 0.43 | 0.00 |
| B3_oracle_api_sequence | 0.80 | 0.77 | 0.20 |
| B4_gold_pair_rule | 0.80 | 0.77 | 0.60 |
| B5_loop | 0.80 | 0.89 | 0.40 |
