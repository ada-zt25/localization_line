# Six-library full-run analysis (5 models, run-level)

Total (model x task) generations per method: 315

## 1. Pass rate by method x library

| lib | pairs | B0 | B1 | B2 | B3* | B4 | B5_loop |
|---|--:|--:|--:|--:|--:|--:|--:|
| simplug | 50 | 0.22 | 0.20 | 0.28 | 0.28 | 0.60 | 0.26 |
| diot | 60 | 0.55 | 0.72 | 0.72 | 0.58 | 0.87 | 0.75 |
| simpleconf | 90 | 0.02 | 0.32 | 0.08 | 0.10 | 0.53 | 0.56 |
| glom | 50 | 0.12 | 0.40 | 0.18 | 0.12 | 0.70 | 0.52 |
| bidict | 50 | 0.60 | 0.62 | 0.40 | 0.72 | 0.76 | 0.82 |
| sqlitedict | 15 | 0.47 | 0.87 | 0.73 | 0.40 | 0.87 | 1.00 |
| **all** | 315 | 0.28 | 0.46 | 0.33 | 0.34 | 0.69 | 0.60 |

## 2. By pair_type (pooled across libs)

| pair_type | pairs | B1 | B3* | B4 | B5_loop | B5_loop−B3* | fill=(B5−B1)/(B4−B1) | McNemar p (B5_loop vs B3*) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| param-dependency | 55 | 0.35 | 0.18 | 0.73 | 0.45 | +0.27 | 29% | 0.001 |
| return-flow | 60 | 0.48 | 0.42 | 0.77 | 0.68 | +0.27 | 71% | 8.6e-04 |
| shared-receiver | 60 | 0.40 | 0.43 | 0.60 | 0.57 | +0.13 | 83% | 0.115 |
| config-return-contract | 65 | 0.57 | 0.43 | 0.75 | 0.66 | +0.23 | 50% | 0.003 |
| lifecycle | 60 | 0.40 | 0.18 | 0.53 | 0.53 | +0.35 | 100% | 1.9e-05 |
| completion-obligation | 15 | 0.87 | 0.40 | 0.87 | 1.00 | +0.60 | n/a | 0.004 |
| **all** | 315 | 0.46 | 0.34 | 0.69 | 0.60 | +0.27 | 63% | 2.0e-15 |

## 3. McNemar exact paired tests (pooled, two-sided)

| comparison A vs B | b (A>B) | c (B>A) | discordant | p |
|---|--:|--:|--:|--:|
| B5_loop vs B3* | 102 | 18 | 120 | 2.0e-15 |
| B5_loop vs B1 | 52 | 8 | 60 | 5.2e-09 |
| B5_loop vs B4 | 30 | 56 | 86 | 0.007 |
| B4 vs B3* | 132 | 22 | 154 | 2.6e-20 |
