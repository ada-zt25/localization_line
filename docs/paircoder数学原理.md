# PairCoder 数学原理

> 本文给出 PairCoder 基准与**完整 B5 方法**(自动抽取 + 失败归因 + 反馈再生成)的数学形式化:统一记号、定义、命题与定理(含证明)。公式与实现一一对应:抽取器 `exec_oracle/pair_extractor.py`、RQ1 评测 `exec_oracle/eval_extraction.py`、闭环 `exec_oracle/b5_feedback.py`、公平闭环运行 `exec_oracle/fair_loop.py`、汇总分析 `exec_oracle/analyze_full.py`。
> 最后更新 2026-06-16。数学渲染用 `$…$` / `$$…$$`(GitHub/VS Code 可渲染)。
> **B5 = 唯一的闭环条件**(`B5_loop`,§3):不再有"一次性 B5";`B5_loop` 从 $\Phi$ 抽取规则起,经"生成→执行→归因→精修"迭代。基准为 **6 库 / 6 类全覆盖**(completion-obligation 由 sqlitedict 提供)。

---

## 0. 记号总表

| 符号 | 含义 |
|---|---|
| $L$ | 一个目标库;$\mathcal A_L$ 其暴露的 API 面(可调用/属性/关键字参数 token) |
| $\mathcal R$ | 关系类型空间,$\lvert\mathcal R\rvert=6$(见 §1.2);$\varnothing$ 表"无约束" |
| $\mathcal K$ | 耦合通道空间,$\mathcal K=\{\mathrm{DFP,DFR,SS,TC,CO,CE}\}$ |
| $\kappa:\mathcal R\to\mathcal K$ | 关系↔通道**双射**(§1.3) |
| $\Sigma$ | 证据源 $\{\mathrm{src,sig,doc,ex}\}$,权重 $w_\sigma\in[0,1]$ |
| $t=(p_t,f_t,C_t,\mathcal I_t,\mathcal O_t)$ | 任务:NL 描述、待实现函数、考核约束 $C_t\in\mathcal R$、隐藏输入、可观察判据 |
| $\mathcal M$ | 被测语言模型,$g\sim\mathcal M(\cdot\mid\pi)$ 表在 prompt $\pi$ 下采样生成 $g$ |
| $\mathrm{Ora}$ | 执行 oracle,$\mathrm{Ora}(g,t)=(y,\rho,\delta)$:$y\in\{0,1\}$ 通过位、$\rho$ 原因码、$\delta$ 细节串 |
| $\Phi$ | 抽取算子(§2);$\mathcal A,\mathcal R$ 上的精修算子 $\mathcal R\!\mathrm{ef}$、归因算子 $\mathcal A\!\mathrm{ttr}$(§4) |

超参(实现默认值):$w=\{\mathrm{src}{:}0.9,\ \mathrm{ex}{:}0.8,\ \mathrm{sig}{:}0.7,\ \mathrm{doc}{:}0.6\}$,抑制 $\lambda=0.55$,检出阈 $\tau=0.12$。

---

## 1. 任务、条件与目标度量

### 1.1 任务与判分

任务 $t$ 的判分**只消费可观察量**(返回值/运行迹/终态),不读生成源码 $g$:
$$
\mathrm{pass}(g,t)\;=\;\bigwedge_{x\in\mathcal I_t}\mathrm{check}_t\big(\mathrm{run}(g,x)\big)\in\{0,1\}.
$$
$\mathrm{check}_t$ 即 `lib_<L>.CHECKS`;$\mathrm{Ora}$ 在锚定套件上经构造性验证(正确解必过、各类违规以预期 $\rho$ 必挂),消除"循环 oracle"。

### 1.2 关系类型空间(6 类)

$$
\mathcal R=\{\text{param-dependency},\ \text{return-flow},\ \text{shared-receiver},\ \text{config-return-contract},\ \text{lifecycle},\ \text{completion-obligation}\}.
$$
完整 6 类(由 §5 的耦合通道穷举推得)。第 6 类 completion-obligation(通道 CE,资源 acquire/release / "必须也调搭档")由 **sqlitedict**(写入须 `commit()` 才持久)提供,数据/配置/提取库本身不含此类,故专门引入资源型库补足。

### 1.3 提示条件与单调信息序

每个条件是一个**注入映射** $B_i:t\mapsto \pi_i(t)$,把不同信息量注入 prompt:

| 条件 | 注入 payload $\;\mathrm{pl}_i(t)$ |
|---|---|
| $B_0$ | $\varnothing$(裸任务) |
| $B_1$ | $\mathrm{API\_LIST}(L)$ |
| $B_2$ | $\mathrm{RAW\_API\_DOCS}(L)$ |
| $B_3^\ast$ | 无约束抽象调用序列 $\mathrm{seq}^\ast(t)$ |
| $B_4$ | $\mathrm{API\_LIST}(L)\ \oplus\ g^\star_{\kappa^{-1}(C_t)}$(API 清单 ⊕ 该任务关系的 **gold** 规则) |
| $B_5$(=$B_5^{\text{loop}}$) | **闭环**(§3):初始注入 $\mathrm{API\_LIST}(L)\ \oplus\ \hat g_{C_t}$,再经"执行→归因→精修"迭代。无一次性 B5。 |

其中 $B_0\!-\!B_4$ 为一次性条件,$B_5$ 是 §3 的不动点迭代。**抽取规则 $\hat g_{C_t}$ 取该任务关系 $C_t$ 的 top-$K$ 条提案**(按判别得分降序、按锚点去重,$K{=}3$),而非仅 top-1——避免真/假提案分差极小时丢掉有用规则;若该关系无提案则 $\hat g_{C_t}=\varnothing$,$B_5$ 退化为 $B_1$。

记条件 $B$ 的任务级通过率(跨模型/多轮多数票)为
$$
\mathrm{Pass}(B)=\mathbb E_{t,\mathcal M}\big[\,\mathbf 1\{\text{多数票}_r\,\mathrm{pass}(g^{(r)}_{B,t},t)\}\,\big].
$$

### 1.4 核心边际度量(干净消融)

因 $B_4,B_5$ 均为 $B_1$ 的**真超集**($\mathrm{pl}\supseteq\mathrm{API\_LIST}$),差分隔离"成对约束"的边际价值:
$$
\boxed{\;\Delta_{4|1}=\mathrm{Pass}(B_4)-\mathrm{Pass}(B_1)\;},\qquad
\Delta_{4|3^\ast}=\mathrm{Pass}(B_4)-\mathrm{Pass}(B_3^\ast),
$$
$$
\Delta_{5|3^\ast}=\mathrm{Pass}(B_5^{\text{loop}})-\mathrm{Pass}(B_3^\ast)\quad(\textbf{RQ2 主命题}),\qquad
\Delta_{5|4}=\mathrm{Pass}(B_5^{\text{loop}})-\mathrm{Pass}(B_4)\ (\text{抽取损失}).
$$
另定义 **gold 差距填补比例** $\;\eta=\dfrac{\mathrm{Pass}(B_5^{\text{loop}})-\mathrm{Pass}(B_1)}{\mathrm{Pass}(B_4)-\mathrm{Pass}(B_1)}\in[0,1]$(当 $\mathrm{Pass}(B_4)>\mathrm{Pass}(B_1)$)。
**目标命题**:$\Delta_{5|3^\ast}>0$ 显著,且 $\Delta_{5|4}\lesssim 0$ 但 $\eta$ 高(闭环 test-free 地补回大部分 gold 差距)。**实测**(6 库/5 模型,§7):$\Delta_{5|3^\ast}=+0.27$(McNemar $p{=}2.0\!\times\!10^{-15}$)、$\eta=63\%$、$\Delta_{5|4}=-0.09$($p{=}0.007$)。

---

## 2. 抽取算子 $\Phi$

$\Phi$ 把库 $L$ 的可读证据(源码 AST、签名、docstring、文档片段;**不含隐藏测试、不含 gold**)映为一组带置信度的 typed 规则。

### 2.1 候选提案

**定义 1(提案).** 一个提案 $P=(r_P,\ A_P,\ \{p_{k,\sigma}(P)\})$,其中 $r_P\in\mathcal R$,锚点集 $A_P\subseteq\mathcal A_L$,每个证据源 $\sigma\in\Sigma$ 对其定义通道 $k=\kappa(r_P)$ 给出子检测概率 $p_{k,\sigma}(P)\in[0,1]$。检测器集 $\{\mathrm{DFP,\dots,CO}\}$ 各产生若干提案。

### 2.2 多源 noisy-OR 通道见证分

**定义 2(通道见证).** 设各源对通道 $k$ 是否激活的判定相互独立、第 $\sigma$ 源以概率 $w_\sigma p_{k,\sigma}$ 给出正判定,则"至少一源见证"的概率
$$
\boxed{\;s_k(P)\;=\;1-\prod_{\sigma\in\Sigma}\big(1-w_\sigma\,p_{k,\sigma}(P)\big)\;}\in[0,1].
$$
**性质**:$s_k$ 对每个 $p_{k,\sigma}$ 单调不减;任一强源($w_\sigma p_{k,\sigma}\to1$)即令 $s_k\to1$。

### 2.3 判别式 typed 得分

令容器 token 集 $\mathcal C_L$(类名)。**区分性锚点** $\hat A_P=A_P\setminus\mathcal C_L$(剔除类名,避免"同类不同 kwarg"被误判为竞争)。

**定义 3(判别得分).**
$$
\boxed{\;\mathrm{score}(P)\;=\;s_{\kappa(r_P)}(P)\;\cdot\!\!\prod_{\substack{Q:\ \kappa(r_Q)\neq\kappa(r_P)\\ \hat A_P\cap\hat A_Q\neq\varnothing}}\!\!\big(1-\lambda\,s_{\kappa(r_Q)}(Q)\big)\;}
$$
**解释(因子化近似).** 设 $E_k$ 为"通道 $k$ 为该锚点对真实媒介"的事件。$\mathrm{score}(P)$ 近似
$$
\Pr\!\big[E_{\kappa(r_P)}\big]\cdot\!\!\prod_{k\neq\kappa(r_P)}\!\!\Pr\!\big[\neg E_k\big]\;\approx\;\Pr\!\big[r_P\text{ 是该对的唯一关系}\big],
$$
即"我这一通道发火 **且** 竞争通道都不发火"。$\lambda$ 调节竞争抑制强度;多通道歧义对被压低 → 低分 → 滤除。

**定义 4(检出决策).** 保留 $P$ 当且仅当 $\mathrm{score}(P)\ge\tau$,否则判 $\varnothing$。$\Phi$ 在每个关系上取存活提案构造规则文本 $\hat g_r$(模板实例化,与 gold 同构,可直接注入 $B_5$)。

### 2.4 置信度校准与精度下界定理

原始 $\mathrm{score}$ 非"正确概率"。用 **Platt 标度**校准:
$$
\boxed{\;c(P)=\sigma\!\big(\alpha\,\mathrm{score}(P)+\beta\big),\quad \sigma(z)=\tfrac1{1+e^{-z}}\;}
$$
其中 $(\alpha,\beta)$ 由**留一库(LOLO)** 逻辑回归在**其它库**的 $(\mathrm{score},\ \text{是否正确})$ 上拟合(跨库迁移、无泄漏)。

**定义 5(校准).** 称 $c$ 为校准的,若 $\Pr[\,C=1\mid c(P)=v\,]=v$,其中 $C\in\{0,1\}$ 表"抽取关系正确"。

**定理 1(精度下界).** 设 $c$ 校准,发出集 $S_\theta=\{P:c(P)\ge\theta\}$。则发出规则的期望精度
$$
\boxed{\;\mathrm{precision}(\theta)=\mathbb E\big[C\mid c(P)\ge\theta\big]=\mathbb E\big[c(P)\mid c(P)\ge\theta\big]\;\ge\;\theta.\;}
$$
**证明.** 由全期望与校准性,
$$
\mathbb E[C\mid c\ge\theta]
=\mathbb E\big[\,\mathbb E[C\mid c]\ \big|\ c\ge\theta\,\big]
=\mathbb E[c\mid c\ge\theta]\ \ge\ \theta,
$$
末步因事件 $\{c\ge\theta\}$ 上 $c\ge\theta$ 处处成立。$\blacksquare$

**推论(操作曲线).** $\theta\mapsto(\mathrm{precision}(\theta),\ \mathrm{coverage}(\theta))$ 为 precision–coverage 曲线,$\mathrm{coverage}(\theta)=\lvert S_\theta\rvert/\lvert\text{gold}\rvert$ 关于 $\theta$ 不增。$\theta$ 即"发出规则的期望精度下界"旋钮。

---

## 3. 完整 B5:抽取 → 生成 → 执行 → 归因 → 精修 的不动点迭代

$\Phi$ 是一次性的、有限精度的($\mathrm{precision}\approx0.5$)。错误规则会反向误导生成,故用**执行反馈**闭合。

**定义 6(B5 闭环).** 给定 $(L,t)$,prompt 构造 $\pi(r,\nu)=\mathrm{API\_LIST}(L)\oplus r\oplus\nu$($\nu$ 为 prompt 级反馈注记),迭代
$$
\boxed{\;
\begin{aligned}
r_0&=\hat g_{C_t}=\Phi(L,t),\qquad \nu_0=\varnothing,\\
g_\theta&\sim\mathcal M\big(\pi(r_\theta,\nu_\theta)\big),\quad
v_\theta=\mathrm{Ora}(g_\theta,t)=(y_\theta,\rho_\theta,\delta_\theta),\\
&\text{若 }y_\theta=1:\ \textbf{停}\ (\text{返回 }r_\theta,g_\theta,\theta);\\
a_\theta&=\mathcal A\!\mathrm{ttr}(v_\theta,\ r_{C_t}),\qquad
(r_{\theta+1},\nu_{\theta+1})=\mathcal R\!\mathrm{ef}(r_\theta,\ a_\theta,\ v_\theta),
\end{aligned}\;}
$$
至首个 $y_\theta=1$ 或预算 $\theta=K$。

### 3.1 失败归因 $\mathcal A\!\mathrm{ttr}$:$\kappa$ 双射的逆(Bayes 形式)

oracle 原因码本就**按关系设计**,故存在标注 $\ell:\rho\mapsto\mathcal R\cup\{\textsf{code}\}$(例:`wrong_output_structure`$\to$config-return-contract;`disable_not_persistent`/`state_not_restored`/`obligation_unmet`$\to$lifecycle;`wrong_enabled_set`$\to$shared-receiver;`syntax/import/undefined`$\to\textsf{code}$)。

对**模糊原因码**(如 `runtime_error`/`wrong_output`),由细节串 $\delta$ 的强判别线索 $\mathrm{cue}(\delta)$ 决定;无强线索时**退回抽取关系作先验**。统一写成 **MAP**:

**定义 7(归因).**
$$
\boxed{\;
\mathcal A\!\mathrm{ttr}(v,\hat r)=
\begin{cases}
(\textsf{code},\ \textsf{prompt}), & \ell(\rho)=\textsf{code}\ \text{或}\ \mathrm{cue}(\delta)=\textsf{code},\\[2pt]
\big(\arg\max_{r\in\mathcal R}\Pr[r\mid\rho,\delta,\hat r],\ \textsf{rule}\big), & \text{否则,}
\end{cases}\;}
$$
其中 $\Pr[r\mid\rho,\delta,\hat r]\propto \underbrace{\Pr[\rho,\delta\mid r]}_{\text{似然(}\ell,\mathrm{cue}\text{)}}\ \underbrace{\Pr[r\mid\hat r]}_{\text{先验集中于 }\hat r}.$

**机制**:似然尖锐(强线索)时覆盖通道;似然平坦(模糊异常,如 `PathAccessError` 既可能缺 `default=` 也可能 spec 形态错)时先验 $\hat r$ 取胜——即"仅在信号明确时才纠正通道"。$\textsf{rule}/\textsf{prompt}$ 决定反馈注入**规则**还是 **prompt**。

### 3.2 类型化精修 $\mathcal R\!\mathrm{ef}$

设归因关系 $r_a=\mathrm{rel}(a)$,抽取关系 $\hat r=C_t$,$\mathrm{cl}(r,\delta)$ 为按关系 $r$ + 细节 $\delta$ 实例化的纠正子句。

**定义 8(精修).**
$$
\boxed{\;
\mathcal R\!\mathrm{ef}(r_\theta,a,v)=
\begin{cases}
\big(r_\theta\ \oplus\ \mathrm{cl}(r_a,\delta),\ \ \nu'\big), & r_a=\hat r\quad(\textbf{加固}:\text{规则本对、模型未遵守}),\\[2pt]
\big(r_\theta\ \oplus\ \mathrm{cl}(r_a,\delta),\ \ \nu'\big), & r_a\neq\hat r\quad(\textbf{纠正}:\text{抽取漏掉 }r_a\text{ 通道}),\\[2pt]
\big(r_\theta,\ \ \nu'=\mathrm{PF}(v)\big), & a.\textsf{target}=\textsf{prompt}\quad(\text{代码层错}\to\text{prompt}),
\end{cases}\;}
$$
$\oplus$ 为子句去重追加,$\mathrm{PF}(v)$ 为 prompt 反馈注记。**信息单调**:$\mathcal I(r_{\theta+1})\supseteq\mathcal I(r_\theta)$(每轮只增不减约束信息)。

### 3.3 动态置信度(Beta 后验)

把每轮通过/失败视作对"该规则有效性"$q$ 的 Bernoulli 观测,先验 $q\sim\mathrm{Beta}(1,1)$:

**定义 9(Beta 置信度).** $a_0=b_0=1$,
$$
a_{\theta+1}=a_\theta+y_\theta,\quad b_{\theta+1}=b_\theta+(1-y_\theta),\qquad
\boxed{\;c_\theta=\mathbb E[q\mid\text{观测}]=\frac{a_\theta}{a_\theta+b_\theta}.\;}
$$
这是叠加在静态 LOLO(定理 1)之上的**第二个动态校准信号**:反复失败的规则置信度下降,经精修通过的规则置信度上升。

### 3.4 收敛与反馈增益

**定义 10(单调性假设).** 设注入更强成对约束信息弱增通过概率:$\mathcal I(r')\supseteq\mathcal I(r)\Rightarrow \Pr[\,y=1\mid \pi(r',\cdot)\,]\ge\Pr[\,y=1\mid\pi(r,\cdot)\,]$。

**命题 2(每轮非降 + 几何界).** 在定义 10 下,逐轮通过概率 $q_\theta=\Pr[y_\theta=1]$ 非降;若存在 $q_\star=\min_\theta q_\theta>0$,则 $K$ 轮内收敛概率
$$
\Pr[\text{在 }\le K\text{ 轮收敛}]\ \ge\ 1-\prod_{\theta=0}^{K-1}(1-q_\theta)\ \ge\ 1-(1-q_\star)^K.
$$
**证明.** 非降由定义 10 与信息单调 $\mathcal I(r_{\theta+1})\supseteq\mathcal I(r_\theta)$ 直接得;界为独立下界放缩(各轮失败事件以 $1-q_\theta\le1-q_\star$ 上界)。$\blacksquare$

**定义 11(反馈增益与收敛轮数).**
$$
G=\mathrm{Pass}(B_5^{\text{loop}})-\mathrm{Pass}(B_5^{\text{static}})\ge0,\qquad
T=\mathbb E[\,\min\{\theta:y_\theta=1\}\wedge K\,]\ (\textbf{收敛轮数,新指标}).
$$

---

## 4. 评测度量的形式化

### 4.1 RQ1:抽取质量

设 gold typed 规则集 $\mathcal G_L=\{(r_j,\mathrm{tok}_j)\}$(关系 + 显著 token)。预测规则 $P$ **命中** gold $j$:
$$
\mathrm{match}(P,j)\iff r_P=r_j\ \wedge\ \mathrm{tok}(P)\cap\mathrm{tok}_j\neq\varnothing.
$$
在阈 $\theta$ 下($S_\theta$ 为发出集):
$$
\mathrm{P}(\theta)=\frac{\lvert\{P\in S_\theta:\exists j,\ \mathrm{match}(P,j)\}\rvert}{\lvert S_\theta\rvert},\quad
\mathrm{R}(\theta)=\frac{\lvert\{j:\exists P\in S_\theta,\ \mathrm{match}(P,j)\}\rvert}{\lvert\mathcal G\rvert},\quad
\mathrm{F1}=\frac{2\mathrm{PR}}{\mathrm P+\mathrm R}.
$$
**Edge-type accuracy**:在 token 可覆盖的预测上,$\frac1N\sum_P\mathbf 1\{r_P=r^{\mathrm{cover}}_P\}$($r^{\mathrm{cover}}_P$ 为 token 重叠最大的 gold 关系)→ 关系混淆矩阵的对角占比。

### 4.2 RQ2:下游收益与显著性

对配对样本(同 $\langle$模型,任务,轮$\rangle$)用 **McNemar 精确检验**:设 $B$ 过-$A$ 挂数 $b$、$A$ 过-$B$ 挂数 $c$,
$$
p=2\!\!\sum_{i=\max(b,c)}^{b+c}\!\binom{b+c}{i}2^{-(b+c)},\qquad
\text{效应量(odds)}=b/c,
$$
用于 $\Delta_{5|3^\ast},\Delta_{4|3^\ast}$ 等;任务级差分配 **bootstrap 95% CI**。RQ1 的 gold 另做双标注 + Cohen's $\kappa$。

---

## 5. Taxonomy 完备性(为何 $\kappa$ 是双射)

**命题 3(成对耦合通道穷举).** 两个调用 $A,B$ 之间,$A$ 影响 $B$ 正确性只能经由有限"媒介":$A$ 算出的**值**(经参数 / 经返回)、$A$ 改的**共享堆状态**、$A$ 确立的**类型/契约**、二者的**控制流关系**(顺序/作用域 / 存在性)。故媒介集为
$$
\{\text{DFP, DFR, SS, TC, CO, CE}\},
$$
无第五种数据通道。每个通道对应唯一关系,$\kappa$ 为双射。∎(经验侧:6 类与 API-misuse 文献 MUBench/MUC 的 missing-call / wrong-order / wrong-param / 误用返回 / 状态误用一一对齐。)

本基准 **6 库覆盖全部 6 类**:simplug/diot/simpleconf/glom/bidict 提供 DFP–CO 五通道,**sqlitedict 提供 CE**(写入→`commit()` 的 completion-obligation,违规由"新连接读不到"运行时可观察)。故 $\mathcal R,\mathcal K$ 取 6 维。

---

## 6. 公式↔代码对照

| 公式 | 实现 |
|---|---|
| noisy-OR $s_k$(定义 2) | `pair_extractor.Proposal.witness` |
| 判别得分(定义 3)+ 区分性锚点 | `pair_extractor.score_proposals`(`distinctive`) |
| 检出阈 $\tau$、抑制 $\lambda$、权重 $w$ | `TAU_DETECT / LAMBDA_SUP / SOURCE_WEIGHTS` |
| Platt + LOLO(§2.4) | `pair_extractor.fit_platt`、`eval_extraction.calibrate_lolo` |
| 定理 1 精度下界 | `eval_extraction.precision_coverage_curve`(`E[c|c≥θ]` 列) |
| 归因 MAP(定义 7) | `b5_feedback.attribute`(`RELATION_BY_REASON`/`DETAIL_CUES`/先验 $\hat r$) |
| 精修(定义 8) | `b5_feedback.refine_rule`(strengthen/correct)、`prompt_feedback` |
| Beta 置信度(定义 9) | `b5_feedback.BetaConfidence` |
| 闭环(定义 6)、收敛轮数 $T$ | `b5_feedback.run_loop` / `LoopResult.rounds_used` |
| 公平闭环运行(B5_loop 条件) | `fair_loop.py`(dev/held 拆分、等预算 K,无泄漏;产 held-out 通过率) |
| top-$K$ 抽取规则注入(§1.3) | `benchlib_generate.extracted_rule_for_task` |
| RQ1 度量(§4.1) | `eval_extraction.prf_at / confusion` |
| RQ2 度量:$\Delta$、$\eta$、McNemar(§4.2) | `analyze_full.py`(`mcnemar_exact` / `fill`) |

---

## 7. 主张汇总(可证伪)与实测(6 库 / 5 模型,run-level)

1. **存在性**:未见库上 $\mathrm{Pass}(B_0),\mathrm{Pass}(B_1)$ 低,$\Delta_{4|1}>0$。实测 $B_4$ 显著优于 $B_3^\ast$($p{=}2.6\!\times\!10^{-20}$)——成对约束相对裸序列增益巨大。
2. **抽取可行**:定理 1 给出可调精度下界;$\Phi$ 在 6 库 RQ1 有非平凡 P/R/F1(合计 P$=$0.38、R$=$0.48;$\theta^\ast{=}0.45$ 时 P$=$0.67)。
3. **RQ2 核心(已确认)**:$\Delta_{5|3^\ast}=+0.27$ 显著(McNemar $p{=}2.0\!\times\!10^{-15}$,6 类里 5 类显著);$\Delta_{5|1}$ 亦显著($p{=}5.2\!\times\!10^{-9}$)。$\Delta_{5|4}=-0.09$($p{=}0.007$,gold 仍略优),但 $\eta{=}63\%$——**闭环 test-free 地补回 63% 的 gold 差距**(lifecycle 100% / shared-receiver 83% / return-flow 71%;completion-obligation 上 $B_5^{\text{loop}}{=}1.00$ 反超 $B_4$)。最弱为 param-dependency($\eta{=}29\%$)与 simplug 库。
4. **闭环增益**:$G\ge0$(命题 2 给几何界);收敛轮数 $T$ 见 `run_config.json::b5_loop_convergence`(多数任务 1 轮收敛)。
