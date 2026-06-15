# PairCoder 审稿弱点与实验补足清单

> 2026-06-10 ｜ 以 SE 顶会(ICSE / FSE / ASE / ISSTA,CCF-A)审稿人视角整理的弱点与对应补足方案,供后续逐条补实验使用。

## 总体判断

- **立意(问题 + 故事)**:达到 A 会水平——概念切割清晰(discovery vs composition、sequence vs pair)、研究债务链叙事完整、test-free 角度有现实价值。
- **当前执行**:投顶 SE 会大概率 borderline → reject。核心债务集中在三处:**自定义静态 oracle 不可信、benchmark 小而同质、缺前沿模型**。
- **一句话**:A 会拒的不是故事,是证据。下表 7 项补完(尤其 P1–P4、P6),才有竞争力。

## 优先级总览

| 编号 | 严重度 | 弱点 | 一句话解法 | 性价比 |
|---|---|---|---|---|
| P1 | 🔴 致命 | 评估存在"循环 oracle":注入的规则 = 检查的规则 | 换成 execution-based hidden tests 作主指标 | ★★★★★ |
| P2 | 🔴 致命 | Benchmark 规模小、库类型同质(全是插件/生命周期类) | 扩到 ≥3 个不同领域库 / ≥60 任务,四类 pair 均衡 | ★★★★★ |
| P3 | 🔴 致命 | 新颖性定位弱:未区隔 API misuse / spec mining / RAG-for-code | 重写 related work,前置差异点 | ★★★★☆ |
| P4 | 🟠 严重 | 方法深度不足:"抽取"是难点却最含糊 | 把高精度抽取+验证做成核心方法贡献 | ★★★★☆ |
| P5 | 🟠 严重 | "test-free" 措辞易被攻击 + 对 UCD 可能稻草人 | 精确限定 + 对基线刻画留余地 | ★★★☆☆ |
| P6 | 🟠 严重 | 统计不严谨:n=6、无置信区间/显著性检验 | 扩样本 + CI + 配对检验 | ★★★★☆ |
| P7 | 🟠 严重 | 只有 7–9B 本地模型,缺前沿模型 | 补 ≥1 个 GPT/Claude 级模型 | ★★★★☆ |

---

## P1 🔴 评估的"循环 oracle"问题 ✅ 已完成(2026-06-12)

**审稿人会怎么打**:
> "你注入规则 X(B4 gold pair rule),又用'是否满足规则 X'的静态 checker 来评分,B4 当然 0% 违规——接近同义反复,不能证明生成代码真的能跑、行为正确。"

**根因**:现有存在性证据完全依赖自写 AST checker;checker 检查的约束与注入的 gold rule 同源。静态检查还会误判"语义对但写法不同"(已出现过 qwen2.5 假阳性),也可能放过"骗过静检但运行时错"的代码。

**解法**:
- 主指标改为 **execution-based hidden test pass rate**;pair violation 静态 checker 降级为**辅助 / 错误归因**用途。
- 为每个 task 建"违反 pair 约束 → 隐藏测试必然失败"的可执行锚定,证明 pair violation 度量的有效性。
- 报告静态 checker 与执行结果的一致率(验证 checker 可信度)。

**补足 TODO**:
- [x] 为每个 pair-critical task 编写 hidden tests(把约束转成可观察行为)→ `Ollama问题存在性实验/exec_oracle/`(真实 simplug 0.5.7 vendored + 运行时插桩 fixture;锚定套件 28/28:正确解与语义等价变体必过、各类违规以预期原因必挂)
- [x] 重跑存在性实验,主表换成 hidden-test pass rate → 450 份已有生成全量执行重评(无需新推理),`result/simplug_7b_5model_comparison/exec_eval/exec_summary.md`;B0–B3 仍 0.50–1.00 高违规,B4 显著下降(B3 vs B4 配对 McNemar 精确检验 p≈9.4e-07);B4 原先两个可疑 0.00 修正为 0.17
- [x] 报告 静态 checker vs 执行结果 的混淆矩阵 / 一致率 → 一致率 93.6%,Cohen's κ=0.83;25 例静过执挂(含 1 例 `ast.parse` 能过但无法编译的代码)+ 4 例静挂执过(语义等价写法被误伤),逐例归因见 `exec_eval/disagreements.csv`

**完成判据**:存在性结论在**执行指标**下依然成立(B0–B3 仍高违规、B4 显著下降),且 checker 与执行的一致率可接受(如 ≥90%)。✅ **已达成,详见 `docs/PairCoder_Benchmark_完整说明.md`(§5 评测方法学、§8 存在性结果)**

---

## P2 🔴 Benchmark 规模与代表性

**审稿人会怎么打**:
> "1 库 6 任务的存在性、3 库 20–40 任务的主实验,量级偏小;gold rule 全自标注,疑似 cherry-picking;而且 watchdog/schedule/simplug/pluggy 全是插件/生命周期风味,你只证明了一类问题。"

**根因**:库领域同质 → 四类 pair 分布偏向 shared-receiver / lifecycle-order,return-flow / param-dependency 样本不足;任务量小 → 外部效度弱。

**解法**:
- 库领域拉开:数据处理、网络/HTTP、序列化、ORM/DB、科学计算等,覆盖四类 pair。
- 规模上推:≥3(理想 5)个库、≥60 任务。
- 明确报告**每类 pair 的任务数分布**,避免"只测一类"。

**补足 TODO**:
- [ ] 选 ≥3 个**不同领域**的低流行度/未见库(替换掉同质的插件类)
- [ ] 扩任务到 ≥60,保证四类 pair 每类有足够样本
- [ ] 在论文里给出 pair-type × 任务数 分布表
- [ ] gold rule 双人标注 + 报告 inter-annotator agreement

**完成判据**:四类 pair 每类 ≥10 任务;结论在跨领域库上一致成立。

---

## P3 🔴 新颖性定位(最易被判"增量")

**审稿人会怎么打**:
> "你的四类 typed 约束与 API misuse 分类(MUC/MUBench)高度重叠;pair rule 本质是已知的 API usage specification;真正新的只是'塞进 prompt',是 RAG 的变体。"

**根因**:related work 只对标 PR-Miner / CAPIR / DomCoder / UCD,忽略了两片成熟文献:
1. **API misuse detection / specification mining**(MAPO、GrouMiner、MUDetect、MUBench/MUC 等);
2. **retrieval-augmented / API-aware code generation**。

**解法(差异点前置)**:
- 与 misuse/spec mining 的区别:它们**事后检测**已有代码的 violation;PairCoder **生成时注入**约束,且**不依赖已有缺陷样本/测试**地恢复约束。
- 与 RAG-for-code 的区别:RAG 注入**文档片段**;PairCoder 注入**带类型、有证据、最小可验证的成对推理单元**,并有 typed-edge↔error-type 的机制对应。

**补足 TODO**:
- [ ] 新增 related work 小节,正面覆盖 misuse/spec mining + RAG-for-code
- [ ] 写一段"差异点表":检测 vs 生成、测试依赖 vs 非测试、文档片段 vs typed pair rule
- [ ] 把这段差异从第 9 节提前到引言/相关工作显著位置

**完成判据**:审稿人能在读完相关工作后一句话复述"PairCoder 与 misuse 检测 / RAG 的不同"。

---

## P4 🟠 方法深度(抽取才是难点)

**审稿人会怎么打**:
> "从文档/示例/类型恢复 pair 再塞进 prompt,是工程不是技术贡献。"

**根因**:真正难且值钱的是**高精度抽取**,但现在最含糊。尤其:
- `param-dependency` 要判"参数的**语义来源**正确"而非仅类型对,远难于 return-flow 的 `x=A(); B(x)`;
- 无明确机制保证 extracted rule 的 precision;错误 rule 会**反向误导**生成(第 10 节已列此失败模式)。

**解法**:把"抽取 + 验证"做成核心方法贡献——
- 证据类型与约束类型的对齐机制(不同 evidence 支持不同 relation 的判定);
- 置信度校准 + 高精度过滤(evidence verifier 去黑盒化);
- 用 RQ1 的 precision/recall/edge-type accuracy 严肃支撑。

**补足 TODO**:
- [ ] 形式化抽取流程,明确每类 pair 的判定证据与判据
- [ ] 设计 evidence verifier / 置信度过滤,并做"过滤阈值 → precision"曲线
- [ ] RQ1 完整跑:抽取 precision/recall vs gold;分 pair-type 报告
- [ ] 分析"错误 pair rule 对生成的负面影响"量级

**完成判据**:extracted rule precision 足够高(如 ≥0.8),且能证明高精度过滤对生成收益必要。

---

## P5 🟠 "test-free" 措辞 + 对 UCD 的刻画

**审稿人会怎么打**:
> "你说不依赖测试,但评估和验证抽取质量都用了 hidden tests / gold rule,自相矛盾。" / "你夸大了 UCD 对内部测试的依赖(它用的是 test/usecase 合成)。"

**解法**:
- 精确限定为 **"extraction-time / inference-time test-free"**——抽取与生成时不用测试;测试**只**用于 gold 审查、hidden 评估、结果验证。
- 对 UCD 表述留余地:改为"UCD 的组合知识恢复以(合成)测试为核心信号",避免稻草人。

**补足 TODO**:
- [ ] 全文统一 test-free 的限定语
- [ ] 复核对 DomCoder / UCD / CAPIR 的描述与原文一致(防审稿人核对)

**完成判据**:无"自相矛盾"或"歪曲基线"的可攻击表述。

---

## P6 🟠 统计严谨性

**审稿人会怎么打**:
> "n=6/格,粒度 16.7%,3 轮投票仍粗;没有置信区间和显著性检验;B5 vs B3 的差距可能落在噪声里。"

**解法**:
- 主实验任务量上去后,报告 pass@k 方差、bootstrap 置信区间;
- B5 vs B3、B5 vs B4 用**配对显著性检验**(如 McNemar / 配对 bootstrap)。

**补足 TODO**:
- [ ] 每条件 ≥3–5 轮,报告均值 + CI
- [ ] 关键对比加配对显著性检验与效应量
- [ ] 明确随机性来源(温度、采样)与控制

**完成判据**:核心结论带显著性(p 值 / CI 不跨临界)。

> 注:P1 重评已先行给出一组配对检验示范(B3 vs B4 运行级 McNemar 精确双侧 p≈9.4e-07,不一致对 38:6),全面统计仍按本节在扩规模后补齐。

---

## P7 🟠 模型档位(缺前沿模型)

**审稿人会怎么打**:
> "只有 7–9B 本地模型。GPT-4o / Claude / DeepSeek-V3 这类前沿模型还会犯吗?若不犯,你的问题只是小模型问题。"

**双刃剑**:若前沿模型**照样犯** → 极强卖点(问题不随能力消失);若基本不犯 → significance 缩水。

**解法**:
- 至少补 **1 个前沿模型**(GPT / Claude 级),验证 pair violation 是否持续。
- 想清楚论文设定:**通用 API 组合问题** vs **边缘小模型部署问题**——别中途换设定(近期往"边缘智能"收的 framing 会削弱普适主张)。

**补足 TODO**:
- [ ] 接入 ≥1 个前沿模型跑同一矩阵
- [ ] 据结果确定主张边界(通用问题 / 受模型规模调节的问题)
- [ ] 统一全文的问题设定,避免"通用"与"边缘"摇摆

**完成判据**:有前沿模型证据;问题设定全文一致。

---

## "从 borderline 到 clear accept" 推荐执行顺序

1. **P1 换 execution-based oracle**(最关键,先做)✅ 已完成
2. **P7 补前沿模型**(放大 significance,成本低)← 下一步
3. **P2 扩库 + 去同质化**
4. **P3 重写 related work 差异化**
5. **P4 把高精度抽取做成真方法**(决定是"方法论文"还是"prompt 工程")
6. **P6 补统计**
7. **P5 精确措辞**(写作收尾期统一过一遍)

> 成败关键命题:**B5(extracted)显著优于 B3(CAPIR-style sequence),且接近 B4(gold)**——这是 RQ2 主实验要打出来的核心结果。

## 会场校准(现实预期)

| 状态 | 预期 |
|---|---|
| 现在直接投 ICSE/FSE/ASE/ISSTA | 大概率 reject(oracle + 规模 + 新颖性区隔) |
| 完成 P1–P4 + P6 后投 A 会 | 有竞争力,weak/borderline accept,取决于 B5 结果 |
| 作为 proposal / 开题 / workshop / registered report | 已相当扎实,概念框架是加分项 |

## 进度追踪(勾选用)

- [x] P1 execution-based oracle(2026-06-12,管线:`Ollama问题存在性实验/exec_oracle/`;说明:`docs/PairCoder_Benchmark_完整说明.md`)
- [~] P2 扩库 + 去同质化 + pair 分布表(进行中:taxonomy 已定 6 类;4 库 simplug/msgspec/peewee/niquests 已实现+锚定全绿,38 任务;距每类≥10/总数≥60 还差约 22 任务。详见 `docs/PairCoder_Benchmark_完整说明.md` §3–§4)
- [ ] P3 related work 差异化定位
- [ ] P4 高精度抽取 + 验证 + RQ1
- [ ] P5 test-free 措辞 + 基线刻画复核
- [ ] P6 统计(CI + 显著性检验)
- [ ] P7 前沿模型 + 设定统一
