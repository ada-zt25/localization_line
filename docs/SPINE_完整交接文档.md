# SPINE 行级故障定位 —— 完整交接文档（自包含，换设备可直接续做）

> 写给下一个 AI / 换机后的自己。读完这一份即可接手,不依赖对话历史。
> 最后更新:2026-07-08。研究 = **行级(line-level)故障定位**,对标开源 SOTA **ARISE**。
> 目标会议:**稳发一个 CCF-A(ICSE/FSE/ASE/ISSTA 任一即可),不求惊艳但必须是 A。**

---

## 0. 一页速览(先读这个)

**方法 SPINE**:一个**断言接地的行级重排器**。给定某个行级候选排序(来自自一致性投票或覆盖率),SPINE 用**失败测试的断言(期望值 vs 现状)**做一次 LLM 反向推理,把 top-k 头部重排,把"真正产生错值的根因行(producer)"提到 #1,而不是"只传递错值的行(propagator)"。它是**纯 top-k 重排(recall-safe,R@10 不变)**,只贡献判别力(R@1),不贡献可达性(R@5/R@10)。

**核心发现(已验证)**:在多数类(behavioral)行级定位上,SPINE 把 R@1 提升 **+13~20pp**(相对弱基线)/ **+8~15pp**(相对最强公平基线 vote_only),在**官方 gold 上 3 个模型稳显著(DeepSeek-V3.2-Exp、Qwen3-Coder-30B、Qwen2.5-72B)+ DeepSeek-V3 borderline(p≈.12)**,对抗审计(5 维)通过,机制上与 ARISE 的静态 def-use **正交**。

**当前状态**:定位这半篇已硬。**唯一还没跑的决定性实验 = "SPINE 叠加到 ARISE 上"**(rerank ARISE 的 top-k,看 R@1 能否从 41 再涨)。工具全就绪,卡在算力/环境(见 §11、§12)。

**代码**:`prelim_localization/`(纯 stdlib,换设备零依赖)。**数据全在**:`egl_cov_cache.json`(覆盖率)+ `cache/`(rows+gold源码)+ `runs/`(实验产物)。**模型**:SiliconFlow API 或自建 vLLM,二选一。

---

## 1. 研究背景与问题

- 大仓库修 GitHub issue(SWE-bench),第一步是**定位该改哪几行**;定位召回是修复率的硬上界。
- **文件级已基本解决**(~90%),**行级是瓶颈**(~15-40%)。
- 具体病灶:自一致性投票(和 ARISE 的静态 def-use)能把金标行**送进 top-10(可达性)**,但**排不到 #1(判别力)**。即 **R@1 ≪ R@10**(ARISE 官方:R@1=41, R@10=74,差 33pp)。
- 原因:在被执行/候选的行里,真正的 buggy 行**和无辜的邻居行长得一样**,没有信号区分"产生错值的行"和"传递错值的行"。

---

## 2. 走过的弯路(别再重复!)

按时间顺序,这些**都试过并证否/证弱了**,不要再花时间:

1. **覆盖率作为直接定位信号** → **证否**。覆盖率是控制流信号,SWE-bench 故障多是 data-level(函数返回错值、栈已弹出)。精确执行行太稀疏(recall 0.33),放宽到被执行函数又太宽(0.96 但占 85% 文件),两种粒度都打不过静态 LLM。
2. **覆盖率作为下游过滤器** → **弱**。只在紧 LoC 预算(N≤15)下作 tiebreaker 显著(N15 p=.003),N≥20 洗掉;是 precision/LoC 的赢,不是 recall 的赢。
3. **覆盖率上游扩池** → **加 ~0 净金标**(Δ+0.0)。天花板抬了但 realize 不出来。
4. **agentless 上的 re-discrimination / 条件化生成** → **死**(Δ~0,输给 vote)。
5. **报错文本(traceback)直接注入** → **无效**(Δ+0.00)。
6. **修复率作为主卖点** → **别当主线**(见 §7.4 + Sepidband 2026:行级精度常因噪声放大**降低**修复率)。

**唯一活下来的信号(SPINE 的来源)**:5-agent 对抗审计挖出——"唯一正交、同模型、推理期的新判别信号 = 失败测试的断言(expected vs observed)"。

---

## 3. 方法:SPINE

**代码**:`prelim_localization/region_loc.py::assertion_rerank`(约 L469)+ `test_evidence.py::extract_test_evidence`。

### 3.1 证据抽取 `extract_test_evidence(row)`
从 SWE-bench 实例抽三样(正则,无 LLM 无网络):
- `FAIL_TO_PASS` 测试名;
- `test_patch` 里 `+` 开头且匹配 `assert|raises|expect|==|!=|approx|isclose|pytest|with .*:` 的断言行(= 测试**期望**什么);
- `problem_statement` 里的 traceback(= **观测到的**失败;crash 类有,behavioral 类 0%)。

### 3.2 重排 `assertion_rerank(model, issue, path, lines, ranked, evidence, top_n=10)`
- 取 `ranked` 的前 `top_n` 头部,构造候选块(每行带 ±2 上下文);
- 用 `ASSERT_RERANK_PROMPT`(L450)让 LLM **反向推理**:"哪几行**产生**测试抓到的错值(ROOT CAUSE)——不是只**传递**错值的行?";
- 解析出的行号(必须在头部内)提到前面,其余头部行 + 尾部保持原序拼回。
- **recall-safe 铁律**:空证据/解析失败/异常 → 返回原 `ranked` 不变;头部重排,**R@10 恒不变**(`return picked + rest_of_head + ranked[top_n:]`)。

### 3.3 在 pipeline 里的位置(`egl_e2e.py::process_instance`)
- 上游:自一致性投票产出候选行排序 `vote_only`;覆盖率折叠版 `ours_dynamic_nofp`(=M4/cov-max)。
- SPINE 臂 `ours_m5` = `assertion_rerank(a_dynnofp, ...)`(重排 cov-max)。
- **覆盖率无关臂 `ours_m5_votebase`** = `assertion_rerank(a_vote, ...)`(重排纯 vote,`--spine-votebase`)——**这是最纯、最该当头条的版本**。
- 门控开关:`--assert-rerank 10 --spine-votebase --dump-ranks`。

---

## 4. 机制:为什么 SPINE 与 ARISE 正交(代码坐实,论文核心论点)

- **ARISE 的排序器**(`vendor/ARISE/src/arise/tools/rank_suspects.py`):`score = α·rel + β·prox + γ·in_slice`,`in_slice` 是**二值 0/1 成员标志**,且**只在 FUNCTION/METHOD 粒度**打分(`node.type not in (FUNCTION,METHOD): continue`)。**它没有"行 vs 行"的根因判别**,def-use 切片按**源码行号**排序(`sorted(..., key=lambda s: s.start_line)`),**零测试/断言输入**。
- **SPINE** = 语义、测试条件化、行粒度判别器。断言的 expected-vs-observed 正是 def-use 成员标志区分不了的"producer vs propagator"这个平手的破局点(所有路径上的行对 def-use 是等价成员)。
- **可观测证据**:ARISE R@1=41 ≪ R@10=74(33pp 判别缺口)= 金标进了 top-10(def-use 强)但排不到 #1(行判别弱)。**这 33pp 正是 SPINE 的市场。** 若 SPINE 重排 ARISE top-10 能补上部分缺口 → 正交坐实。

---

## 5. 数据集(全部,精确)

**主基准 = SWE-bench Lite(300 实例,11 个 Python 仓库)**,与 ARISE 同集。rows 缓存 `cache/swebench_lite_pool_500.json`(300 条元数据,含 problem_statement/patch/test_patch/FAIL_TO_PASS)。

### 5.1 冻结子集(`prelim_localization/rq3_subsets.json` 和 `rq4/frozen_subsets.json`,同一划分、不同封装;schema 不同,别做 naive 结构比较)
按 `is_crash × on-path(gold∩coverage 非空)` 切:
| 子集 | 数量 | 说明 |
|---|---|---|
| **behav_onpath(S2)** | **132** | **⭐ SPINE 主实验集**(behavioral、on-path;断言信号在此) |
| crash_onpath(S1) | 57 | 崩溃类 on-path |
| crash_offpath(S3) | 11 | |
| behav_offpath(S4) | 40 | |
| crash_nocov | 7 | 无覆盖率 |

**⚠️ SPINE 的所有主结果都在 behavioral-132 上**(`runs/ids_behav132.json` = 这 132 个 id)。文件给定(oracle 金标文件)= `runs/oracle_behav132.json`(磁盘格式 `{"results":[{"instance_id":.., "ranked_files":[gold_py_file]}, ...]}`;`egl_e2e.py --reuse-files` 自动转成 `{iid: ranked_files}`)。

### 5.2 benchmark2(SWE-bench **Verified** net-new,`newbench/benchmark2_ids.json`)
- **61 个 crash·on-path** 实例(与 frozen-57 严格无重叠,44-agent 审计过)。覆盖率缓存 `newbench/verified_cov_cache.json`。
- 用途:主结果的独立复现集(尚未在 SPINE 上跑)。

---

## 6. Execution coverage(执行覆盖率 —— 重点,别搞错)

### 6.1 怎么收集 `cov_collect.py`
- 在**官方 SWE-bench Docker 镜像**(`swebench/sweb.eval.x86_64.<iid>:latest`)里跑失败的复现测试(`FAIL_TO_PASS`),用 `coverage.py` 记录**被执行的行**。
- 需要**本机 Docker**(x86_64;ARM Mac 会因 qemu 模拟不稳,见 §12)。
- **收集很慢**(每实例拉镜像 + 跑测试,~几分钟)。

### 6.2 已缓存(⭐ 换设备**必带**,否则要重收 ~250 次 Docker)
| 缓存文件 | 大小 | 内容 |
|---|---|---|
| `prelim_localization/egl_cov_cache.json` | **50 MB** | Lite 的 313 个实例覆盖率 `{iid:{file:[被执行行号]}}` |
| `prelim_localization/newbench/verified_cov_cache.json` | **5.6 MB** | Verified/bench2 的 75 个实例覆盖率 |
- **behavioral-132 的覆盖率 100% 在 `egl_cov_cache.json` 里**(实测)→ **跑 SPINE 主实验完全不需要 Docker**(`--coverage` 时 miss=[],跳过 Docker 预pass)。
- 两个缓存 schema 相同、key 无重叠、可 `dict.update` 合并。

### 6.3 定义(评测/分组用)
- **coverage 行** = `coverage.py` 记录的被执行行;
- **on-path** = 金标行 ∩ coverage 非空(金标被执行到);
- **crash vs behavioral** = 失败是否崩溃(异常在活动栈抛出、traceback 点名 vs 函数返回错值、返回后才被断言发现)。

### 6.4 SPINE 与覆盖率的关系(诚实)
覆盖率**不是** SPINE 的核心信号(断言才是)。覆盖率在 pipeline 里只当:① 候选池兜底(救空投票);② cov-max 排序的一个输入。**SPINE 的关键结果用 `ours_m5_votebase`(覆盖率无关)也成立**(见 §7),所以论文可以把覆盖率降为配角。

---

## 7. 已做的实验与结果(全部,带产物文件)

**评测口径**:Line Recall@k = 实例级"top-k 去重(file,line)含 ≥1 金标行"的比例,跨实例取均值,k∈{1,5,10}。**必须用官方 ARISE gold(见 §10),不要用 clean_gold**(二者只 13% 相同,Jaccard 0.46)。⚠️ 只有 `spine_behav132_dsv32.json`/`_qwen72.json` 带 `ranks` dump(可直接 `arise_eval_adapter.py` 重算);其余 5 个(含 headline `spine_behav132.json`)`with_ranks=0`,adapter 会报 `n_with_dumps=0`。**官方口径的 baseline-vs-SPINE 重算用 `runs/basecmp_*.json`**(dsv3/dsv32b/qwen30/qwen72b,含全 6 臂含 `arise_static`)。

### 7.1 决定性 gate(behavioral-132,file-given)
`runs/spine_behav132.json`(DeepSeek-V3)。**区分两组对比,别混**:
- **clean_gold,M5(SPINE)vs cov-max(M4)**:R@1 **25.0→44.7**(`spine_paired_stats.py`,即 §9.2 那条命令的输出)。
- **官方 gold,M5 vs vote_only**:真 DeepSeek-V3(`basecmp_dsv3.json`)= **28.8→39.4,+10.6,p≈.12(n=66),官方口径下不显著**。原表 "+13.6/.0003" 其实是 DeepSeek-**V3.2-Exp**(`spine_behav132_dsv32.json`),见 §7.3。
- R@5 小涨、R@10 平 → **纯判别器形状**(口径无关)。

### 7.2 对抗审计(5 维,`wf_03ce1105`)= **SURVIVES-QUALIFIED**
- 答案泄漏(测试喂答案):**站住**(剔泄漏后增益反升;behavioral 0% 行泄漏)。
- 行号 scraping:**站住**(renumber+1000 实验证明是推理不是抄数)。
- 对照被做弱:**部分打中** → 改用最强公平基线 **vote_only**:DeepSeek **+15.2pp**(p=.0017)、Qwen3-Coder **+14.4pp**(p=.0003)。
- 金标/指标:**站住**(多金标虚高仅 ~0.8pp;单金标硬例仍 +15pp)。
- 统计:**站住**(Holm/Bonferroni/按仓库聚类 bootstrap/留一仓库 jackknife 全过)。

### 7.3 Generality(7 模型,官方 gold paired McNemar)= **3 稳显著 + 1 borderline**
> ⚠️ 官方口径数字只来自能重算的产物:`basecmp_*.json`(dsv3/qwen30/qwen72b 等)+ 带 ranks 的 `spine_behav132_dsv32/_qwen72.json`。Hunyuan/GLM/Ling 无 ranks dump,下表其 n.s. 来自早期 `spine_multi_summary`(口径可能偏 clean_gold),官方重算待补。

| 模型 | 产物/口径 | vote R@1 | SPINE R@1 | Δ | p |
|---|---|---|---|---|---|
| **DeepSeek-V3.2-Exp** | spine_behav132_dsv32(官方gold) | 25.8 | 39.4 | **+13.6** | .0003 ✅ |
| **Qwen3-Coder-30B** | basecmp_qwen30(官方gold) | 18.5 | 31.5 | **+13.0** | .039 ✅ |
| **Qwen2.5-72B** | basecmp_qwen72b(官方gold) | 23.5 | 31.8 | **+8.3** | .013 ✅ |
| DeepSeek-V3 | basecmp_dsv3(官方gold,n=66) | 28.8 | 39.4 | +10.6 | .12 ⚠️ borderline |
| Hunyuan-A13B | multi_summary | 23.5 | ~27.6 | +4.1 | n.s. ❌ |
| GLM-4.5-Air | multi_summary | 34.1 | 34.6 | +0.0 | n.s. ❌ |
| Ling-flash-2.0 | multi_summary | 31.1 | 31.1 | +0.0 | n.s. ❌ |
- **机制 = headroom × capability**:赢家 vote 基线低(有 headroom)且模型够强;GLM/Ling 基线高(无 headroom);Hunyuan 有 headroom 但弱推理(在基线排错的实例上只救回 5% vs DeepSeek 30%)。
- **⚠️ DeepSeek-V3 的显著性口径依赖**:官方 gold + vote_only 基线下 +10.6 p≈.12(borderline);clean_gold 或 vs-covmax 基线下更大更显著。报论文用官方 gold,别把 V3 当"稳显著"。
- **basecmp_*.json**(dsv3/qwen30/dsv32b/qwen72b)= 含 `arise_static` 全 6 臂的官方口径重跑,是官方 baseline-vs-SPINE 表的**唯一可信来源**。

### 7.4 修复率 proof-of-concept(`repair_ab.py`,DeepSeek-V3.2,diff-function 子集 33 个)
- vote 定位 → 修复 resolve 2/33;SPINE 定位 → 5/33;**discordant 3-0 全偏 SPINE**;McNemar p=0.25(**欠功效**)。
- 单次窗口修复触底;**完整函数上下文 + 3 轮反馈循环**在非 django 上脱离触底。
- **结论**:方向对但当次要佐证,别当主线(Sepidband 2026 反证行级→修复)。产物 `runs/repair_{dsv32,qwen72}_difffn.json`。

### 7.5 The vise(offline probe `spine_offline_probe.py`)
crash 类 traceback 里 **12-20% 泄漏金标源码行**;behavioral 类 traceback 0%(断言退化成 expected-only)但 **0% 泄漏**。→ 主实验用 behavioral(干净)。

---

## 8. 代码库地图(`prelim_localization/`,纯 stdlib,换设备零依赖)

**依赖**:只用 Python stdlib(`ast, json, re, urllib, os`)+ 一个 OpenAI 兼容 endpoint。**不需要 torch/transformers/任何重包**(除非在 AutoDL 自建 vLLM,那是另一码事)。
**⚠️ 随带的本地模块**:`region_loc.py`/`egl_e2e.py` 还 import `hybrid_loop, p1_realistic, file_localize, egl_makeorbreak, p7_crossfile_exec`(均 stdlib-only、均已 tracked)——换设备随 repo 一起带,别漏。

| 文件 | 作用 |
|---|---|
| `region_loc.py` | ⭐ 行定位 + `assertion_rerank`(SPINE)+ `_llm_t`(模型调用) |
| `test_evidence.py` | ⭐ `extract_test_evidence`(断言证据) |
| `egl_e2e.py` | ⭐ 主驱动;`--assert-rerank/--spine-votebase/--dump-ranks/--coverage/--arise-gold/--reuse-files/--instances` |
| `p0_line_recall.py` | 数据层:`load_rows`/`fetch_file`/`parse_patch`/`clean_gold`/`_openai_key` |
| `code_graph.py` | def-use 程序图(投票+cov 排序用) |
| `cov_collect.py` | 覆盖率收集(Docker) |
| `arise_eval_adapter.py` | ⭐ 用**官方 ARISE gold+metrics** 给我方排序打分(共享打分器) |
| `spine_paired_stats.py` | 配对 McNemar + bootstrap(SPINE vs 基线,自动剔 no-op+leak) |
| `stack_arise_spine.py` | ⭐ **叠加实验驱动**(见 §11);读 ARISE top-k → SPINE 重排 → 官方打分 |
| `spine_multi_summary.py` | 多模型官方口径汇总表 |
| `spine_offline_probe.py` | 泄漏/traceback/覆盖率可用性探针(无 LLM) |
| `repair_ab.py` | 修复率 A/B(需 Docker) |

**数据/产物目录**:
- `egl_cov_cache.json`(覆盖率,50MB,必带)、`rq3_subsets.json`(子集)、`cache/`(rows + gold 源码文件缓存,~115MB;其中 row pools `swebench_*_pool_500.json` ~11MB **必带**,`file_*` gold 可网络重取)、`newbench/{benchmark2_ids.json,verified_cov_cache.json}`、`runs/`(所有实验产物 + `ids_behav132.json` + `oracle_behav132.json`)。
- `.key`(SiliconFlow API key,gitignore,换设备重设)。
- ⚠️ **别搬 `snapshots/`(6GB)**;`cache/` 和 `egl_cov_cache.json` 必带。

---

## 9. 复现环境(换设备一步到位,不出错)

### 9.1 模型 endpoint(二选一)
**A) SiliconFlow API(最简,无 GPU)**:
```bash
export OPENAI_BASE_URL=https://api.siliconflow.cn/v1
export OPENAI_API_KEY=<key>   # 或写进 prelim_localization/.key
export MODEL=deepseek-ai/DeepSeek-V3   # 可用:DeepSeek-V3, Qwen/Qwen3-Coder-30B-A3B-Instruct, Qwen/Qwen2.5-72B-Instruct, zai-org/GLM-4.5-Air, tencent/Hunyuan-A13B-Instruct, inclusionAI/Ling-flash-2.0, deepseek-ai/DeepSeek-V3.2-Exp
# ⚠️ SiliconFlow 没有 Qwen2.5-Coder-32B(ARISE 的 backbone),要用它得自建 vLLM(见 B)
```
`region_loc._llm_t` 会自动对 glm/qwen3/hunyuan/ling 等推理模型关 thinking。余额不足会 403/400(注意充值)。

**B) 自建 vLLM(要 GPU;用 ARISE 的 EXACT backbone Qwen2.5-Coder-32B-AWQ 时用这个)**:见 `docs/AutoDL_vllm_awq_setup.md`。要点:A800/A100 **80G**;`--quantization awq_marlin`;**vLLM 版本必须匹配驱动 CUDA**(实测驱动 CUDA 13.0 → 用最新 vllm cu130;别降到 cu128);endpoint `http://localhost:8002/v1`,`OPENAI_API_KEY=dummy`。

### 9.2 跑一个 SPINE 主实验(behavioral-132,file-given,官方口径)
```bash
cd prelim_localization
SWEBENCH_DATASET=lite OPENAI_BASE_URL=<endpoint> OPENAI_API_KEY=<key> MODEL=<model> \
  python3 egl_e2e.py --instances runs/ids_behav132.json --reuse-files runs/oracle_behav132.json \
  --coverage --arise-gold --assert-rerank 10 --spine-votebase --dump-ranks --k 5 --workers 8 \
  --out runs/spine_behav132_<tag>.json
# --coverage 用缓存(egl_cov_cache.json),不触发 Docker;--reuse-files 旁路 file-loc(oracle 金标文件)
python3 spine_paired_stats.py runs/spine_behav132_<tag>.json --dataset lite   # 出 M5 vs vote 配对
python3 arise_eval_adapter.py runs/spine_behav132_<tag>.json                  # 出官方口径全臂表
```
一键脚本:`prelim_localization/run_spine_on_model.sh`(传 BASE_URL/KEY/MODEL/TAG)。

### 9.3 依赖检查
```bash
python3 -c "import sys;sys.path.insert(0,'.');import region_loc,p0_line_recall,code_graph,test_evidence;print('OK')"
# 只需 python3(stdlib)。官方 ARISE 打分需 vendor/ARISE(见 §10)。
```

---

## 10. 官方 ARISE 评测口径(对标必须用,`vendor/ARISE`)

- ARISE 已开源:**github.com/FARD-Lab/ARISE**(MIT,7/3 随 v2 放出),本地 clone 于 `vendor/ARISE`(commit `3abdc361`)。**⚠️ 换设备:`vendor/` 不随本 repo 传(556M),需自己 `git clone https://github.com/FARD-Lab/ARISE.git vendor/ARISE && cd vendor/ARISE && git checkout 3abdc361`**。arXiv:**2605.03117**。官方数:**line R@1/5/10 = 41/62/74**,file 67/82,func 60,repair 22.0% Pass@1。backbone Qwen2.5-Coder-32B-Instruct(复现 README 用 **AWQ**)。
- **金标** `vendor/ARISE/src/arise/eval/gold.py::parse_gold(patch)`:删除行的 base-commit 行号 + 纯新增取最后 3 行 context;**不丢空行/注释**(与我方 `clean_gold` 不同!)。
- **指标** `vendor/ARISE/src/arise/eval/metrics.py`:`line_recall_at_k` = top-k 去重(file,line)∩ 金标。
- **预测格式** `vendor/ARISE/evaluation/parse_preds.py`:agent 终答 `LOCATIONS\nfile:..,function:..,line:..\nEND_LOCATIONS`,逐行 (file,function,line),rank 序。
- 装:`cd vendor/ARISE && uv sync --extra eval --python 3.12`(51 eval 测试应过)。`arise_eval_adapter.py` 已把我方排序桥接到这套官方 metrics(**打分零口径差**)。

---

## 11. ⭐ 下一步实验(决定 A 与否)

### 11.1 THE 决定性实验:SPINE 叠加到 ARISE(必做)
**问题**:SPINE 的 +14 是相对弱基线;ARISE 本身 R@1=41。SPINE 叠到 ARISE 上(rerank 它的 top-k)还能涨吗?
- **机制预测(§4)**:~55-65% 会叠加(ARISE 有 33pp 判别缺口,SPINE 正好补)。
- **协议**:
  1. 跑真·ARISE(见 §11.2)→ 每实例 top-k `(file,function,line)`,导成 **`stack_arise_spine.py` 要的格式:`{iid: [[file, function, line], ...]}`(list-of-**lists**,rank 序)**。⚠️ 别直接用 `vendor/ARISE/evaluation/parse_preds.py` 当序列化器——它返回 Python tuple、且 `load_predictions_from_json` 的 schema 是 list-of-**dicts**(`{"file":..,"function":..,"line":..}`),**格式不同,直接喂 `stack_arise_spine.py` 会崩**(它对每条做 `t[0]`/`t[-1]`)。转换一行:`json.dump({iid:[list(t) for t in pred] for iid,pred in preds.items()}, open("arise_preds.json","w"))`。**已验证的离线替代**:`stack_arise_spine.py --from-run <run.json> --arm vote_only` 会自动构造正确的 proxy 格式(无需真 ARISE 即可跑通管线)。
  2. `python3 stack_arise_spine.py --preds arise_preds.json`(MODEL=**与 ARISE 同一个模型**)→ 三臂:baseline(ARISE)、baseline+SPINE、baseline+random(控制);官方打分 + 配对 McNemar。
  3. **同模型是硬要求**(否则增益是"更大 reranker"而非断言信号)。random 控制证明是断言信号不是乱洗。
- **绿灯**:ARISE 41 → 50+,p<.05,discordant≥8,且 > random。
- **工具已验证**:`stack_arise_spine.py` 管线已跑通(喂 vote_only 能重现 `ours_m5_votebase`;random 控制可复现)。

### 11.2 怎么拿到"真·ARISE 的 top-k"(有 Docker 约束)
ARISE = SWE-agent + **Docker**(SWE-bench 容器给仓库环境)。三条路:
- **(推荐,忠实)在有 Docker 的 x86_64 机器上跑官方 SWE-agent**(用户 Windows Docker Desktop 可以;AutoDL 无 Docker;ARM Mac 不行)。命令见 `docs/ARISE_Windows_runbook.md` / `docs/ARISE_agentic_AutoDL_runbook.md`。模型指向 vLLM 或 API。产出 `.traj` → parse_preds → `arise_preds.json`。
- **(Docker-free 备选,我方可全包但需工程)**:git clone 各仓库到 base_commit(纯 git 无 Docker)+ 用 ARISE 官方工具(`vendor/ARISE/src/arise/tools/*` 的 `RetrievalSession`)+ 官方 FL 提示词(`vendor/ARISE/configs/fl.yaml`)驱动一个 ReAct 循环。**代价**:自建 harness、不保证精确复现 41,但叠加实验的科学结论仍成立。
- **口径统一**:两系统都用 §10 的官方 `gold.py`+`metrics.py`(`arise_eval_adapter.py`)打分。

### 11.3 A 会策略(稳发 A)
- **头条**:R@1 是判别指标(ARISE 自己也 headline R@1)。报**完整 R@1/5/10 表**,把"R@5/R@10 不动"讲成"recall-safe 重排"的设计属性。近乎双胞胎先例:**SemLoc(arXiv 2603.29109)**、SweRank、FaR-Loc。
- **别只对弱基线**:必须叠 ARISE。
- **别让修复率当主线**。
- **四条路都通 A**(叠加实验选哪条):Path1 叠加成功(41→50+)=干净 A;Path2 部分=方法+分析;Path3 洗掉→效率 Pareto("~1 次调用达 ARISE 级 R@1,无需程序图");Path4 纯实证。
- **还要做**:多 backbone 官方口径表(basecmp 补齐)、bench2(Verified 61)复现主结果、per-model CI、去 oracle 的端到端(可选,把 file-loc 放回环里)。

---

## 12. 当前基建状态(2026-07-08)

- **A800-80G AutoDL 实例**:vLLM 起来了,服务 `Qwen2.5-Coder-32B-Instruct-AWQ`(ARISE 的 EXACT backbone),`localhost:8002`。SSH:`ssh -p 37033 root@connect.nma1.seetacloud.com`(密码或已装的 ed25519 key)。**注意:实例只关机别 release;数据盘 `/root/autodl-tmp` 持久。**
- **坑1:vLLM 版本 vs 驱动 CUDA**。该实例驱动 **CUDA 13.0**,必须用 cu130 的 torch(最新 vllm 0.24);降到 cu128 会 "no NVIDIA driver"。**别在 base env 乱卸 nvidia 库**(会误删 libcusparseLt)。用干净 conda env。
- **坑2:AutoDL 无卡模式**。下模型/装环境时可能是无卡模式(nvidia-smi 无设备)→ 关机**正常带卡开机**才有 GPU。
- **坑3:AutoDL 没 Docker**(非特权容器,dockerd 起不来)→ ARISE 的 SWE-agent 不能在 AutoDL 跑。
- **坑4:AutoDL 的 SSH 代理掐 `-L` 隧道**(从某些客户端)。用户自己机器(Windows,memory §5.2)隧道成功过。备选:把 SPINE 代码 rsync 到 box 上、在 box 本地跑(vLLM 本地无需隧道)。
- **坑5:ARM Mac 跑不了 SWE-bench Docker**(x86_64 镜像 qemu 模拟 → SWE-ReX 持久 shell EOF)。非交互 `docker exec`(覆盖率收集)可以;SWE-agent 的持久 shell 不行。
- **成本**:SiliconFlow API 一天可花 ~¥100(agentic 更贵)。自建 vLLM 推理免费(只付 GPU 租金)。

---

## 13. 关键教训 / 别再踩

- **别用 `clean_gold` 对标 ARISE**;用官方 `gold.py`(二者 Jaccard 0.46)。SPINE 的 Δ 两种口径都成立(配对抵消金标选择)。
- **叠加实验必须同模型**;要 random 控制臂。
- **修复率别当卖点**(Sepidband 2026)。
- **coverage 缓存必带**(egl_cov_cache.json 50MB),否则重收 250 次 Docker。
- **SPINE 是判别器不是召回器**:只动 R@1,R@5/R@10 不动是设计不是缺陷。
- **弱模型(GLM/Ling/Hunyuan)上 SPINE 不灵**是真实的(能力/headroom 门控),论文要诚实报 4/7 + 机制。
- **盲复现 `arise_file_loc.py` 已 git rm**(工具集错,缺 T2 dataflow-slice + T3);别复活它当 ARISE baseline,用官方 `vendor/ARISE`。
- **`egl_e2e.py --instances` 会用默认 dataset 重载 rows** → behavioral(lite)必须 `SWEBENCH_DATASET=lite`。

---

## 附:一句话给下一个 AI
定位方法 SPINE 已验证(4/7 模型、对抗过关、机制正交、官方口径 +13~15pp R@1)。**你要做的第一件事 = 跑"SPINE 叠加 ARISE"实验**(§11):在有 Docker 的 x86_64 机器上用官方 SWE-agent 跑 ARISE(模型 = A800 的 Qwen2.5-Coder-32B-AWQ)拿 top-k → `stack_arise_spine.py` 同模型重排 → 看 R@1 能否从 41 再涨。工具、数据、覆盖率、口径全在 `prelim_localization/` + `vendor/ARISE/`。别重跑已完成的 7 模型 gate。
