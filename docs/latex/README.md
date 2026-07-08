# Overleaf 编译说明

## 上传到 Overleaf
把整个 `docs/latex/` 目录打包上传（或直接拖拽这些文件），保持目录结构：

```
main.tex
refs.bib
figures/fig1_pipeline.pdf
figures/fig2_taxonomy.pdf
figures/fig3_filter_result.pdf
```

## 关键设置（必做）
**Menu → Settings → Compiler → 选 `XeLaTeX`**
（正文为英文，但含中文批注 〔需核对〕/〔GPU待跑〕，用 xeCJK + Fandol 字体，必须 XeLaTeX；Fandol 随 Overleaf/TeXLive 自带，无需上传字体。）

文献用 BibTeX，Overleaf 会自动跑（`unsrtnat` 数字引用，按出现顺序）。

## 本地编译
```bash
cd docs/latex
latexmk -xelatex main.tex          # 或：xelatex main; bibtex main; xelatex main; xelatex main
```

## 文献状态（已联网核对 2026-06）
- **`refs.bib` 现有 30 条真实题录**（含 DOI/arXiv），已替换原 12 条占位。仅极少数预印本的 venue/作者顺序仍标〔需核对〕（`orcaloca` 的 ICML 2025、`dissecting` 的 ICSE-SEIP 2026）——定稿前再确认一次即可。
- **ARISE 已核实**（arXiv:2605.03117, Seddik & Fard, UBC）：line R@{1,5,10}=**41/62/74**（ARISE-Full, Qwen2.5-Coder-32B-Instruct, SWE-bench Lite 300）；**不做分层报告**（所以本文 RQ1 分层是真新意）。
- 转换中修正的两处误引（原草稿/笔记里的错误）：① “LocAgent 行级 ~15%” —— LocAgent **无行级指标**（仅 file/module/function，文件级 92.7% 属实），已删除该错误归属；② Tarantula 占位标题曾误用 2002 ICSE 论文，已改为正确的 ASE 2005 题录。

## 仍待作者补全
- **〔GPU待跑〕**：标注尚未在完整 vote+graph+LLM 方法上确认的结论（+14pp、SBFL-null）。

## 图
三张图由 `docs/figures/*.svg` 用 `rsvg-convert -f pdf` 转成矢量 PDF。要改图：改 SVG 后重转，或直接编辑 PDF/改用 TikZ。

## 转换时做的两处数值订正（与已核实的正文/真实数据对齐）
- 摘要 RQ2 的 off-path 漏分支计数 `9/11` → **`6/11`**（正文 §5.3 已按 `rq3/classify_offpath.py` 实跑结果订正为 6 漏分支 + 4 插入 + 1 函数未达 = 11；摘要此前漏改）。
- off-path 占比统一为 **16%**（57/68 命中 → 11/68≈16%；原 §5.3 写 17% 为四舍五入笔误，§6 本已写 16%）。
