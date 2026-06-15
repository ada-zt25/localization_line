# exec_oracle — Execution-based hidden-test oracle (P1)

把存在性实验的主指标从"自写 AST checker"换成**对真实 simplug 库的执行隐藏测试**,消除"注入规则 = 检查规则"的循环 oracle 问题。

## 组成

| 文件 | 作用 |
|---|---|
| `vendor/` | 逐字 vendored 的真实依赖:simplug **0.5.7**(实验对象库)、diot 0.3.4、inflection 0.5.1。来源:GitHub 上游仓库对应 tag/master,未做任何修改(沙箱无法访问 PyPI 才采用 vendor 方式;在能联网的机器上 `pip install simplug==0.5.7` 等价) |
| `fixture_simplug.py` | 提示词承诺的 `make_score_manager()`,带运行时插桩:记录每次 `hooks.score` 调用时的 enabled 集合与转发值、直接的 `get_plugin`/`wrapper.disable()` 调用、`sp.disable/enable`、`plugins_context` 入参。每次调用使用唯一 project 名(simplug 按名单例) |
| `hidden_tests.py` | 6 个任务的隐藏测试:只消费 (返回值, 运行时迹, 调用后各 manager 的 enabled 终态),从不看源码。细粒度失败原因 → 粗类:`exec_error` / `wrong_behavior` / `pair_state_violation` |
| `exec_runner.py` | 子进程 runner:一份生成代码一个进程(隔离崩溃/挂起),verdict 写 JSON 文件(不经 stdout) |
| `anchor_solutions.py` | 锚定套件 28 例:每任务的 canonical 正确解、**静态 checker 必误判的语义等价变体**(`-alpha`/`-gamma` 减号模式、手动 disable/enable 还原等)、每类已记录违规模式(必须以预期原因失败) |
| `run_exec_eval.py` | 编排:先跑锚定(不绿不评模型),再并发评估全部已保存生成,产出 `exec_eval/`(结果 CSV、与静态 checker 的混淆矩阵/一致率/κ、分歧清单、汇总 md/json) |

## 用法

```bash
cd exec_oracle
python3 run_exec_eval.py --anchors-only          # 仅验证 oracle 本身
python3 run_exec_eval.py                         # 锚定 + 450 份全量重评(~6s, --jobs 8)
python3 run_exec_eval.py --result-dir <其他结果目录>
```

输出落在 `<result-dir>/exec_eval/`:`exec_results.csv`、`exec_summary.md`、`exec_summary.json`、`disagreements.csv`、各 verdict JSON;锚定报告在本目录 `anchor_report.json`。

## 隐藏测试判据(从任务文本导出,与注入规则无关)

每个任务用两个测试值(5、11)分别运行,均须通过:

- T001/T002:返回值 == 仅 {beta}/{alpha,gamma} enabled 时的 hook 结果;迹中存在该 enabled 集合且值正确的 score 调用;函数返回后该 manager 状态**恢复**为三者全 enabled("temporarily")。
- T003/T006:返回值与 score 时 enabled 集合同上({alpha,gamma}/{beta});disable 是**持久**的——函数返回后被禁插件仍处禁用态。
- T004:T003 的行为 + 任务规定的机制在运行时可观察:同一 manager 上,合格 score 调用之前出现直接 `get_plugin("beta")` 且其返回 wrapper 的 `.disable()` 被调用(return-flow 对的运行时证据)。
- T005:返回二元组;第一个结果在 enabled=={beta} 下收集、第二个在三者全 enabled 下收集,先后次序与同一 manager 约束;结束时状态恢复。

插件 score 实现按值单射(`alpha→(“alpha”,v+1)`、`beta→(“beta”,2v)`、`gamma→(“gamma”,v−3)`),结果列表唯一决定"哪些插件以哪个值运行过"。

## 语义实证(vendored 0.5.7 源码 + 运行验证)

gold pair rule 描述的确为真库行为:无前缀字符串列表 = only 模式且退出恢复;传插件**对象** = 仅 enable(不进入 only 模式)→ 行为级可观察失败;`disable(name)` 持久;对象传给 `disable/get_plugin` → `NoSuchPlugin` 运行时异常;hook 支持位置参数;结果按注册序收集。

## 扩展到新任务/新库

新任务:在 `hidden_tests.py` 注册 `FUNC_NAMES`/`CHECKS`,在 `anchor_solutions.py` 给出 canonical+变体+违规锚定;新库:仿 `fixture_simplug.py` 写带迹插桩的 fixture。锚定套件不绿,评估拒绝运行——这是 oracle 可信度的硬门槛。
