# Pair-violation rate matrix

- Models: 5 | Methods: 5 | Runs/condition: 3 (majority vote)

| Model | B0 direct | B1 api-list | B2 raw-docs | B3 oracle-seq | B4 gold-rule |
|---|---:|---:|---:|---:|---:|
| qwen2.5:7b | 100% | 83% | 67% | 83% | 17% |
| qwen2.5-coder:7b | 100% | 100% | 100% | 100% | 0% |
| llama3.1:8b | 100% | 100% | 100% | 100% | 17% |
| gemma2:9b | 100% | 67% | 50% | 50% | 0% |
| mistral:7b | 100% | 100% | 100% | 50% | 50% |

_Lower is better. Non-zero violations under B0-B3 (no explicit pair rule)
across all models support the problem-existence claim; B4 (gold rule) is the
oracle upper bound showing the problem is solvable once pair knowledge is given._