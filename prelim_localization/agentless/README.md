# Agentless 宿主实验（Task: 复现 Agentless + 投票 + 覆盖率过滤，crash·on-path）

计划见 `docs/实验计划_Agentless宿主_crash_onpath.md`。本目录 = P0..P5 的代码。

## Vendor（gitignored，`../agentless_vendor/`）
- `repo/` = Agentless 浅克隆（`git clone --depth 1 https://github.com/OpenAutoCoder/Agentless`）。
  两处本地改动（避免重依赖，不影响 `transfer_arb_locs_to_locs`）：
  - `agentless/util/parse_global_var.py` → 纯 AST stub（去 libcst）。
  - `get_repo_structure/get_repo_structure.py` → 注释掉 `import pandas/tqdm`（未用于展开）。
- `agentless_gpt4o_lite_loc_outputs.jsonl` = Agentless v0.1.0 释出的 GPT-4o SWE-bench-Lite 定位产物
  （300 题，`found_files`/`found_related_locs`/`found_edit_locs`；来自 release v0.1.0 `agentless_logs.zip::artifact/location/loc_outputs.jsonl`）。

## 指标（= Agentless Table 2，非 R@k）
`transfer_arb_locs_to_locs(context_window=10)` 展开 `line:N`→±10、`function:/class:`→整段，并集成候选集：
- **Contains-all**（superset，= Agentless "correct location"）：候选集 ⊇ 全部金标 (file,line)
- **Contains-any**：候选集 ∩ 金标 ≠ ∅（机制变体）
- **LoC**：候选集大小（精度/成本轴）

## P0 门（已过 2026-07-05）
`contains_gt_eval.py` 在全 300 上复现 Agentless Table 2：file-contains 82.7%（论文 81.7）、merged LoC 336（论文 342）、per-sample LoC 179（论文 165-213）、contains-all per-sample/merged 47/55%（论文 51-53/59；低 ~4pp 因我 gold 含插入锚点使 superset 更严）。**指标代码已验证。**

## 早期信号（覆盖率过滤挂 Agentless 产物，crash·on-path n=56）
`cov_filter_on_agentless.py`：
- AL：Contains-all 62.5 / any 85.7 / LoC 299
- AL+硬过滤(∩执行)：all **25.0**(−37.5) / any 83.9 / LoC 89(−70%) —— **硬过滤砸 superset**
- AL+frontier(执行∪±2)：all 57.1(−5.4) / any 83.9 / LoC 180(−40%) —— frontier 基本救回 superset
结论：superset 下覆盖率过滤须用 **frontier**；且 superset 的召回缺口要靠**投票**(未在此信号中，需本地 backbone)补回。any 口径下覆盖率是大精度赢（−70% LoC，−1.8pp）。
