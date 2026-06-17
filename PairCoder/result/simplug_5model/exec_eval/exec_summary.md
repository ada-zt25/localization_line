# Execution-oracle summary: simplug

- Models: qwen2.5:7b, qwen2.5-coder:7b, llama3.1:8b, gemma2:9b, mistral:7b
- Tasks: 10; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 11 | 50 | 0.22 |
| B1_api_list | 10 | 50 | 0.20 |
| B2_raw_api_docs | 14 | 50 | 0.28 |
| B3_oracle_api_sequence | 14 | 50 | 0.28 |
| B4_gold_pair_rule | 30 | 50 | 0.60 |
| B5_loop | 13 | 50 | 0.26 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 1.00 | 0.00 | 0.00 | 0.00 | 0.10 |
| B1_api_list | 0.80 | 0.00 | 0.00 | 0.20 | 0.00 |
| B2_raw_api_docs | 0.70 | 0.00 | 0.00 | 0.30 | 0.40 |
| B3_oracle_api_sequence | 1.00 | 0.00 | 0.00 | 0.10 | 0.30 |
| B4_gold_pair_rule | 0.80 | 0.60 | 0.80 | 0.70 | 0.10 |
| B5_loop | 0.80 | 0.10 | 0.10 | 0.30 | 0.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.40 | 0.25 | 0.00 |
| B1_api_list | 0.27 | 0.25 | 0.07 |
| B2_raw_api_docs | 0.40 | 0.40 | 0.00 |
| B3_oracle_api_sequence | 0.40 | 0.40 | 0.00 |
| B4_gold_pair_rule | 0.60 | 0.55 | 0.67 |
| B5_loop | 0.33 | 0.30 | 0.13 |
