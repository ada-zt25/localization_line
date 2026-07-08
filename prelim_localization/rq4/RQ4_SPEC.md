# RQ4 实验契约（防跑偏 harness · 锁定后只读）

> 本文件是**唯一事实源**。开卡前全部设计完成；开卡后只按 §8 的 `run_all.py` 一次跑完。
> 任何与本文件冲突的改动都视为跑偏。修改本文件需显式记 changelog（文末）。

## 0. 不可变目标 & 锁定决策
**目标**：在 **崩溃类(crash) 且 on-path** 的实例上，验证并**最大化** execution coverage 对**行级定位 recall** 的提升（= RQ4 尝试）。**评测口径 = file-given（给定金标文件）**：file 定位只是上游闸门（RQ1 已刻画），**不在 RQ4 研究范围**；M0..M4 在**同一金标文件**上配对评测，把"覆盖率对行排序的作用"从 file-loc 噪声中干净隔离（与 `docs/memory.md` 已锁口径一致）。

**锁定决策（用户 2026-06-28 确认，不再改）**
- **Backbone = `Qwen2.5-Coder-32B-Instruct`**（与 ARISE 同口径；file/line 全用它）。
- **评测口径 = file-given / oracle 金标文件**（`--reuse-files` 喂 `ranked_files=[gold_file]`，旁路 file-loc）。
- **RQ4 成功口径 = 内部增益为主**：主结论是 crash on-path 上 `M0(ours-static) → M4(coverage-max)` 的 line R@k 提升（bootstrap 95% CI of Δ 不含 0）。**ARISE 41/62/74 是端到端口径，与本 file-given 口径不可直接比绝对值**，仅作机理对照。
- **范围 = file-given 行定位（过夜级）**：RQ4 coverage 配置网格(crash on-path, oracle 文件) + bootstrap 显著性。**不跑 file-loc**（已剔出关键路径，见 changelog v2）。一次跑完。

## 1. 冻结子集（locked；运行期**只读** `rq4/frozen_subsets.json`，禁止重新推导）
划分逻辑 = `rq3/crash_coverage_rank_test.py` 同款：`is_crash`(traceback/≥2 frame/assertRaises) × `on-path`(≥1 gold 行 ∈ 失败测试覆盖)。每实例取首个有 region 的 `.py` gold 文件。
- **S1 = crash · on-path（主集）** —— RQ4 全部主结论在此。
- S2 behav·on-path / S3 crash·off-path / S4 behav·off-path —— **仅作负对照**，不进主结论。
- `frozen_subsets.json` 固化：每实例 `instance_id, gold_file, gold_lines, exec_lines(该文件), repo, base_commit, subset`。
- 子集大小以该文件为准（解决历史上 131 vs 132 不一致）；论文/结果一律引用该文件的 n。

## 2. 指标 & 基线
**指标**：line **R@{1,5,10}**、**MRR**、**候选集大小**(撒网宽度)。显著性：对 Δ(method−baseline) 做 **bootstrap 95% CI**（≥10000 重采样，按实例配对）。
**基线（事实，勿改）**
| 来源 | 口径 | file R@1/3(/5/10) | line R@1/5/10 |
|---|---|---|---|
| **ARISE（外部参照）** | 全300, Qwen-32B | 67 / 82 | 41 / 62 / 74 |
| 我方现状 file-loc | 全300（`egl_e2e_ARISE_dynamic.json`） | 63.3 /—/ 71.7 / 73.7 | — |
| 我方 line 各臂(全300) | arise_static | — | 8.7/16.3/22.0 |
| | vote_only / ours_static / ours_dynamic | — | 25/37.7/42 · 24/36.3/41.7 · 27.7/39.3/43 |
| 我方 file-given 过滤(Table5) | S1 crash·on-path, n=57 | — | static 10.5/28.1/**29.8** → filter 14.0/29.8/**43.9** (+14.1pp) |

## 3. Task 1 —— File 定位 ≥ ARISE（**可选·已剔出 RQ4 关键路径，见 changelog v2**）
> **不在本轮 RQ4 范围**：file-given 口径下不需要 file-loc。以下保留为独立可选实验（`run_all.py --task fileloc`）；想单独做端到端/对标 file 定位时再跑，**不进过夜主序列、不影响 RQ4 结论**。
**（可选）目标**：n=300、Qwen-32B 上 **file R@1 ≥ 67 且 R@3 ≥ 82**。
**做法（全部 recall-safe：只并集/重排，绝不丢候选）**——基于已有 `arise_file_loc.py`(agentic) + `file_localize.py`(agentless+embed+rerank)：
- L1 base：`localize_files_arise`（ARISE 式 agentic，program-graph + 工具 API），`--arise-turns` 调。
- L2 listwise rerank：`llm_file_rerank` 重排 top-N（抬 R@1）。
- L3 retrieval 补召回：embedding/BM25 与 LLM 选择**轮转并集**（抬 R@3/5）。
- L4 import-graph 扩展：top-k 的 importers/importees 1-hop 并入（ARISE 用 import 边）。
- L5 self-consistency：file-loc 跑 m 次，RRF 并集（抬 R@3/5）。
**实验**：`file_loc_sweep` 在 n=300 上扫 {L1, L1+L2, L1+L2+L3, +L4, +L5} → 选**首个达标**且最省 token 的配置 = `FILELOC_FROZEN`。产物 `rq4/results/fileloc_sweep.json`（每配置 file R@{1,3,5,10}+token/turn）。
**失败处置**：若无配置达标，报告最优配置 + 差距（是 finding，不无限调）。

## 4. Task 2 —— RQ4：最大化 coverage 对 line recall 的作用（crash on-path）
覆盖率可用的 5 个杠杆（来自现有代码）：① **filter**(候选 ∩ executed，已证 +14pp) ② **score 项** `δ·covered`(`line_scores_v2`) ③ **function-boost**(`rank_functions` 执行函数 +1.5，进 region) ④ **coverage-收窄 region/vote**(只把 executed 行喂给 LLM 投票) ⑤ **coverage-seeded slice**(用 executed∩issue 行做 def-use 切片种子)。

### 4a. 离线天花板（**无 GPU，现在就能跑** = `lineloc_offline.py`）
在 S1（+S2/S3/S4 对照）上，def-use 排序器的覆盖率消融：
- A 静态(`use_coverage=False`) —— 基线
- B filter(A ∩ executed) —— 复现 +14pp
- C score(`use_coverage=True`,δ 默认) —— 仅打分项
- D filter+score(`use_coverage=True` 排序后再 ∩ executed)
- E δ-sweep(δ∈{0.8,1.5,3,6})×filter —— 找最优覆盖权重
- F **coverage-max(offline)** = best(B..E) 组合
出：每臂 R@{1,5,10}+MRR+候选数 + **Δ(F−A) 的 bootstrap CI**。产物 `rq4/results/lineloc_offline.json`。
**意义**：确立"纯 def-use 排序器下 coverage 的提升上限"，开卡前锁死、并验证代码正确。

> **【已跑·2026-06-28 结论，定 GPU 方向】** S1(n=57) 离线天花板：
> - A 静态 R@10=29.8 → **B filter R@10=43.9（+14.1pp，复现）**；候选 837→378。
> - **C(score 项) / D(filter+score) / E(δ∈{0.8,1.5,3,6}) 全部 = B**：coverage 的**打分项与 δ 调权对排序零增益**（印证 RQ2.4：覆盖不能"排序"）。
> - **∴ 离线唯一有效杠杆 = filter；天花板锁死在 43.9 R@10。δ-sweep 作废，GPU 不再扫 δ。**
> - 显著性：Δ(F−A) **R@10=+14.0pp，95%CI[+3.5,+24.6] 显著**；R@1=+3.5pp CI[0,+8.8]、R@5=+1.8pp CI[-3.5,+8.8] **不显著**（n=57 偏小）。
> - 负对照成立：S3/S4 off-path filter→0；S2 behav on-path filter +6.9pp（on-path 通用，非崩溃专属）。
> **推论**：要"最大化"且超过 43.9 天花板，增益**只能来自 LLM 侧**（M2 coverage-收窄 region+vote 让 LLM 在 executed 集内重排），这正是 GPU 唯一值得验的杠杆。

### 4b. file-given 含-LLM 行定位（**开卡跑** = `run_all.py --task e2e`）
在 S1 上**给定金标文件（oracle，`--reuse-files` 喂 `ranked_files=[gold_file]`）**，跑 region→k-vote→RRF 流水线的覆盖率消融。file 定位被 oracle 旁路 → 行定位被干净隔离。
**因离线已证 score/δ 无效 → GPU 只验 LLM 侧杠杆**：
- M0 ours-static（pipeline，无 coverage）—— **配对基线**
- M1 +filter（投票/排序后 ∩ executed，on-path 安全）—— 复现离线 filter 于完整流水线
- M2 +coverage-收窄 region+vote（**只把 executed 行编号喂给 LLM 投票** → LLM 在 executed 集内重排）—— **唯一可能超 43.9 天花板的杠杆**
- M3 = M1 + function-boost（执行函数进 region，抬 region 召回上限）
- M4 **coverage-max(full)** = M1+M2+M3 —— **RQ4 方法**
- 参照臂：vote_only、arise_static（口径锚）。**外部参照 ARISE 41/62/74 是端到端口径，不与本 file-given 绝对值比较**，仅机理对照。
- （**不含 δ-sweep**：离线已证零增益；**不含 file-loc**：oracle 旁路）
出：S1 上 M0 vs M4 的 line R@{1,5,10}+MRR + **Δ bootstrap CI**（file-given）。产物 `rq4/results/lineloc_e2e.json`。
**主结论**：M4 − M0 在 S1 显著 >0（CI 不含 0）= "coverage 最大化提升崩溃 on-path 行级 recall"。**核心假设**：M2（LLM 在 executed 集内投票）能否超过离线 filter 天花板 43.9。

> **【已跑·2026-06-28 端到端结果】** S1(n=57, file-given, 完整流水线): M0 29.8/50.9/56.1 → **M4 35.1/52.6/68.4**；**M4−M0 R@10 = +12.3pp, 95%CI[1.8,22.8] 显著**；R@1(+5.3)/R@5(+1.8) 不显著。**M3−M0=0**(覆盖打分项零增益,印证离线)。诊断:覆盖把金标从 rank>10 捞进 **6-10 区**(非 top-5),即只抬"可达性"不抬"判别力";多行修复总召回 −0.002、单行 +0.091。→ 催生 §4c。

### 4c. M5 —— 断言倒推 reranker（攻 R@1/R@5，coverage 的正交信号）
**动机**：上面诊断显示 coverage 在 ~41 条执行行里**无法判别**哪条是 bug(精度 0.084)——它是 membership 信号、不能排序。攻 R@1/R@5 需要**和覆盖率正交**的信号。
**信号 = 失败测试的断言(expected vs observed)**：memory 验证过的、唯一同模型/推理期/正交的信号(vote-count、exec-flag、def-use 都与冻结候选集同源→塌成噪声)。
**M5** = M2(coverage-收窄投票)+ `region_loc.assertion_rerank`：抽证据(`test_evidence.extract_test_evidence`= FAIL_TO_PASS 名 + test_patch 断言 + issue traceback),让 LLM 在 cov-narrowed 候选 top-N 上**倒推"哪条产生了错误值/根因"**重排头部。**recall-safe**(只动 head、保 R@10 尾;空证据/解析失败/报错→回退原序)。+1 次 LLM 调用/实例。
**臂/产物**：PASS_C = `--cov-narrow --dump-substrate --assert-rerank 10` → 臂 `ours_m5`；`run_all` 出 **M5−M0、M5−M4 的 bootstrap CI**(M5−M4 下界>0 = 断言倒推在覆盖收窄之上确加判别力)。
**判据**：M5 成功 = R@1 或 R@5 的 M5−M0(或 M5−M4)95%CI 下界>0。**不显著也是结论**("覆盖+断言推理仍攻不动精确定位",印证执行信号天花板,可发表)。
**离线已验**(`rq4/smoke_m5.py`,无 API):recall-safe + 三种回退 + 57/57 有证据,**全过**。
**算力**：下次开卡**只跑 PASS_C**(passA/B 已缓存),~57 实例 ×~8 调用,几分钟。

### 4d. M_hetero —— 异构强验证器 **upper-bound** 消融臂（显式标注·可选·破同模型可比性）
**授权**：护栏原文（`docs/实验进展.md`）"裁判这条路放弃……**除非引入异构强模型当显式标注的 upper-bound 消融臂**（破同模型可比性，标可选）"。本臂即此口子的落地。
**动机**：M4−M0 只抬 R@10（可达性）、不抬 R@1/R@5（判别力，RQ3.4）。问题：这个判别力天花板是**任务本身给的**，还是**弱验证器（同模型自洽）给的**？换异构强验证器若能抬 R@1/R@5，则天花板非本质 → 生成器–验证器不对称的干净实验。
**M_hetero（离线·无新调用）** = 逐实例 **oracle 选择**：base(Qwen2.5-Coder-32B M4)与更强异构模型(DeepSeek-V3.2 M4，T2 已缓存)两者中取把金标排更高者。**显式 upper bound**（oracle 路由，非可部署）：它上界化"理想异构验证器能恢复多少判别力"。**不新调 API**（用 T2 逐实例命中缓存）；**不动 backbone/口径/指标**；S1 file-given n=57；base 主线不变，M_hetero 单列、标 upper-bound。
**臂/产物**：`rq4/m_hetero_upper.py` → `results/m_hetero_upper.json`（schema 全带；per-instance 命中留存）。报 base_M4、strong_M4、UB(base⊕strong)、UB(best-of-fleet) 及 **Δ(UB−base) 的配对 bootstrap 95%CI**。
**判据**：UB−base 的 R@1/R@5 CI 下界>0 ⇒ 判别力天花板**非本质**、异构验证器值得建（可部署版=future work）；若≈0 ⇒ 天花板本质，coverage/自洽都够不着。**两种结论都可发表**。
**已跑（2026-07-01，离线上界）**：base 35.1/52.6/68.4 → **UB(base⊕DeepSeek-V3.2) 49.1/70.2/87.7**；ΔR@1 **+14.0pp[5.3,22.8]**、ΔR@5 **+17.6[8.8,28.1]**、ΔR@10 **+19.3[10.5,29.8]**，**全显著** ⇒ 判别力可由异构信号恢复。best-of-fleet(全4) 56.1/75.4/87.7。

**M_hetero-real（真·可部署验证器重排，2026-07-01 API 跑，`rq4/m_hetero_real.py`）**：DeepSeek-V3.2 在 Qwen 的 cov-narrowed region 候选上、只看 issue+代码（**无 gold**）重排 top-10。候选=passB substrate.region；源码 GitHub raw 拉取缓存 `cache/src/`；key 走 `.t2_secrets`（gitignored，跑完轮换）。结果(n=57)：**42.1/64.9/77.2**，Δ vs Qwen-M4 **+7.0/+12.3/+8.8pp，全 n.s.（CI 含 0，n=57 偏小）** ⇒ 真验证器**兑现约一半上界**、无 gold。产物 `results/m_hetero_real.json`(+`_perinst.jsonl`)。合规：单独臂、显式标"real/deployable"、不动主线 backbone/口径/指标。

## 5. 实验清单 manifest（每项 = 脚本·输入·产物·算力·状态）
| ID | 脚本 | 输入 | 产物 | 算力 | 状态 |
|---|---|---|---|---|---|
| F0 | `freeze_subsets.py` | rows + egl_cov_cache | `frozen_subsets.json` | CPU | 现在 |
| L0 | `lineloc_offline.py` | frozen_subsets + caches | `results/lineloc_offline.json` | CPU | 现在 |
| T1（可选）| `run_all.py --task fileloc` | 全300 | `results/fileloc_sweep.json` | GPU | **剔出主序列** |
| T2 | `run_all.py --task e2e` | S1 + **oracle 金标文件** | `results/lineloc_e2e.json` | **GPU** | 开卡(主) |
| T3 | `run_all.py --task sig` | 上述 json | `results/significance.json` | CPU | 开卡后即跑 |
| H1 | `m_hetero_upper.py` | T2 逐实例命中缓存(4 backbone) | `results/m_hetero_upper.json` | CPU(离线) | ✓ 已跑 2026-07-01 |
| H2 | `m_hetero_real.py` | passB substrate.region + GitHub src + DeepSeek-V3.2 API | `results/m_hetero_real.json` | API(~57 调用) | ✓ 已跑 2026-07-01 |
| B4 | `../rq3/datalevel_classifier.py` | `cache/swebench_lite_pool_300.json` | `results/datalevel_scale.json` | CPU(离线) | ✓ 已跑 2026-07-01 |
| ✓ | `run_all.py --verify` | 所有产物 | 完整性报告 | CPU | 收尾 |

## 6. 成功/失败判据（**开跑前定死，null 也是结果**）
- **RQ4 成功** = S1 上 `M4−M0` 的 line R@10 Δ 的 95% bootstrap CI **下界 > 0**（file-given）。否则如实记"覆盖率在完整流水线上提升不显著"（仍是可发表的 boundary 结果）。
- **可信度三条件（写论文必守）**：① 正文/表题明标 **file-given / oracle 文件**，不冒充端到端；② 主张 = 配对内部增益（M4−M0，同实例同金标文件，bootstrap CI）；③ **不拿 file-given 绝对数比 ARISE 41/62/74（端到端、口径不同）**。
- **（可选）Task1** = file R@1≥67 ∧ R@3≥82。不在主序列；不达标不影响 RQ4。
- **不追指标**：任何臂为 null/负，记录即停，不在该臂上无限调参。

## 7. 防跑偏护栏（DO / DON'T）
**DO**：① 一切经 `run_all.py`；② 每个产物 JSON 带 `{config, model, base_url, git_sha, n, metrics}` schema；③ 运行期只读 `frozen_subsets.json`；④ 断点续跑（已存在产物跳过）；⑤ 每臂记原始 per-instance 命中，便于 bootstrap 复算。
**DON'T**：① 运行期重新推导/改子集；② 加 manifest 之外的新臂；③ 中途改指标/口径/backbone；④ 把 behav/off-path 结论混入主结论；⑤ 改 §0/§1/§2（要改先写 changelog）。

## 8. 一次跑完流程（开卡后）
```bash
cd prelim_localization
export MODEL=Qwen2.5-Coder-32B-Instruct OPENAI_BASE_URL=<vllm/api> OPENAI_API_KEY=<key> SWEBENCH_DATASET=lite
python rq4/run_all.py --task e2e       # T2(主) → M0..M4 on S1（oracle 金标文件，file-given）
python rq4/run_all.py --task sig       # T3 → bootstrap CI
python rq4/run_all.py --verify         # 完整性 + 汇总表
# （可选，不在主序列）python rq4/run_all.py --task fileloc   # 单独跑 file-loc 对标 ARISE
```
全程断点续跑；中断后重跑同命令自动跳过已完成项。**默认主序列不含 file-loc**（见 changelog v2）。

## Changelog
- 2026-07-01 v4：**新增 M_hetero 异构强验证器 upper-bound 消融臂（§4d）+ B4 数据集级 data-level 近似分类器**。M_hetero：护栏允许的"异构强模型 upper-bound"落地，逐实例 oracle 选择 base(Qwen2.5) 与 DeepSeek-V3.2，**离线用 T2 缓存命中、不新调 API、不动 backbone/口径/指标**，显式标 upper-bound。已跑：ΔR@1 +14.0pp[5.3,22.8]、ΔR@5 +17.6[8.8,28.1] 全显著 → 判别力天花板非本质（生成器–验证器证据）。B4：patch-结构近似分类器（新增分支实体化 ⇒ CF，否则 data-level），对 n=9 SBFL 真值 **8/9(89%)** 一致，外推全 300 得 data-level=66.3% Wilson[60.8,71.4]，把 §7"以数据级为主"从 n=9 扩到数据集级。产物 `results/m_hetero_upper.json`、`results/datalevel_scale.json`。均为**离线新增分析臂**（非运行期改子集/指标），合规。理由：正面回答 RQ4"什么信号破判别力天花板"+ 补强 §7 普适断言。
- 2026-07-01 v4.1：**M_hetero 增真·可部署版 M_hetero-real（H2）**。DeepSeek-V3.2 经 SiliconFlow API 在 Qwen cov-narrowed region 候选上**无 gold**重排；n=57 得 42.1/64.9/77.2，Δ vs Qwen-M4 +7.0/+12.3/+8.8pp 全 n.s.（兑现约一半 oracle 上界）。API key 走 gitignored `.t2_secrets`（跑完轮换），源码缓存 `cache/src/`，产物带完整 schema。补 §7 Table 9（含 M_hetero 三档 + real + B4 两规则）。修正 M_hetero_upper 的 bootstrap 种子（`hash()` 每进程随机→改 `KS.index(k)` 确定性），R@1 CI [5.3,24.6]→[5.3,22.8]。
- 2026-06-28 v1：初版，锁定 §0 决策。
- 2026-06-28 v3：**新增 M5 臂(断言倒推 reranker)**——经 RQ4 端到端诊断(M4−M0 仅 R@10 显著、R@1/5 不动:coverage 只抬可达性、不抬判别力;精度 0.084)定向补的杠杆。M5 = M2 + `assertion_rerank`(用失败测试 expected-vs-observed 这个**与覆盖率正交**的信号倒推根因行,recall-safe)。新增 `test_evidence.py`、`region_loc.assertion_rerank`、`egl_e2e --assert-rerank`、PASS_C/`ours_m5`,sig 加 M5−M0/M5−M4。离线 `smoke_m5.py` 全过。详见 §4c。理由:这是攻 R@1/R@5 唯一正交、未试过的杠杆。
- 2026-06-28 v2：**file 定位剔出 RQ4 关键路径**（用户决定：只研究行定位）。口径回到 `docs/memory.md` 已锁的 **file-given（给定金标文件，oracle reuse）**；RQ4 = S1 上 file-given 的 M0..M4 配对对比，主序列删 `--task fileloc`、T2 改吃 oracle 金标文件。Task1(file-loc) 降为可选独立实验。新增"可信度三条件"。**理由**：file-given 隔离覆盖率对行排序的作用、消除 file-loc 混淆，是 FL 标准做法且更严谨；ARISE 端到端数不再作绝对对比。**预期**：主序列 GPU 时间从 ~1.5–3h 降到 **~20–40min**。
