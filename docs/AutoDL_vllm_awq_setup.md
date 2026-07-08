# AutoDL 上自建 vLLM 服务 Qwen2.5-Coder-32B-AWQ(ARISE 的 EXACT backbone)

> 用途:当要复现 ARISE 的 EXACT 41(它的 backbone 是 Qwen2.5-Coder-32B-Instruct-AWQ,SiliconFlow 没有此模型)时,自建 vLLM。SPINE 侧和 ARISE 侧都指向这个 endpoint(同模型对比)。
> ⚠️ 血泪教训全在这:CUDA 版本、无卡模式、无 Docker、隧道。**照做,别自作聪明降版本。**

## 0. 租卡
- **A800-80G 或 A100-80G**(要并行 → 80G,KV cache 大)。AWQ-32B 权重 ~20G,80G 富余。
- 镜像:官方 **PyTorch 2.x + CUDA 12.x/13.x**。开机后 `nvidia-smi` 看**右上角 `CUDA Version`**(= 驱动支持的最高 CUDA,决定用哪个 vLLM,见 §2)。

## 1. 下载模型(ModelScope,国内快,~20G)
```bash
pip install -U modelscope
cd /root/autodl-tmp     # 数据盘,持久
modelscope download --model Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
  --local_dir /root/autodl-tmp/qwen25coder32b-awq
ls /root/autodl-tmp/qwen25coder32b-awq   # 应有 5 个 *.safetensors + config/tokenizer
```

## 2. ⭐ 装 vLLM —— 必须匹配驱动的 CUDA(最大的坑)
`pip install -U vllm` 会装**最新 vLLM(如 0.24)+ torch cu130(CUDA 13)**。**如果驱动 CUDA < 13,会 `cuda False`。**
```bash
# 建干净 conda 环境(别在 base 乱装/乱卸 nvidia 库,会误删 libcusparseLt)
conda create -n vllm python=3.11 -y && conda activate vllm
export OMP_NUM_THREADS=8
```
- **驱动 CUDA 13.0** → 用最新:`pip install -U vllm`(0.24,torch cu130)。**别降到 cu128,会 "no NVIDIA driver"。**
- **驱动 CUDA 12.x** → 降到 cu12 版:`pip install "vllm==0.11.0"`(torch 2.8+cu128)。
- 验证(**必须 cuda True**):
```bash
python -c "import torch; print(torch.__version__, '| cuda', torch.cuda.is_available())"
```

## 3. ⚠️ 若 `cuda False` 但 torch 版本对了 → 检查"无卡模式"
```bash
nvidia-smi
```
- 报 `No devices found` / `couldn't communicate with driver` → 你是 **AutoDL 无卡模式**(下模型/装环境用的省钱模式,没 GPU)。
- **修**:AutoDL 控制台 → **关机** → **正常开机(带卡)**,别点"无卡模式开机"。数据盘不丢。

## 4. 起 vLLM 服务(端口 8002)
```bash
conda activate vllm; cd /root/autodl-tmp
pkill -9 -f vllm 2>/dev/null; sleep 3
nohup env VLLM_USE_FLASHINFER_SAMPLER=0 OMP_NUM_THREADS=8 python -m vllm.entrypoints.openai.api_server \
  --model /root/autodl-tmp/qwen25coder32b-awq \
  --served-model-name Qwen2.5-Coder-32B-Instruct-AWQ \
  --quantization awq_marlin --tensor-parallel-size 1 \
  --max-model-len 32768 --gpu-memory-utilization 0.92 --port 8002 > ~/vllm.log 2>&1 &
tail -f ~/vllm.log   # 等 "Application startup complete."(Ctrl+C 退出 tail,服务继续)
```
建议在 `tmux`(`tmux new -s vllm` → 跑 → `Ctrl+b d`)里起,防 SSH 断连。

## 5. 验证
```bash
curl -s http://127.0.0.1:8002/v1/models
curl -s http://127.0.0.1:8002/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"Qwen2.5-Coder-32B-Instruct-AWQ","messages":[{"role":"user","content":"reply OK"}],"max_tokens":5}'
```

## 6. 从外部机器用这个 endpoint(隧道)
- **AutoDL 没 Docker**(非特权容器)→ ARISE 的 SWE-agent 不能在 AutoDL 跑;要在有 Docker 的 x86_64(你的 Windows)上跑,隧道进来。
- **隧道坑**:AutoDL 代理会掐纯 `-N` 隧道(从某些客户端)。从**你自己机器**(Windows,带命令的会话)通常 OK:
```bash
# 在你 Windows(WSL2)/本机,AutoDL 控制台查 SSH 端口:
ssh -CNL 8002:127.0.0.1:8002 -p <端口> root@connect.nma1.seetacloud.com
# 之后本机 OPENAI_API_BASE=http://localhost:8002/v1，OPENAI_API_KEY=dummy
```
- ARISE(SWE-agent)/ SPINE 的模型参数:`openai/Qwen2.5-Coder-32B-Instruct-AWQ` + `api_base=http://localhost:8002/v1`。

## 7. 成本 / 保活
- 自建 vLLM 推理**免费无限**(只付 GPU 租金,A800-80 约 ¥7/时)。
- 实例**只关机别 release**;数据盘 `/root/autodl-tmp` + 模型持久,重开即用。
