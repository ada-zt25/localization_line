# CBA 行级召回优化方案（前沿技术 + 抗幻觉，2026-06-25）

> 一句话:**B 把候选池做大(扩召回、抬天花板),A 对每个候选做"是/否"二分裁判把金标排进 top-k(realize),C 只给 A 喂 grounded 的"为什么"。** 你图里"把 AI 列清单换成 AI 做是非判断"不是风格选择——它是离线门控(Q3)已经证明的**唯一能兑现候选集天花板**的机制,也是文献里最硬的一条路。

本方案针对 `prelim_localization/` 的 CBA 流水线(圈区域 → **C** 根因锚点 → **B** 建候选池 → **A** 逐块裁判 → 排序行号),目标 = 抬 **LINE-level recall**(R@5/R@10)。所有手段都是**推理期/提示期**,不动权重,保持与 ARISE 同模型可比。

来源:多 agent workflow `wf_27c4b024`(4 研究 + 3 设计 + 对抗校验,结论一致;仅"综合"agent 撞会话额度,本文档为人工综合)。配套记忆 `cba-optimization-plan.md`,诊断底料见 `6.24实验.md` / `arise-rk-gap-diagnosis`。

---

## 0. 战略:R@10 天花板链 —— 每道墙由哪个杠杆攻破

| R@10 上限 | 含义 | 攻破它的杠杆 |
|---|---|---|
| 47.3 | 现状(输给 ARISE 74) | — |
| 57.7 | 完美排序**当前**投票集 | **A 逐块裁判**(p(Yes) 排序信号) |
| 67.0 | 区域墙(完美投票) | **B 多视角并集扩池 + 覆盖兜底**(抬 voted_ceiling),A realize |
| 73.7 | 文件墙 = file R@10 | 换文件检索器(SweRank 式) — **C/B/A 之外** |
| 74 | ARISE(在文件墙之上) | 需跨文件召回(仅 +0.3) |

**关键区分(必须在论文里分开说):**
- **B / 对齐金标 / 扩池** 只抬"天花板"(候选集里**有没有**金标)——**必要不充分**。
- 只有 **A 裁判**能把天花板 **realize** 成真实 R@k。

**已证实的死路(不要再走):**
- 机械 def-use 扩展 + 重排 → 天花板 +6.9,realize +0(扩进来的金标是 ~84 个 def-use 邻居里的 1 根针,没有排序信号能单独挑出)。见 `Q3_离线门控结论.md`。
- 覆盖率当排序项(`δ·covered`)→ 惰性(300 里仅 1 个实例改变 R@k),结构上无法把找到的金标加进候选集。

---

## 1. A 段(逐块裁判)—— realize 杠杆，优先级最高

**现状缺口**:`region_line_loc_ex` 之后只有 `_rank_v0`/`_rank_counts`(机械 RRF 重排)+ `llm_final_pick`(重排 top-8)。**没有真正的 A 段。** 诊断 #4 已证明任何重排都 realize 不出扩进来的金标——唯一能挑出针的,是对**每个候选**做一次独立的二分判断。

### A1 · 批量 GenRM-CoT 是非裁判（headline）
- **机制**:对 B 池子里每个候选行,给模型 `issue + C 的锚点 + 该行 + 它的 def-use 邻居 / 覆盖证据`,让它先写一句理由再吐单 token `Yes/No`。**从 logprob 读 `p(Yes)` 当连续排序分**——不信模型自报的置信数字。
- **为什么 realize**:判断是 discriminative 任务(LLM 强项);它给每个候选一个独立、可比的分数,正是把针从 84 邻居里挑出来需要的排序信号。
- **落点**:新增 `region_loc._judge_pool(model, issue, anchors, path, lines, candidates, evidence) -> {line: p_yes}`;`region_line_loc_ex` 加 `rank_mode='judge'`,门控、默认 OFF、字节不变。
- **召回安全(关键)**:裁判**只当 ranker、不当 filter**——永不把 B 的候选丢到 top-10 之外;若要门控,阈值偏召回(如 `p(Yes)>0.2`)。加 `unsure` 档但**只降权不删除**。
- **依据**:GenRM (arXiv:2408.15240);Abstain-and-Validate 双 LLM (arXiv:2510.03217,filtered accept@1 38→62);CriticGPT 的 precision-recall 旋钮 (arXiv:2407.00215)。

### A2 · 自一致性陪审团 + 打乱顺序
- **机制**:每个候选判 m=3–5 次,**每次打乱候选顺序**,并换视角框架(数据流 / 控制流 / issue 改写 = 单模型 PoLL)。聚合 = `p(Yes)` 的 maj@K;跨样本一致计数当 R@1 tiebreak(复用现有 `counts`,现作用在二分任务)。
- **落点**:`region_loc._judge_pool_jury`。
- **依据**:LLM 故障定位位置偏见 (arXiv:2412.18750);PoLL (arXiv:2404.18796);AutoFL 的"5 次后收益递减"(arXiv:2308.05487,别超采)。

### A3 · cite-then-decide(抗幻觉）
- **机制**:强制 JSON 顺序 `{"quote": <从区域逐字复制的子串>, "line_id": <int∈池>, "edit":"yes|no", "reason":...}`,quote/line_id **先于** yes/no。程序校验 quote 是 `lines[line_id-1]` 子串、line_id 合法;不符则 abstain。
- **依据**:Attribute-First-then-Generate (arXiv:2403.17104);CoVe (arXiv:2309.11495)。

### A4 · 多智能体辩论（**只**当 head 精排，替换/增强 `llm_final_pick`）
- **机制**:辩论会**收敛、剪掉少数意见** → 用在 B(需扩集)上会缩召回,**严禁**。只用在 A 排好序后的 top-8/12 **head** 上:两个 grounded 人设("此行必改,因为 <C 锚点>" vs "此行只是旁路")逐候选辩论,judged against C 锚点 + 覆盖证据。抬 R@1/R@5 排序,不动 R@10 尾巴/候选集。
- **落点**:替换/增强 `region_loc.llm_final_pick`。**永不让辩论从候选集删行**(召回地板)。
- **依据**:Multiagent Debate (Du 2023);SWE-Debate (arXiv:2507.23348)。

### A5 · 排序融合：RRF 保留为 tiebreaker，不要拆掉 `_rank_v0`
- **机制**:A 裁判的 `p(Yes)` / yes-fraction 是**主排序键**;现有 `_rank_v0` 的 RRF(vote 质量 + 图分 + counts 一致性)**保留为 A 之后的 tiebreaker**。文献确认 RRF 的"纯 rank、抗尺度失配"正是融合异构信号的稳健选择,**别换成分数归一化**。
- **额外先验(CodeT 式一致性)**:喂给裁判的每个候选可带一个先验 = (跨样本投票一致计数) × (它落在几条 def-use 切片上),当裁判可引用的"有几个独立信号指向这里"证据。
- **依据**:Reciprocal Rank Fusion (Cormack 2009);CodeT (arXiv:2207.10397)。

> **对抗层砍掉的 A 类死路**:成对/列表式裁判当主排序(位置偏见 + "从 84 个里挑 1 个"失败模式,你已离线证实 R@10≈60.8)。**逐候选 pointwise 二分**才能逃出。

---

## 2. B 段(建候选池)—— 召回杠杆，抬 voted_ceiling 0.557 → 逼近 0.784

**核心依据**:诊断 #5 —— 22 分缺口**大部分不是 def-use 邻接的金标**(机械扩展只补 6.9%)。真正杠杆 = 让投票本身看到更多金标,靠**多样性**,不靠机械扩展。

### B1 · 多视角并集投票（MoRE，headline）
- **机制**:同一区域用 3–4 个正交提示框架各投一轮、**取并集**:① issue-症状 ② traceback/异常路径 ③ 数据流/def-use(用 C 锚点当种子) ④ 测试期望。不同提示捞到互补金标。
- **为什么比机械扩展强**:每个视角自带排序信号(不像 84 个无信号 def-use 邻居),A 裁判能用上。
- **落点**:`region_loc._vote` 内循环加 `view` 维度,并集喂 A。
- **依据**:MoRE (arXiv:2305.14628);Agentless 实测 union 把行级 containment 50.67→56.33(arXiv:2407.01489,与我们 0.557 一致 → 已到 k=4 并集天花板,**杠杆是更多样本 + 更多视角,不是更好的 merge 规则**)。

### B2 · k 自适应上调
- **机制**:`k_samples` 5→15~25,高温(T≈0.8–1.0, top-p≈0.95)+ 保留一个 greedy;预算偏向难实例(region 大 / freq 分歧大),易实例早停。召回随 k 近似 log-线性(到区域墙 67 平)。
- **落点**:`_vote` 的 k 循环 + `counts` 一致性早停(Adaptive-SC / ESC)。
- **依据**:Brown "Large Language Monkeys" (arXiv:2407.21787)。

### B3 · 覆盖率改成"召回兜底"，不再当排序项
- **机制**:投票后,把"在区域内 ∧ 距投票行 ±3 ∧ 被失败测试执行过"的行**并进候选集**(给合成低票质、排尾,保 R@1/R@5),只救 32/48 个投票全漏实例;**同时把"这行真被执行过"作为 A 裁判证据**。
- **落点**:`region_line_loc_ex` vote 之后注入 `freq`。**别并入全部覆盖行**(中位 813 行→精度崩)。
- **诚实**:`cov_on_gold` 只有 0.37,上限有限,严格 backstop。
- **依据**:NExT 执行证据 (arXiv:2404.14662)。

### B4 · 解除区域墙（Lever 1 + Lever 2，已实现）
- `--arise-gold`(对齐金标,区域天花板 0.801→0.896,**且公平**)+ `--small-file 1800 --max-region 2000 --all-module-lines`(整文件当区域→1.0)。见 `区域天花板_两个杠杆.md`。
- **必要不充分**:只解除"第 1 步卡死后面"的硬约束;realize 仍靠 A。大区域→投票 prompt 变大,这正是换逐块裁判的动机。

### B5 ·（可选/次要）异构模型并集 —— "联邦"的诚实落地
- **机制**:若能负担第二个模型(不同 Qwen 尺寸或别的 code 模型),不同模型族犯**互补错误**,并集能捞到单模型 self-consistency 捞不到的金标,抬天花板。**这才是"异构集成"的真实技术内容**(见 §5)。
- **硬约束**:**union-then-JUDGE,永不 union-then-vote** —— 词表/质量失配会让朴素异构投票放大相关错误;让 A 裁判当唯一仲裁者,顺手过滤非法行号。第二个模型**只当召回助推器并进池子**。
- **代价/取舍**:加一个模型依赖 + 破坏"与 ARISE 同模型"可比性 → **标为可选、次要**;能不引入就靠 B1 单模型多视角(MoRE)拿到大部分多样性收益。
- **依据**:DEI (arXiv:2408.07060);More Agents Is All You Need (arXiv:2402.05120);异构集成需谨慎 (DeePEn arXiv:2404.12715)。

> **对抗层砍掉的 B 类死路**:把锚点注入投票 prompt(收窄 union 多样性→反伤召回);区域分块投票(加进无信号候选,同针海问题);机械 def-use 扩展 + 重排(已证伪);多智能体辩论当 B 的并集器(辩论收敛→缩召回,只能用在 A head);朴素异构投票(放大相关错误,必须 union-then-judge)。

---

## 3. C 段(根因分析 → 锚点)—— 角色重定位:给 A 喂证据，不自己修召回

**对抗层关键发现**:别指望 C 靠"重新给 def-use 切片喂种子"来修召回(诊断 #5:缺口大部分非 def-use 邻接)。**C 的真正价值 = 给 A 裁判和 B 数据流视角提供 grounded 的"为什么"。**

### C1 · 显式根因锚点段，锚点强制是真实 AST 符号
- **机制**:一次 LLM pass 说清"哪个变量 / 哪条出错路径是根因",产出锚点,替换 token-match 的 `seed_from_issue`/`seed_from_traceback`。
- **抗幻觉(硬保证)**:锚点**必须命中 `code_graph.CodeGraph` 符号表**(`g.funcs`/`g.classes` 名 + def-use 变量名),不命中就 reject-and-resample = Monitor-Guided Decoding 效果,用 vLLM `guided_choice`(终结符 = 真实符号名)轻量实现。
- **用途**:① B 数据流视角的种子 ② A 每条判断必须 reason against 的"为什么"上下文。**只收窄注意力,不直接定位。**
- **依据**:LLM4FL (arXiv:2409.13642);MGD (Agrawal, NeurIPS 2023)。

> **对抗层砍掉的 C 类死路**:CoVe 重锚点验证(过度工程,一个 AST 校验门就够);锚点注入投票 prompt(见 B)。

---

## 4. 跨阶段抗幻觉的"硬"保证（"最稳妥、不跑偏"的地基）

不靠 prompt 祈祷,要**结构性**保证。已 POST 到 vLLM OpenAI 接口(`region_loc._llm_t`),近乎零代码:

1. **约束解码(最便宜的赢)**:payload 加 `guided_json`/`guided_choice`(vLLM 内置 XGrammar)。
   - `_vote`:强制"区域内合法行号的 JSON 数组"→ `parse_ranked` 不再因解析失败丢票。
   - A 裁判:`guided_choice` 限定 `{yes,no}` + 读 logprob;行号枚举 = 真实候选集 → **永不可能吐区域外行号**(替掉软性 `if p in region` 静默丢弃)。
   - C 锚点:枚举 = 真实 AST 符号名。
   - 注意 Grammar-Aligned Decoding (arXiv:2405.21047):硬约束会扭曲分布 → **按 logprob 排序而非贪心 argmax**。
2. **事后 AST/区域校验门(belt-and-suspenders)**:任何 LLM 输出元素违反"符号存在 / 行号合法 / 引用是真子串"→ drop 或 resample,绝不信任。即使某 serving 栈开不了 XGrammar 也兜底。

> **砍掉**:RAG(文件已全量给,无外部知识可检索,只引入检索噪声);微调校准(破坏与 ARISE 同模型对比,且"人为训练方向"已废弃)。

---

## 5. 联邦学习:诚实裁决（不适用，4 研究 agent 一致）

- 联邦学习(FedAvg/FedProx)解决的是**训练**问题:多数据持有方因隐私/合规/带宽不能集中数据,交换梯度/权重而非原始数据共训一个模型。前提:① ≥2 数据孤岛 ② 训练循环 ③ 不许集中。
- **本问题三个都没有**:单一公开数据集(SWE-bench Lite n=300)、单台本地 vLLM 服务的 Qwen-32B、**不训练**、无隐私约束。瓶颈是**推理期 recall**,FL 碰不到。强行加 = 增加基础设施 + 零召回 + 破坏同模型可比性。
- **用户真意 = "把多个独立弱判断聚合成强决策"**,这就是 A 段。正确的前沿类比:Self-Consistency 并集 (arXiv:2203.11171)、MoRE 多提示专家 (arXiv:2305.14628)、GenRM-CoT (arXiv:2408.15240)、PoLL 陪审团 (arXiv:2404.18796)。
- **结论**:不把"联邦学习"写进论文(那是跑偏);写"推理期多视角集成 + 认证裁判"。若确实想要"异构模型并集"那层意思,正确落地见 **B5**(union-then-JUDGE,标为可选/次要)。

---

## 6. 落地顺序（offline-first / cheap-first）

| 步 | 做什么 | 成本 | 性质 |
|---|---|---|---|
| **0** | `--arise-gold` 重算历史 bf16 结果 → 拿**公平**的对 ARISE 差距(数大概率上升) | 免费/离线 | 先 re-baseline,别在脏金标上比 |
| **1** | 约束解码 + 事后校验门(`_llm_t` payload + 校验) | 极低/近零代码 | 纯抗幻觉,顺手救回解析失败丢的票 |
| **2** | **A 段 GenRM-CoT 裁判**(`_judge_pool`, `rank_mode='judge'`, p(Yes) logprob) | 中 | **headline realize 杠杆**,门控 OFF,先小样本验证 |
| **3** | B 段多视角并集 + k 上调 + 覆盖率兜底注入 | 中 | 抬 voted_ceiling,给 A 更全 haystack |
| **4** | C 段锚点段(AST 约束)给 A 当证据 | 中 | grounding,提质 |
| **5** | A 段陪审团 + 打乱顺序(A2/A3) | 中 | 精排 + 稳健性 |
| **6+** | SweRank 式 embedding 文件检索器 (arXiv:2505.07849) | 高 | 唯一能过**文件墙 73.7**、够 ARISE 74 的路 |

每步先在 `egl_e2e --dump-substrate` 导出的底料上离线门控(`ablation_rank_sweep.py`)验能验的先验,再上 GPU。

---

## 7. 诚实的天花板提醒

- **天花板 ≠ realized**:B / 对齐金标 / 扩池只抬必要不充分的天花板;只有 A 把它变成真实 R@k。
- **文件墙 73.7 卡死端到端**:line R@10 ≤ file R@10。ARISE 74 在文件墙**之上** → 光做 C/B/A 最多 ~67;够 ARISE 必须同时抬文件召回(步 6)。
- **覆盖率 cov_on_gold 0.37**:很多修复是插入新行 / 未执行分支,覆盖率天然抓不到 → 严格 backstop。
- **量级要离线验**:k→并集、裁判收益的具体数字别信预测,先 dump 底料(上次因底料不存在被审核抓到)。
- **弱验证器风险(对 A 段最重要)**:Qwen-32B **不会自动是好裁判**——"生成能力 ≠ 验证能力",且验证能力不随规模可靠提升(Mind the Gap, Song ICLR 2025;Small LMs Need Strong Verifiers, Zhang ACL 2024)。所以裸的"这行有 bug 吗?"单发自判是死路(LLMs Cannot Self-Correct, arXiv:2310.01798)。**必须**靠 A1–A3 的三重保险兜住:① 喂 grounded 证据(def-use 邻居 + 覆盖) ② maj@K 多采样聚合 ③ cite-then-decide 逐字引用。三者齐全前,别信任单次裁判结果。

---

## 8. 引用一览（已核实，2022–2026）

- GenRM 生成式验证器 — arXiv:2408.15240
- Abstain-and-Validate 双 LLM — arXiv:2510.03217
- CriticGPT / LLM Critics — arXiv:2407.00215
- Attribute-First-then-Generate — arXiv:2403.17104 · CoVe — arXiv:2309.11495
- 输入顺序偏见(故障定位) — arXiv:2412.18750 · PoLL 陪审团 — arXiv:2404.18796
- AutoFL — arXiv:2308.05487 · LLM4FL — arXiv:2409.13642
- MoRE 多提示专家 — arXiv:2305.14628 · Self-Consistency — arXiv:2203.11171
- Large Language Monkeys(重复采样标度) — arXiv:2407.21787
- NExT 执行证据 — arXiv:2404.14662 · Agentless — arXiv:2407.01489
- Grammar-Aligned Decoding — arXiv:2405.21047 · XGrammar — arXiv:2411.15100
- Monitor-Guided Decoding — Agrawal, NeurIPS 2023
- SweRank 文件检索 — arXiv:2505.07849 · "Why LMs Hallucinate" — arXiv:2509.04664
- SelfCheckGPT — arXiv:2303.08896 · Universal Self-Consistency (USC) — arXiv:2311.17311
- CodeT(生成测试一致性) — arXiv:2207.10397
- DEI 多样性委员会 — arXiv:2408.07060 · More Agents Is All You Need — arXiv:2402.05120
- 异构集成需谨慎(DeePEn) — arXiv:2404.12715
- 多智能体辩论(Du 2023) · SWE-Debate — arXiv:2507.23348
- LLMs Cannot Self-Correct Reasoning Yet — arXiv:2310.01798
- Mind the Gap(验证≠生成,ICLR 2025) · Small LMs Need Strong Verifiers(ACL Findings 2024)
- Adaptive-Consistency(Aggarwal 2023) · Early-Stopping Self-Consistency(ESC, ICLR 2024)
