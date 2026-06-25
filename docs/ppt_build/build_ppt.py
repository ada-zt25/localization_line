# -*- coding: utf-8 -*-
# Build the advisor-report deck (行级故障定位) with python-pptx. v2 (revised narrative).
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

NAVY = "13294B"; TEAL = "1B9AAA"; CORAL = "EE6C4D"; INK = "1F2A37"; MUTED = "6B7785"
WHITE = "FFFFFF"; TINT = "EEF3F7"; TINT2 = "E3ECF2"; GREEN = "2A9D5C"; RED = "C2413A"; AMBER = "E0A458"
FONT = "Microsoft YaHei"
def C(h): return RGBColor.from_string(h)

prs = Presentation()
prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
SW, SH = 13.333, 7.5
BLANK = prs.slide_layouts[6]

def slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid(); s.background.fill.fore_color.rgb = C(bg)
    return s

def _setfont(run, name):
    run.font.name = name
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {}); rPr.append(el)
        el.set("typeface", name)

def text(s, x, y, w, h, runs, size=16, bold=False, color=INK, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, space_after=4, line=1.0, font=FONT):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.04); tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02); tf.margin_bottom = Inches(0.02)
    if isinstance(runs, str): runs = [[(runs, {})]]
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space_after); p.line_spacing = line
        if isinstance(para, str): para = [(para, {})]
        for t, o in para:
            r = p.add_run(); r.text = t
            r.font.size = Pt(o.get("size", size)); r.font.bold = o.get("bold", bold)
            r.font.color.rgb = C(o.get("color", color)); _setfont(r, o.get("font", font))
    return tb

def rect(s, x, y, w, h, fill=None, line=None, lw=1.0, rounded=False, shadow=False):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None: shp.fill.background()
    else: shp.fill.solid(); shp.fill.fore_color.rgb = C(fill)
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb = C(line); shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    if shadow:
        sp = shp._element.spPr
        ef = sp.makeelement(qn('a:effectLst'), {}); sp.append(ef)
        sh = ef.makeelement(qn('a:outerShdw'), {'blurRad': '60000', 'dist': '25000', 'dir': '5400000', 'rotWithShape': '0'}); ef.append(sh)
        clr = sh.makeelement(qn('a:srgbClr'), {'val': '1F2A37'}); sh.append(clr)
        a = clr.makeelement(qn('a:alpha'), {'val': '18000'}); clr.append(a)
    return shp

def arrow(s, x, y, w, h, fill=CORAL):
    shp = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = C(fill); shp.line.fill.background(); shp.shadow.inherit = False
    return shp

def chip(s, x, y, w, h, fill, tcolor, label, size=12):
    rect(s, x, y, w, h, fill=fill, rounded=True)
    text(s, x, y, w, h, [[(label, {"bold": True, "color": tcolor, "size": size})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

def notes(s, t):
    s.notes_slide.notes_text_frame.text = t

MX = 0.7
def title(s, t, sub=None, dark=False):
    tc = WHITE if dark else NAVY
    text(s, MX, 0.42, SW - 2 * MX, 0.8, [[(t, {"size": 30, "bold": True, "color": tc})]])
    if sub:
        text(s, MX, 1.18, SW - 2 * MX, 0.5, [[(sub, {"size": 15, "color": (TEAL if not dark else "CADCFC")})]])

# ---- Slide 1 封面 ----
s = slide(NAVY)
text(s, MX, 2.0, SW - 2 * MX, 1.7, [
    [("行级故障定位", {"size": 46, "bold": True, "color": WHITE})],
    [("——LLM 仓库级 Issue 修复：从问题刻画到静动结合的定位方法", {"size": 21, "color": "CADCFC"})],
], space_after=10)
rect(s, MX, 3.95, 2.2, 0.06, fill=CORAL)
text(s, MX, 4.25, SW - 2 * MX, 1.2, [
    [("研究进展汇报", {"size": 16, "color": "CADCFC"})],
    [("目标会议：CCF-B　|　基准：SWE-bench Verified　|　前沿模型：DeepSeek-V3", {"size": 13, "color": "9FB3C8"})],
    [("2026-06　研究生科研汇报", {"size": 13, "color": "9FB3C8"})],
], space_after=7)
notes(s, "今天汇报：把大模型集成进大型代码仓库修 issue，第一步『定位要改的代码』是核心瓶颈，我聚焦更细的『行级定位 recall 低』。本汇报分两条线：先用实证刻画把问题和它的成因讲透，再提出我设计的『静动结合——执行-反馈-修复闭环』定位方法。基准是 SWE-bench Verified，前沿模型 DeepSeek-V3。关键优势：问题在前沿不消失。")

# ---- Slide 2 背景与问题 ----
s = slide()
title(s, "研究背景与问题", "把 LLM 集成进大型代码仓库：定位是第一步、也是瓶颈")
text(s, MX, 1.85, 7.4, 4.6, [
    [("● 任务", {"size": 17, "bold": True, "color": TEAL})],
    [("  修复真实 GitHub issue（SWE-bench）。仓库常上千文件、数十万行，远超上下文窗口。", {"size": 15})],
    [("", {"size": 6})],
    [("● 核心瓶颈：定位（localization）", {"size": 17, "bold": True, "color": TEAL})],
    [("  必须先找到要改的代码，再交给模型修复。", {"size": 15})],
    [("  定位的召回率是修复率的", {"size": 15}), ("硬上界", {"size": 15, "bold": True, "color": CORAL}),
     ("——没被定位到的代码，下游再强也改不到。", {"size": 15})],
    [("", {"size": 6})],
    [("● 问题聚焦", {"size": 17, "bold": True, "color": TEAL})],
    [("  文件级定位已基本解决；", {"size": 15}), ("行级（line 级）定位 recall 低", {"size": 15, "bold": True, "color": CORAL}),
     ("才是真问题。", {"size": 15})],
], space_after=5, line=1.08)
rect(s, 8.6, 1.95, 4.0, 4.2, fill=NAVY, rounded=True, shadow=True)
text(s, 8.6, 2.3, 4.0, 0.5, [[("典型仓库规模", {"size": 15, "color": "CADCFC"})]], align=PP_ALIGN.CENTER)
text(s, 8.6, 2.72, 4.0, 1.1, [[("1600+", {"size": 60, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER)
text(s, 8.6, 3.88, 4.0, 0.5, [[("个 Python 文件 / 实例", {"size": 14, "color": "CADCFC"})]], align=PP_ALIGN.CENTER)
rect(s, 9.1, 4.55, 3.0, 0.04, fill=TEAL)
text(s, 8.6, 4.75, 4.0, 1.2, [
    [("一次 issue 平均改动", {"size": 13, "color": "9FB3C8"})],
    [("2.45 个文件", {"size": 24, "bold": True, "color": CORAL})],
], align=PP_ALIGN.CENTER, space_after=4)
notes(s, "任务是修真实 GitHub issue，仓库放不进上下文，必须先定位。定位召回率是修复率的硬上界——漏掉的代码下游碰不到。文件级定位社区已做得好，真正卡住修复的是行级定位 recall 低。右边给体量：平均 1600 多文件、一次改 2.45 个文件。")

# ---- Slide 3 研究链路 ----
s = slide()
title(s, "研究链路（问题 → A → B → 缺口）", "一条清晰递进的脉络，定位本研究的切入点")
cards = [
    ("论文 A", "Agentless (FSE'25)", "分层、纯 LLM、无执行的静态定位", "不足：靠词法/结构相似度，漏依赖相连代码；分层是单向漏斗", TEAL),
    ("论文 B", "LocAgent (ACL'25)", "依赖图多跳定位，文件级 92.7%", "不足：行级 recall 仅约 15%，靠『撒大网』维持召回", TEAL),
    ("缺口", "2026 三篇独立工作", "SWE-Explore / ReCUBE / 粒度研究", "行级召回是新瓶颈；无人在前沿刻画为何失败、也无人验证执行能否救", CORAL),
]
cw = 3.95; gap = (SW - 2 * MX - 3 * cw) / 2; cy = 2.0; ch = 4.3
for i, (tag, name, what, gap_txt, col) in enumerate(cards):
    cx = MX + i * (cw + gap)
    rect(s, cx, cy, cw, ch, fill=TINT, rounded=True, shadow=True)
    chip(s, cx + 0.3, cy + 0.3, 1.5, 0.5, col, WHITE, tag, size=13)
    text(s, cx + 0.3, cy + 1.0, cw - 0.6, 0.7, [[(name, {"size": 18, "bold": True, "color": NAVY})]])
    text(s, cx + 0.3, cy + 1.7, cw - 0.6, 1.0, [[(what, {"size": 14, "color": INK})]], line=1.05)
    rect(s, cx + 0.3, cy + 2.75, cw - 0.6, 0.02, fill="C7D5DF")
    text(s, cx + 0.3, cy + 2.92, cw - 0.6, 1.3, [[(gap_txt, {"size": 13.5, "color": MUTED})]], line=1.08)
    if i < 2:
        text(s, cx + cw + gap / 2 - 0.18, cy + 1.7, 0.4, 0.6, [[("→", {"size": 28, "bold": True, "color": CORAL})]], align=PP_ALIGN.CENTER)
notes(s, "三步递进。A（Agentless）：分层、纯 LLM、无执行的静态定位，漏依赖相连代码、单向漏斗。B（LocAgent）：依赖图多跳，文件级 92.7%，但行级 recall 只有约 15%、靠撒大网。缺口：行级召回是新瓶颈，没人在前沿刻画为何失败、也没人验证执行能不能救——这正是我的切入点。")

# ---- Slide 4 研究问题 (RQ3 revised) ----
s = slide()
title(s, "研究问题", "围绕『行级定位 recall 低』展开，递进到方法")
rqs = [
    ("RQ1", "问题存在性与刻画", "前沿模型上行级定位是否仍是瓶颈？如何随真实度、文件规模变化？失败是召回还是精度？", TEAL),
    ("RQ2", "纯执行信号能否定位", "把『失败测试的执行覆盖 / 报错』当作直接定位信号，能否在行级超过强静态 LLM？", AMBER),
    ("RQ3", "静动结合的定位方法（核心）", "在静态定位基础上引入『执行—反馈—修复』闭环（定位→试修→重跑→新报错→再定位），用动静结合提升行级 recall。", CORAL),
]
y = 2.0
for tag, h, body, col in rqs:
    rect(s, MX, y, SW - 2 * MX, 1.45, fill=TINT, rounded=True, shadow=True)
    chip(s, MX + 0.35, y + 0.42, 1.3, 0.62, col, WHITE, tag, size=18)
    text(s, MX + 2.0, y + 0.22, SW - 2 * MX - 2.4, 0.5, [[(h, {"size": 17, "bold": True, "color": NAVY})]])
    text(s, MX + 2.0, y + 0.72, SW - 2 * MX - 2.4, 0.65, [[(body, {"size": 14, "color": INK})]], line=1.05)
    y += 1.65
notes(s, "三个研究问题递进。RQ1 是问题刻画：行级定位多差、随真实度和文件规模怎么变、失败是召回还是精度。RQ2 是诊断：把失败测试的执行覆盖或报错当作『直接定位信号』，能不能打败强静态 LLM——这一问的答案是否定的，它正好暴露了执行该怎么用。RQ3 是核心方法：不把执行当直接信号，而是把它做成『执行—反馈—修复』闭环，和静态定位结合，靠动静结合提升行级 recall。这就是我要做的真正方法创新。")

# ---- Slide 5 实验设计 (NEW, C1 design) ----
s = slide()
title(s, "实验设计（C1 实证）", "全部基于现成 benchmark，仅需 API + 本机 Docker（无训练 / 无大算力）")
# top: setup three cards
setup = [
    ("数据", "SWE-bench Verified（500 真实实例）；HF 取元数据，按 base_commit 取文件，官方 Docker 镜像跑测试"),
    ("模型", "前沿 DeepSeek-V3；本地 qwen2.5-coder:7b / gemma2:9b（跨规模对照）"),
    ("指标", "行级 recall / precision / 文件级 recall / 过预测比 / 上下文效率"),
]
sx = MX; sw = (SW - 2 * MX - 2 * 0.3) / 3
for i, (h, b) in enumerate(setup):
    cx = sx + i * (sw + 0.3)
    rect(s, cx, 1.85, sw, 1.55, fill=TINT, rounded=True, shadow=True)
    text(s, cx + 0.25, 2.0, sw - 0.5, 0.4, [[(h, {"size": 15, "bold": True, "color": CORAL})]])
    text(s, cx + 0.25, 2.45, sw - 0.5, 0.9, [[(b, {"size": 12.5, "color": INK})]], line=1.05)
# bottom: experiment matrix table
matrix = [
    ("实验", "设定", "测什么"),
    ("P0 / P0-big", "单文件、文件已给", "粒度 gap；随文件规模的精度 / 过预测"),
    ("P1", "真实两阶段（不给文件）", "端到端行级 recall、文件命中"),
    ("P2", "多文件（最真实）", "多文件行级 recall、找全文件"),
    ("EGL", "失败测试覆盖（Docker）", "覆盖能否做行级定位信号"),
    ("P3 / P8", "报错文本 / 执行-反馈-修复 loop", "执行反馈能否提升行级 recall"),
]
tx, ty = MX, 3.65; cwid = [2.6, 3.6, 5.73]; rh = 0.56
for ri, row in enumerate(matrix):
    cx = tx
    for ci, val in enumerate(row):
        fill = NAVY if ri == 0 else (TINT if ri % 2 else WHITE)
        rect(s, cx, ty + ri * rh, cwid[ci], rh, fill=fill, line="D6E0E8", lw=0.75)
        tc = WHITE if ri == 0 else INK
        text(s, cx + (0.12 if ci else 0.12), ty + ri * rh, cwid[ci] - 0.2, rh,
             [[(val, {"size": 12.5, "bold": (ri == 0 or ci == 0), "color": (tc if ci or ri == 0 else NAVY)})]],
             anchor=MSO_ANCHOR.MIDDLE, align=(PP_ALIGN.CENTER if ri == 0 else PP_ALIGN.LEFT))
        cx += cwid[ci]
notes(s, "这页是 C1 实证的实验设计。数据用社区标准 SWE-bench Verified，500 个真实实例；元数据从 HuggingFace 取，文件按提交号取，测试在官方 Docker 镜像里真跑。模型用前沿 DeepSeek-V3，再加本地两个 7 到 9B 模型做跨规模对照。指标包括行级 recall、precision、文件级 recall、过预测比、上下文效率。下面的实验矩阵是我设计的一组递进实验：P0 系列看粒度 gap 和精度墙；P1、P2 看真实和多文件设定的行级召回；EGL 看覆盖能不能做定位信号；P3 和 P8 看执行反馈能不能提升行级召回。下面几页就是这些实验的结果。")

# ---- Slide 6 核心结果① ----
s = slide()
title(s, "核心结果 ①：问题真实，且前沿模型扛不过去", "行级 recall 随任务真实度单调恶化（DeepSeek-V3）")
cd = CategoryChartData()
cd.categories = ["单文件 / 文件已给", "多文件 / 真实设定", "完整 agentic / 独立基准"]
cd.add_series("行级 recall", (0.53, 0.28, 0.15))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MX), Inches(2.0), Inches(6.6), Inches(4.6), cd)
chart = gf.chart; chart.has_legend = False; chart.has_title = False
plot = chart.plots[0]; plot.has_data_labels = True; plot.gap_width = 80
plot.data_labels.number_format = '0%'; plot.data_labels.number_format_is_linked = False
plot.data_labels.font.size = Pt(16); plot.data_labels.font.bold = True; plot.data_labels.font.color.rgb = C(NAVY)
for i, pt in enumerate(plot.series[0].points):
    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = C([TEAL, AMBER, CORAL][i])
chart.value_axis.has_major_gridlines = False; chart.value_axis.visible = False
chart.value_axis.minimum_scale = 0; chart.value_axis.maximum_scale = 0.6
chart.category_axis.tick_labels.font.size = Pt(11); chart.category_axis.tick_labels.font.color.rgb = C(INK)
rect(s, 7.7, 2.0, 4.9, 4.6, fill=TINT, rounded=True, shadow=True)
text(s, 8.0, 2.3, 4.3, 4.2, [
    [("要点", {"size": 15, "bold": True, "color": CORAL})],
    [("", {"size": 4})],
    [("• 文件级定位已基本解决（", {"size": 14}), ("0.66–0.90", {"size": 14, "bold": True, "color": NAVY}), ("），", {"size": 14})],
    [("  但行级才是瓶颈。", {"size": 14})],
    [("", {"size": 4})],
    [("• 多文件下连『找全所有该改文件』", {"size": 14})],
    [("  都仅 ", {"size": 14}), ("0.35", {"size": 14, "bold": True, "color": CORAL}), ("。", {"size": 14})],
    [("", {"size": 4})],
    [("• 23% 实例的决定性行被完全漏掉。", {"size": 14})],
    [("", {"size": 6})],
    [("关键：与上一方向不同——", {"size": 14, "bold": True, "color": NAVY})],
    [("问题在前沿不消失。", {"size": 15, "bold": True, "color": CORAL})],
], space_after=3, line=1.05)
notes(s, "第一个核心结果：问题真实、前沿扛不过去。柱状图是 DeepSeek-V3 三种真实度下的行级 recall：单文件且文件已给 0.53，多文件真实 0.28，完整 agentic 下独立基准约 0.15，单调恶化。要点：文件级不差（0.66 到 0.90），瓶颈在行级；多文件下连找全文件都只有 0.35；23% 实例决定性行被完全漏掉。最关键：问题在前沿不消失。")

# ---- Slide 7 核心结果② ----
s = slide()
title(s, "核心结果 ②：精确性 / 效率墙", "前沿模型靠『撒大网』维持召回，且随文件规模恶化")
rows = [
    ("文件规模 (行)", "精确行 recall", "precision", "过预测比"),
    ("0 – 200", "0.58", "0.49", "1.9×"),
    ("200 – 500", "0.73", "0.36", "4.7×"),
    ("500 – 1000", "0.44", "0.42", "3.9×"),
    ("1000 – 3000", "0.48", "0.20", "5.8×"),
]
tx, ty = MX, 2.1; rh = 0.78; cwid = [2.7, 1.8, 1.4, 1.4]
for ri, row in enumerate(rows):
    cx = tx
    for ci, val in enumerate(row):
        fill = NAVY if ri == 0 else (TINT if ri % 2 else WHITE)
        rect(s, cx, ty + ri * rh, cwid[ci], rh, fill=fill, line="D6E0E8", lw=0.75)
        tc = WHITE if ri == 0 else (CORAL if (ci >= 2 and ri == 4) else INK)
        bold = (ri == 0) or (ci >= 2 and ri == 4)
        text(s, cx, ty + ri * rh, cwid[ci], rh, [[(val, {"size": 13.5, "bold": bold, "color": tc})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        cx += cwid[ci]
rect(s, 9.7, 2.1, 2.9, 3.45, fill=NAVY, rounded=True, shadow=True)
text(s, 9.7, 2.5, 2.9, 2.7, [
    [("大文件上 precision", {"size": 14, "color": "CADCFC"})],
    [("0.20", {"size": 50, "bold": True, "color": CORAL})],
    [("过预测 5.8×", {"size": 16, "bold": True, "color": WHITE})],
], align=PP_ALIGN.CENTER, space_after=8)
text(s, MX, 6.45, SW - 2 * MX, 0.7, [[("→ 『找得到、找不准』：精度坍塌、上下文效率差，是修复率的隐性约束。", {"size": 14, "color": MUTED})]])
notes(s, "第二个结果：精确性/效率墙。单文件按文件大小分层，随文件变大 precision 从 0.49 掉到 0.20、过预测比 1.9 倍涨到 5.8 倍。前沿模型在大文件上靠撒大网兜召回，是『找得到、找不准』。上下文效率是修复率的隐性约束。")

# ---- Slide 8 核心发现③ ----
s = slide()
title(s, "核心发现 ③：纯执行覆盖做不了『行级』定位", "在 SWE-bench Docker 中跑失败测试取覆盖，与静态 LLM 对比")
items = [
    ("精确执行行", "recall 0.33", "太稀疏：决定性行常在未走分支 / 插入位，根本没被执行", RED),
    ("被执行函数整段", "recall 0.96 但 = 85% 文件", "太粗：失败测试进入的函数覆盖了大半文件，不缩小搜索空间", RED),
    ("LLM 静态（对照）", "recall 0.42，约 9 行", "更窄更准——覆盖法两种粒度都打不过它", GREEN),
]
y = 2.0
for name, stat, desc, col in items:
    rect(s, MX, y, SW - 2 * MX, 1.25, fill=TINT, rounded=True, shadow=True)
    text(s, MX + 0.35, y, 4.0, 1.25, [[(name, {"size": 16, "bold": True, "color": NAVY})]], anchor=MSO_ANCHOR.MIDDLE)
    chip(s, MX + 4.4, y + 0.33, 3.2, 0.6, col, WHITE, stat, size=14)
    text(s, MX + 7.9, y, SW - 2 * MX - 8.2, 1.25, [[(desc, {"size": 13.5, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE, line=1.05)
    y += 1.45
text(s, MX, y + 0.05, SW - 2 * MX, 0.7, [[("→ 答 RQ2：纯执行覆盖作为『直接定位信号』被严格证伪。但这不等于执行无用——关键在『怎么用』（见后）。", {"size": 14.5, "bold": True, "color": CORAL})]])
notes(s, "第三个发现回答 RQ2：纯执行覆盖做不了行级定位。我在官方 Docker 里真跑失败测试取覆盖：只取精确执行行 recall 仅 0.33，因为决定性行常在未走分支或要新增的位置、根本没执行；放宽到被执行函数整段 recall 到 0.96 但等于覆盖了 85% 的文件、没缩小范围。LLM 静态 0.42、只选约 9 行，又窄又准，覆盖两种粒度都打不过。结论：覆盖作为『直接信号』被证伪——但这不代表执行没用，关键在怎么用，后面会讲。")

# ---- Slide 9 为什么失效（详细机制）----
s = slide(NAVY)
text(s, MX, 0.45, SW - 2 * MX, 0.7, [[("为什么纯执行对『行级』定位失灵？", {"size": 28, "bold": True, "color": WHITE})]])
text(s, MX, 1.15, SW - 2 * MX, 0.45, [[("两条技术原因 + 一条根因（bug 类型门控）——解释了所有负面结果", {"size": 14, "color": "CADCFC"})]])
# two technical reasons (top row)
rect(s, MX, 1.75, 5.95, 2.05, fill="1B3A5C", rounded=True)
text(s, MX + 0.3, 1.9, 5.45, 1.8, [
    [("原因一：覆盖『太宽』", {"size": 15, "bold": True, "color": "7FD4E0"})],
    [("import 连锁——一个测试 import 上百模块，", {"size": 13, "color": WHITE})],
    [("每个模块的顶层/def 头部行在导入时即执行；", {"size": 13, "color": WHITE})],
    [("函数体只有被调用才执行。覆盖分不清二者。", {"size": 13, "color": "CFE2EA"})],
], space_after=3, line=1.05)
rect(s, MX + 6.15, 1.75, 5.95, 2.05, fill="1B3A5C", rounded=True)
text(s, MX + 6.45, 1.9, 5.45, 1.8, [
    [("原因二：覆盖『太稀疏』", {"size": 15, "bold": True, "color": "7FD4E0"})],
    [("决定性行常在未走到的分支、或是要", {"size": 13, "color": WHITE})],
    [("新增的代码（插入位）——它们", {"size": 13, "color": WHITE}), ("从不执行", {"size": 13, "bold": True, "color": "F6A58C"}), ("，", {"size": 13, "color": WHITE})],
    [("因此根本不在覆盖里。", {"size": 13, "color": "CFE2EA"})],
], space_after=3, line=1.05)
# root cause: bug-type gating (bottom)
text(s, MX, 3.95, SW - 2 * MX, 0.4, [[("根因：bug 类型门控 —— 失败如何被『发现』，决定执行有没有信号", {"size": 16, "bold": True, "color": "CADCFC"})]])
rect(s, MX, 4.4, 5.95, 2.35, fill="234A36", rounded=True)
chip(s, MX + 0.3, 4.6, 3.4, 0.5, GREEN, WHITE, "崩溃类（约 28%）", size=13)
text(s, MX + 0.3, 5.2, 5.45, 1.5, [
    [("失败＝仓库代码内部抛异常。", {"size": 13, "color": WHITE})],
    [("异常在", {"size": 13, "color": "CFE2EA"}), ("活动调用栈", {"size": 13, "bold": True, "color": WHITE}), ("上抛出 → traceback", {"size": 13, "color": "CFE2EA"})],
    [("直接点名出错文件:行。执行有效 ✓", {"size": 13, "bold": True, "color": "7CE0A8"})],
], space_after=2, line=1.05)
rect(s, MX + 6.15, 4.4, 5.95, 2.35, fill="3A2330", rounded=True)
chip(s, MX + 6.45, 4.6, 4.6, 0.5, CORAL, WHITE, "行为 / 断言类（约 58–65%）", size=13)
text(s, MX + 6.45, 5.2, 5.45, 1.5, [
    [("失败＝函数返回", {"size": 13, "color": WHITE}), ("错值", {"size": 13, "bold": True, "color": "F6A58C"}), ("，返回", {"size": 13, "color": WHITE}), ("之后", {"size": 13, "bold": True, "color": WHITE}), ("才被 assert 发现。", {"size": 13, "color": WHITE})],
    [("此刻函数帧", {"size": 13, "color": "F0D9D0"}), ("已弹出栈", {"size": 13, "bold": True, "color": WHITE}), ("，traceback 里没有它；", {"size": 13, "color": "F0D9D0"})],
    [("差分 SBFL 也救不了（buggy 是正常代码，", {"size": 12.5, "color": "F0D9D0"})],
    [("通过测试也覆盖它）。执行『不透明』 ✗", {"size": 13, "bold": True, "color": "F6A58C"})],
], space_after=2, line=1.03)
notes(s, "这页把『为什么纯执行对行级失灵』讲细。两条技术原因：原因一覆盖太宽——pytest 一 import 就连锁导入上百模块，每个模块的顶层代码和 def 头部行在导入时就执行了，但函数体只有被调用才执行，而覆盖分不清这两者，所以一个测试动辄覆盖大半个包。原因二覆盖太稀疏——决定性的行常在没走到的分支、或者是要新增的代码，这些行从不执行，根本不在覆盖里。根因是 bug 类型门控：崩溃类约 28%，失败是代码内部抛异常，异常在活动栈上抛出，traceback 直接点名出错行，执行有效；行为/断言类约 58 到 65%、是大多数，失败是函数返回了错值、在返回之后断言才发现，这时函数帧已经弹出栈、traceback 里没有它，差分 SBFL 也救不了因为 buggy 代码是正常代码、通过测试也覆盖它，所以执行对行级是不透明的。SWE-bench 以行为类为主，这一句解释了我前面所有执行类负面结果。")

# ---- Slide 10 方法探索：失败的 coverage 与 traceback ----
s = slide()
title(s, "方法探索（一）：两条失败的执行设计 + 失败原因", "失败本身指明了执行的正确用法 → 引出新方法")
fail = [
    ("设计 A：覆盖即定位（EGL）", "用失败测试的执行覆盖直接作为『要改的行』候选",
     "证伪", "精确行 0.33 太稀疏 / 函数级 0.96 但占 85% 文件；打不过静态 0.42",
     "失败原因：覆盖的粒度两难 + 决定性行 off-path（见上页机制）"),
    ("设计 B：报错反馈注入（traceback）", "把运行得到的报错文本喂回 LLM，让它重定位",
     "无效", "行级 recall +0.00；6 个完全 miss 一个都没救回",
     "失败原因：行为/断言类 bug 栈已弹出，traceback 无仓库行信息"),
]
y = 1.95
for name, what, verd, res, why in fail:
    rect(s, MX, y, SW - 2 * MX, 2.05, fill=TINT, rounded=True, shadow=True)
    text(s, MX + 0.35, y + 0.22, 7.0, 0.5, [[(name, {"size": 16, "bold": True, "color": NAVY})]])
    chip(s, SW - MX - 1.9, y + 0.25, 1.5, 0.55, RED, WHITE, verd, size=15)
    text(s, MX + 0.35, y + 0.78, SW - 2 * MX - 0.7, 0.5, [[("做法：", {"size": 13.5, "bold": True, "color": TEAL}), (what, {"size": 13.5, "color": INK})]], line=1.05)
    text(s, MX + 0.35, y + 1.2, SW - 2 * MX - 0.7, 0.5, [[("结果：", {"size": 13.5, "bold": True, "color": TEAL}), (res, {"size": 13.5, "color": INK})]], line=1.05)
    text(s, MX + 0.35, y + 1.62, SW - 2 * MX - 0.7, 0.4, [[(why, {"size": 13, "color": CORAL})]], line=1.0)
    y += 2.25
text(s, MX, y + 0.0, SW - 2 * MX, 0.5, [[("启发：执行不该当『直接信号』，而应作『迭代反馈』驱动定位修正 → 静动结合闭环（下页）。", {"size": 14, "bold": True, "color": NAVY})]])
notes(s, "方法探索第一部分：我设计并验证了两条用执行的方法，都失败了，但失败指明了正确用法。设计 A 是覆盖即定位（EGL）：直接拿失败测试的覆盖当『要改的行』候选——证伪，精确行 0.33 太稀疏、函数级 0.96 但占 85% 文件，打不过静态 0.42，原因是覆盖粒度两难加决定性行 off-path。设计 B 是报错反馈注入：把运行报错文本喂回 LLM 重定位——无效，行级 recall 加 0.00、6 个完全 miss 一个没救回，原因是行为类 bug 栈已弹出、traceback 没有仓库行。关键启发：执行不该当直接信号，而应该当迭代反馈来驱动定位修正——这就引出我的静动结合闭环方法。")

# ---- Slide 11 新方法设计 P8 (design only) ----
s = slide()
title(s, "方法探索（二）：静动结合的执行—反馈—修复闭环", "核心方法创新（P8）")
# flow boxes
labels = [("静态定位", "LLM 给\n候选行", TEAL), ("试修", "SEARCH/\nREPLACE", NAVY),
          ("执行", "跑 FAIL_\nTO_PASS", AMBER), ("反馈", "新报错 /\n失败形态", CORAL), ("再定位", "据反馈\n补漏定位", TEAL)]
n = len(labels); bw = 1.95; bh = 1.15; gapx = (SW - 2 * MX - n * bw) / (n - 1)
fy = 2.15
for i, (h, d, col) in enumerate(labels):
    bx = MX + i * (bw + gapx)
    rect(s, bx, fy, bw, bh, fill=col, rounded=True, shadow=True)
    text(s, bx, fy + 0.12, bw, 0.5, [[(h, {"size": 15, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER)
    text(s, bx, fy + 0.55, bw, 0.55, [[(d, {"size": 11.5, "color": "F2F6F9"})]], align=PP_ALIGN.CENTER, line=0.95)
    if i < n - 1:
        arrow(s, bx + bw + 0.04, fy + bh / 2 - 0.13, gapx - 0.08, 0.26)
text(s, MX, fy + bh + 0.08, SW - 2 * MX, 0.4, [[("↺  迭代 K = 5 轮；定位输出 = 各轮『被编辑行』的并集", {"size": 13.5, "bold": True, "color": CORAL})]], align=PP_ALIGN.CENTER)
# bottom three explainer cards
exp = [
    ("核心思想", "静态负责『看代码选候选』，动态负责『用真实失败反馈纠偏、补漏』——执行当反馈而非直接信号。", TEAL),
    ("为何能涨 recall", "一次部分修复后测试以『不同方式』失败，新报错暴露第一次漏掉的位置（尤其多位置 bug）。", NAVY),
    ("关键实现", "SEARCH/REPLACE 小输出（防 API 断流）+ 官方 Docker 内跑测试 + 容器内超时兜底；编辑即定位。", AMBER),
]
ey = 4.45; ew = (SW - 2 * MX - 2 * 0.3) / 3
for i, (h, b, col) in enumerate(exp):
    cx = MX + i * (ew + 0.3)
    rect(s, cx, ey, ew, 2.0, fill=TINT, rounded=True, shadow=True)
    chip(s, cx + 0.25, ey + 0.22, ew - 0.5, 0.5, col, WHITE, h, size=13)
    text(s, cx + 0.25, ey + 0.85, ew - 0.5, 1.0, [[(b, {"size": 12.5, "color": INK})]], line=1.08)
notes(s, "这是核心方法创新——静动结合的执行-反馈-修复闭环。流程：静态定位先给候选行 → 试修以 SEARCH/REPLACE 编辑块输出（小输出，避免 API 断流）→ 在官方 Docker 容器里跑 FAIL_TO_PASS 测试 → 拿到新的报错或失败形态作反馈 → 据反馈再定位补漏，迭代 5 轮；最终定位输出是各轮被编辑行的并集，编辑即定位。核心思想是分工：静态负责看代码选候选，动态负责用真实失败反馈纠偏补漏——执行在这里是『反馈』而不是『直接信号』，正好绕开前面证伪的失败模式。为什么能涨 recall：一次部分修复后测试以不同方式失败，新报错暴露出第一次漏掉的位置，尤其是要改多个地方的 bug。下一页是它的实验设计和结果。")

# ---- Slide 12 P8 实验设计与结果 ----
s = slide()
title(s, "P8 实验设计与结果", "诚实呈现：两个指标，两个结论")
# left: experiment design
rect(s, MX, 1.9, 5.5, 4.7, fill=TINT, rounded=True, shadow=True)
text(s, MX + 0.32, 2.1, 5.0, 4.4, [
    [("实验设计", {"size": 16, "bold": True, "color": CORAL})],
    [("", {"size": 3})],
    [("• 数据：SWE-bench Verified，pytest 原生", {"size": 13})],
    [("  仓库，单文件实例，≤400 行，n=12", {"size": 13})],
    [("• 每实例自带 FAIL_TO_PASS 复现测试", {"size": 13})],
    [("• 执行：官方 Docker 镜像，K=5 轮，", {"size": 13})],
    [("  容器内超时兜底（无卡死/无断流）", {"size": 13})],
    [("• 对照：round0（纯静态单次） vs", {"size": 13})],
    [("  loop（5 轮并集）", {"size": 13})],
    [("• 指标：① fraction-recall（召回全部", {"size": 13})],
    [("  gold 行的比例）② ARISE 同口径 Recall@k", {"size": 13})],
], space_after=3, line=1.06)
# right: results, two blocks
rect(s, MX + 5.85, 1.9, SW - 2 * MX - 5.85, 2.25, fill="EAF5EF", rounded=True, shadow=True)
text(s, MX + 6.15, 2.05, SW - 2 * MX - 6.45, 2.0, [
    [("指标①  fraction-recall（P8 赢 ✓）", {"size": 14.5, "bold": True, "color": GREEN})],
    [("round0 0.393  →  loop ", {"size": 14}), ("0.557", {"size": 16, "bold": True, "color": GREEN}),
     ("　(Δ +0.164, 相对 +42%)", {"size": 13})],
    [("3/12 实例提升（xarray-4075: 0 → 1.0）；解决率 8/12", {"size": 12.5, "color": INK})],
    [("→ 环路能捞回单次漏掉的决定性行（多行编辑）", {"size": 12.5, "color": MUTED})],
], space_after=3, line=1.08)
rect(s, MX + 5.85, 4.3, SW - 2 * MX - 5.85, 2.3, fill="FBEEEA", rounded=True, shadow=True)
text(s, MX + 6.15, 4.45, SW - 2 * MX - 6.45, 2.1, [
    [("指标②  ARISE 同口径 Recall@k（尚未赢 ✗）", {"size": 14.5, "bold": True, "color": CORAL})],
    [("           @1      @5      @10", {"size": 12.5, "bold": True, "color": INK})],
    [("静态     66.7    83.3    100", {"size": 12.5, "color": INK})],
    [("P8        8.3     66.7    91.7", {"size": 12.5, "color": INK})],
    [("原因：P8 输出无置信排序（@1 吃亏）+ 单文件静态已封顶", {"size": 12, "color": MUTED})],
    [("→ 需多文件难设定 + 置信排序，才能同口径显出价值", {"size": 12, "color": MUTED})],
], space_after=2, line=1.06)
notes(s, "P8 的实验设计和结果，诚实呈现。设计：SWE-bench Verified 的 pytest 原生单文件实例、≤400 行、12 个，每个自带复现测试；在官方 Docker 里跑 5 轮，容器内超时兜底，所以这次零卡死零断流；对照是 round0 纯静态单次 vs loop 五轮并集；两个指标。结果是两个相反的故事——指标一 fraction-recall（召回全部 gold 行的比例）P8 赢：从 0.393 提到 0.557，相对涨 42%，3 个实例明显提升、xarray-4075 从 0 到 1.0，解决率 8/12，说明环路确实能捞回单次漏掉的决定性行。指标二 ARISE 同口径 Recall@k（top-k 里有≥1 条 gold 行）P8 还没赢：静态 66.7/83.3/100，P8 只有 8.3/66.7/91.7——但主因不是定位差，而是 P8 的预测行没有置信排序（@1 吃亏）加上单文件下静态已经封顶。结论：P8 在『完整性』上有真实增益，但要在 ARISE 头条指标上显出价值，需要搬到多文件难设定加置信排序。这是下一步。")

# ---- Slide 13 三大贡献总览 ----
s = slide()
title(s, "三大贡献（发现问题 → 设计方法 → 得到结果）", "一条逻辑链：查实问题 → 排除错误解法并解释 → 给出正确解法")
contribs = [
    ("①", "行级定位是前沿真瓶颈", TEAL,
     "大模型『定位』真解决了吗？瓶颈在文件还是行？换大模型能消除吗？",
     "SWE-bench 上按真实度递进 + 跨规模（前沿 + 本地）受控实验",
     "文件级已解决、行级是瓶颈；行级 recall 0.53→0.28→0.15，前沿不消失"),
    ("②", "证伪『跑代码即定位』+ 机制解释（给热潮纠偏）", CORAL,
     "2026『执行接地』热潮默认跑代码能帮定位——对『行级』真的吗？",
     "官方 Docker 真跑失败测试取覆盖，与强静态 LLM 同台对比 + 机制剖析",
     "覆盖证伪（精确行 0.33 / 函数 0.96 但占 85% < 静态 0.42）；根因 = bug 类型门控"),
    ("③", "静动结合的执行-反馈-修复闭环（新方法）", NAVY,
     "执行不能当『直接信号』，那到底该怎么用？",
     "执行作『反馈闭环』：猜 → 试跑 → 看怎么错 → 再补找漏掉的行（P8，K=5）",
     "比单次多找回 +42%（0.39→0.56），有实例 0→1.0；机制成立"),
]
cy = 1.85; cardh = 1.55; cgap = 0.18
for num, ttl, col, prob, meth, res in contribs:
    rect(s, MX, cy, SW - 2 * MX, cardh, fill=TINT, rounded=True, shadow=True)
    chip(s, MX + 0.3, cy + 0.5, 0.7, 0.55, col, WHITE, num, size=20)
    text(s, MX + 1.2, cy + 0.14, SW - 2 * MX - 1.5, 0.45, [[(ttl, {"size": 16, "bold": True, "color": NAVY})]])
    text(s, MX + 1.2, cy + 0.6, SW - 2 * MX - 1.5, 0.95, [
        [("问题　", {"size": 12.5, "bold": True, "color": CORAL}), (prob, {"size": 12.5, "color": INK})],
        [("方法　", {"size": 12.5, "bold": True, "color": TEAL}), (meth, {"size": 12.5, "color": INK})],
        [("结果　", {"size": 12.5, "bold": True, "color": GREEN}), (res, {"size": 12.5, "color": INK})],
    ], space_after=2, line=1.04)
    cy += cardh + cgap
notes(s, "三大贡献，是一条逻辑链。贡献一，查实问题：通过按真实度递进、跨规模的受控实验，证明行级定位是前沿真瓶颈——文件级已解决、行级才是瓶颈，recall 随真实度 0.53、0.28、0.15 单调恶化，且换大模型也不消失。贡献二，排除错误解法并解释：在官方 Docker 里真跑覆盖，证伪了『跑代码就能定位』，并用 bug 类型门控机制解释为什么——给当前执行接地热潮纠偏。贡献三，给出正确解法：把执行从直接信号改造成反馈闭环（猜→试→看错→再补），比单次多找回 42%、有实例从 0 到 1.0，机制成立。一句话：查实问题 → 排错并解释 → 给出新方法。")

# ---- Slide 14 论文定位与贡献 ----
s = slide()
title(s, "论文定位与贡献", "CCF-B · 实证刻画（C1） + 方法创新（C2）")
rect(s, MX, 2.0, 5.9, 4.5, fill=TINT, rounded=True, shadow=True)
text(s, MX + 0.35, 2.2, 5.3, 4.1, [
    [("C1　实证刻画（主）", {"size": 16, "bold": True, "color": CORAL})],
    [("前沿 LLM 行级定位失败模式的系统刻画：", {"size": 13})],
    [("• 粒度 gap：文件级解决、行级是瓶颈", {"size": 12.5})],
    [("• 真实度恶化：0.53 → 0.28 → 0.15", {"size": 12.5})],
    [("• 精确性墙：大文件 precision 0.20", {"size": 12.5})],
    [("• 纯执行无效 + bug 类型门控机制", {"size": 12.5})],
    [("（实验：P0–P3 / EGL，DeepSeek-V3 + 跨规模）", {"size": 11.5, "color": MUTED})],
    [("", {"size": 5})],
    [("C2　方法创新（主）", {"size": 16, "bold": True, "color": CORAL})],
    [("静动结合的执行—反馈—修复闭环（P8）：", {"size": 13})],
    [("把执行作迭代反馈而非直接信号，与静态", {"size": 12.5})],
    [("融合提升行级 recall。真实有效的创新方法。", {"size": 12.5})],
], space_after=2, line=1.08)
rect(s, MX + 6.2, 2.0, SW - 2 * MX - 6.2, 4.5, fill=NAVY, rounded=True, shadow=True)
text(s, MX + 6.55, 2.2, SW - 2 * MX - 6.9, 4.1, [
    [("新颖性定位（须区分）", {"size": 16, "bold": True, "color": "CADCFC"})],
    [("", {"size": 3})],
    [("• T2L-Agent (2025)：trace→line 但 C/C++", {"size": 12.5, "color": WHITE})],
    [("• DAIRA / Echo (2026)：执行接地，但无", {"size": 12.5, "color": WHITE})],
    [("  行级 / 效率视角——本文给出反例", {"size": 12.5, "color": "F6A58C"})],
    [("• ARISE (2026)：静态行级 SOTA（对照）", {"size": 12.5, "color": WHITE})],
    [("• LocAgent / Agentless / SWE-Explore", {"size": 12.5, "color": WHITE})],
    [("", {"size": 8})],
    [("本文双卖点：", {"size": 14, "bold": True, "color": "CADCFC"})],
    [("①『纯执行对行级不灵 + 机制』给热潮纠偏；", {"size": 13, "color": WHITE})],
    [("②『执行作反馈闭环』的静动结合定位方法。", {"size": 13, "color": WHITE})],
], space_after=2, line=1.08)
notes(s, "论文定位：CCF-B 的『实证刻画加方法创新』。C1 实证刻画是主线：前沿 LLM 行级定位失败模式的系统刻画——粒度 gap、真实度恶化 0.53 到 0.28 到 0.15、精确性墙、纯执行无效加 bug 类型门控机制，实验是 P0 到 P3 加 EGL，在 DeepSeek-V3 上并跨规模对照。C2 方法创新也是主线、不是配角：静动结合的执行-反馈-修复闭环，把执行当迭代反馈而不是直接信号、和静态融合提升行级 recall——这是真实有效的创新方法，我们不做简单方法。右边新颖性定位：T2L 是 trace 到 line 但做 C/C++；DAIRA、Echo 是 2026 执行接地但没有行级和效率视角，我们给出反例；ARISE 是静态行级 SOTA 当对照。本文双卖点：一是纯执行对行级不灵加机制解释给热潮纠偏，二是执行作反馈闭环的静动结合定位方法。")

prs.save("行级故障定位_汇报.pptx")
print("saved slides:", len(prs.slides._sldIdLst))
