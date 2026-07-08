# 实验计划 · Agentless 宿主 + LLM投票 + 覆盖率过滤（crash·on-path 专属）

> 2026-07-04。转向：**放弃对标闭源 ARISE，改为在可复现的 Agentless 上做增量**，用 **Agentless 论文原生指标**（不再用 R@k），只解决 **crash·on-path** 一类 issue。
> 本计划顺带修好了上一轮暴露的两个硬伤：①绝对值与端到端不可比（复现 Agentless = 天然端到端，不再 file-given）；②对标闭源不可复现（Agentless 开源、MIT、已被 CoSIL 用 Qwen-32B 复跑）。

---

## 0. 一句话设计

> 复现 Agentless 的三段定位（文件→元素→编辑位置）作为**同底座基线**，把它的编辑位置阶段换成/叠加**我们的 k-采样自洽投票 + 执行覆盖率过滤（A3）**，在 **crash·on-path** 子集上用 **Agentless 原生的〈Contains-GT %，候选集 LoC〉** 证明：**我们能在更小的候选集上达到 ≥ 的金标完整覆盖**（Pareto 占优）。

---

## 1. 锁定事实（web 实查，2026-07-04）

| 项 | 事实 | 来源 |
|---|---|---|
| Benchmark | **SWE-bench Lite (300)** 为主；Verified (500) 可选（`--dataset`）| arXiv 2407.01489 + repo README_swebench |
| 定位指标① | **% Correct Location** = 预测编辑位置集 **⊇ 全部金标行**（superset）。GPT-4o/Lite：File 69.7 / Func 52.0 / **Line 35.3** | 论文 Table 1 |
| 定位指标② | **Contains-GT % + Avg LoC**（每阶段候选集是否含金标 + 集合大小）。file 阶段 ~81.7% @ 3424 行；element ~58% @ 698 行；**edit-location ~50% @ 165 行** | 论文 Table 2 |
| 输出形态 | edit-location = **无序集合**，4 次采样（temp 0.8），各自独立进 repair（非 ranked list）| 论文 §3 + repo |
| 底座 | 论文用 GPT-4o；repo 走 openai client，`OPENAI_BASE_URL` 可换本地 vLLM；CoSIL 已用 **Qwen2.5-Coder-32B** 复跑其定位 | repo api_requests.py + CoSIL 论文 |
| 复现成本 | 完整定位管线约 4 天集成；唯一云硬依赖 = 文件检索的 OpenAI embedding（可换本地或走 prompting-only 文件定位，代价 −2.7pp contains-GT）| 前期调研 wf_7090b3a8 |

---

## 2. 评测指标（要求 2）：R@k → Agentless 原生

**弃用 R@{1,5,10}**。改用 Agentless 的两轴（都在 **line/edit-location 粒度**、**crash·on-path 子集**上算）：

1. **Contains-GT（金标完整覆盖率）**：预测编辑位置集是否 **⊇ 全部金标行** 的实例占比。= Agentless "% Correct Location (line)" 的定位阶段版。
   - 同时报**宽松变体** Contains-any（集合含 ≥1 金标）以刻画机制，但**主指标是 superset（⊇ 全部）**，与 Agentless 一致。
2. **Avg LoC（候选集大小）**：预测编辑位置集的平均行数 = 精度/成本轴。越小越好。

**核心判据 = 〈Contains-GT, LoC〉平面上的 Pareto 占优**：我们的方法应在**更低 LoC** 下拿到 **≥ 的 Contains-GT**（同召回、更高精度），或同 LoC 下更高 Contains-GT。这正是 RQ3-E1 的"缩窄 55% 候选而召回反升"在 Agentless 原生指标下的表达。

> 为什么这个指标对我们有利：Agentless 撒 4 采样得到 ~165 行的大集合、Contains-GT ~50%；**投票抬 Contains-GT（更多采样更全），覆盖率过滤砍 LoC（on-path 保金标）** → 两轴同时改善。

---

## 3. Benchmark + crash·on-path 子集（要求 3）

- **主 benchmark = SWE-bench Lite（与 Agentless 头条一致，且我们已有 crash_onpath n=57）**。
- **扩样 = SWE-bench Verified（500）** 采更大 crash·on-path 池 → 补 n=57 的统计功效不足（上轮 McNemar p≥0.125 的根因）。Agentless 原生支持 Verified。
- **crash·on-path 判定**：
  - **crash**（测试期可得）：issue 含 Traceback / `pytest.raises` 等（现有 `is_crash` regex）。
  - **on-path**（需跑失败测试收覆盖）：金标行被失败测试执行（`gold ∩ coverage`）。⚠️ 用到 gold，是**oracle 定义的分析子集**——须披露为 scope 假设（上轮审计 minor caveat 已坐实：on-path 对 gold-blind ranker 反而更难，不 cherry-pick 抬基线）。
  - 我们**只解决这一类**（用户要求）：attempt 面 = crash + 可复现（失败测试能跑出覆盖）；报告面 = crash·on-path。可选加一个**测试期路由器**（traceback 特征预测 on-path，CraTer 模板）给一个全诚实的端到端数。

---

## 4. 方法集成（要求 1）：A3 挂在 Agentless 上

Agentless 三段：**文件定位 → 相关元素定位 → 编辑位置定位（4 采样集合）**。
把**编辑位置阶段**换成我们的，**共用 Agentless 的文件+元素定位**（隔离"编辑位置方法"这一变量）：

| 臂 | 编辑位置阶段 | 隔离变量 |
|---|---|---|
| **AL**（基线） | Agentless 原生（4 采样，无序并集）| — |
| **AL + vote** | Agentless 文件/元素 → 我们的 **k=16 自洽投票**（RRF 频次集合，无覆盖率）| LLM 投票 vs 4 采样 |
| **AL + vote + cov（= A3）** | + **执行覆盖率过滤/精细化**（on-path 分档保金标，砍非执行行）| 覆盖率过滤 |

- 三臂共用 Agentless 的文件+元素定位（其强项）→ 干净归因到"编辑位置阶段"。
- 覆盖率取自**失败测试的整仓覆盖**（`cov_collect` 返回 `{file: 执行行}`），**按 Agentless 预测的文件取**，不碰金标文件身份 → 消除上轮"gold-file 泄漏"隐患。
- 输出统一成**集合**（不再 ranked）：投票集合按频次阈值/top-N 定；覆盖率过滤后的集合直接量 Contains-GT + LoC。

---

## 5. 查漏补缺（我补的关键设计决策）

1. **底座一致性**：Agentless 论文是 GPT-4o；**我们全程用 DeepSeek-V3（与 A3 实验同底座）跑 Agentless 与三臂** → 同底座对比，杜绝"模型更强"混淆。**另** 用 Agentless 免费释出的 GPT-4o `loc_outputs.jsonl` artifact，先用我们的指标代码**复现其 Table 2 数字**（0 算力）→ 验证指标实现无误再花算力（**验证门**）。
2. **superset 指标 vs 覆盖率过滤的张力（关键）**：on-path 只保证 ≥1 金标行被执行,**非全部**（多行修复的插入锚点常不执行）。硬过滤会砍掉未执行金标 → 伤 superset Contains-GT。**对策**：覆盖率过滤用**执行 ∪ 执行邻接（frontier 保锚点）**而非纯执行，或用软分档 + top-N 成集；主报〈Contains-GT, LoC〉Pareto 曲线（扫过滤强度）而非单点，看是否 Pareto 占优。
3. **失败测试来源 oracle**：FAIL_TO_PASS 可能是金标 patch 新增测试。**对策**：(a) 审计 pre-patch 存在率、优先用已存在测试；(b) 用 Agentless 自己的 reproduction-test 阶段产出的测试收覆盖（最干净，全端到端）；(c) 显式声明 + 引 AutoCodeRover-SBFL/LIBRO 先例。主口径用 (a)+(b)。
4. **统计功效**：n=57 欠功效 → Lite+Verified 合并 crash·on-path 目标 n≥120；配对 McNemar + bootstrap CI；主张写成"Pareto 占优 + 效应量"，够则声称显著。
5. **embedding 云依赖**：Agentless 文件定位的检索分支用 OpenAI embedding → 换本地 embedding 或走 prompting-only 文件定位（−2.7pp），保持全本地。
6. **端到端带来的红利**：复现 Agentless = 不给金标文件 → 绝对数与 Agentless 公布值同口径可比，**彻底消除上轮 file-given 虚高质疑**。

---

## 6. 执行阶段（带验证门，先零算力）

| 阶段 | 内容 | 算力 | 门 |
|---|---|---|---|
| **P0 指标复现门** | 下载 Agentless v1.5 GPT-4o Lite artifact，用我们的〈Contains-GT, LoC〉代码复算，对齐论文 Table 1/2 | 0 | 数字对齐才继续 |
| **P1 集成 Agentless** | repo 接本地 vLLM（DeepSeek-V3），补 `--model` + embedding 补丁；5 题冒烟 | 小 | 跑通端到端定位 |
| **P2 全量 Agentless 基线** | Lite 300（+Verified）跑 AL 三段定位，存 `found_edit_locs` | 中 | AL 的 Contains-GT/LoC 对齐 CoSIL-Qwen 量级 |
| **P3 crash·on-path 子集 + 覆盖率** | regex 筛 crash，收失败测试覆盖（按预测文件），定 on-path 子集；审计测试 provenance | 本地 Docker | n、provenance 表 |
| **P4 三臂 + A3** | AL / AL+vote / AL+vote+cov，同底座，量〈Contains-GT, LoC〉+ 配对检验 | 中 | Pareto 占优 |
| **P5 扫过滤强度** | 覆盖率过滤强度 sweep → Pareto 曲线；路由器可选 | 小 | 曲线 |

---

## 7. 成功判据（诚实）

- **主**：crash·on-path 上,**AL+vote+cov 在〈Contains-GT, LoC〉平面 Pareto 占优 AL**（更低 LoC 拿 ≥ Contains-GT，或同 LoC 更高 Contains-GT），配对显著（或明确标 underpowered + 效应量）。
- **次**：拆解 vote（抬 Contains-GT）与 cov（砍 LoC）各自贡献。
- **诚实边界**：scope = crash·on-path（oracle 子集，披露）；覆盖率过滤对 superset 的风险用 Pareto 曲线兜底；absolute 数与 Agentless 公布同口径可比（端到端）。

---

## 8. 风险 / 待定

- Agentless 编辑位置是集合非 ranked → 我们的投票/覆盖率产物要统一成集合口径（已定：频次阈值/top-N + 过滤后集合）。
- 覆盖率硬过滤可能伤 superset Contains-GT（§5.2）→ 用 frontier 保锚点 + Pareto 曲线,是本计划最大不确定性。
- Verified 上 crash·on-path 的覆盖率采集是新 Docker 工作量（~小时级/批，可断点）。
- 若 AL+vote+cov 在 superset 指标下 **无法 Pareto 占优**（覆盖率砍掉多行金标）→ 退路：主报 Contains-any + LoC（宽松），或把覆盖率定位成"精度杠杆"（同 Contains-GT 砍 LoC）而非召回杠杆。诚实记录。
