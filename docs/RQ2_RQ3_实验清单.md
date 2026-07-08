# RQ2 → RQ3 实验清单（设计 + 已跑结果 + 待跑准备）

> 2026-06-26 · 研究链路：**RQ2「证伪 execution coverage 作直接定位信号能提升行级 recall」→ RQ3「如何用 execution coverage 提升崩溃类行级定位」**。
> **凡标 `pending` 的 = 还没跑，没有数字。所有已填数字均来自实际离线运行（脚本 `prelim_localization/crash_*.py`），无任何编造。**

---

## 0. ⚠️ ARISE 对标说明（诚实，必读）
- 项目代码里存了引用常量 `arise_ref_line_R@k = {1:41, 5:62, 10:74}`、`file_R@1=67`——记录的是 **ARISE 论文公布的【整体】行级 R@k**（SWE-bench-Lite，Qwen-32B）。**我没有 ARISE 原文，无法独立核实；请你自行翻论文确认这三个数 + 它是否分层报告。**
- **据现有信息，ARISE 没有单独公布"崩溃类子集"的 R@k。** 所以：
  - **RQ3（崩溃子集）无法直接对标一个 ARISE 崩溃数** → 崩溃子集的对标只能是**"我们带执行 vs 不带执行"的内部消融**。
  - **"必须比 ARISE 高"只在【整体集】成立** → 需要 RQ3-E8（整体跑），且那是把崩溃类的执行增益**加回整体**后看能否过 41/62/74。

---

## 1. 实验清单总表

| ID | 研究问题 | 在哪跑 | 状态 | 一句话结果 |
|---|---|---|---|---|
| **RQ2-E1** | 崩溃类有多少？每库分布？ | 离线 | ✅ | crash 23–29%（~70–89 例） |
| **RQ2-E2** | coverage 当**直接信号**能定位吗？ | 离线 | ✅ | 否——执行集 259 行、崩溃 vs 行为只差 6–7pp |
| **RQ2-E3** | coverage 召回天花板多高？为什么 <100%？ | 离线 | ✅ | 83% 天花板；缺口主因=漏分支(9/11) |
| **RQ2-E4** | traceback 信号多强？对静态互补吗？ | 离线 | ✅ | 函数级 58%、最深帧 32%；只救回静态漏的 19% |
| **RQ3-E1** | coverage 当**过滤器**能提升排序吗？on/off-path、崩溃/行为分层？ | 离线 | ✅ | **崩溃on-path +14pp R@10**；行为on-path +7pp；off-path→0 |
| **RQ3-E2** | 反向数据流切片能够到上游根因吗？ | 离线 | ✅ | 否（文件内切片无效，已证伪） |
| **RQ3-E3** | **SBFL（失败 vs 通过差分）**能否在 on-path 上比"过滤"再涨？ | 本地 Docker | 🔧 代码就绪，待采通过覆盖 | pending |
| **RQ3-E4** | **完整方法**(vote+graph+LLM) ± coverage-filter，on-path × 3 模型 | GPU | ⏳ 命令就绪，待开卡 | pending |
| **RQ3-E5** | 完整方法 ± SBFL，on-path × 3 模型 | GPU（依赖 E3） | ⏳ | pending |
| **RQ3-E6** | 最优方法消融（−filter / −SBFL / −traceback） | GPU | ⏳ | pending |
| **RQ3-E7** | 负对照：off-path / 行为类上执行**不**该有效 | GPU+离线 | ⏳ | pending（离线雏形已见 off-path→0） |
| **RQ3-E8** | 把崩溃类执行增益加回**整体集**，对标 ARISE 41/62/74 | GPU | ⏳ | pending |

---

## 2. 已完成的离线实验 —— 真实结果

### RQ2-E1 崩溃类占比（脚本 `crash_coverage_analysis.py`）
- SWE-bench-Lite：strict（issue 含 Traceback）**23%**、loose（+测试 pytest.raises）**29%** ≈ **70–89 例**。
- 富集库：astropy 66% · matplotlib 60% · seaborn 50% · sklearn 43% · sympy 37%；稀疏：django 19% · sphinx 0%。

### RQ2-E2 coverage 当直接信号（证伪）
| | 崩溃 | 行为 |
|---|---|---|
| 金标行被执行% | 54 | 47 |
| ≥1 金标被执行% | 85.7 | 79.2 |
| 执行集中位行数 | 259 | 279 |
→ 裸覆盖太粗、崩溃 vs 行为差距小 → **"覆盖当直接定位器"被证伪**（与旧 RQ2 一致）。

### RQ2-E3 覆盖天花板 83% + off-path 机制（`crash_coverage_analysis.py` 末段）
- 崩溃类 ≥1 金标被执行 = **83%**；缺口 16%（n=68 里 11 道）拆解：**漏分支/off-path 9** · 函数没被调用 2 · 插入型补丁 4。
- → 执行对 off-path 结构性瞎 → **任何纯执行法召回上限 ≈ 83%**。

### RQ2-E4 traceback 信号 + 互补性（`crash_fusion_estimate.py`）
- traceback 函数级够到金标 **58%**、最深帧==金标文件仅 **32%**（根因 68% 在上游/已弹栈）。
- 静态 @10 漏掉的题里 traceback 只救回 **19%** → 互补性弱、单独增益上限仅 **~+10pp**（端到端，issue traceback 为代理）。

### RQ3-E1 ⭐ coverage-as-filter，4 子集（`crash_coverage_rank_test.py`，def-use 排序器、file-given、无 LLM）
| 子集 | n | A静态 R@10 | B过滤 R@10 | Δ | A MRR | B MRR |
|---|---|---|---|---|---|---|
| **S1 崩溃·on-path** ⭐ | 57 | 29.8 | **43.9** | **+14.1** | 0.184 | 0.244 |
| S2 行为·on-path | 131 | 27.5 | 34.4 | +6.9 | 0.169 | 0.210 |
| S3 崩溃·off-path | 11 | 45.5 | 0.0 | −45.5 | 0.283 | 0.000 |
| S4 行为·off-path | 40 | 35.0 | 0.0 | −35.0 | 0.163 | 0.000 |
**结论**：① 覆盖过滤在 **on-path** 有效（崩溃 +14、行为 +7）= 本质是"on-path 通用、崩溃尤甚"；② **off-path 过滤→0**（删掉没执行的金标），**必须按 on/off-path 路由**；③ off-path 上**静态 A=45.5 还在干活** → 静态管 off-path、执行管 on-path，互补。

### RQ3-E2 反向切片（`crash_slice_validation.py`，证伪）
文件内反向切片 recall 不升（48.9%=traceback区域）、只加噪声 → 漏的根因在已 return 的跨函数处，文件内够不到 → **暂不做跨过程切片**。

---

## 3. 待跑实验 —— 设计 + 准备状态（不编任何结果）

### RQ3-E3 SBFL（本地 Docker，**不占 GPU**）
- **问题**：SBFL（Ochiai，失败 vs 通过差分）能否把"崩溃路径"从"import 连锁噪声"里分出来，在 on-path 上比覆盖过滤的 +14pp 再涨？
- **需要**：① 扩 `cov_collect` 采 **PASS_TO_PASS（通过测试）覆盖**（现有缓存只有失败覆盖）；② Ochiai 打分 `ef/√((ef+nf)(ef+ep))`；③ 在 on-path 崩溃子集上比 A静态 / B过滤 / D=Static∩SBFL 的 R@k+MRR。
- **准备**：Ochiai 排序器代码就绪（`sbfl.py`，待写）；通过覆盖采集是 P1 那步 Docker（~57 例 × 镜像，~小时级、本机可跑、可断点续）。**这步跑完整条线就能离线出 SBFL 结果，不用开卡。**

### RQ3-E4 / E5 / E6 / E7 完整方法（**GPU，待开卡**）
- **E4**：`region_loc/egl_e2e` 完整方法（vote+graph+LLM）在 on-path 崩溃子集上，**开/关 coverage-filter** 比 R@k+MRR × {DeepSeek-V3, Qwen-32B, Qwen-7B}。→ 确认离线 +14pp 雏形在完整方法上成立 + 验 H4（弱模型增益更大）。
- **E5**：加 SBFL 臂（依赖 E3 的通过覆盖）。
- **E6**：最优臂消融（−filter / −SBFL / −traceback），量各组件增量。
- **E7**：同样的方法跑 off-path / 行为类子集 → **执行不该有效**（负对照，坐实边界）。
- **命令就绪**：见 `RQ3_GPU_commands.sh`（待写）；隧道稳定性见 `实验进展.md` 教训。

### RQ3-E8 整体对标 ARISE（GPU）
- 把崩溃类的 on-path 执行增益**加回整体方法**，整体集跑 R@{1,5,10}，看能否 > ARISE 41/62/74（**仅此处才是"对标 ARISE"**）。诚实预期：崩溃类只占 ~25%，整体增益 = 25% × 崩溃增益，**对整体 R@k 的提升有限**，需结合 R@1 排序突破一起看。

---

## 4. 执行顺序（先榨干离线/本地，再开卡）
1. **离线**：RQ2-E1~E4、RQ3-E1/E2 — ✅ 全部完成（见 §2）。
2. **本地 Docker（不占卡）**：RQ3-E3 = 采通过覆盖 + SBFL。← **下一步,我准备代码,你本机 Docker 跑(或我跑,~小时级)**。
3. **开卡 GPU**：RQ3-E4~E8 完整方法 × 模型。← **我把命令全准备好,你开卡我一次性跑**。

> 脚本：`crash_coverage_analysis.py`/`crash_fusion_estimate.py`/`crash_slice_validation.py`/`crash_coverage_rank_test.py`(已跑)；`sbfl.py`/`RQ3_GPU_commands.sh`(待写,见下一步)。
