# 真·ARISE 端到端 —— Windows 运行手册(最方便最快,无 GPU、无 vLLM、无隧道)

> 目标:在你的 Windows 机器上跑**真·agentic ARISE**(模型走 SiliconFlow API,DeepSeek-V3),产出每实例 top-k 定位 → 发给 Mac 端,由我跑 SPINE 叠加分析出决定性结果。
> 为什么 Windows:你已有 Docker Desktop 且 CPU 是 **x86_64**(SWE-bench 镜像原生跑,无模拟;Mac 跑不了只因为是 ARM)。

## 0. 前提(装一次)
- **Docker Desktop** 开着,且开了 **WSL2 集成**(Settings → Resources → WSL Integration → 勾上你的 Ubuntu 发行版)。
- **WSL2 Ubuntu** 终端(在里面能 `docker ps` 通)。**下面所有命令都在 WSL2 Ubuntu 里跑。**
- `uv`:`curl -LsSf https://astral.sh/uv/install.sh | sh` (装完 `source ~/.bashrc`)
- `git`;你的 SiliconFlow key。

## 1. 装 ARISE + SWE-agent(和我在 Mac 上验证过的命令一致)
```bash
mkdir -p ~/arise-run && cd ~/arise-run
git clone https://github.com/FARD-Lab/ARISE.git arise
git clone https://github.com/princeton-nlp/SWE-agent
cd arise
uv sync --extra eval --python 3.12
uv build                                    # 出 dist/arise-*.whl
uv pip install -e ../SWE-agent
uv run pytest tests/eval -q                 # 应 51 passed(验证打分口径)
# 同步 ARISE 工具 bundle 进 SWE-agent:
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

## 2. 先 smoke 1 题(确认 native 下能跑完并吐 LOCATIONS)
```bash
cd ~/arise-run/SWE-agent
export OPENAI_API_KEY=<你的 SiliconFlow key>
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
  --output_dir outputs/smoke
# 验收:outputs/smoke/<iid>/<iid>.traj 里有 assistant 消息含 LOCATIONS...END_LOCATIONS(native 下不会像 Mac 那样 shell EOF)
```

## 3. 正式跑(并行加速)—— 全 Lite-300 或 behav-132 子集
**方案 A(最省事,推荐):全 300**(顺带 sanity-check ARISE≈41,不用管子集对齐):
```bash
../arise/.venv/bin/python -m sweagent.run.run_batch \
  --config config/default.yaml --config ../arise/configs/arise.yaml \
  --config ../arise/configs/fl.yaml --config ../arise/configs/swe_bench_lite.yaml \
  --agent.model.name openai/deepseek-ai/DeepSeek-V3 \
  --agent.model.api_base https://api.siliconflow.cn/v1 \
  --agent.model.per_instance_cost_limit 0 --agent.model.max_input_tokens 60000 \
  --instances.num_workers 8 \
  --output_dir outputs/fl-300
```
**方案 B(只跑 SPINE 的 132,更快)**:把上面 `--instances.num_workers 8` 后加一行
`--instances.filter "$(cat behav132_filter.txt)"` —— 该 filter 文件我在 Mac 端已生成(`prelim_localization/runs/behav132_filter.txt`,132 个 id 的正则),同步过去即可。
> `--instances.num_workers 8` 是并行度(8 个实例并行,各自 Docker 容器)。机器内存够可提到 12-16。SiliconFlow 并发 OK(余额已恢复)。

## 4. 导出 top-k,发我
```bash
cd ~/arise-run/arise
../arise/.venv/bin/python - <<'EOF'
import json, sys; sys.path.insert(0,'.')
from evaluation.parse_preds import load_predictions_from_dir as L
preds = L("../SWE-agent/outputs/fl-300")     # 或 outputs/fl-132
json.dump({k:[list(t) for t in v] for k,v in preds.items()}, open("arise_preds.json","w"))
print("wrote arise_preds.json with", len(preds), "instances")
EOF
# 顺便存 ARISE 官方口径的 R@k(sanity-check 是否 ≈41):
../arise/.venv/bin/python evaluation/run_eval.py --traj-dir ../SWE-agent/outputs/fl-300 --output results_fl.json
cat results_fl.json    # 看 line_recall@1 是否 ~0.41
```
把 **`arise_preds.json`**(和 `results_fl.json`)发我。

## 5. 我这边(Mac,API,几分钟)
```bash
# 我跑:baseline(ARISE) vs baseline+SPINE vs baseline+random,官方打分 + McNemar
MODEL=deepseek-ai/DeepSeek-V3 python3 stack_arise_spine.py --preds arise_preds.json
```
→ 出 **ARISE-alone R@1 vs ARISE+SPINE R@1**(叠加结果)+ 随机控制。这就是决定性结果 → 选 Path 1/2/3/4。

## 注记
- **同模型是硬要求**:ARISE 用 DeepSeek-V3,我这边 SPINE 重排也用 DeepSeek-V3。
- 若 Windows 内存紧,`num_workers` 调小;Docker 磁盘留 50GB+(镜像用完 `remove_container: true` 自动删)。
- 若 WSL2 里 `docker` 不通:Docker Desktop → Settings → Resources → WSL Integration 打开对应发行版。
