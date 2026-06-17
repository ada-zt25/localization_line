# Execution-oracle summary: sqlitedict

- Models: qwen2.5:7b, qwen2.5-coder:7b, llama3.1:8b, gemma2:9b, mistral:7b
- Tasks: 3; runs/condition: 1
- Pass rate = task-level majority vote across runs, averaged over models.

## Pass rate by method

| Method | pass | total | rate |
|---|---:|---:|---:|
| B0_direct | 7 | 15 | 0.47 |
| B1_api_list | 13 | 15 | 0.87 |
| B2_raw_api_docs | 11 | 15 | 0.73 |
| B3_oracle_api_sequence | 6 | 15 | 0.40 |
| B4_gold_pair_rule | 13 | 15 | 0.87 |
| B5_loop | 15 | 15 | 1.00 |

## Pass rate by method x pair_type

| Method | completion-obligation |
|---|---:|
| B0_direct | 0.47 |
| B1_api_list | 0.87 |
| B2_raw_api_docs | 0.73 |
| B3_oracle_api_sequence | 0.40 |
| B4_gold_pair_rule | 0.87 |
| B5_loop | 1.00 |

## Pass rate by method x difficulty

| Method | easy | medium | hard |
|---|---:|---:|---:|
| B0_direct | 0.80 | 0.30 | - |
| B1_api_list | 1.00 | 0.80 | - |
| B2_raw_api_docs | 1.00 | 0.60 | - |
| B3_oracle_api_sequence | 0.80 | 0.20 | - |
| B4_gold_pair_rule | 1.00 | 0.80 | - |
| B5_loop | 1.00 | 1.00 | - |
