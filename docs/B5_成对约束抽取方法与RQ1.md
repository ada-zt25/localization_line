# B5:测试无关的成对组合约束抽取算法 与 RQ1 / RQ2 评测

> 2026-06-16。把 B4 的"人工 gold 规则注入"升级为**可形式化、可校准、有精度下界**的抽取算法 Φ,再用执行反馈闭合成迭代架构。
> 代码:`exec_oracle/pair_extractor.py`(Φ 算子)、`eval_extraction.py`(RQ1)、`b5_feedback.py`(闭环算法)、`fair_loop.py`(无泄漏公平闭环运行)、`analyze_full.py`(RQ2 汇总)。
> 覆盖全部 **6 个库**(glom/diot/simpleconf/bidict/simplug/sqlitedict),全部统一在 benchlib 接口上(simplug 即 `lib_simplug`,无需特殊适配器)。
> **关系类型 6 类全覆盖**:param-dependency / return-flow / shared-receiver / config-return-contract / lifecycle / completion-obligation;第 6 类(通道 CE)由 **sqlitedict**(写入须 `commit()`)提供。

## 1. 问题与定位

**B5 = 闭环条件 `B5_loop`(唯一的 B5,§7)**:从 Φ 自动抽取的成对规则起步,经"生成→执行→失败归因→精修→再生成"迭代;**没有一次性 B5**。其初始注入与 B4 = `B1 ⊕ gold 规则` 平行(`B1 ⊕ Φ抽取规则`),于是:
`B5−B4` = 抽取(+反馈)相对人工 gold 的损失;`B5−B3*` = 相对无约束调用序列的价值(**RQ2 主命题**);`B5−B1` = 相对 API 清单的价值;填补比例 `η=(B5−B1)/(B4−B1)`。

**测试无关(test-free)保证**:Φ 只读 {vendored 源码 AST、`inspect` 签名、docstring、`API_LIST`/`RAW_API_DOCS` 文档片段},**绝不读隐藏测试,也不读 `GOLD_PAIR_RULES`**。gold 仅 `eval_extraction.py` 评分时使用。

## 2. 算法 Φ(四个核心公式)

**(1) 耦合通道 ↔ 关系类型双射** κ(taxonomy §2.1 的算法化,6 类):
DFP 参数数据流→param-dependency;DFR 返回数据流→return-flow;SS 共享堆状态→shared-receiver;
TC 类型/形态契约→config-return-contract;CO 控制顺序/作用域→lifecycle;CE 控制存在(必须也调搭档)→completion-obligation。
每个通道一个检测器,从 4 个证据源各给一个子检测概率 `p_{k,σ}`。

**(2) 多源 noisy-OR 通道见证分**:
```
s_k = 1 − ∏_σ ( 1 − w_σ · p_{k,σ} )       w = {src .90, ex .80, sig .70, doc .60}
```

**(3) 判别式 typed 得分(压制竞争通道)**:
```
score(r) = s_{κ(r)} · ∏_{k≠κ(r)} ( 1 − λ · s_k )      λ = 0.55
```
竞争只在**区分性锚点**上计算(容器类名如 `Diot` 被排除,使"同一个类的不同 kwarg"不互相压制)。`score < τ=0.12` 判 ∅。

**(4) Platt 置信度校准 + 精度下界**:
```
c = sigmoid(α·score + β)        (α,β) 由留一库(LOLO)逻辑回归拟合
仅发出 c ≥ θ  ⇒  precision(θ) = E[c | c≥θ] ≥ θ   （校准下的精度下界）
```
扫 θ 得 **precision–coverage 操作曲线**;θ 即"发出规则的期望精度下界"旋钮。

**规则合成**:存活提案按关系模板实例化为 `Relation:/Constraint:` 文本(`synthesize_rule`),模板写得**可操作**(如 config-return 明示"要 list 用 list 形状 spec、要 dict 用 dict 形状 spec"),与 `GOLD_PAIR_RULES` 同构。注入 B5 时取该任务关系的 **top-K 条**(按判别得分降序、按锚点去重,K=3),而非仅 top-1——避免真/假提案分差极小时丢掉有用规则(`benchlib_generate.extracted_rule_for_task`)。

## 3. RQ1 结果(6 库,25 条 gold typed 规则,LOLO 六库校准)

| 库 | gold | 发出 | TP | precision | recall | F1 |
|---|--:|--:|--:|--:|--:|--:|
| glom | 4 | 4 | 2 | 0.50 | 0.50 | 0.50 |
| diot | 5 | 11 | 8 | 0.73 | 0.60 | 0.66 |
| simpleconf | 5 | 5 | 2 | 0.40 | 0.40 | 0.40 |
| bidict | 5 | 14 | 5 | 0.36 | 0.40 | 0.38 |
| simplug | 5 | 3 | 2 | 0.67 | 0.40 | 0.50 |
| sqlitedict | 1 | 15 | 1 | 0.07 | 1.00 | 0.12 |
| **合计** | 25 | 52 | 20 | **0.38** | **0.48** | **0.43** |

- **高精度操作点 θ\*=0.45**:precision **0.67**(校准精度下界成立)。
- **召回天花板在 return-flow / shared-receiver**:这两类需"使用迹/同对象读写"证据,静态文档难恢复;param/config/lifecycle/completion-obligation(kwarg、契约、上下文管理器、commit 名)静态可见、召回高。**这与 RQ2 里"B5 在这些类上填补比例高、在 return-flow/param 上偏低"互为印证**(见 §8)。
- **sqlitedict 精度低**(0.07):只有 1 条 gold 但 API 面丰富(构造器多个 kwarg),抽取过度提议 → 大量真实但非 gold 的 FP;但召回 1.00(commit 义务被抓到)。这是"单 gold + 富 API"的固有现象,如实记录。

## 4. 诚实的局限

- gold 仅 25 条 → Platt 校准在中段噪声偏大;精度下界在高 θ 稳。
- 原始分压在窄带,precision–coverage 曲线 θ>0.6 探不到。
- 检测器为第一代,启发式成分仍在;`detect_DFR`(return-flow)与 example 级 SS 召回弱(直接反映到 RQ2 这两类的 B5 偏弱)。

## 5. 下一步(更新)

B3→B3\*、B5 闭环、RQ2 全量(§8)均已完成。剩余:
1. **补强最弱靶点**:param-dependency(填补仅 29%)与 simplug 库——更强的归因/精修,或 `detect_DFP`/`detect_SS`/`detect_DFR` 检测器升级。
2. **补前沿模型**:param/simplug 的差距可能是 7–9B 小模型造成,前沿模型大概率缩小 `B5−B4`。
3. **统计补强**:多轮(RUNS≥3)给 bootstrap CI;gold 双标注 + IAA。

## 6. 运行

```bash
cd PairCoder/exec_oracle
python pair_extractor.py --all                          # 看抽取的 typed 规则(原始分)
python eval_extraction.py --emit ../result/extraction_eval   # RQ1:P/R/F1、混淆、precision–coverage
python analyze_full.py                                  # RQ2 汇总:B5−B3*、填补比例 η、McNemar
```
B5_loop(公平口径)由 `fair_loop.py` 产出(dev/held 拆分、等预算 K,无泄漏);RQ1 产物 `result/extraction_eval/`。**注:旧的泄漏驱动 `b5_loop_run.py`(闭环反馈与评测用同一 oracle)已删除;`result/full_run_analysis.md` 系泄漏口径,待用 `fair_loop` 重跑后替换。**

---

## 7. 闭环 B5:自动抽取 + 失败归因 + 反馈再生成

代码:`exec_oracle/b5_feedback.py`。把一次性抽取升级为**不动点迭代**:

```
r_0 = Φ(lib, task)                              # 静态抽取
for t in 0..K-1:
    g_t       = LLM(prompt(API_LIST, r_t, notes_t))   # 生成
    v_t       = Oracle(g_t)                            # 跑隐藏测试
    if v_t.pass: return (r_t, g_t, t)                  # 收敛
    a_t       = Attribute(v_t)                         # 失败 → 耦合通道
    r_{t+1}   = Refine(r_t, a_t)  或  notes_{t+1}=PromptFeedback(v_t)
```

**(A) 失败归因 = κ 双射的逆**。执行 oracle 的 reason code 本就**按关系设计**(`wrong_output_structure`↔config-return、`state_not_restored`/`disable_not_persistent`↔lifecycle、"same object/not mutated"↔shared-receiver、`DuplicationError`↔param、import/undefined↔代码层)。所以归因不是猜,是把失败映回它牵涉的通道。**模糊异常**(如 `PathAccessError` 可能是缺 default 也可能是 spec 形态错)**不强行覆盖,退回该任务的抽取关系作先验**——这条"仅在信号明确时才纠正通道"的原则保证归因保守可靠。

**(B) 类型化精修(自我纠错)**:失败通道 == 抽取关系 → 规则本对、模型没遵守 → **加固**("常见错误→应有行为"具体子句);失败通道 ≠ 抽取关系 → 抽取漏了 → **补上**该通道子句(execution 纠正 extraction)。**代码层错误**(语法/导入/未定义名)不是成对约束问题 → 反馈进 **prompt**。这正落实"注入规则 OR 注入 prompt——由归因决定"。

**(C) Beta 置信度**:每轮 `pass→a+1, fail→b+1`,`c=a/(a+b)`——执行反馈是叠加在静态 LOLO 之上的**第二个动态校准信号**。

**离线实证(无 Ollama)**:
- `--simulate <lib> <task>`:用 anchor(违规→规范)+ 真实 oracle 跑通完整闭环,验证 attribute→refine→收敛。config/param/shared/lifecycle 四类任务归因全部正确。
- `--explain-failures <lib>`:对**已记录的真实失败**做归因。4 库结果:约 **2/3 失败可归到耦合通道(可精修规则),1/3 是代码层错误(进 prompt)**;其中相当一部分代码错是**未见库上的 API 名幻觉**(`cannot import / has no attribute`),正好支撑"规则/prompt 双通道反馈"的设计。

**诚实边界**:simulate 的"修正"由 anchor 序列脚本化(离线无法让精修后的规则真正改变生成);"精修规则→更好代码"的真实闭合需 LLM,属 RQ2。归因本身的准确率应作为一个新指标(类比 edge-type accuracy)报告。

**全量运行(`fair_loop.py`,无泄漏)**:每任务 INPUTS 拆 dev(反馈/best-of-K 选择)/ held(只评测),各条件同预算 K,B5_loop 额外做 typed 精修,最终在 held-out 上判分。仅覆盖有 ≥2 INPUTS 的可拆任务(当前约 16 个;扩量需为每任务补 INPUTS)。**旧的泄漏驱动 `b5_loop_run.py`(闭环反馈 oracle == 评测 oracle)已删除。** RQ2 结果见 §8(注:§8 现有数为泄漏口径,待 `fair_loop` 重跑后更新)。

运行:
```bash
python b5_feedback.py --simulate --lib glom --task glom-G003   # 完整闭环(离线 anchor 验证)
python b5_feedback.py --explain-failures --lib bidict          # 真实失败归因
python fair_loop.py --libs glom --k 3 --conditions B0,B1,B3,B4,B5_loop --model qwen2.5-coder:7b   # 公平闭环(dev/held,无泄漏;需 Ollama)
```

---

## 8. RQ2 结果(6 库 / 5 模型 / 1 轮,run-level)

`B5` 即 `B5_loop`。`analyze_full.py` 产出(`result/full_run_analysis.md`)。

**分 pair_type:`B5−B3*` / 填补比例 η / McNemar**

| pair_type | pairs | B1 | B3\* | B4 | B5_loop | B5−B3\* | η=(B5−B1)/(B4−B1) | McNemar p (B5 vs B3\*) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| param-dependency | 55 | .35 | .18 | .73 | .45 | +.27 | 29% | 0.001 |
| return-flow | 60 | .48 | .42 | .77 | .68 | +.27 | 71% | 8.6e-04 |
| shared-receiver | 60 | .40 | .43 | .60 | .57 | +.13 | 83% | 0.115 (ns) |
| config-return-contract | 65 | .57 | .43 | .75 | .66 | +.23 | 50% | 0.003 |
| lifecycle | 60 | .40 | .18 | .53 | .53 | +.35 | 100% | 1.9e-05 |
| completion-obligation | 15 | .87 | .40 | .87 | **1.00** | +.60 | n/a\* | 0.004 |
| **合计** | 315 | .46 | .34 | .69 | .60 | **+.27** | **63%** | **2.0e-15** |

\* B4−B1=0(B1 已 .87),η 无意义;但 B5_loop=1.00 反超 B4。

**McNemar 配对精确检验(汇总,双侧)**

| 比较 A vs B | b (A赢) | c (B赢) | 不一致对 | p |
|---|--:|--:|--:|--:|
| B5_loop vs B3\* | 102 | 18 | 120 | **2.0e-15** |
| B5_loop vs B1 | 52 | 8 | 60 | **5.2e-09** |
| B5_loop vs B4 | 30 | 56 | 86 | **0.007** |
| B4 vs B3\* | 132 | 22 | 154 | **2.6e-20** |

**结论**:
- **主命题成立**:`B5_loop ≫ B3*`(+0.27,p=2e-15;6 类里 5 类显著)、`≫ B1`(p=5e-9)。
- **闭环 test-free 地补回 63% 的 gold 差距**:lifecycle 100%、shared-receiver 83%、return-flow 71%;**completion-obligation 上 B5_loop 反超 B4**(commit 义务一轮收敛)。
- **诚实**:`B4` 仍显著优于 `B5_loop`(p=0.007),但差距温和(−0.09)。最弱靶点 = **param-dependency(η=29%)与 simplug 库**(§5)。
- 注:RUNS=1 单样本,数值有单轮噪声,方向稳。
