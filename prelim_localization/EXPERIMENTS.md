# 实验代码结构（按 RQ1/2/3 分类）

> 共享底座留在 `prelim_localization/`（`p0_line_recall.py` 数据加载、`code_graph.py` def-use、`cov_collect.py` 失败覆盖、
> `egl_e2e.py`/`region_loc.py` 主流水线）。每个实验脚本头部有 shim：把自身目录+父目录加进 sys.path 并 chdir 到父目录，
> 所以从任意位置 `python rqX/xxx.py` 都能跑。数据缓存（`egl_cov_cache*.json`、`rq3_subsets.json`）在 `prelim_localization/`。
> 运行前缀：`SWEBENCH_DATASET=lite`。

## RQ1 — 行级定位失败的刻画（哪些因素压低 recall）
| 脚本 | 研究问题 | 算力 | 状态 |
|---|---|---|---|
| `rq1/rq1_dimensions.py` | 按 文件定位/文件规模/#gold行/#gold文件/bug类型/仓库 分层 line recall | 离线 | ✅ |

## RQ2 — 证伪 execution coverage 作【直接信号】+ 根因分析
| 脚本 | 研究问题 | 算力 | 状态 |
|---|---|---|---|
| `rq2/crash_coverage_analysis.py` | 崩溃占比/每库；覆盖金标命中率(崩溃vs行为)；覆盖天花板83%+off-path机制；traceback信号 | 离线 | ✅ |
| `rq2/crash_fusion_estimate.py` | traceback 对静态的互补性/增益上限 | 离线 | ✅ |
| `rq3/classify_offpath.py` | 11 个 off-path 崩溃实例机制三分（漏分支6/插入4/函数未达1=11，坐实83%天花板） | 离线 | ✅ |

## RQ3 — 如何用 execution coverage 提升崩溃类行级定位
| 脚本 | 研究问题 | 算力 | 状态 |
|---|---|---|---|
| `rq3/crash_coverage_rank_test.py` | **覆盖当过滤器** 4子集 R@k+MRR+精度(候选缩窄/EXAM)——主结果 +14pp | 离线 | ✅ |
| `rq3/crash_slice_validation.py` | 反向数据流切片(R1/R2/R3，on-path) | 离线 | ✅(切片null) |
| `rq3/crash_region_expand.py` | 沿调用图扩 R2(1/2-hop callee) | 离线 | ✅(扩展null) |
| `rq3/sbfl.py` | SBFL/Ochiai 差分排序器(模块) | — | ✅ |
| `rq3/cov_collect_pass.py` | 采 PASS_TO_PASS / FAIL_TO_PASS 孤立覆盖(Docker) | 本地Docker | ✅ |
| `rq3/rq3_collect_passing.py` | 全量通过覆盖采集驱动(断点续) | 本地Docker | 部分(4 astropy) |
| `rq3/rq3_e3_sbfl_eval.py` | SBFL vs 覆盖过滤 R@k | 离线(需通过覆盖) | ✅(SBFL null) |
| `rq3/find_worked_examples.py` | 论文 worked example 取数：filter救回(django-16873 #40→#6)+off-path漏分支(django-14017) | 离线 | ✅ |

## 数据/子集
- `rq3_subsets.json` — 崩溃/行为 × on/off-path 实例清单（crash_onpath 57 等）
- `egl_cov_cache.json` — 失败测试覆盖（整测试文件，258 例）
- `egl_cov_cache_pass.json` — PASS_TO_PASS 覆盖（4 astropy，SBFL 用）
- `egl_cov_cache_failiso.json` — 孤立 FAIL_TO_PASS 覆盖（4 astropy，SBFL 用）

## ⏳ 待开卡（GPU，未跑）
- RQ3 完整方法(vote+graph+LLM) ± coverage-filter，on-path × {DeepSeek-V3, Qwen-32B, Qwen-7B}：确认离线 +14pp 在完整方法上成立。命令见 `docs/RQ2_RQ3_实验清单.md` RQ3-E4~E8。

> 结果与分析详见 `docs/RQ2_RQ3_实验清单.md`、`docs/RQ2_崩溃类实验方案.md`、`docs/实验进展.md`。
