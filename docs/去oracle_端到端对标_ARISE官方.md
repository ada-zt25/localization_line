# 去-oracle 端到端对标方案（对标官方 ARISE）

> 2026-07-08。ARISE 已开源（[github.com/FARD-Lab/ARISE](https://github.com/FARD-Lab/ARISE)，MIT，随 v2 于 7/3 放出），本地 clone 于 `vendor/ARISE`（pin commit `3abdc361`）。盲复现 `arise_file_loc.py` 已 `git rm`（工具集缺 T2 数据流切片 + T3 层，非真 ARISE）。本方案把定位从「file-given 内部对照」升级为「可对标 ARISE 的端到端 R@k」。

## 0. 一句话
两个系统各自产出「排序的 (file, function, line) 预测」，**用 ARISE 官方 `gold.py` + `metrics.py` 同一把尺打分** → 得到真正可比的端到端 line/file/func R@k，对标官方复现的 41/62/74。

## 1. ARISE 官方评测口径（唯一参考，读自 `vendor/ARISE`）

### 1.1 金标 `src/arise/eval/gold.py::parse_gold(patch)`
- **files** = 补丁改动的所有文件。
- **functions** = 每个 hunk header 第二个 `@@` 后 context 里的函数名（`def/class/async def` 或 `名(` ）。
- **lines** = 每个**删除行（`-`）**在**原文件（base commit）**的行号；**纯新增 hunk**（无 `-` 行）回退取该 hunk **最后 3 行 context** 的行号，保证非空。
- ⚠️ **与我方 `clean_gold` 的差异（必须对齐）**：
  1. ARISE **不丢空行/注释行**（只取删除行 + context 回退）；我方 `--arise-gold`/`clean_gold` **丢空行/注释/纯标点**。
  2. 纯新增：ARISE 用「最后 3 行 context」；我方用「插入锚点 old-1, old」。
  3. `+` 新增行两者都**不计**（无 base-commit 行号）。
  → **对标时改用 ARISE 的 `gold.py`**，别用 `clean_gold`；否则金标集不同，R@k 不可比。

### 1.2 指标 `src/arise/eval/metrics.py`
- **预测格式** = 排序的 `(file, function, line)` 三元组列表，index 0 最可疑。
- `line_recall_at_k`：取前 k 个**去重后的 (file,line)**，与金标行集有交 → 命中 1，否则 0；实例级二值，**跨实例取均值**。**k ∈ {1,5,10}**。→ **与我方 Line R@k 定义一致**（放心）。
- 另有 `file_recall@{1,3,5}` + `file_mrr`；`func_recall@{1,3,5}` + `func_mrr` + `func_f1`；`line_iou`；`coverage@budget`。
- 聚合入口 `compute_all_metrics(predictions, golds, ...)`。

### 1.3 预测来源 `evaluation/parse_preds.py`
- ARISE agent 终答块：
  ```
  LOCATIONS
  file: path/to/file.py, function: func_name, line: 42
  ...
  END_LOCATIONS
  ```
  逐行正则解析成 `(file, function, line)`，去重、保持 rank 序。**是逐行，不是 span** → line R@k 就是逐行命中，无 span 膨胀。
- `parse_trajectory(.traj)` 从 SWE-agent 轨迹取最后一个含 LOCATIONS 的 assistant 消息。

## 2. 官方 ARISE baseline 复现（拿到真 41/62/74）

需 GPU ≥48GB（vLLM 32B）= AutoDL。步骤（`vendor/ARISE/README.md` §Reproducing）：

```bash
# 1. 装 ARISE
cd vendor/ARISE && pip install -e ".[eval]"
# 2. 起 vLLM（官方指定 AWQ checkpoint + awq_marlin）
VLLM_USE_FLASHINFER_SAMPLER=0 python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct-AWQ --quantization awq_marlin --port 8002
# 3. 装 SWE-agent，跑 FL 条件（ARISE-Full）
OPENAI_API_BASE=http://localhost:8002/v1 python -m sweagent.run.run_batch \
  --config config/default.yaml \
  --config ../arise/configs/{arise,fl,swe_bench_lite}.yaml \
  --output_dir outputs/qwen25coder/condfull-fl
# 4. 评测 → 复现 41/62/74
python evaluation/run_eval.py --traj-dir .../condfull-fl
```
**验收**：line R@1/5/10 落在 41/62/74 ± 噪声内，再信这套口径。**pin commit `3abdc361`** 并在论文写「reproduced from FARD-Lab/ARISE @3abdc361，与原文相差 X pt」。

⚠️ 待确认（README 未写全，从 configs 读）：temperature/top-p、agent turn budget(40)、context bundle budget(8k)。

## 3. 我方系统端到端（去 oracle）

把 file-loc 放回环里，产出与 ARISE 同格式的预测：

```
issue
  → [file-loc] SweRankEmbed（冲 R@10≥0.9，见 docs/文件定位_冲90方案.md）或 agentless file_localize
  → [line-loc] 对每个候选文件跑 SPINE（region vote + assertion_rerank，覆盖率可选）
  → 汇总成排序的 (file, function, line) 预测（function 取该行的 enclosing scope）
  → ARISE gold.py + metrics.py 打分
```

- **关键**：不再喂 `--reuse-files runs/oracle_*.json`（那是 oracle 金标文件）。改用真实 file-loc 输出。
- **诚实预期**：端到端 line R@k = P(命中金标文件) × P(SPINE 在文件内排对)。file-given 上 SPINE 的 +14~16pp R@1 会被 file-loc 误差**打折**；SweRankEmbed R@1~0.70–0.80 是上游天花板。所以端到端绝对值会低于 file-given，这正是要如实测出来的数。
- **对标**：端到端 line R@{1,5,10} vs 官方 ARISE 41/62/74（同尺）。这是能不能声称「file-loc + SPINE > ARISE 端到端」的唯一合法比较。

## 4. 落地清单（按序）

1. **[代码] 加 ARISE-口径评测适配器** `prelim_localization/arise_eval_adapter.py`：`import vendor.ARISE` 的 `gold.parse_gold` + `metrics.compute_all_metrics`；把我方 (file,line) 排序转成 `(file,function,line)` 预测 dict，喂官方 metrics。**先用它把现有 file-given SPINE 结果重算一遍**（换成 ARISE gold）——0 GPU，先看口径切换后数字变多少。
2. **[GPU] 复现官方 ARISE baseline**（§2）→ 存 41/62/74 复现值 + pin commit。
3. **[GPU] 我方端到端**（§3）：SweRankEmbed file-loc + SPINE，产出预测 → ARISE 尺打分 → 对标。
4. **[写作] bench2（Verified 61）复现主结果** + 论文。

## 5. 风险/注记
- 官方仓库很新（0 star、单次 push），文档可能糙；跑不通先查 configs/ 里的 YAML。
- 架构不同（ARISE=SWE-agent ReAct 联合定位；我方=localize-then-edit）——**输出层同格式同尺打分是公平的**，这正是 localization 方法的标准比法。
- 修复率：按已定，proof-of-concept（m5 4/9 vs vote 2/9，discordant 3-0 全偏 SPINE）+ 天花板论证，不追 p<.05。
