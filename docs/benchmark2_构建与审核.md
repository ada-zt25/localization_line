# benchmark2 —— SWE-bench Verified crash·on-path 新基准（构建与审核）

> 2026-07-06。目的：在**独立于原有 57 例**（SWE-bench Lite）的一批数据上，验证方法在 **crash·on-path**
> 这一类问题上普遍有效。benchmark2 与原有 57 例（下称 **benchmark1**）用**逐字节相同的定义**构建，两者可直接比较。
> 代码全部在 `prelim_localization/newbench/`。

---

## 0. 一句话

从 **SWE-bench Verified (500)** 里，用与 benchmark1 **完全相同的谓词**筛出 crash·on-path 实例，且**只取
Lite/57 之外的 net-new 实例**（证明泛化，而非重复原集）。经 44-agent 对抗式审核确认严格对齐后，收集失败测试
覆盖率、按 on-path 冻结。

---

## 1. 定义（与 benchmark1 逐字节一致）

一个实例入选当且仅当**同时**满足：

| 谓词 | 实现（与 57 例同一份代码） | 说明 |
|---|---|---|
| **单一 .py 金标文件** | `p0.parse_patch(patch)` 中 `.py` 金标文件数 == 1 | 与 `cov_refine_eval.run_instance` 一致 |
| **code_gold 非空** | `p0.clean_gold(region, src)` 非空 | 去空行/注释/纯标点，只留真实代码行 |
| **crash（is_crash 规范版）** | `Traceback (most recent call last)` ∨ ≥2 个 `File "..",line N` 帧 ∨ test_patch 含 `pytest.raises\|assertRaises\|with raises\|.raises(` | 与 `rq4/freeze_subsets.py` 字符级相同 |
| **on-path** | `code_gold ∩ 失败测试执行行 ≠ ∅` | `cov_collect.collect` 收覆盖，`cov_for` endswith 匹配，与 57 例同 |

**关于 `code_gold`（原 `arise_gold`）**：这是"金标只算真实代码行"的归一化。保留它的两个理由**都与 ARISE 无关**：
① 与 benchmark1 逐字节一致，两基准才可比；② 行级定位本就不该把空行/注释锚点算作"要改的行"。历史脚注：清洗规则最早
对齐过 ARISE，但 **ARISE 已不是我们的基线，也不是保留它的依据**。底层 `p0.clean_gold` 未改动（与 57 例共用）。

**金标来源**：金标行来自**真实修复补丁**（`row.patch`，当年合入的 PR/commit），**不是** issue 文本。issue 只是
自然语言 bug 报告，不指明改哪几行。

---

## 2. 数量（零 Docker 扫描 → 审核）

Verified 500 → 单 .py 金标 430 → `+is_crash` 101 → **`+code_gold` 非空 = 99 candidates**。
其中 **76 net-new**（不在 Lite 池、也不在 57 例内），23 与 Lite 重叠（覆盖率已缓存）。

**回归门（防漂移）**：同一份谓词跑 Lite，重新选出全部 **57/57**（`audit_candidates.py` 从原始 row 重新推导，
非读回子集）。

---

## 3. 对抗式严格对齐审核（workflow `wf_e08f116c-efa`，44 agents）

| 维度 | 结果 |
|---|---|
| **代码对齐** | ✅ `is_crash` 正则与 `freeze_subsets.py` **字符级相同**；回归门 57/57；无漂移 |
| **on-path 对齐** | ✅ 从 Lite 覆盖率**重现 57/57** on-path（raw-region 与 code_gold 两种口径，0 分歧）|
| **数据完整性** | ✅ 76 net-new，**0 泄漏**进 57/Lite，全部单 .py 金标、字段完整、无重复 |
| **crash 语义** | 19 例送对抗复核：14 例两视角一致为真崩溃；4 例边界（保留）；**1 例一致判误报（剔除）** |

**唯一剔除 —— `django__django-9296`**（用户 2026-07-06 决定）：纯 feature request（给 Paginator 加 `__iter__`），
修复只是新增方法、不阻止任何异常；`is_crash` 只因**无关的未改动上下文行** `with self.assertRaises(EmptyPage):`
命中，真正新增的测试无任何 raises、无 traceback、无 error。两个对抗视角一致 2/0 判 exclude。

**处理原则（用户选择"只剔 1 例明确误报"）**：`is_crash` 是**纯语法正则**，其误报模式（assertRaises 命中无关上下文行 →
收进非崩溃 bug）是**benchmark1 与 benchmark2 共享定义的固有性质**——57 例内同样存在（如 sympy-12419 / xarray-3364，
按同一模式被保留）。为保持与 57 例可比，**不对 57 例重新过滤**；benchmark2 仅剔除唯一被一致确认的误报。这一
不对称是**显式披露的**取舍。→ **benchmark2 crash-half = 75**。

---

## 4. 覆盖率与冻结（最终结果）

- 收集：`collect_verified_cov.py`（官方 SWE-bench Docker 镜像，失败测试在 `coverage` 下跑；与 57 例同一收集器
  `cov_collect.collect`）。可断点续跑，逐实例 checkpoint 到 `verified_cov_cache.json`。
- 冻结：`freeze_benchmark2.py` **只在** `code_gold ∩ coverage ≠ ∅` 时把实例收进 `benchmark2_crash_onpath`；
  off-path / 无覆盖的实例路由到透明清单（`_crash_offpath` / `_crash_nocov`），**绝不混入**。

**最终 `benchmark2.json`（75 crash-half）：**

| 类别 | n | 处置 |
|---|---|---|
| **crash·on-path** | **61** | ✅ benchmark2 交付集 |
| crash·off-path | 5 | 排除（跑了真实测试、gold 未被执行 = 守卫/分支插入型，与 bench1 的 11 例 off-path 同类）|
| crash·no-cov | 9 | 排除（子进程型测试无法收覆盖，与 bench1 的 7 例 no-cov **同仓库同机制**）|

- on-path 仓库分布：django 32 / astropy 7 / sympy 6 / matplotlib 5 / scikit-learn 3 / psf 2 / pydata 2 /
  pylint-dev 2 / mwaskom 1 / pallets 1。crash-rule：traceback 36 / raises 22 / frames≥2 3。
- **与 benchmark1(57) 合并 = 118 crash·on-path**（benchmark2 独立集 61 本身已 > 57，作 held-out 泛化集；合并
  补足原 n=57 统计功效）。

### 4.1 ⚠️ 收集期修复的两个覆盖率 bug（`cov_collect.py`；on-path 标签仅在修复后有效）

抓这两个 bug 很关键——不修的话 benchmark2 会被严重**低估**（大量真 on-path 被误判 off-path）：

1. **新版 Django boot-only**：`coverage run ./tests/runtests.py` 无法 import `test_sqlite` 设置（老版 Django
   自己把 `tests/` 塞进 sys.path，新版依赖 `sys.path[0]`，而 `coverage run` 设置方式不同）→ runtests 在 setup
   阶段中止 → **测试体从未运行，只录到 Django 启动期覆盖**（196 个跨 bug 完全相同的文件，Jaccard≈1.0）→ 约 20
   例 Django **被误判 off-path**。**修复**：`cov_collect._test_cmd` 加 `env PYTHONPATH=/testbed/tests`（并让
   `_is_testfile` 识别 Django 的 `tests.py`，剔除 fixture 文件当成的伪 label）。**实测**：django-16100
   196→371 文件 gold 9/10 ON-PATH；django-14007 198→341 gold 3/10 ON-PATH；共 17/20 翻转为 on-path。
2. **pytest files=0**：部分实例在 4-worker Docker 争用下容器失败（非命令 bug；低并发重收即恢复，如 flask-5014
   串行=ON-PATH）。剩余 9 例（pytest-dev×3 / scikit-learn×4 / sphinx×2）**串行仍 files=0**——因这些测试在
   **子进程**里跑被测代码（pytest 的 `pytester`、sklearn 的 joblib 并行、sphinx 的 build 子进程），`coverage run`
   在父进程看不到 → 归入 no-cov。**这与 bench1 完全一致**：bench1 的 7 例 no-cov 正是 pytest-dev×2 + scikit-learn×4
   + sympy×1，同仓库同机制。故排除它们 = 与 57 例逐字节同口径，非 benchmark2 特殊处理。

---

## 5. 诚实边界（与 benchmark1 同源，披露不修）

- **oracle 嫌疑覆盖率**：覆盖率取自应用 test_patch 后跑 FAIL_TO_PASS；若该测试是补丁新增且直接命中金标区域，覆盖
  率对金标有 oracle 倾向。与 57 例同一机制。
- **1 行边界脆弱**：57 例中 13 例仅靠 1 行被执行的金标判为 on-path；覆盖率漂移（镜像/coverage 版本/并行度）可能翻转。
  故**冻结固定覆盖率产物、不重采**。
- **cov_for basename 回退**：endswith/basename 回退按 dict 顺序首个命中，同名文件可能绑错覆盖；与 57 例同一实现。

---

## 6. 文件索引（`prelim_localization/newbench/`）

| 文件 | 作用 |
|---|---|
| `newbench_scan.py` | 从数据集挖 crash 候选（STAGE A，零 Docker）|
| `audit_candidates.py` | 从原始 row 重推全部谓词 + 回归门 → `audit_crash_half.json` |
| `make_bundle.py` | 全证据离线包 `audit_bundle.json`（审核用）|
| `curate_crash_half.py` | 应用审核裁决 → `benchmark2_crash_half.json`（75 confirmed + 1 excluded + provenance）|
| `collect_verified_cov.py` | Docker 收覆盖率（STAGE B，续跑）→ `verified_cov_cache.json` |
| `freeze_benchmark2.py` | on-path 门冻结 → `benchmark2.json` |

**下一步（覆盖率跑完后自动）**：`python newbench/freeze_benchmark2.py` → 得 benchmark2 crash·on-path 最终 n；
随后在 benchmark2（及合并 n≥120）上重跑 A0–A3 覆盖率精细化实验（见 `docs/覆盖率精细化_on-path方法与实验.md`）。
