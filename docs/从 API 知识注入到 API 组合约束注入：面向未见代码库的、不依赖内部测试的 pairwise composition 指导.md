# PairCoder 研究计划（Research Proposal）

> 从 API 知识注入到 API 组合约束注入：面向未见代码库的、不依赖内部测试的 pairwise composition 指导

> [!abstract] 摘要
> PairCoder 建立在 CAPIR 的 library-oriented 代码生成框架之上。CAPIR 通过任务分解、API 检索与重排序改善 API discovery，但 API discovery 不保证 API composition correctness——即使推荐了正确的 API，生成代码仍可能违反 return-flow、param-dependency、shared-receiver 或 lifecycle-order 约束。PairCoder 因此把注入的知识单元从 API 序列升级为 **typed, evidence-backed API pair rule**，并主张这类最小组合知识可不依赖内部测试、仅从非测试证据中恢复，从而适用于缺乏高质量测试的私有库与低流行度库。

---

## 研究背景概述

面向未见 / 低资源 Python 代码库的代码生成，已有工作沿着"向 LLM 注入 API 知识"这条主线不断推进：DomCoder 解决了"模型不知道该用哪些 API"（API discovery）；UCD-Training 进一步证明"单个 API 知识不够，还需要 compositional API reasoning（组合知识）"，但其组合知识的恢复**依赖高质量内部测试**；CAPIR 转而走"任务分解 + API 检索 + 重排序 → API sequence"的路线，绕开了测试依赖，却把输出停留在"推荐 API"层面。

本文指出并通过实验验证：**即使 LLM 已经拿到正确的 API 序列，在面对需要满足细粒度成对约束（two-constraint API compose）的任务时，仍会稳定地产生 pair violation。** 我们在 5 个跨 4 家厂商的 7–9B 开源模型上做了问题存在性实验：在仅提供 API 清单 / 文档 / 甚至 oracle API 调用顺序的条件下，pairwise composition 违规率普遍在 50%–100%；而一旦显式注入成对约束（pair rule），违规率大幅下降。

据此，本文提出 **PairCoder**：将注入的知识单元从"API 序列"升级为 **typed, evidence-backed pairwise API composition rule（带类型、有证据支撑的成对 API 组合规则）**，并主张这类最小组合知识可以**不依赖内部测试**、仅从文档、示例、类型信息和轻量源码证据中恢复，从而适用于缺乏高质量测试的私有库与低流行度库。

---

## 1. 研究背景与动机

本文的问题是沿着一条清晰的"研究债务链"逐步逼近的：每一项前序工作解决了上一项的遗留问题，同时暴露出新的、更深一层的问题。

### 1.1 DomCoder：把"API 知识"注入 LLM——解决了 API discovery

DomCoder 的出发点是：LLM 在特定领域代码生成上性能下降，一个重要原因是预训练阶段缺乏领域库、领域 API 及其使用模式的数据。其核心做法是 **API knowledge injection**：

- 先预测任务相关的 API，再把 API 信息拼接进 prompt 引导生成；
- 在生成过程中逐步预测 API 状态与任务状态（链式思考）；
- 并可把"先想 API 再写代码"的推理过程通过微调固化进模型参数。

**DomCoder 真正解决的是 API discovery / API selection**——让模型知道"这个任务可能要用哪些 API"。

**它遗留的问题**：API list 或 API sequence 能告诉模型"可能调用哪些 API"，却无法稳定表达"为什么 `API_B` 必须以特定方式接在 `API_A` 之后"。例如序列 `create_client → send_request → close` 并未说明：`create_client` 返回的 client 对象必须被 `send_request` 复用、`close` 必须释放同一个 client。**即 DomCoder 解决了 discovery，未解决 API composition semantics（组合语义）。**

### 1.2 UCD-Training：证明"组合知识有用"——但把恢复路径绑死在内部测试上

UCD-Training 进一步证明：未见代码库生成不仅需要单个 API 知识，更需要 **compositional API reasoning**。其做法是借助 code graph 与"测试 / 用例合成"来构造训练数据，再通过持续预训练 + 监督微调，把代码库结构与 API 组合知识注入模型参数。

**UCD 的关键贡献**：实证了"compositional API data 对生成性能至关重要"——它补上了 DomCoder 留下的"组合语义"这一环。

**它遗留的、也是本文最关键的动机问题**：UCD 恢复 compositional API data 的路径**高度依赖高质量内部测试**（用测试 / 用例去合成、验证组合知识）。然而这一前提在现实中常常不成立：

1. **私有库 / 低流行度库常缺失高质量内部测试**：大量公司私有库、市面上少见的第三方库，根本没有覆盖真实使用场景的、可执行的高质量测试套件；
2. **即便有测试，也常与应用场景不符**：内部测试可能只覆盖边界条件、回归用例或实现细节，无法反映 API 在真实任务中的组合用法，导致据此恢复的组合知识失真甚至误导。

因此 UCD 暴露出一个更基础的、尚未被回答的问题：

> **高质量内部测试，究竟是恢复 compositional API knowledge 的"必要条件"，还是仅仅是"高质量证据的一种实现路径"？**

### 1.3 CAPIR：用 API sequence 绕开测试依赖——但退回到了 API discovery 层面

CAPIR 面向低资源 / 未见代码库，给出了另一条不依赖训练、也不依赖内部测试的思路：通过**任务分解 → API 检索 → API 重排序**，在生成时把相关的 **API sequence** 注入 prompt。它证明了：在未见库中，粗粒度任务描述无法直接映射到正确 API 使用，必须经由检索与重排序来改善 API discovery。

**CAPIR 的价值**：提供了一个测试无关、生成时（inference-time）注入外部 API 知识的 library-oriented code generation 框架。

**它遗留的问题**：CAPIR 的输出本质仍是 **API list / API sequence**。它能回答"这个任务需要哪些 API、大致什么顺序"，但**无法显式表达这些 API 之间为什么、如何、以什么对象 / 参数 / 状态 / 生命周期顺序正确组合**。换言之，CAPIR 在方法形态上回到了与 DomCoder 同层的 API discovery，只是不依赖训练数据。

### 1.4 关键缺口与本文切入点

把三项工作并置，研究债务链清晰可见：

| 工作 | 解决了 | 遗留的问题 |
|---|---|---|
| DomCoder | API discovery（知道用哪些 API） | 不能表达 API 之间的组合语义 |
| UCD-Training | 证明组合知识有用、并注入模型 | 组合知识的恢复依赖高质量内部测试 |
| CAPIR | 测试无关、生成时注入 API sequence | 输出止于 API 序列，仍是 discovery |

本文的切入点正落在这条链的交汇处：

> 当 LLM **已经获得**正确的 API（甚至正确的 API 调用顺序）之后，它为什么仍然组合错？而恢复这种"如何正确组合"的知识，是否**必须依赖内部测试**？

我们主张并验证：(1) 仅有 API 序列不足以消除细粒度成对组合错误；(2) "如何正确组合"这一最小组合知识，对相当一部分高精度的成对约束而言，**可以不依赖内部测试**、仅从非测试证据中恢复。由此提出 **PairCoder**——把注入的知识单元从"API 序列"升级为"带类型、有证据的成对 API 组合规则"。

---

## 2. 研究问题

**主研究问题（Main RQ）：**

> 对于未见代码库的 Python 代码生成，从**非测试证据**中恢复的 **typed, evidence-backed pairwise API composition rule**，相比 API-list、API-sequence（CAPIR 式）与 documentation-RAG 等 prompt，是否能更有效地降低 pairwise composition errors？

分解为四个子问题：

- **RQ0（问题存在性）**：当 LLM 已获得 API 名称、签名乃至 CAPIR 式 API sequence 时，是否仍会产生 pairwise composition errors？——用于确立 PairCoder 不是"又一个 API discovery 方法"，而是针对 discovery 之后**仍然残留**的组合错误。
- **RQ1（抽取可行性）**：仅使用非测试证据（README / docs / examples / docstrings / type hints / 轻量源码分析），能否抽取出高精度的 typed pair rules？——用于回答 1.2 节提出的"内部测试是否必要"。
- **RQ2（生成收益，主实验）**：与 API-list、Doc-RAG、CAPIR 式 API sequence 相比，注入抽取出的 pair rule 是否能提升生成正确性、降低 pair violation rate？
- **RQ3（机制解释）**：收益是否真正来自 typed 成对约束本身（relation / constraint / evidence / reason / usage pattern），而非"prompt 里多给了 API 名称或更多文本"？

RQ2 为体现创新的主实验，RQ0、RQ1、RQ3 为支撑。

---

## 3. 核心概念与严格定义

本节是全文论证的基础。PairCoder 的关键在于把若干此前被混用的概念严格区分开——尤其是 **API sequence** 与 **API pair**。

### 3.1 API discovery 与 API composition correctness 的区分

- **API discovery（API 发现）**：确定完成某任务**需要哪些** public API 的问题。其输出是一个 API 集合或序列。DomCoder 与 CAPIR 主要解决此问题。
- **API composition correctness（API 组合正确性）**：在 API 已被发现的前提下，判定生成代码是否**正确地连接**了这些 API 的问题——即返回值是否正确流转、receiver 是否一致、参数语义是否正确、生命周期顺序是否满足。本文研究此问题。

二者正交：discovery 正确（用对了 API、顺序也对）并不蕴含 composition 正确。

### 3.2 API sequence 与 API pair 的本质区别

这是 PairCoder 与 CAPIR 的概念分水岭：

> **API sequence**：API 名称按出现 / 调用顺序排列的序列，只表达"顺序"或"共现"——"A 和 B 经常一起出现"。它**不必然**表达 A 与 B 之间的依赖原因。
>
> **API pair（成对约束）**：两个 public API 之间的**有向组合单元**，要求 `API_B` 的正确使用**依赖于** `API_A` 产生或改变的**对象、值、状态、资源或协议条件**——"B 依赖于 A 所产生 / 修改的东西"。

也即：序列回答"先后 / 共现"，成对约束回答"依赖的因果与绑定"。一条 API sequence 可以完全正确，而对应的代码仍然违反成对约束（例如顺序对了，但 receiver 用错了实例）。

### 3.3 四类 typed pairwise composition constraint

本文主实验保留四类有类型的成对约束。每一类都精确对应一种真实的程序错误机制（继承 CAPIR 的实验场景，并要求实验库中存在符合该类型的真实 API 调用实例）：

| Pair type | 严格定义 | 所编码的依赖 | 主要预防的错误 |
|---|---|---|---|
| **return-flow（返回值流）** | `API_A` 的返回对象、句柄、迭代器或其派生对象，必须被 `API_B` 作为操作目标使用 | 数据 / 对象的来源依赖 | broken data flow（返回值未正确传递或绑定到 B） |
| **param-dependency（参数依赖）** | `API_A` 产生、解析或选择出的值，应作为 `API_B` 某个关键参数传入；该参数表面类型可能正确，但**语义来源、值域或身份**必须来自 A | 值的语义来源依赖 | wrong parameter semantics（参数类型对、但语义来源错） |
| **shared-receiver（共享接收者）** | `API_A` 与 `API_B` 必须作用在**同一个** receiver 或资源对象上（因为 A 改变了该对象的内部状态，B 依赖该状态） | 状态依赖 / 实例一致性 | receiver inconsistency（用了不同实例）/ missing call |
| **lifecycle-order（生命周期顺序）** | `API_A` 打开 / 注册 / 启用 / 启动某资源，`API_B` 关闭 / 注销 / 禁用 / 停止**同一**资源；二者必须按协议顺序成对出现 | 资源生命周期协议依赖 | wrong order / lifecycle leak（顺序违反或资源未释放） |

允许一条规则存在 secondary relation，但必须指定一个 **primary relation**，用于统计与错误归因。

### 3.4 Pair rule（成对规则）：可检索、可注入、可检查的最小推理单元

一条 **pair rule** 是把上述某类成对约束实例化为可被检索、注入 prompt 并据以检查的"推理单元"，至少包含：参与的两个 API、relation type、约束（constraint）、支撑证据（evidence）、因果解释（reason）与正确用法范式（usage pattern）。它以**自然语言推理单元**的形式呈现，而非长文档或完整源码——核心特征是**紧凑、有类型、有证据、可验证**。

> 概念性示例（自然语言描述，非实现）：
> 对于"配置后再执行"的客户端：`configure` 与 `execute` 构成 **shared-receiver** 约束——`execute` 必须在**调用过 `configure` 的同一个 client 实例**上执行，因为 `configure` 改变了该 client 的内部配置状态，而该状态被 `execute` 消费。

### 3.5 其他关键术语

| 概念 | 定义 |
|---|---|
| **Public API** | 目标库**公开承诺**给外部用户调用的函数、类、方法、构造器或 re-export 符号（依据 `__all__`、`__init__` re-export、非下划线开头的模块级符号、以及文档 / 示例中出现的 API 判定）。 |
| **Pairwise composition constraint** | 约束两个 API 如何正确连接的**最小规则**，包含 relation type、调用顺序、对象 / 参数绑定、状态条件与证据。 |
| **API Pair Graph** | 以 public API 为节点、以 typed pairwise composition constraint 为边的**轻量图**；它不是完整的 code graph，只刻画成对组合约束。 |
| **Non-test evidence（非测试证据）** | 不来自内部测试的证据：官方文档、README、docstring、示例、tutorial、类型签名、public 源码、轻量静态分析结果。 |
| **High-quality internal tests** | 由库维护者编写、覆盖真实 API 使用场景、可执行且能揭示正确行为的测试。本文不否认其有用，仅检验其是否为**必要条件**。 |
| **Minimal API composition knowledge** | 支撑两个 API 正确组合所需的**最小可验证知识**，不要求恢复完整 workflow、完整 code graph 或完整业务语义。 |
| **Pairwise composition error** | 生成代码违反 API pair constraint 的错误——即便其中单个 API 的名称与签名都正确。 |
| **Gold pair rule** | 人工标注并经审查的 pair rule，用作抽取上限（oracle）与 pair knowledge 有效性的验证基准。 |
| **Extracted pair rule** | PairCoder 从非测试证据中自动抽取出的 pair rule。 |
| **Unseen codebase** | 模型预训练阶段大概率未充分见过、或目标 API 在训练数据中稀疏的新库、私有库或低流行度库。 |

---

## 4. 问题存在性证据（RQ0 实证）

为确立"API sequence 之后仍残留 pairwise composition error"这一前提，我已在 `simplug` 库上完成一轮跨模型问题存在性实验。

### 4.1 设置

- **模型**：5 个跨 4 家厂商的 7–9B 开源模型——`qwen2.5:7b`（阿里，通用）、`qwen2.5-coder:7b`（阿里，代码专精）、`llama3.1:8b`（Meta）、`gemma2:9b`（Google）、`mistral:7b`（Mistral）。其中前两者构成"通用 vs 代码"同家族同尺寸受控对照。
- **任务**：6 个 pair-critical tasks，覆盖 `plugins_context → hooks.score`（参数语义）、`disable → hooks.score`（共享 receiver / 状态依赖）、`get_plugin → wrapper.disable → hooks.score`（返回值流向）。
- **知识注入条件（从弱到强）**：仅任务 → API 清单 → 文档片段 → **oracle API 调用顺序（CAPIR 式上界）** → gold pair rule。
- **稳健性**：每个条件独立运行 3 轮，按任务级多数投票汇总；评测采用基于 AST 的 pair violation checker。

### 4.2 核心发现

1. **问题跨厂商普遍存在**：在不提供任何 API 知识时，5 个模型的违规率**全部为 100%**，排除了"只是某一家模型的毛病"。
2. **API 序列不足以消除组合错误（RQ0 成立）**：即便提供 **oracle API 调用顺序**（已排除 API discovery / sequence 推荐错误），违规率仍高达 50%–100%——证明残留错误来自 API 之间的组合语义，而非"用哪些 API、什么顺序"。
3. **更强的代码模型在问题区反而更差**：`qwen2.5-coder:7b` 在所有"无 pair rule"条件下违规率**稳定为 100%**，而在 gold pair rule 下**稳定为 0%**，形成"悬崖式"对比——说明瓶颈在于**缺失配对知识**，而非模型能力。
4. **知识注入并非单调有效**：更强的 API 知识不保证更低违规率（部分模型给"oracle 顺序"反而不如给文档），佐证"堆叠 API 知识"路径的不可靠。
5. **gold pair rule 是有效的约束载体**：显式注入成对约束后多数模型违规率降至 0%–17%。

> 该结果支撑核心论断：**pair violation 不是由"模型太弱"或"API 序列推荐错误"造成的，而是一个独立于 API discovery、跨模型普遍存在、且尚未被现有知识注入方式解决的问题。**

### 4.3 与方法实验的衔接

存在性实验中的 `oracle API sequence` 条件对应"最强的 CAPIR 式 baseline"（它甚至比真实 CAPIR 检索出的序列更强，因为排除了检索错误）；`gold pair rule` 条件对应 PairCoder 注入知识单元的**上界**。二者之间的显著差距，正是 PairCoder 方法（用**自动抽取**的 pair rule 去逼近 gold 上界）的价值空间。

---

## 5. PairCoder 方法（概念性，不含实现细节）

PairCoder 在 CAPIR 式 library-oriented 框架内，把注入的知识单元从 API sequence 替换为 typed pair rule。方法由五个概念阶段构成：

```text
CAPIR:     task → 任务分解 → API 检索 → API 重排序 → API sequence prompt
PairCoder: task → 识别成对约束需求 → pair rule 检索/重排序 → typed pair reasoning units prompt
```

1. **Public API Identification（公开 API 识别）**：从目标库中识别可被外部用户调用的 public API，作为 pair graph 的节点来源。
2. **Non-test Evidence Collection（非测试证据收集）**：仅从文档、README、docstring、示例、类型签名、public 源码与轻量静态分析中收集证据；**严格排除测试目录、benchmark 测试、hidden tests 与评测 oracle**——这是 PairCoder "test-free" 主张的方法保证。
3. **API Pair Graph Construction（成对图构建）**：在 public API 之间建立四类 typed pairwise composition edge（见 3.3），每条边都需有非测试证据支撑。它是轻量的成对约束图，而非完整 code graph。
4. **Pairwise Reasoning Unit Generation（成对推理单元生成）**：把每条边转换为紧凑、可检索、可注入、可检查的自然语言 pair rule（含 relation / constraint / evidence / reason / usage pattern）。
5. **Pair-grounded Code Generation（基于成对约束的代码生成）**：依据用户任务检索 top-k 相关 pair rule，**只注入这些紧凑约束单元**（而非长文档或完整源码），引导 LLM 生成满足 return-flow / param-dependency / shared-receiver / lifecycle-order 约束的代码。

> 与已有注入范式的对比：RAG 注入文档片段；DomCoder 注入 API 序列；UCD-Training 在 code-graph 合成数据上训练；**PairCoder 注入 API 组合约束**。

---

## 6. 实验设计（概念性）

### 6.1 数据集：CAPIR-derived PairCoder Benchmark

复用 CAPIR 式 library-oriented 任务场景，但在其上**补充**三类 PairCoder 专属标注：required pair constraints、pair-specific oracle、pair-specific hidden tests / pair violation labels。候选库优先选择中小规模、文档清楚、天然存在成对约束的 Python 库（如 `watchdog`、`schedule`、`simplug`、`pluggy`、`dependency-injector`）。

- **Pilot**：1 个库、8–12 个 pair-critical tasks、12–20 条 gold pair rules；
- **Main**：3 个库、20–40 个 pair-critical tasks、50–75 条 gold pair rules。

**Pair-critical task 判定**：当且仅当（1）正确代码必须满足至少一条 pair constraint；（2）仅给 API 名称 / 签名不足以保证正确生成；（3）违反该约束会导致 hidden test 失败或被 pair oracle 判为语义错误。

**测试隔离原则**：内部测试**只能**用于 gold 标注审查、hidden evaluation 与结果验证，**绝不进入** PairCoder 的抽取流程——以此干净地检验 RQ1。

### 6.2 Gold Pair 标注

人工标注覆盖四类关系的 gold pair rules，每条至少含 API_A、API_B、relation_type、constraint、evidence、usage_pattern；需双人标注或二次审查，并报告标注者一致性（inter-annotator agreement）。

### 6.3 对比方法

| 方法 | 注入内容 | 目的 |
|---|---|---|
| Base LLM | 仅任务描述 | 下界 |
| API-list | 相关 API 名称与签名 | API discovery baseline |
| Doc-RAG | 相关文档 / docstring / 源码片段 | 文档检索 baseline |
| CAPIR-style API sequence | API 序列 + API 描述 | 直接继承 CAPIR 的 baseline |
| Gold Pair Rule | 人工标注 pair rule | pair knowledge 上界（oracle） |
| Extracted Pair Rule | PairCoder 自动抽取 pair rule | **PairCoder 主方法** |

为保证公平：同一模型、相近 token budget、一致的温度与采样次数、完整保存 prompt 与 response。

### 6.4 指标体系

- **生成指标**：pass@1、pass@k、hidden-test pass rate、runtime error rate、static validity；
- **Pair 指标**：pair recall@k、pair precision@k、edge type accuracy、pair violation rate、semantic oracle score。

### 6.5 错误归因（pair-specific）

不只看最终 pass rate，更要看每类成对错误的下降——把违规精确归因到 missing API call、wrong order、broken data flow、receiver inconsistency、wrong parameter semantics、lifecycle leak 等类型，并与四类 pair type 一一对应。

### 6.6 结果解释逻辑

1. Gold Pair 明显优于 CAPIR-style sequence → 成对组合知识本身有价值；
2. Extracted Pair 接近 Gold Pair → 非测试证据能恢复有用的最小组合知识（回答 RQ1）；
3. Extracted Pair 弱于 Gold、但优于 API-list / Doc-RAG / sequence → 方法有效、但抽取质量是瓶颈；
4. sequence 与 Extracted Pair 差距明显 → "因果约束"比"调用顺序"更重要；
5. 不同 pair type 对应不同错误类型的下降 → typed edge 不是 prompt 装饰，而对应真实错误机制（回答 RQ3）。

---

## 7. 创新点

- **问题重构创新**：把研究对象从"如何让 LLM 知道更多 API"推进到"当 LLM 已知道 API 后，为什么仍组合错、以及恢复组合知识是否必须依赖内部测试"——从 API discovery 推进到 API composition semantics。
- **知识单元创新**：把 UCD 的 compositional API reasoning **收缩为最小可验证单元**——typed, evidence-backed pairwise API composition rule。它既不是普通 API 共现，也不是单纯 API 序列。
- **注入方式创新**：不向 prompt 塞长文档或完整源码，而是注入紧凑的成对推理单元。
- **数据假设创新**：主张并检验"高质量内部测试并非恢复最小组合知识的必要条件"，使方法可迁移到缺测试的私有库 / 低流行度库。

---

## 8. 论文贡献

1. **概念贡献**：将 pairwise API composition constraint 识别为未见代码库生成的**最小知识单元**，在 API usage mining 与 LLM API 知识注入之间搭桥。
2. **方法贡献**：提出 PairCoder——一个**轻量、test-free** 的框架，从非测试证据构建 API Pair Graph，并将 typed pair edge 转为可注入 prompt 的推理单元。
3. **生成贡献**：提出 pair-grounded code generation，通过检索并注入相关成对推理单元，引导 LLM 满足数据流、receiver 一致性、参数依赖与生命周期顺序约束。
4. **实证贡献**：系统比较 extracted pair rule 与 API list / API sequence / Doc-RAG / gold pair rule，回答"非测试证据能否恢复一个有用的高精度最小组合知识子集"。

---

## 9. 与已有研究的继承关系

- **承自 PR-Miner（仅思想源头）**：PR-Miner 说明"API 使用中的隐式成对规则是一种有意义的程序知识，可解释许多'单个 API 正确但整体程序错误'的现象"。PairCoder 继承这一思想，但**不沿用**其面向既有代码缺陷检测的实验设置——PairCoder 不以检测已有 violation 为目标，而是从非测试证据中**恢复**高精度成对约束用于**生成**。
- **承自 CAPIR（实验框架）**：PairCoder 继承 CAPIR 的 library-oriented code generation 场景与任务 / 评估框架，并把 CAPIR 的 API-sequence benchmark 扩展为 **CAPIR-derived PairCoder Benchmark**（补充 pair-level 标注、pair-specific hidden tests 与 pair violation evaluation）。
- **核心推进**：把 API 知识注入从"推荐 API"推进到"注入 API 组合约束"——研究当 LLM 已获得相关 API 后，如何进一步减少其间的组合错误。

核心假设：

- **H1**：CAPIR 式 API sequence 改善 API discovery，但不能完全解决 API composition correctness；
- **H2**：typed API pair rule 提供显式约束，能降低 pair-specific 生成错误；
- **H3**：非测试证据能恢复一个高精度、有用的 API pair rule 子集。

---

## 10. 预期结果与解释

| 结果模式 | 解释 |
|---|---|
| Gold 明显优于 sequence，Extracted 接近 Gold | pair knowledge 有价值，且非测试证据能恢复有效子集（最强结论） |
| Gold 明显优于 sequence，Extracted 优于 sequence 但弱于 Gold | 研究问题成立，自动抽取质量为瓶颈 |
| Extracted 与 sequence 接近 | 需检查任务是否真 pair-critical、pair rule 是否退化为 sequence、hidden tests 是否够敏感 |
| Extracted 弱于 sequence | 错误 pair rule 会误导生成，需加强 evidence verifier 与高精度过滤 |

最小可行版本的成功判据：在 pilot 上出现 `Gold > sequence`、`Extracted ≥ sequence`、且 `Extracted 的 pair violation rate < sequence`，即可扩展到 3 个库。

---

## 11. 当前局限与下一步

**局限**：

1. 现阶段为 small-scale existence experiment，任务规模有限；
2. gold pair rule 是 oracle 上界，不代表自动检索模块的最终效果；
3. doc 片段为手工整理，非完整 RAG pipeline；
4. 尚未加入完整 CAPIR 复现或 retriever / reranker baseline；
5. 评测以静态语义检查为主，运行时验证尚待补充；
6. 模型集中于本地可运行的 7–9B 开源模型，未覆盖闭源最强模型。

**下一步**：

1. 保留五模型 × 方法 × 多轮存在性矩阵作为问题存在性主证据；
2. 在第二个低资源库上复制同一矩阵，避免单库特例；
3. 将 gold pair rule 替换为自动抽取的 extracted pair rule，形成完整方法对比（RQ2 主实验）；
4. 补充 pair rule 表达消融与证据源消融，验证机制来源（RQ3）；
5. 深入分析"即便给定显式规则仍无法遵循"的模型（如存在性实验中的 mistral 异常），作为"模型对显式约束遵循能力差异"的 case study；
6. 视资源补充一个云端闭源强模型，验证 updated-LLM setting 下结论的稳健性。
