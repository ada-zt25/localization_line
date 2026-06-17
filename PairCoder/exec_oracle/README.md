# exec_oracle — 执行式隐藏测试 oracle + 抽取(B5)

把成对组合约束的判分从"自写 AST checker"换成**对真实 vendored 库的执行隐藏测试**(只看可观察行为,不读源码),消除"注入规则 = 检查规则"的循环 oracle。6 个库统一跑在通用 `benchlib` 引擎上。

## 库(6 个,全部真实 vendored、纯本地)

| 库 | 版本 | 领域 | 角色 |
|---|---|---|---|
| simplug | 0.5.7 | 插件/扩展 | 主(未见) |
| diot | 0.3.4 | 属性字典 | 主(中先验) |
| simpleconf | 0.9.3 | 分层配置 | 主(未见) |
| glom | 25.x | 嵌套提取 | 主(未见) |
| bidict | 0.23.x | 双向映射 | 高先验对照 |
| sqlitedict | 2.1.0 | 持久化存储 | **completion-obligation 第 6 类** |

`vendor/` 不入库,用 `pip install --target vendor <6 个库固定版本>` 重建(见 `docs/PairCoder_Benchmark.md` §3.3)。

## 组成

| 文件 | 作用 |
|---|---|
| `benchlib.py` | 通用判分核心 `evaluate_source`(deepcopy 隔离)+ 锚定运行器 `run_anchors`。命令 `python3 benchlib.py <lib>` 跑某库锚定门槛 |
| `benchlib_generate.py` | 任意库的 B0–B4 提示生成(Ollama),B4 按任务分层注入 |
| `benchlib_eval.py` | 锚定门控 → 子进程全量判分 → 按 method×pair_type×difficulty 切片出 `exec_summary.md` |
| `benchlib_runner.py` | 单份生成的子进程隔离判分(崩溃/挂起隔离,verdict 写 JSON) |
| `lib_<name>.py` | 各库的统一接口:`make_namespace`/`FUNC_NAMES`/`INPUTS`/`CHECKS`/`ANCHORS`/`TASKS`/`GOLD_PAIR_RULES`/`API_LIST`/`RAW_API_DOCS`/`ORACLE_API_SEQUENCES`/`HELPER_LINE` |
| `fixture_<name>.py` | 各库执行夹具(真实库对象 + 运行时插桩 / 临时资源) |
| `hidden_tests.py`、`anchor_solutions.py` | simplug 的判据与锚定(由 `lib_simplug.py` 复用,封装进 benchlib 接口) |
| `audit_injection.py` | 上线前注入文本可执行性闸门:`python3 audit_injection.py`(默认审计 6 库) |
| `pair_extractor.py` | **B5 抽取算子 Φ**:6 通道检测 + noisy-OR + 判别式 typed 得分 + Platt/LOLO 校准 + 规则合成 |
| `eval_extraction.py` | **RQ1**:抽取 vs gold 的 P/R/F1、关系混淆矩阵、precision–coverage 曲线(6 库一体脚本) |
| `b5_feedback.py` | **闭环 B5**:失败归因(κ 逆映射)+ 类型化精修 + Beta 置信度;`--simulate` / `--explain-failures` 离线模式 |

## 用法

```bash
cd exec_oracle
python3 benchlib.py glom                  # 单库锚定自检(无需 Ollama)
python3 audit_injection.py                # 注入文本可执行性闸门(6 库)
python3 pair_extractor.py --all           # B5 抽取(原始分)
python3 eval_extraction.py --emit ../result/extraction_eval   # RQ1:P/R/F1 + 曲线
python3 b5_feedback.py --explain-failures --lib bidict        # 真实失败归因
```
全量实验(需 Ollama)从仓库根 `bash run_full.sh`(6 库×5 模型×B0–B4×3 轮)。

## 锚定(可信度硬门槛)

判分前过锚定:canonical 正确解 + 静态会误判的语义等价变体 **必过**;每类违规模式 **必挂**且 reason 符合预期。不全绿则评估拒绝运行。当前全过:**simplug 42 / diot 25 / simpleconf 36 / glom 20 / bidict 20 / sqlitedict 10 = 153 例**。

## 扩展新库

仿 `lib_<name>.py` + `fixture_<name>.py` 填 `FUNC_NAMES/INPUTS/CHECKS/ANCHORS/TASKS`(GOLD_PAIR_RULES 每条带 `Relation:` 标签以供分层 B4)。须 `python3 benchlib.py <lib>` 锚定全绿 + `audit_injection.py <lib>` 通过方可交付。
