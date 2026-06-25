# prelim_localization — 代码地图（行级故障定位 EGL）

研究目标:给一个 GitHub issue,在仓库里定位**该改哪几行**(line-level fault localization)。
SOTA 参照 = **ARISE**(arXiv 2605.03117,Qwen2.5-Coder-32B,SWE-bench Lite,行 R@{1,5,10}=41/62/74)。

> 全部 18 个 `.py` 都是**活代码**(经依赖审计确认,含惰性 import,无废弃文件)。文件保持扁平布局,
> 因为三个模块用 `HERE` 相对路径**拥有大体量资产**:`p0_line_recall`→`cache/`(142MB)+`.key`、
> `repo_snapshot`→`snapshots/`(6GB)、`egl_e2e`/`egl_headtohead`→`egl_cov_cache.json`(54MB)。
> 物理移动这些会重指向路径、触发重下载/重收集。改动按下面四类组织。

---

## 1. CORE — 数据层 + 行定位方法核心
| 文件 | 交付了什么 |
|---|---|
| `p0_line_recall.py` | SWE-bench 数据加载 / patch 解析 / `fetch_file` 工具(被 15 个模块导入的**中枢**)+ 文件内行召回 harness。**拥有 `cache/` 与 `.key`**。 |
| `code_graph.py` | 纯 `ast` 的多粒度程序图(def-use 数据流切片、`line_scores_v2`)—— ARISE 风格的图信号来源。 |
| `region_loc.py` | **方法核心**:区域收窄 → 自一致性投票 → 排序(`_rank_v0`/`_rank_counts`/`llm_final_pick`)。自带 file-given 评测 `__main__`。 |
| `hybrid_loop.py` | 静态+动态执行反馈定位器;同时导出 `_llm`/`RANK_PROMPT`/`parse_ranked`(被 ~7 模块共用的 LLM 工具)。 |
| `p1_realistic.py` | file-not-given 两阶段 harness;提供 repo-tree / Stage-1 复用 helper。 |

## 2. FILE_LOC — Stage-A 文件定位（冻结后复用，不必每次重跑）
| 文件 | 交付了什么 |
|---|---|
| `arise_file_loc.py` | ARISE 风格 agent 文件定位(程序图 + ReAct 循环)—— 口径对齐的参照文件查找器。 |
| `file_localize.py` | Agentless 单发强检索文件前端;可选 LLM listwise 重排。 |
| `repo_snapshot.py` | 从 GitHub tarball 只读检出仓库快照。**拥有 `snapshots/`(6GB)**。 |

## 3. COVERAGE — 动态半边（Q3：执行覆盖率信号）
| 文件 | 交付了什么 |
|---|---|
| `cov_collect.py` | 仓库感知的失败测试执行覆盖率收集器(Django `runtests.py` + pytest,Docker 内)。 |
| `p7_crossfile_exec.py` | 跨文件执行证据恢复(traceback + 覆盖率)+ site-packages→repo 路径归一化。 |
| `egl_makeorbreak.py` | 拉 SWE-bench 镜像、打 gold `test_patch`、`coverage.py` 跑失败测试的底层原语。 |
| `egl_cov_prefetch.py` | 独立预取器,与 LLM 阶段并行填充 `egl_cov_cache.json`。 |

## 4. EXPERIMENTS — 驱动 + 离线消融
| 文件 | 交付了什么 |
|---|---|
| `egl_e2e.py` | **主驱动**:端到端 file-not-given、ARISE 对齐、5 臂行定位分解(`--file-loc`/`--coverage`/`--final-pick`/`--dump-substrate`/`--reuse-files`)。 |
| `ablation_rank_sweep.py` | 在导出的 substrate 上**免费离线**扫排序(无 GPU/LLM)。 |
| `stageb_ablation.py` | E6 Stage-B 构件留一消融(file-given)。 |
| `egl_headtohead.py` | 等召回配对 head-to-head 排序器对比 + ARISE/SieveFL 覆盖率臂。 |
| `hybrid_loop_v2.py` | *(遗留但仍被 `egl_headtohead` 引用:`run_coverage`)* 早期行召回最大化定位器。 |
| `hybrid_loop_agentic.py` | *(遗留但仍被 `file_localize`/`hybrid_loop_v2` 引用:`import_neighbors`)* agentic 仓库级循环。 |

---

## 数据资产 & 当前交付物
- **活结果**:`egl_e2e_ARISE_static.json`、`egl_e2e_ARISE_dynamic.json`(bf16 n=300 主结果)、`ablation_rank_sweep.json`、`egl_headtohead.json`、`stageb_ablation_awq.json`。
- **缓存(可再生,勿删/勿提交)**:`cache/`、`snapshots/`、`egl_cov_cache.json`(已 gitignore)。
- **密钥**:`.key`/`.key.old` —— API key,永不移动/打印/提交。
- **文档**:`6.24实验.md`(当前实验记录)、`RUN_PLAN.md`、`archive/`(历史结果)、`logs/`(运行日志)。

## 只调行定位的三档廉价迭代（不必重跑 agentic 文件定位）
| 档位 | 成本 | 命令 |
|---|---|---|
| 纯离线改排序 | 0 LLM | 先 `egl_e2e --dump-substrate` 一次 → `ablation_rank_sweep.py` 离线扫 |
| 只重跑行定位投票 | 分钟级 | `egl_e2e --reuse-files egl_e2e_ARISE_static.json`(冻结文件定位) |
| 纯 file-given 行定位 | 分钟级 | `python region_loc.py --broad --sample N`(直接对 gold 文件,不经文件定位) |
