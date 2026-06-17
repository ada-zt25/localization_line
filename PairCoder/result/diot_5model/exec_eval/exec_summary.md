# Execution-oracle summary: diot

- Models: qwen2.5:7b, qwen2.5-coder:7b, llama3.1:8b, gemma2:9b, mistral:7b
- Tasks: 12; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 33 | 60 | 0.55 |
| B1_api_list | 43 | 60 | 0.72 |
| B2_raw_api_docs | 43 | 60 | 0.72 |
| B3_oracle_api_sequence | 35 | 60 | 0.58 |
| B4_gold_pair_rule | 52 | 60 | 0.87 |
| B5_loop | 45 | 60 | 0.75 |

## Pass rate by method x pair_type

| Method | config-return-contract | lifecycle | param-dependency | return-flow | shared-receiver |
|---|---:|---:|---:|---:|---:|
| B0_direct | 0.40 | 0.40 | 0.40 | 0.80 | 0.90 |
| B1_api_list | 0.80 | 0.80 | 0.40 | 0.90 | 0.80 |
| B2_raw_api_docs | 0.53 | 0.60 | 0.80 | 0.90 | 0.80 |
| B3_oracle_api_sequence | 0.40 | 0.70 | 0.27 | 0.80 | 1.00 |
| B4_gold_pair_rule | 0.73 | 0.90 | 1.00 | 0.90 | 0.80 |
| B5_loop | 0.80 | 0.90 | 0.40 | 1.00 | 0.80 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.87 | 0.47 | 0.20 |
| B1_api_list | 0.80 | 0.70 | 0.60 |
| B2_raw_api_docs | 0.80 | 0.72 | 0.40 |
| B3_oracle_api_sequence | 0.93 | 0.45 | 0.60 |
| B4_gold_pair_rule | 0.87 | 0.85 | 1.00 |
| B5_loop | 0.93 | 0.65 | 1.00 |
