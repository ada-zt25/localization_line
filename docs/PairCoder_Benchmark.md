# PairCoder Benchmark:面向"未见/低流行度/私有库"的 API 成对组合约束执行式评测基准

> 权威说明 ｜ 最后更新 2026-06-15。本文是 benchmark 的唯一权威说明。代码在 `Ollama问题存在性实验/`(生成/脚本)与 `Ollama问题存在性实验/exec_oracle/`(执行 oracle)。每个组件标注对应交付代码。

## 0. 摘要(TL;DR)

PairCoder Benchmark 评测一个问题:**对一个模型"未见过"的库,要注入什么程度的知识,模型才能正确地把它的 API 组合起来用?** 焦点是**有状态 API 的成对调用组合约束**(两个 API 必须以特定方式配合,配错则产生运行时可观察的错误)。

- **5 个真实、低流行度库**(逐字 vendored,纯本地可跑),跨数据/配置/插件/提取四个领域:`simplug 0.5.7`(插件)、`diot 0.3.4`(属性字典)、`simpleconf 0.9.3`(分层配置)、`glom 25.x`(嵌套数据提取)、`bidict 0.23.x`(双向映射)。前四个用于"未见→收益"主张;**bidict 作为高先验对照**(模型已熟,B4 无收益,印证"收益依赖未见程度")。**不含自编玩具库**——经科学性复核,自编库存在构造效度/循环性问题,不能作为主证据(见 §6)。
- **gold 成对规则从真实库语义手工抽取并标注出处**(可追溯);自动抽取器的 precision/recall 列为**明确的后续实验**(不在此编造)。
- **6 类 pair 关系**的 typed taxonomy(由"调用间耦合通道"穷举推导 + 与 API-misuse 文献 MUBench/MUC 对齐)。
- **B0–B4 五档提示梯度**作为唯一自变量,隔离"成对约束知识"的贡献。**B4 是分层注入**(= B1 的 API 清单 + 该任务对应的那一条成对规则),使 B4 成为 B1 的真超集,从而 **B4−B1 干净隔离成对规则的边际价值**(见 §4.1)。
- **执行式隐藏测试 oracle**:只依据可观察行为判分(绝不读源码),消除"循环 oracle";每库配**锚定套件**作为可信度硬门槛;每库注入文本上线前过**可执行性审计闸门**(§5.6)。

**现状**:**60 个任务**(simplug 10、diot 12、simpleconf 18、glom 10、bidict 10),全部锚定自检通过(simplug 42 / diot 25 / simpleconf 36 / glom 20 / bidict 20 = **143 例**)。这些库自然覆盖 **5 类 pair,每类 ≥11**(param-dependency 11 / config-return-contract 13 / return-flow 12 / shared-receiver 12 / lifecycle 12);第 6 类 **completion-obligation 在这类库中天然不出现**(它是资源型库的模式),如实列为 future work(§6/§9)。

---

## 1. 研究动机与问题定义

### 1.1 问题
调用单个 API 模型大多会用;难点在**两个 API 如何搭配**:传名字还是对象?临时还是持久?返回列表还是单值?这些约束在单条 API 文档里看不出来,且常只在运行时暴露。对**未见/私有库**,模型没有先验,这一问题尤为突出——正是本研究的核心场景。

### 1.2 研究问题(RQ)
- **RQ1(存在性)**:仅给 API 清单/文档/调用序列(B0–B3),模型能否满足成对约束?
- **RQ2(干预)**:在 API 清单之上叠加从真实库抽取的成对规则(B4)是否显著提升,且 **B4−B1 > 0**(即成对规则在 API 知识之外仍有边际贡献)?
- **RQ3(泛化/边界)**:收益是否与**库的未见程度**(B0 作先验探针)相关?是否跨**难度、pair 类型**一致?
- **RQ4(度量可信)**:评测 oracle 自身是否可信(不冤枉语义等价写法、不放过运行时错误)?注入文本是否可执行(不因措辞 bug 系统性压低某档位)?

### 1.3 任务形式化
任务 $t=(p_t,f_t,C_t,\mathcal I_t,\mathcal O_t)$:NL 描述 $p_t$、待实现函数 $f_t$、考核的成对约束 $C_t$(属六类之一)、隐藏测试输入 $\mathcal I_t$、可观察判据 $\mathcal O_t$(返回值/运行迹/终态)。判分 $\bigwedge_{x}\text{check}_t(\text{run}(g,x))$,**只消费可观察量,不读 $g$ 源码**。
> 对应代码:`exec_oracle/lib_<lib>.py`(`FUNC_NAMES`/`INPUTS`/`CHECKS`)+ `fixture_<lib>.py`;判分核心 `exec_oracle/benchlib.py::evaluate_source`(新库)与 `exec_runner.py`(simplug)。

---

## 2. Pair 关系 Taxonomy(六类)

### 2.1 原则框架:两调用间的"耦合通道"穷举
两个调用 A、B 间的约束,只能经由有限"媒介"传递——一条语句影响另一条只可能经由它**算出的值**、它**改的堆状态**、它**确立的类型契约**、它与对方的**控制流关系**:

| 大类 | 通道 | pair 类型 |
|---|---|---|
| 数据 | 经参数传值/传形 | **param-dependency** |
| 数据 | 经返回值传值 | **return-flow** |
| 状态 | 经共享可变对象 | **shared-receiver** |
| 类型/契约 | A 的配置定 B 的返回类型/形态 | **config-return-contract** |
| 控制流 | 顺序/作用域/生命周期 | **lifecycle** |
| 控制流 | 存在性/必然性(必须也调搭档) | **completion-obligation** |

**完备性命题**:对**成对**约束,A 影响 B 正确性的媒介只有 {数据(参数/返回)、共享状态、类型契约、控制流(顺序/存在)},无第五种,故六类穷举该框架的叶子。∎

### 2.2 与 API-misuse 文献对齐
6 类映射到 MUBench/MUC 经验类别:missing method call→completion-obligation;wrong order→lifecycle;wrong parameter→param-dependency;误用返回/缺检查→return-flow/config-return-contract;状态/接收者误用→shared-receiver。**分析完备 + 经验完备**双重论证。

### 2.3 各类的 error-type 与真实库实例

| 类型 | error-type | 真实库实例 |
|---|---|---|
| param-dependency | `wrong_output`/`runtime_error` | simplug 名字vs对象;diot `diot_transform=`;simpleconf 合并顺序;glom `default=`/`Coalesce`;bidict `put` vs `forceput`(值冲突) |
| return-flow | `wrong_output_structure`/`runtime_error` | simplug `get_plugin→wrapper.disable`;diot 嵌套链式访问;simpleconf `load→access`;glom 点号路径导航/`('nums',sum)` 链;bidict 反查走 `.inv` |
| shared-receiver | `wrong_output` | simplug 同一 `sp`;diot 同一 Diot;simpleconf 同一 conf+`use_profile`;glom `Assign` 原地改同一 target;bidict `.inv` 是同对象活视图 |
| config-return-contract | `wrong_output_structure` | simplug `result=FIRST`;diot `to_dict()`/`diot_nest=`;simpleconf 返回 Diot/profile 取值;glom spec 形态定输出形态(`['v']`→list、`{...}`→dict);bidict 1:1 契约、`.inv` 也是 bidict |
| lifecycle | `obligation_unmet`/`state_not_restored` | simplug context 恢复;diot `FrozenDiot.thaw()`;simpleconf `with_profile`(临时) vs `use_profile`(持久);bidict `putall` 原子回滚 / `frozenbidict` 不可变 |
| completion-obligation | `obligation_unmet` | **本套件未覆盖**(数据/配置/提取库无资源 open/close;需资源型库,见 §6) |

> 说明:glom 是无状态的提取库,**天然无 lifecycle**(如实省略,见 §3.2);其余四库覆盖含 lifecycle 在内的 5 类。

### 2.4 范围界定
显式排除并列 future work:n 元顺序/优先级、声明级型/协议一致(async/签名)、跨库全局配置。
> 对应代码:gold 规则文本——simplug `paircoder_step0_simplug_pilot.py::GOLD_PAIR_RULES`;其余 `exec_oracle/lib_<lib>.py::GOLD_PAIR_RULES`(每条标注真实语义/源码出处)。

---

## 3. 实验库与领域

### 3.1 选库准则与"为何用真实低流行度库"
1. **未见/低流行度/私有**(模型零或极低先验——本研究核心场景);2. 真实(有 PyPI/源码,可抽取真实约束、可外推);3. 纯本地可执行(无网络/服务器,确定性);4. **有真实的成对组合约束**(光看 API 名字会写错,否则成为"弱基准"——见 pyparam 退役教训 §10.2);5. 跨领域。

> **为何不是自编玩具库**:自编库的约束、规则、oracle 都由作者定,存在构造效度/循环性问题,且玩具规模不可外推——会被顶会审稿判为 toy。**真实低流行度库**兼顾"低先验"与"真实可抽取"。
> **为何不是流行真实库**:流行库(如 msgspec/peewee/niquests)模型先验过强,仅给 API 清单(B1)即可做对,B4 无增益(早期实测,见 §10.2)。**bidict 实测 B0≈0.85 落在这一端,故定位为"高先验对照"而非主张库**——它的 B4 无收益恰好印证"收益依赖未见程度"。

### 3.2 五库一览(全部真实、vendored)

| 库 | 版本 | 领域 | 覆盖的 pair 类型 | B0 先验 | 角色 | 对应代码 |
|---|---|---|---|---|---|---|
| **simplug** | 0.5.7 | 插件/扩展 | param/sr/rf/lifecycle/config-return | 低(~0.20) | 主(未见) | `fixture_simplug.py`、`hidden_tests.py`、`anchor_solutions.py` |
| **diot** | 0.3.4 | 属性字典 | param/config-return/rf/sr/lifecycle | 中(~0.65) | 主 | `fixture_diot.py`、`lib_diot.py` |
| **simpleconf** | 0.9.3 | 分层配置 | param/config-return/rf/sr/lifecycle | 极低(~0.03) | 主(未见) | `fixture_simpleconf.py`、`lib_simpleconf.py` |
| **glom** | 25.x | 嵌套数据提取 | rf/config-return/param/sr(无 lifecycle) | 低(~0.15) | 主(未见) | `fixture_glom.py`、`lib_glom.py` |
| **bidict** | 0.23.x | 双向映射 | param/config-return/rf/sr/lifecycle | 高(~0.85) | **高先验对照** | `fixture_bidict.py`、`lib_bidict.py` |

> 五库正好覆盖 **B0 先验强度全谱**(simpleconf 0.03 → glom 0.15 → simplug 0.20 → diot 0.65 → bidict 0.85),比"全是未见库"更能支撑"B4 收益 ∝ 未见程度"的主张。
> **退役记录**:pyparam 0.5.4 曾在册,经实测 B1(纯 API 清单)即满分、B4−B1≈0——其 `add_param/parse/ns.attr` 语义被 API 清单完全表达,且自动类型推断使非平凡候选无干净 oracle,**于 6.15 移除**(数据归档 `result/_archive/`,代码保留)。varname 曾作候选,因靠帧/源码魔法、仅契合 3 类 pair、exec 下需 hack 而弃用。

### 3.3 vendoring(复现)
```bash
cd Ollama问题存在性实验/exec_oracle
# simplug/diot 已逐字 vendored。补装其余库到 vendor/:
python3 -m pip install --target vendor python-simpleconf==0.9.3
python3 -m pip install --target vendor glom bidict
```
> 全部纯 Python、纯本地;跑实验用能 import vendor 的同一解释器(本机 Python 3.14)。

---

## 4. 任务构造

### 4.1 提示档位 B0–B4(唯一自变量)
| 档位 | 内容 |
|---|---|
| B0_direct | 仅任务文字(裸考) |
| B1_api_list | API 清单 |
| B2_raw_api_docs | 原始文档片段 |
| B3_oracle_api_sequence | 理想调用顺序(无成对约束) |
| B4_gold_pair_rule | **B1 的 API 清单 + 该任务对应的那一条成对规则**(分层注入) |

**B4 的分层设计(关键)**:B4 = `API_LIST` ⊕ `该任务 pair_type 对应的那一条 gold 规则`。两点理由:
1. **B4 是 B1 的真超集** → `B4−B1` 干净隔离"成对规则"在 API 知识之外的边际价值(此前 B1/B4 内容不相交,"B4 vs B1"是在比两种不同东西)。
2. **按任务只注入相关那一条规则**(而非整块灌入全部规则) → 避免无关规则的 usage pattern 串到当前任务上造成跨任务模式污染(此污染在 simplug config-return 上曾把 B4 从应得的高分压到 0,见 §6)。

**对照逻辑**:若 `B4−B1` 在未见库上显著为正,即证"光给 API 文档不够,须额外注入成对约束";若在高先验库(bidict)上 `B4−B1≈0`,则印证收益依赖未见程度。
> 对应代码:simplug `paircoder_step0_simplug_pilot.py::method_payload`(`gold_rule_for_task` 按 pair_type 选规则、`API_LIST ⊕ 规则`);其余库 `exec_oracle/benchlib_generate.py::method_payload`(同机制,`gold_rule_for_task` + `_split_pair_rules` 按 `Relation:` 标签切分整块 GOLD_PAIR_RULES)。

### 4.2 难度分层
easy(单约束/无干扰)、medium(主约束+诱导项)、hard(多约束相互作用/反直觉)。产物含 `pair_type`/`difficulty`,结果可按类型/难度切片(`benchlib_eval.py::aggregate`)。

### 4.3 任务目录(60 任务,全部锚定通过)

**simplug**(10):T001–T010,覆盖 param(2)/shared-receiver(2)/return-flow(2)/lifecycle(2)/config-return(2)。

**diot**(12,`lib_diot.py`;gold 规则标注 `vendor/diot/*.py` 出处):D001/D002 access_camel/snake(param)、D003 get_default(param)、D004 to_plain_dict / D005 nested_stays_dict / D006 nested_is_diot(config-return)、D007 nested_chain / D008 todict_then_index(return-flow)、D009 set_then_get / D010 nested_mutate_reflects(shared-receiver)、D011 thaw_to_modify / D012 thaw_is_temporary(lifecycle)。

**simpleconf**(18,`lib_simpleconf.py`):param(2:S001/S002 合并顺序)、config-return(3:S003 返回Diot/S004 profile取值/S005 当前profile名)、return-flow(3:S006–S008)、shared-receiver(4:S009/S010/S011/S018 同一conf)、lifecycle(6:S012–S017 `with_profile`临时 vs `use_profile`持久/嵌套/还原)。

**glom**(10,`lib_glom.py`):

| id | 函数 | 类型 | 难度 |
|---|---|---|---|
| G001 | deep_get | return-flow | easy |
| G002 | apply_after_nav | return-flow | medium |
| G009 | first_item(列表索引路径) | return-flow | medium |
| G003 | pluck_list(`['v']`→list) | config-return | easy |
| G004 | restructure(dict spec→dict) | config-return | medium |
| G010 | summarize(dict spec) | config-return | medium |
| G005 | safe_get(`default=`) | param-dependency | medium |
| G006 | coalesce_get(`Coalesce`) | param-dependency | medium |
| G007 | assign_in_place(`Assign` 原地改) | shared-receiver | medium |
| G008 | assign_return_target | shared-receiver | medium |

(glom 无状态生命周期 → 不含 lifecycle,如实省略)

**bidict**(10,`lib_bidict.py`):

| id | 函数 | 类型 | 难度 |
|---|---|---|---|
| B001 | key_for(`.inv[val]` 反查) | return-flow | easy |
| B007 | roundtrip(`.inv[b[key]]`) | return-flow | medium |
| B002 | invert(`dict(b.inv)`) | config-return | medium |
| B003 | inverse_view(`.inv` 也是 bidict) | config-return | easy |
| B004 | remap(`forceput` 丢旧键) | param-dependency | medium |
| B010 | reject_dup(值冲突须 catch) | param-dependency | medium |
| B005 | add_then_lookup(同对象 `.inv`) | shared-receiver | medium |
| B006 | set_through_inverse(逆视图写) | shared-receiver | medium |
| B008 | atomic_add(`putall` 原子回滚) | lifecycle | hard |
| B009 | make_frozen(`frozenbidict` 不可变) | lifecycle | medium |

### 4.4 分布表

**pair-type × 库(60,5 类各 ≥11)**:

| 类型 | simplug | diot | simpleconf | glom | bidict | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| param-dependency | 2 | 3 | 2 | 2 | 2 | **11** |
| shared-receiver | 2 | 2 | 4 | 2 | 2 | **12** |
| return-flow | 2 | 2 | 3 | 3 | 2 | **12** |
| lifecycle | 2 | 2 | 6 | 0 | 2 | **12** |
| config-return-contract | 2 | 3 | 3 | 3 | 2 | **13** |
| completion-obligation | 0 | 0 | 0 | 0 | 0 | **0**(future work) |
| **合计** | **10** | **12** | **18** | **10** | **10** | **60** |

**难度**:easy 16 / medium 36 / hard 8。

> completion-obligation 需引入一个**真实低流行度资源型库**(连接/文件/会话类),为 future work。

---

## 5. 评测方法学:执行式 oracle

### 5.1 为什么执行式(消除循环 oracle)
判据只看**可观察行为**(返回值/轨迹/终态),不读源码,从根本消除"注入规则=检查规则"与"语义等价误判/运行时漏判"。
> 判分核心:`exec_oracle/benchlib.py::evaluate_source`(新库)、`exec_runner.py`(simplug)。

### 5.2 各库可观察判据
- **simplug**:返回值 + 运行迹(每次 hook 的 enabled 集合)+ 终态;单射 score 公式反推行为。harness 按任务绑定其约定的管理器(`fixture_simplug.MANAGER_FACTORY_BY_TASK`:T007=first/T008=last),使"prompt 承诺的 sp 已存在且正确"成真(见 §6 修复记录)。
- **diot**:返回值的 Python 类型与值(Diot vs dict、嵌套类型);frozen 修改抛 `DiotFrozenError`。
- **simpleconf**:`Config.load`/`ProfileConfig` 返回的 Diot 值;profile 切换后的取值;`current_profile`。
- **glom**:`glom(target,spec)` 的返回类型/值(标量/list/dict);缺失路径抛 `PathAccessError`;`Assign` 后**原地检查 target 是否被改**(shared-receiver)。
- **bidict**:返回类型/值;`.inv` 反查;值冲突抛 `ValueDuplicationError`;`putall` 原子性(冲突后整体回滚);`frozenbidict` 不可变(改抛错)。
> 对应代码:`exec_oracle/fixture_<lib>.py` + `lib_<lib>.py::CHECKS`。

### 5.3 锚定套件(可信度硬门槛)
判分前过锚定:canonical 正确解 + **静态会误判的语义等价变体** 必过;每类违规模式 必挂且 reason 符合预期。**不全绿,评估拒绝运行**。当前(全过):**simplug 42 / diot 25 / simpleconf 36 / glom 20 / bidict 20 = 143 例**。
> 代码:simplug `anchor_solutions.py`+`run_exec_eval.py::run_anchors`;新库 `lib_<lib>.py::ANCHORS`+`benchlib.py::run_anchors`(命令 `python3 benchlib.py <lib>`);评测前门控 `benchlib_eval.py`。

### 5.4 隔离与防作弊
模型生成在独立子进程运行(隔离崩溃/挂起);多输入均须通过(防写死);**每次调用前 deepcopy 输入参数**,使"原地改 target"的任务(如 glom `Assign`)不会跨输入/跨锚定 case 污染共享输入对象(`benchlib.py` 测试隔离)。锚定为可信 gold 代码,进程内运行。
> 代码:`exec_runner.py`(simplug)、`benchlib_runner.py`(新库)。

### 5.5 指标与统计
任务级(跨轮多数票)/运行级通过率;B0→B4 梯度;**核心指标 `B4−B1`**(成对规则的边际价值,因 B4⊇B1);**B0 作先验探针**(对比各库收益与未见程度);**按 pair_type/difficulty 切片**;B1/B3 vs B4 McNemar 配对检验;静态 vs 执行的一致率/κ。
> 代码:`benchlib_eval.py::aggregate`(出 `exec_summary.md` 三张切片表)、可视化 `visualize_exec.py`。

### 5.6 注入文本可执行性审计(上线前闸门)
任何全量跑之前先过 `exec_oracle/audit_injection.py`:用每库真实 exec 命名空间(`fixture_<lib>.make_namespace()`),AST 抽出注入文本(GOLD_PAIR_RULES/API_LIST/RAW_API_DOCS)里 Usage pattern 的**裸函数调用**,凡命名空间没有却是某暴露类方法的报 HIGH(必为运行时 NameError)。**目的**:防止某档位注入文本用了 harness 跑不通的调用约定,从而系统性压低该档位、污染对照(此类 bug 曾使 simpleconf 的 B4 被裸 `use_profile(...)` 压低,见 §6)。当前 5 库全 PASS。
> 命令:`cd exec_oracle && python3 audit_injection.py`(默认审计 5 主库;可传库名审计其它)。

---

## 6. 效度与威胁(Validity)

- **构造效度**:① oracle 经锚定构造性验证(正确必过、违规必挂);② **gold 规则从真实库语义/源码手工抽取并标注出处**(`lib_<lib>.py::GOLD_PAIR_RULES`),非自编;③ 判分只看行为,容忍语义等价写法;④ **注入文本经可执行性审计**(§5.6),排除"措辞 bug 压低某档位"的测量假象。
- **内部效度**:B0–B4 信息单调递增,**B4 设计为 B1 真超集**使 `B4−B1` 干净隔离成对规则贡献;多输入+子进程+deepcopy 隔离防作弊。
- **外部效度**:5 个真实、低流行度、跨领域库,覆盖 B0 先验全谱;"未见"靠**低流行度论证**(而非自编"保证")。
- **诚实的覆盖边界**:这些数据/配置/提取库**不含 completion-obligation**;glom 无 lifecycle——强行制造会重蹈"自编约束"覆辙,故如实标注(需真实资源型库,future work)。
- **抽取评测**:当前 gold 规则为**单人手工抽取**;自动抽取器的 precision/recall 与双人标注 IAA 列为明确的后续实验。
- **复现性**:真实库逐字 vendored + 版本固定 + 纯本地 + 确定性输入 + 锚定门槛 + 注入审计随仓库分发。

**已修复的方法学缺陷(记录在案,体现度量自检)**:
1. **simpleconf 裸调用 bug**:gold 规则 Usage pattern 把 `ProfileConfig.use_profile(...)` 写成裸 `use_profile(...)`,模型照抄→NameError→B4 被系统性压低。修正后 B4 0.33→0.69。由此建立 §5.6 审计闸门。
2. **simplug config-return B4 反降**:旧 B4 整块灌入全部规则,无关规则的 `plugins_context` 模式串到 config-return 任务;且 prompt 承诺的 sp 与 harness 绑定的 sp 模式不一致。修复 = 分层按任务注入(§4.1)+ harness 按任务绑管理器(§5.2),config-return 0/8→8/8。
3. **测试隔离**:`Assign` 类原地改 target 的任务会跨 case 污染共享输入 → 改为每次调用 deepcopy 输入(§5.4)。

---

## 7. 代码与产物(Artifact)

| 组件 | 文件 | 作用 |
|---|---|---|
| simplug 生成+静态 | `paircoder_step0_simplug_pilot.py` | simplug 的 TASKS/B0–B4/按任务分层 B4/summarize |
| simplug 执行 oracle | `exec_oracle/fixture_simplug.py`、`hidden_tests.py`、`anchor_solutions.py`、`exec_runner.py`、`run_exec_eval.py` | 夹具(含按任务管理器)/判据/锚定/子进程/编排 |
| 通用多库 harness | `exec_oracle/benchlib.py` | 统一接口+锚定运行器+判分核心(deepcopy 隔离) |
| 通用子进程 runner | `exec_oracle/benchlib_runner.py` | 单份生成隔离判分 |
| 通用生成(Ollama) | `exec_oracle/benchlib_generate.py` | 任意库 B0–B4 生成(B4 按任务分层) |
| 通用评测 | `exec_oracle/benchlib_eval.py` | 锚定门控→子进程判全量→按 method×pair_type×difficulty 切片 |
| 真实库模块 | `exec_oracle/fixture_<lib>.py` + `lib_<lib>.py`(lib∈{diot,simpleconf,glom,bidict}) | 夹具 + 任务/INPUTS/CHECKS/ANCHORS/抽取规则 |
| **注入审计闸门** | `exec_oracle/audit_injection.py` | 上线前查注入文本可执行性(§5.6) |
| vendored 真实库 | `exec_oracle/vendor/` | simplug、diot、simpleconf、glom、bidict(+依赖) |
| **实验脚本(引擎)** | `run_benchmark.sh` | 参数化:每库 锚定→生成→评测(simplug 走 pilot,其余走 benchlib) |
| **快速有效性测试** | `run_quicktest.sh` | benchlib 新库上 B0 vs B4、少模型、1 轮 |
| **完整实验** | `run_full.sh` | 5 库 × 5 模型 × B0–B4 × 3 轮(60 任务) |
| 可视化 | `visualize_benchmark.sh` + `visualize_exec.py` | 自动发现 `exec_eval` 出图(method×{model,pair_type,difficulty}) |

**运行**(前置:Ollama 在 `localhost:11434`,模型已 pull;实验用能 import vendor 的解释器;可视化用有 matplotlib 的解释器,如 conda 的 `python`):
```bash
cd Ollama问题存在性实验
cd exec_oracle && python3 audit_injection.py && cd ..   # 0. 注入文本可执行性闸门
bash run_quicktest.sh                     # 1. 快速看 B4 是否在未见库上压过 B0/B1
bash run_full.sh                          # 2. 完整实验(可加 CLEAN=1 / RUNS=5)
VIZ_PY=python bash visualize_benchmark.sh # 3. 出图(须用有 matplotlib 的解释器)
# 单库 oracle 自检(无需 Ollama):cd exec_oracle && python3 benchlib.py glom
```
**扩展新任务/新库**:在 `lib_<lib>.py` 增 `FUNC_NAMES`/`INPUTS`/`CHECKS`/`ANCHORS`/`TASKS`(GOLD_PAIR_RULES 每条带 `Relation:` 标签以供分层 B4 按 pair_type 选取);新库仿 `fixture_<lib>.py`+`lib_<lib>.py`,须 `python3 benchlib.py <lib>` 锚定全绿 + `audit_injection.py <lib>` 通过方可交付。

---

## 8. 现有结果

### 8.1 simplug 存在性实验(完整 10 任务,执行口径)
**任务级 pair violation rate**:B0_direct 各模型 0.80–1.00(高违规);B4 降至 0.00–0.50。**运行级梯度** B0 0.0% → B1 11.1% → B2 16.7% → B3 25.6% → **B4 61.1%**。**B3 vs B4 McNemar 精确双侧 p≈9.4×10⁻⁷**。**静态 vs 执行(n=750)**:一致率 0.712、κ 0.459、209 例静过执挂——"必须用执行 oracle"的证据。

### 8.2 五库中间档(2 模型 qwen2.5:7b/qwen2.5-coder:7b,1 轮,分层 B4,任务级通过率)

| 库 | B0 | B1 | B2 | B3 | B4 | B4−B0 | B4−B1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| simpleconf(未见) | 0.03 | 0.44 | 0.11 | 0.22 | **0.69** | +0.66 | **+0.25** |
| glom(未见) | 0.15 | 0.60 | 0.25 | 0.70 | **0.85** | +0.70 | **+0.25** |
| simplug(未见) | 0.20 | 0.40 | 0.45 | 0.25 | **0.90** | +0.70 | **+0.50** |
| diot(中先验) | 0.71 | 0.83 | 0.83 | 1.00 | **1.00** | +0.29 | +0.17 |
| bidict(高先验) | 0.85 | 0.90 | 0.75 | 1.00 | 0.85 | +0.00 | −0.05 |

**读法(诚实)**:
- **严格单调 B0<B1<B2<B3<B4 不成立**:B2(原始文档)在多库回落(7B 被原始文档绕晕,贯穿所有库的稳健现象);B3 不稳。
- **核心规律稳固**:在**未见库**(simpleconf/glom/simplug)上 B4 明显最高,`B4−B1` 显著为正(+0.25~+0.50);在**高先验库**(bidict)上 `B4−B1≈0`——**收益与未见程度(B0)强相关**,这是比"B4 处处最优"更扎实的可发表结论。
> 产物:`result/{simplug_5model,diot_5model,simpleconf_5model,glom_5model,bidict_5model}/exec_eval/`。
> 注:这是 2 模型/1 轮的中间档(无多轮多数票,单点有方差);最终数以 `run_full.sh`(5 模型×3 轮)为准。

---

## 9. 局限与未来工作
- **completion-obligation 未覆盖**:需引入真实低流行度资源型库(连接/文件/会话)。
- **规模**:60 任务、5 类各 ≥11;可按真实约束扩到更大。
- **抽取评测**:实现自动抽取器并报告 precision/recall;gold 规则双人标注 + IAA。
- **最终全量待跑**:`run_full.sh`(5 库 × 5 模型 × B0–B4 × 3 轮);当前为 2 模型/1 轮中间档。
- **模型档位**:存在性实验仅 7–9B 本地模型,需补前沿模型。

---

## 10. 附录

### 10.1 失败原因码
`syntax_error`/`import_time_error`/`runtime_error`/`timeout`/`function_not_defined`→`exec_error`;`wrong_output`/`wrong_output_structure`/`no_score_call`/`wrong_enabled_set`→`wrong_behavior`;`state_not_restored`/`disable_not_persistent`/`mechanism_not_used`/`obligation_unmet`→`pair_state_violation`。

### 10.2 历史脉络
2026-06-12 执行 oracle 上线(P1)→ 06-13 taxonomy 扩到 6 类 → 06-14 通用 harness,先以流行真实库 msgspec/peewee/niquests 实测发现**强先验混淆**;改用自编合成库经复核发现**构造效度/循环性问题**;最终改用真实低流行度库(simplug/diot/simpleconf + pyparam),gold 规则从真实源码抽取 → **06-15**:① 发现并修复 simpleconf 裸调用 bug、simplug config-return B4 反降(分层 B4 + harness 按任务绑管理器)、测试隔离 bug,建立注入可执行性审计闸门;② **pyparam 因 B1 即满分(无组合缺口)退役**,**新增 glom(未见、提取域)与 bidict(高先验对照)**,主实验定型为 **5 库 60 任务**;③ B4 统一为**分层注入**(B1⊕该任务规则),核心指标改为 `B4−B1`。本文为权威说明。
