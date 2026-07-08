# RQ4 并行化 + 防掉线 运行手册（A800-80G）

## 0. 一句话
**全部在 A800 机器上、tmux 里、调本地 vLLM 跑**；掉的是 SSH 隧道、不是实验。每个子run 断点续跑。监控只用**一条**常驻连接（`cat STATUS.txt` / `tail -f run.log`），**绝不反复重连**（历史上把 AutoDL 网关打限流了）。

## 1. 开机后三步
```bash
# ① 起 vLLM（若开机脚本没自动起）——ARISE 同 backbone
python -m vllm.entrypoints.openai.api_server \
  --model <Qwen2.5-Coder-32B-Instruct 权重路径> --served-model-name Qwen2.5-Coder-32B-Instruct \
  --port 8000 --max-model-len 16384 --gpu-memory-utilization 0.92 &     # A800-80G 单卡放得下 bf16 32B

# ② 打补丁/同步代码（见 §4）——把 rq4/ + 改过的 egl_e2e.py/region_loc.py + egl_cov_cache.json 同步到机器
# ③ 一键起跑（tmux，掉线不死）
bash prelim_localization/rq4/launch.sh
```
监控：`cat prelim_localization/rq4/results/STATUS.txt`（30s 心跳）｜`tail -f .../run.log`｜`tmux attach -t rq4`。

## 2. 并行化设计（哪里并行、为什么快）
| 层 | 机制 | 设定 | 说明 |
|---|---|---|---|
| **LLM 实例级** | `egl_e2e --workers`（线程池打 vLLM） | `RQ4_WORKERS=24` | vLLM 连续批处理，并发越高吞吐越高；按 GPU 利用率调（A800 单卡 32B 建议 16–32）|
| **vote 采样** | 每实例 k=5 采样仍是顺序 | k=5 | 在 vLLM 端被其它实例的并发填满，不浪费 |
| **Docker 覆盖** | `--cov-workers` 并行 | `RQ4_COV_WORKERS=6` | **S1 全部已缓存→基本跳过**；只在缓存缺失时触发 |
| **跨臂复用** | 一次 vote pass 出 5 个臂 + `--dump-substrate` | — | **关键省 GPU**：M0/M3/anchors 一趟出；M1(filter) 离线从 substrate∩coverage 推 |
| **file-loc 复用** | 赢家 file-loc 在 S1 跑一次 → `--reuse-files` 喂两个 pass | — | file-loc 跨 M0..M4 恒定，且只算一次 |

**GPU 工作量（过夜级，实际很小）**：
- Task1 file-loc 扫 3 配置 × n=300（k=1，line-loc 便宜）≈ 主要成本。
- Task2：file-loc(S1=57) 1 趟 + PASS_A(57) + PASS_B(57) = 3 趟 ×57 实例。
- 合计远小于一次 n=300 全方法跑。A800 单卡过夜绰绰有余。

## 3. 防掉线设计
- **tmux**：`launch.sh` 把整条 `fileloc→e2e→sig→verify` 放进 tmux 会话 `rq4`，SSH 掉了进程继续。
- **热路径无隧道**：LLM 调 `127.0.0.1:8000` 本地 vLLM；隧道只用于你看日志。隧道断 ≠ 实验断。
- **断点续跑**：每个 `egl_e2e --out X.json` 每实例写盘、跳过 `done`；`run_all` 跳过已 `summary` 的子run。中断后**重跑同一条 `launch.sh` 即继续**。
- **心跳**：`results/STATUS.txt` 每 30s 一行（时间+最后日志），`tail` 一条连接即可；完成写 `results/DONE.txt`。
- **致命错误自停**：余额/鉴权 403 → egl_e2e 抛 `FatalAPIError` 直接停（不空转烧钱），充值后重跑续。

## 4. 要打的补丁（开机后同步到 A800）
**代码（已在本地改好，随 rq4/ 一起带过去）**：
1. `egl_e2e.py` —— 新增 `--instances`（锁 S1）、`--cov-narrow`（M2）。✅已改
2. `region_loc.py` —— `_make_region` 加 `cov_narrow`（region∩executed 再投票）。✅已改
3. `rq4/`（新目录）—— `config.py / run_all.py / launch.sh / guardrails_hook.sh / freeze_subsets.py / lineloc_offline.py / frozen_subsets.json / RQ4_SPEC.md`。✅已建
**数据**：`egl_cov_cache.json`（覆盖率缓存，S1 全靠它免 Docker）必须在机器上；不在就先 `--prefetch-coverage`（会跑 Docker，慢）。
**待办补丁（Task1 冲 ≥90，可选）**：`swerank_loc.py` + `egl_e2e` 加 `--file-loc swerank`（SweRankEmbed-Large，函数级检索→max 聚到文件）。诚实预期 file R@10~0.92–0.94 / R@5~0.90–0.93 / R@1~0.70–0.80。先用现有 agentless+rerank/arise-agentic 扫，达不到 67/82 再上 swerank（见 `docs/文件定位_冲90方案.md`）。

## 5. 同步命令（示例，按你的 AutoDL 路径改）
```bash
# 本地 → A800（一条 rsync，省得反复 scp）
rsync -avz --include='rq4/***' --include='egl_e2e.py' --include='region_loc.py' --include='egl_cov_cache.json' \
  prelim_localization/ root@<host>:~/prelim_localization/
```
（或 git push + 机器 git pull；注意 `prelim_localization/` 当前未纳入 git，见 docs/memory.md §0）

## 6. 跑完看什么
- `results/lineloc_e2e.json` → M0..M4 的 line R@{1,5,10}（RQ4 主表）。
- `results/significance.json` → **M4−M0 的 bootstrap CI**（主结论：CI 下界>0 = 显著）。
- `results/fileloc_sweep.json` → Task1 file R@k 是否 ≥67/82。
- 对照：`config.ARISE_REF` 41/62/74（全300，外部参照，口径不同）；离线天花板 filter=43.9。
