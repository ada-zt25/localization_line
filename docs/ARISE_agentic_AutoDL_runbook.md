# 真·agentic ARISE 端到端复现 + SPINE 对比 —— AutoDL 运行手册

> 2026-07-08。**结论:真·agentic ARISE 不需要 GPU,但需要 native x86_64 Linux 主机。**
> 在 arm64 Mac 上已把整套装通并验证(config 兼容、model→SiliconFlow 通、ARISE 工具在 ReAct 循环里被调用),但 **SWE-bench 镜像是 x86_64,Mac 上走 qemu 模拟 → SWE-ReX 持久 shell 的亚秒级 PS1 超时扛不住 → shell EOF**(STEP 1 就挂,系统性、非偶发)。
> **AutoDL 是 x86_64 Linux,镜像原生跑,无模拟 → shell 稳定。模型仍走 SiliconFlow API → 全程无 GPU。**

## 0. 为什么 AutoDL 而不是本地
- 需要:**native x86_64 Linux + Docker**(AutoDL 满足)。
- **不需要 GPU**:LLM 走 SiliconFlow API(`OPENAI_API_BASE`)。GPU 只在"本地 vLLM 起模型"那条路才要,我们不走。
- 已在 Mac 验证的部分(直接搬):ARISE 装好、51 eval 测试过、wheel 编好、SWE-agent 1.1.0 装好、configs 兼容、litellm→SiliconFlow 通、ARISE 工具在 agent 循环里正常调用。唯一挂点=模拟 Docker 的 shell,AutoDL 无此问题。

## 1. AutoDL 环境准备
```bash
# 前提:AutoDL x86_64 实例,Docker 可用(docker ps 通),已装 uv
docker ps                                   # 必须通
curl -LsSf https://astral.sh/uv/install.sh | sh   # 若无 uv
# 传代码:把本仓库 vendor/ARISE + vendor/SWE-agent 打包上传,或直接 clone:
git clone https://github.com/FARD-Lab/ARISE.git arise
git clone https://github.com/princeton-nlp/SWE-agent
```

## 2. 装 ARISE + SWE-agent(与 Mac 上完全一致,已验证)
```bash
cd arise && uv sync --extra eval --python 3.12 && uv build      # 出 dist/arise-*.whl
uv pip install -e ../SWE-agent                                  # 装 SWE-agent 到同 venv
uv run pytest tests/eval -q                                     # 应 51 passed(验证 gold.py/metrics.py)
# 同步 ARISE 工具 bundle 进 SWE-agent(README §3 的 python 片段):
cd ../SWE-agent && ../arise/.venv/bin/python - <<'EOF'
import arise, shutil, pathlib, glob
pkg=pathlib.Path(arise.__file__).parent
for s,d in [("swe_agent_bundle","tools/arise"),("swe_agent_bundle_tier1","tools/arise-tier1"),
            ("swe_agent_bundle_tier2","tools/arise-tier2"),("swe_agent_bundle_coarse","tools/arise-coarse"),
            ("swe_agent_bundle_explain","tools/arise-explain")]:
    shutil.copytree(pkg/s, d, dirs_exist_ok=True)
whl=sorted(glob.glob("../arise/dist/arise-*.whl"))[-1]
for d in ["tools/arise","tools/arise-tier1","tools/arise-tier2","tools/arise-coarse","tools/arise-explain"]:
    shutil.copy(whl, d)
print("bundles synced")
EOF
```

## 3. 跑真·ARISE-Full 定位(FL),模型=SiliconFlow DeepSeek-V3(与 SPINE 同模型)
```bash
cd SWE-agent
export OPENAI_API_KEY=<你的 SiliconFlow key>      # 就是 prelim_localization/.key
# 先 smoke 1 题(native 下应能跑完 40 轮并吐 LOCATIONS 块):
../arise/.venv/bin/python -m sweagent.run.run_batch \
  --config config/default.yaml \
  --config ../arise/configs/arise.yaml \
  --config ../arise/configs/fl.yaml \
  --config ../arise/configs/swe_bench_lite.yaml \
  --agent.model.name openai/deepseek-ai/DeepSeek-V3 \
  --agent.model.api_base https://api.siliconflow.cn/v1 \
  --agent.model.per_instance_cost_limit 0 \
  --agent.model.max_input_tokens 60000 \
  --instances.slice :1 \
  --output_dir outputs/smoke-fl
# 验收:outputs/smoke-fl/<iid>/<iid>.traj 里有 assistant 消息含 LOCATIONS...END_LOCATIONS
# 通过后全量(300 Lite)或指定子集:去掉 --instances.slice(全量),或用 --instances.slice ":132" 等。
#   注:为与 SPINE 的 behavioral-132 对齐,理想是同 132 实例;SWE-agent 的 swe_bench 源按 slice 取,
#   如需精确 id 子集,用 --instances.filter '正则' 或自建 instances json(见 SWE-agent 文档)。
```
关键参数:`per_instance_cost_limit 0`(SiliconFlow 模型 litellm 不知定价,cost 计算会报错,置 0 绕开);`max_input_tokens 60000`(DeepSeek-V3 上下文)。轮数上限在 `fl.yaml`(40)。

## 4. 评测(ARISE 官方口径 → line/file/func R@k)
```bash
cd ../arise
python evaluation/run_eval.py \
  --traj-dir ../SWE-agent/outputs/smoke-fl \
  --output results_fl.json
# 输出 line_recall@{1,5,10}, file_recall@{1,3,5}, func_recall@{1,3,5}+MRR+F1, line_iou —— 这就是真·ARISE 在 DeepSeek-V3 上的端到端定位数。
```
> 数字不会是 41/62/74(那是 Qwen-32B-AWQ),但这是**真·ARISE 系统在 DeepSeek-V3 上**的端到端结果,与 SPINE 同模型可比。

## 5. SPINE 端到端(同模型、同口径),做对比
- SPINE 侧**能在本地 Mac 跑**(它用 non-interactive `docker exec` 取覆盖率,不用 SWE-ReX 持久 shell,我的 repair 实验已证通),但为口径统一建议也在 AutoDL 上跑。
- 端到端:file-loc(SweRankEmbed 或 agentless)→ SPINE 行定位 → 汇总成 `(file,function,line)` 排序预测 → **用 ARISE `src/arise/eval/{gold.py,metrics.py}` 打分**(不是 clean_gold!见 [去oracle_端到端对标_ARISE官方.md](去oracle_端到端对标_ARISE官方.md))。
- 需要一个适配器把 SPINE 的排序行转成 ARISE 的 prediction 格式 + 调 `metrics.compute_all_metrics`。

## 6. 对比产出
| 系统(同 DeepSeek-V3,同 132/300,同 ARISE gold.py 打分) | line R@1/5/10 | file R@1 | func R@1 |
|---|---|---|---|
| 真·ARISE-Full(agentic) | (跑出来填) | | |
| 我方 file-loc + SPINE(端到端) | (跑出来填) | | |

这就是你要的 **真·agentic ARISE vs SPINE 端到端对比**,同模型、同口径、无 GPU。

## 7. 注记/风险
- **成本**:agentic 每题 ~40 轮 ReAct;300 题是笔 SiliconFlow token 账(但无 GPU)。可先 30-50 题小样本。
- **Docker**:SWE-agent 每题拉 x86_64 镜像(AutoDL 原生,快);`remove_container: true` 用完即删。
- Mac 侧遗留:`vendor/{ARISE,SWE-agent}` 已装好可参考;`smoke-fl*` 输出可删。
- 若 AutoDL 也偶发 shell 问题,提高 `agent.tools.execution_timeout`(现 900)或 SWE-ReX 超时。
