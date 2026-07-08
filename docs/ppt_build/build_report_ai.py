# -*- coding: utf-8 -*-
# Advisor / progress report deck (AI-reframed narrative, 2026-07).
# Paper: "Reachability, Not Discrimination: When Does Execution Grounding Help
#         LLM Line-Level Fault Localization?"  (docs/latex/main.pdf, 21pp)
# Reuses the toolchain of build_ppt.py; ~16 slides for a 10-15 min talk.
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
LGREEN = "E4F1E9"; LRED = "F6E5E4"; SKY = "CADCFC"
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

def arrow(s, x, y, w, h, fill=CORAL, down=False):
    shape = MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW
    shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
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
    text(s, MX, 0.40, SW - 2 * MX, 0.8, [[(t, {"size": 29, "bold": True, "color": tc})]])
    if sub:
        text(s, MX, 1.16, SW - 2 * MX, 0.5, [[(sub, {"size": 15, "color": (TEAL if not dark else SKY)})]])
    rect(s, MX, 1.62, 1.5, 0.05, fill=CORAL)

def box(s, x, y, w, h, label, fill=TINT, tcolor=INK, line="C9D6E0", size=13, bold=True, sub=None):
    rect(s, x, y, w, h, fill=fill, line=line, lw=1.0, rounded=True)
    if sub:
        text(s, x, y, w, h, [[(label, {"bold": bold, "color": tcolor, "size": size})],
                             [(sub, {"color": MUTED, "size": size-3})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=2, line=1.0)
    else:
        text(s, x, y, w, h, [[(label, {"bold": bold, "color": tcolor, "size": size})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# ============================================================================
# Slide 1 — 封面
# ============================================================================
s = slide(NAVY)
text(s, MX, 1.75, SW - 2 * MX, 2.1, [
    [("可达性，而非判别", {"size": 44, "bold": True, "color": WHITE})],
    [("Reachability, Not Discrimination", {"size": 22, "color": SKY})],
    [("——执行接地何时能帮助 LLM 行级故障定位？", {"size": 20, "color": SKY})],
], space_after=10)
rect(s, MX, 4.15, 2.2, 0.06, fill=CORAL)
text(s, MX, 4.45, SW - 2 * MX, 1.5, [
    [("研究进展汇报", {"size": 17, "color": SKY, "bold": True})],
    [("基准 SWE-bench-Lite · 骨干 Qwen2.5-Coder-32B + 3 个开源模型复现 · 目标会议 CCF-B", {"size": 13, "color": "9FB3C8"})],
    [("一项关于自一致性与覆盖率信号的对照研究　|　2026-07", {"size": 13, "color": "9FB3C8"})],
], space_after=7)
notes(s, "各位老师好。今天汇报我这段时间的工作，主题是：在用大模型自动修复软件 issue 时，'执行信息'到底能不能、在什么时候帮助我们更准地定位要改的代码行。\n\n这份工作已经写成一篇 21 页的论文，投稿目标是 CCF-B。标题叫《可达性，而非判别》——这六个字就是全篇的结论，我会在最后让它落地。汇报大概 12 分钟，分四块：为什么做、怎么做、做出了什么、下一步。")

# ============================================================================
# Slide 2 — 一分钟看懂：动机
# ============================================================================
s = slide()
title(s, "大背景：定位是 LLM 修 bug 的命门", "召回率是修复能力的硬上界——找不到的行，再强的模型也修不了")
# left: library analogy / funnel
rect(s, MX, 2.05, 6.0, 4.5, fill=TINT, rounded=True, shadow=True)
text(s, MX+0.35, 2.30, 5.4, 0.5, [[("把代码仓库想成一座图书馆", {"size": 16, "bold": True, "color": NAVY})]])
box(s, MX+0.35, 2.95, 5.3, 0.72, "① 找对是哪本书（文件级定位）",
    fill=LGREEN, tcolor=GREEN, line="BFE0CC", size=13.5, sub="已基本解决：图/检索类方法 ≈ 0.9")
arrow(s, MX+2.85, 3.72, 0.5, 0.4, fill=MUTED, down=True)
box(s, MX+0.35, 4.18, 5.3, 0.72, "② 书里点准哪几句（行级定位）",
    fill=LRED, tcolor=RED, line="E6C6C4", size=13.5, sub="最弱环：最强静态定位器行级召回远低于文件级")
text(s, MX+0.35, 5.15, 5.3, 1.2, [
    [("端到端聚合行级召回仅约 ", {"size": 13.5}), ("47%", {"size": 13.5, "bold": True, "color": CORAL}),
     ("（R@10）", {"size": 13.5})],
    [("——在整个仓库里点准那两三行，才是真瓶颈。", {"size": 13.5})],
], line=1.15, space_after=3)
# right: two lenses
rect(s, 7.15, 2.05, 5.45, 4.5, fill=WHITE, line="C9D6E0", lw=1.2, rounded=True, shadow=True)
text(s, 7.45, 2.30, 4.9, 0.5, [[("贯穿全文的两个视角", {"size": 16, "bold": True, "color": NAVY})]])
box(s, 7.45, 2.88, 4.85, 1.2, "可达性  Reachability",
    fill=TINT2, tcolor=TEAL, line="AECBD8", size=17,
    sub="把金标行送进候选 top-k —— 进没进候选池")
box(s, 7.45, 4.22, 4.85, 1.2, "判别  Discrimination",
    fill=TINT2, tcolor=CORAL, line="E6C6C4", size=17,
    sub="把金标行排到第一 —— 能不能顶到最前")
text(s, 7.45, 5.6, 4.85, 0.85, [
    [("流水线已能买到可达性，却卡在判别——", {"size": 12.5, "color": NAVY, "bold": True})],
    [("本报告问：执行接地能补上判别吗？", {"size": 12.5, "color": CORAL, "bold": True})],
], line=1.1, space_after=1)
notes(s, "先讲为什么。大模型要修一个真实仓库里的 bug，仓库可能几十万行，远超上下文窗口，所以它必须先'定位'——锁定要改哪几行，再动手。这里有个铁律：定位的召回率是修复能力的硬上界，一条从没被定位器呈现出来的行，后面模型再强也修不到。\n\n左边这个漏斗：文件级定位其实已经基本解决了，图和检索方法能做到 0.9 左右；真正的瓶颈是行级——在一本几百页的书里点准那两三句话。端到端的行级召回只有 47% 左右。\n\n右边引入全文最重要的两个概念，请老师记住：'可达性'是指把正确的行送进候选 top-k（进没进池子）；'判别'是指把它排到第一（顶没顶到最前）。后面所有结果都围绕这两个词展开。")

# ============================================================================
# Slide 3 — 研究问题
# ============================================================================
s = slide()
title(s, "核心问题：执行接地，能补上自一致性缺的那块吗？", "2026 一波方法主张：跑失败测试，把覆盖率喂给定位器")
rect(s, MX, 2.0, SW-2*MX, 1.25, fill=NAVY, rounded=True, shadow=True)
text(s, MX+0.4, 2.0, SW-2*MX-0.8, 1.25, [
    [("流水线自己靠", {"size": 16, "color": WHITE}), ("自一致性投票", {"size": 16, "bold": True, "color": SKY}),
     ("买到可达性，但停在一个天花板：常把金标送进 top-10，却很少排第一。", {"size": 16, "color": WHITE})],
    [("那么——外部的", {"size": 16, "color": WHITE}), ("执行接地", {"size": 16, "bold": True, "color": AMBER}),
     ("，能不能补上它缺的『判别力』？", {"size": 16, "bold": True, "color": WHITE})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.2, space_after=6)
rqs = [
    ("RQ1", "地形", "召回到底丢在哪？\n六维分层，找出主导因素", TEAL),
    ("RQ2", "证伪 + 根因", "覆盖率当直接信号，\n能增加判别力吗？", CORAL),
    ("RQ3", "正确用法", "那它到底有没有\n有效的用法？", GREEN),
]
cw = (SW - 2*MX - 2*0.4) / 3
for i, (tag, name, desc, col) in enumerate(rqs):
    x = MX + i*(cw+0.4)
    rect(s, x, 3.55, cw, 2.5, fill=WHITE, line="C9D6E0", lw=1.2, rounded=True, shadow=True)
    chip(s, x+0.3, 3.8, 1.3, 0.5, col, WHITE, tag, size=15)
    text(s, x+1.75, 3.8, cw-2.0, 0.5, [[(name, {"size": 16, "bold": True, "color": NAVY})]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x+0.3, 4.5, cw-0.6, 1.4, [[(desc, {"size": 14, "color": INK})]], line=1.2)
rect(s, MX, 6.2, SW-2*MX, 0.82, fill=TINT2, rounded=True)
text(s, MX+0.3, 6.2, SW-2*MX-0.6, 0.82, [
    [("先前工作：静态 SOTA（ARISE）从不跑代码 · 执行-LLM（AutoFL / AgentFL）只把覆盖率当未检验的过滤器 / 补丁校验（函数级）", {"size": 10.5, "color": INK})],
    [("本文：首次在行粒度、真实 issue 上检验『覆盖率何时 / 为何』有用 —— 基线排序器是 def-use 分数的独立重实现，仅作同输入内部对照、不比绝对值", {"size": 10.5, "color": NAVY, "bold": True})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.15, space_after=2)
notes(s, "带着这个背景，看我要回答的核心问题。2026 年出现一波'执行接地'的方法：把那个会失败的测试真跑一遍，把覆盖率、回溯栈喂给定位器，依据是一个几十年的老直觉——失败测试跑到的代码，就是 bug 所在。\n\n但有个反差：当前最强的行级定位器 ARISE 其实是纯静态的，它建程序图、做数据流切片，却从不真跑代码。一边是几十年的执行派传统，一边是静态的 SOTA，加上'执行理应有用'的新假设——这就逼出我的核心问题：执行接地能不能在模型自身自一致性之上，补上它缺的那块判别力？\n\n我把它拆成三个自成一体的研究问题：RQ1 先画地图——召回丢在哪；RQ2 证伪——覆盖率当直接信号行不行；RQ3 找正确用法。")

# ============================================================================
# Slide 4 — 研究设计
# ============================================================================
s = slide()
title(s, "研究设计：把『覆盖率的作用』干净地隔离出来", "同一金标文件内排序，带/不带覆盖率配对对照——差异只归因于执行接地")
# pipeline diagram
py = 2.15
labels = ["文件定位", "区域收窄", "自一致性投票\n(k 采样)", "RRF 排序\n(def-use 图)"]
bw = 2.55; gap = 0.42; x0 = MX
for i, lab in enumerate(labels):
    x = x0 + i*(bw+gap)
    box(s, x, py, bw, 1.05, lab, fill=TINT, tcolor=NAVY, size=14.5)
    if i < 3:
        arrow(s, x+bw+0.02, py+0.32, gap-0.04, 0.4, fill=TEAL)
# coverage lane
rect(s, x0, py+1.55, bw, 0.95, fill=LRED, line="E6C6C4", rounded=True)
text(s, x0, py+1.55, bw, 0.95, [[("失败测试执行覆盖率", {"size": 13.5, "bold": True, "color": RED})],
                                 [("（Docker 内采集）", {"size": 11, "color": MUTED})]],
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=1)
arrow(s, x0+bw+0.02, py+1.8, (bw+gap)*3-0.4, 0.4, fill=CORAL)
text(s, x0+bw+0.2, py+2.55, (bw+gap)*3, 0.4, [[("→ 作为『带/不带』的那个对照变量", {"size": 12.5, "color": CORAL, "bold": True})]])
# bottom design choices
yb = 5.35
cols = [
    ("基准", "SWE-bench-Lite 300 例\n100% 单一金标文件", TEAL),
    ("口径 = file-given", "只在金标文件内排序\n旁路文件定位噪声", CORAL),
    ("分层", "crash / on-path =\n金标行被失败测试真执行到", AMBER),
    ("稳健性", "4 个骨干模型\n复现主结果", GREEN),
]
cwid = (SW-2*MX-3*0.35)/4
for i, (h, d, col) in enumerate(cols):
    x = MX + i*(cwid+0.35)
    rect(s, x, yb, cwid, 1.35, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
    rect(s, x, yb, cwid, 0.42, fill=col, rounded=False)
    text(s, x, yb, cwid, 0.42, [[(h, {"size": 12.5, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x+0.1, yb+0.5, cwid-0.2, 0.8, [[(d, {"size": 12, "color": INK})]], align=PP_ALIGN.CENTER, line=1.1)
notes(s, "研究设计的关键，是把'覆盖率的作用'干净地隔离出来。上面这条流水线是我的基线：文件定位 → 区域收窄（把 2000 行缩到约 200 行）→ 自一致性投票（多次采样取并集，负责挣召回）→ RRF 排序（融合投票、def-use 图分数、跨采样共识来定顺序）。下面红色那条是执行覆盖率，它就是我要研究的那个'带 / 不带'的对照变量。\n\n四个设计决定：第一，基准用 SWE-bench-Lite 全部 300 例，都是单一金标文件；第二，也是最关键的——评测口径是 file-given，也就是只在给定的正确文件内部排序，把文件定位那层噪声旁路掉，这样任何差异都只来自执行接地本身；第三，重点分析 crash 且 on-path 的子集，也就是执行原则上能帮上忙的地方；第四，主结果在 4 个骨干模型上复现，保证不是单个模型的偶然。")

# ============================================================================
# Slide 5 — RQ1 地形
# ============================================================================
s = slide()
title(s, "RQ1｜地形：召回主要丢在『文件闸门』和『大文件』", "六维分层（Qwen2.5-Coder-32B, n=300）")
cd = CategoryChartData()
cd.categories = ["文件命中", "文件未命中"]
cd.add_series("行 R@10 (%)", (63.3, 0.0))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MX), Inches(2.15), Inches(4.0), Inches(3.0), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = False
pl = ch.plots[0]; pl.has_data_labels = True; pl.gap_width = 90
pl.data_labels.number_format = '0.0"%"'; pl.data_labels.number_format_is_linked = False
pl.data_labels.font.size = Pt(15); pl.data_labels.font.bold = True; pl.data_labels.font.color.rgb = C(NAVY)
for i, pt in enumerate(pl.series[0].points):
    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = C([GREEN, RED][i])
ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = 70
ch.category_axis.tick_labels.font.size = Pt(12); ch.category_axis.tick_labels.font.color.rgb = C(INK)
text(s, MX, 5.2, 4.0, 0.5, [[("文件级定位 = 一阶闸门", {"size": 13.5, "bold": True, "color": NAVY})]], align=PP_ALIGN.CENTER)
text(s, MX, 5.5, 4.0, 1.15, [[("多文件下全部金标文件命中率仅 ", {"size": 12}), ("35%", {"size": 12, "bold": True, "color": CORAL}),
                              (" → 全局召回坍缩到 0.277", {"size": 12})],
                             [("（示例性：Table 2 · DeepSeek-V3 · SWE-bench Verified 多文件 n=20；非 Qwen n=300 设定）", {"size": 9.5, "color": MUTED})]],
     align=PP_ALIGN.CENTER, line=1.1, space_after=2)
# right panel: findings
rect(s, 5.05, 2.15, 7.55, 4.55, fill=TINT, rounded=True, shadow=True)
text(s, 5.4, 2.4, 6.9, 4.1, [
    [("五点发现", {"size": 15, "bold": True, "color": CORAL})],
    [("① 文件闸门主导：", {"size": 13.5, "bold": True, "color": NAVY}), ("命中 63.3% vs 未命中 0%。", {"size": 13.5})],
    [("② 大文件是精确率墙：", {"size": 13.5, "bold": True, "color": NAVY}),
     ("R@10 随规模 51→29，即便给定文件也如此。", {"size": 13.5})],
    [("③ 领域差异被低报：", {"size": 13.5, "bold": True, "color": NAVY}),
     ("scikit-learn 26% ≪ django 54%。", {"size": 13.5})],
    [("④ 多行修复伤『找全』：", {"size": 13.5, "bold": True, "color": NAVY}),
     ("金标行越多，给定命中召回 45→38。", {"size": 13.5})],
    [("⑤ 缺陷类型不影响可达召回：", {"size": 13.5, "bold": True, "color": NAVY}),
     ("crash 46.8% ≈ behavioral 46.6%。", {"size": 13.5})],
    [("", {"size": 5})],
    [("→ ⑤是关键伏笔：缺陷类型改变的是执行『如何』帮忙，", {"size": 13, "color": CORAL, "bold": True})],
    [("　 而非一条行『是否』可定位。", {"size": 13, "color": CORAL, "bold": True})],
], line=1.3, space_after=6)
notes(s, "RQ1 是画地图：召回到底丢在哪。我沿六个维度对 300 个实例分层，讲五点。\n\n第一，也是最重要的：文件级定位是一阶闸门——文件找对了行召回 63.3%，找错了就是 0，没有中间地带。多文件设定下，把所有该改的文件都找全只有 35%，单这一点就能解释全局召回坍缩到 0.277。第二，大文件是一堵精确率墙，即便把正确文件给你，文件越大召回越低，从 51% 掉到 29%。第三，领域复杂度差异很大但常被低报，科学计算库比 web 框架难得多。第四，多行修复更难'找全'。\n\n第五点是关键伏笔：缺陷类型 crash 和 behavioral 的可达召回几乎一样。这说明——缺陷类型改变的不是一条行能不能被定位，而是'执行信息怎么帮忙'。这正好把接力棒交给 RQ2。")

# ============================================================================
# Slide 6 — RQ2 证伪
# ============================================================================
s = slide()
title(s, "RQ2｜证伪：覆盖率当『直接信号』——不行", "三个机理性、可证伪的根因")
cards = [
    ("① 太粗", "中位 259 行 / 金标文件", "覆盖率本身没有内部排序——\n是一个约 259 行的『大草垛』", RED),
    ("② 83% 结构天花板", "只有 57/68 有金标行被执行", "16% 的修复改在没跑过的代码：\n漏分支 6 + 插入 4 + 未达函数 1", RED),
    ("③ SBFL(谱系) 差分依缺陷而定", "9 例中仅 3 例控制流可区分", "对数据层缺陷，『仅失败』集合\n为空、根本不含金标", RED),
]
cw = (SW-2*MX-2*0.4)/3
for i, (h, big, d, col) in enumerate(cards):
    x = MX + i*(cw+0.4)
    rect(s, x, 2.1, cw, 3.35, fill=WHITE, line="E6C6C4", lw=1.2, rounded=True, shadow=True)
    rect(s, x, 2.1, cw, 0.62, fill=col, rounded=False)
    text(s, x, 2.1, cw, 0.62, [[(h, {"size": 15, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x+0.25, 2.9, cw-0.5, 0.7, [[(big, {"size": 13.5, "bold": True, "color": NAVY})]], line=1.1)
    text(s, x+0.25, 3.75, cw-0.5, 1.6, [[(d, {"size": 13, "color": INK})]], line=1.25)
rect(s, MX, 5.75, SW-2*MX, 0.95, fill=NAVY, rounded=True)
text(s, MX+0.4, 5.75, SW-2*MX-0.8, 0.95, [
    [("结论：把执行覆盖率用作『直接候选集』或『排序信号』——在真实 issue 上被证伪。", {"size": 15.5, "bold": True, "color": WHITE})],
], anchor=MSO_ANCHOR.MIDDLE)
notes(s, "RQ2 我给出一个机理性的、可证伪的三段根因，说明覆盖率当直接信号为什么不行。\n\n第一，太粗：每个金标文件中位数有 259 行被执行，而且覆盖率内部没有任何排序，就是个 259 行的大草垛。第二，有个 83% 的结构性天花板：crash 实例里只有 57/68 有金标行真被执行到；剩下 16% 的修复改的是根本没跑过的代码——6 个是走错了分支、修复在没走的那条路上，4 个是纯新增代码，1 个是没被调用的函数。这类没有任何执行方法能救。第三，正规 SBFL 要用'失败 vs 通过'的差分，但这个差分依赖缺陷类型：我采集的 9 个跨仓库例子里只有 3 个是控制流可区分的；对数据层缺陷，'仅失败'集合是空的，压根不含金标。\n\n所以结论很硬：把覆盖率当直接候选集或排序信号，在真实 issue 上被证伪。")

# ============================================================================
# Slide 7 — 统一区分 (Figure 2, 核心)
# ============================================================================
s = slide()
title(s, "全文的概念核心：控制流缺陷 vs 数据层缺陷", "覆盖率 / 回溯 / SBFL 都只是『成员关系（控制流）信号』——只告诉你哪些行跑过")
# (a) works
rect(s, MX, 2.05, 5.75, 4.05, fill=LGREEN, line="BFE0CC", lw=1.2, rounded=True, shadow=True)
text(s, MX+0.35, 2.28, 5.1, 0.5, [[("(a) 控制流可区分缺陷 ✔ 信号生效", {"size": 15.5, "bold": True, "color": GREEN})]])
text(s, MX+0.35, 2.85, 5.1, 1.6, [
    [("失败输入走了一条", {"size": 13.5}), ("不同的路径", {"size": 13.5, "bold": True, "color": GREEN}),
     ("，", {"size": 13.5})],
    [("金标行出现在『仅失败』覆盖里。", {"size": 13.5})],
    [("", {"size": 5})],
    [("→ 覆盖率过滤、SBFL 差分、回溯栈", {"size": 13, "color": INK})],
    [("　 三者全部生效。", {"size": 13, "color": INK})],
], line=1.25, space_after=4)
chip(s, MX+0.35, 5.25, 5.05, 0.62, WHITE, GREEN, "例：matplotlib-22711（5/13 金标在仅失败集合）", size=12)
# (b) fails
rect(s, 6.85, 2.05, 5.75, 4.05, fill=LRED, line="E6C6C4", lw=1.2, rounded=True, shadow=True)
text(s, 7.2, 2.28, 5.1, 0.5, [[("(b) 数据层缺陷 ✘ 信号失效", {"size": 15.5, "bold": True, "color": RED})]])
text(s, 7.2, 2.85, 5.1, 2.1, [
    [("同样的行", {"size": 13.5, "bold": True, "color": RED}), ("在通过和失败测试里都跑到，", {"size": 13.5})],
    [("→ SBFL 差分为空、没有排序信号；", {"size": 13, "color": INK})],
    [("或修复落在出错运行", {"size": 13.5}), ("跳过的分支", {"size": 13.5, "bold": True, "color": RED}), ("上。", {"size": 13.5})],
    [("", {"size": 5})],
    [("→ 覆盖率只剩『成员关系』= 一个过滤器。", {"size": 13, "color": INK})],
], line=1.25, space_after=4)
chip(s, 7.2, 5.25, 5.05, 0.62, WHITE, RED, "例：astropy-14182（0/14）· django-14017（漏分支）", size=12)
rect(s, MX, 6.35, SW-2*MX, 0.72, fill=NAVY, rounded=True)
text(s, MX, 6.35, SW-2*MX, 0.72, [[("SWE-bench 以 (b) 数据层为主导（直接测 9/12，代理外推 49–66%，为指示性）——这条区分统一解释了 RQ2 的每个负面结果。", {"size": 13, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "这一页是全篇的概念核心，请老师重点看。所有失败都能用一条区分解释：控制流缺陷 vs 数据层缺陷。\n\n关键洞察是：覆盖率、回溯栈、SBFL 本质上都是'控制流信号'，它们只告诉你哪些行跑过、按什么顺序跑。\n\n左边(a)：当 bug 改变了控制流，失败输入走一条不同的路，金标行就出现在'仅失败'的覆盖里——这时覆盖率过滤、SBFL 差分、回溯栈全都生效，比如 matplotlib-22711。右边(b)：当 bug 是数据层的——同样的行在通过和失败里都会跑，只是算出的值错了，差分就是空的；或者修复落在出错运行跳过的那条分支上。这时覆盖率只剩'成员关系'这一点信息，也就是只能当过滤器。\n\n而 SWE-bench 绝大多数是(b)。这一条区分，预测了 RQ2 里每一个负面结果。")

# ============================================================================
# Slide 8 — RQ3 过滤器有效
# ============================================================================
s = slide()
title(s, "RQ3｜正确用法：覆盖率作『召回侧过滤器』", "crash on-path 子集，file-given，def-use 排序器")
cd = CategoryChartData()
cd.categories = ["静态 def-use", "+ 覆盖率过滤"]
cd.add_series("行 R@10 (%)", (29.8, 43.9))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MX), Inches(2.1), Inches(4.2), Inches(3.2), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = False
pl = ch.plots[0]; pl.has_data_labels = True; pl.gap_width = 100
pl.data_labels.number_format = '0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.font.size = Pt(16); pl.data_labels.font.bold = True; pl.data_labels.font.color.rgb = C(NAVY)
for i, pt in enumerate(pl.series[0].points):
    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = C([MUTED, TEAL][i])
ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = 50
ch.category_axis.tick_labels.font.size = Pt(12); ch.category_axis.tick_labels.font.color.rgb = C(INK)
text(s, MX, 5.28, 4.2, 1.3, [[("+14.1pp", {"size": 21, "bold": True, "color": CORAL})],
                             [("95% CI [3.5, 24.6]，候选集 −55%", {"size": 11.5, "color": MUTED})],
                             [("= oracle 路由机理上界；可部署下限 +4.5pp（n=57）", {"size": 10.5, "color": MUTED})]],
     align=PP_ALIGN.CENTER, space_after=1, line=1.05)
# right: mechanism + example
rect(s, 5.15, 2.1, 7.45, 4.6, fill=TINT, rounded=True, shadow=True)
text(s, 5.5, 2.35, 6.8, 4.2, [
    [("机理：删掉未执行的干扰项，被执行的金标存活并上浮", {"size": 14.5, "bold": True, "color": NAVY})],
    [("", {"size": 4})],
    [("工作实例  django-16873（982 行文件）", {"size": 13.5, "bold": True, "color": CORAL})],
    [("• 静态排序器给 656 个候选，金标排在 ", {"size": 13}), ("第 40 位", {"size": 13, "bold": True, "color": RED}), ("（漏）", {"size": 13})],
    [("• 限制到失败测试真执行的 75 行（削 88%）", {"size": 13})],
    [("• 金标上浮到 ", {"size": 13}), ("第 6 位", {"size": 13, "bold": True, "color": GREEN}),
     ("——命中，候选集缩小 8.7×", {"size": 13})],
    [("", {"size": 5})],
    [("→ 召回与精确率在同一实例上一起上升。", {"size": 13.5, "color": GREEN, "bold": True})],
    [("", {"size": 5})],
    [("⚠ 但必须路由：off-path 会删掉金标（→0）；", {"size": 13, "bold": True, "color": RED})],
    [("　 此时回退纯静态（那里静态仍有 45.5）。", {"size": 13, "color": INK})],
], line=1.25, space_after=4)
notes(s, "RQ3 给出唯一有效的用法：把覆盖率当'召回侧过滤器'。做法是把候选限制到失败测试真执行到的行。\n\n左边柱图：在 crash on-path 子集上，行 R@10 从 29.8 提升到 43.9，也就是 +14.1 个百分点，置信区间 [3.5, 24.6] 显著，而且候选集同时缩小了 55%。\n\n右边用一个实例讲机理，django-16873，982 行的文件：静态排序器给出 656 个候选，把金标排在第 40 位，R@10 漏掉；把范围限制到失败测试真跑到的 75 行，删掉了 88% 的干扰项，金标就上浮到第 6 位命中了，候选集缩小 8.7 倍。注意——排序器本身没变，纯粹靠删掉结构上不相关的行，召回和精确率在同一个实例上一起上升。\n\n但有个硬约束：必须路由。off-path 的实例，过滤会把金标删掉直接归零；所以 off-path 必须回退到纯静态——而静态在那里其实还有 45.5。这就规定了'on-path 过滤、off-path 回退'的设计。")

# ============================================================================
# Slide 9 — 流水线验证 + 可达性≠判别
# ============================================================================
s = slide()
title(s, "在完整流水线中复刻，并揭示：提升的是可达性，不是判别", "投票 + 图 + LLM 全流水线，crash on-path, n=57")
cd = CategoryChartData()
cd.categories = ["R@1", "R@5", "R@10"]
cd.add_series("M0 静态", (29.8, 50.9, 56.1))
cd.add_series("M4 覆盖率最大化", (35.1, 52.6, 68.4))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MX), Inches(2.1), Inches(6.3), Inches(4.3), cd)
ch = gf.chart; ch.has_title = False
ch.has_legend = True; ch.legend.position = 2; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12)
pl = ch.plots[0]; pl.has_data_labels = True; pl.gap_width = 80
pl.data_labels.number_format = '0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.font.size = Pt(11); pl.data_labels.font.bold = True; pl.data_labels.font.color.rgb = C(INK)
ch.series[0].format.fill.solid(); ch.series[0].format.fill.fore_color.rgb = C(MUTED)
ch.series[1].format.fill.solid(); ch.series[1].format.fill.fore_color.rgb = C(TEAL)
ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = 78
ch.category_axis.tick_labels.font.size = Pt(13); ch.category_axis.tick_labels.font.color.rgb = C(INK)
text(s, 3.0, 2.05, 2.2, 0.4, [[("n.s.", {"size": 12, "color": MUTED})]], align=PP_ALIGN.CENTER)
rect(s, 7.35, 2.1, 5.25, 4.55, fill=TINT, rounded=True, shadow=True)
text(s, 7.65, 2.35, 4.7, 4.1, [
    [("增益集中在 R@10：", {"size": 14.5, "bold": True, "color": NAVY})],
    [("+12.3pp", {"size": 24, "bold": True, "color": CORAL}), ("  CI [1.8, 22.8] 显著 (n=57)", {"size": 11.5, "color": MUTED})],
    [("", {"size": 4})],
    [("• R@1(+5.3) / R@5(+1.8) 不显著", {"size": 13})],
    [("→ 提升", {"size": 13.5}), ("可达性", {"size": 13.5, "bold": True, "color": TEAL}),
     ("，而非", {"size": 13.5}), ("判别", {"size": 13.5, "bold": True, "color": CORAL})],
    [("", {"size": 6})],
    [("覆盖率『分数项』毫无贡献：", {"size": 13.5, "bold": True, "color": NAVY})],
    [("M3 ≡ M0", {"size": 16, "bold": True, "color": RED})],
    [("过滤=成员关系操作；打分才需", {"size": 12.5, "color": INK})],
    [("判别力——而覆盖率不含它。", {"size": 12.5, "color": INK})],
    [("", {"size": 5})],
    [("＝ 在 Qwen2.5-Coder 上与自一致性撞同一道", {"size": 12.5, "bold": True, "color": CORAL})],
    [("　 天花板（更强骨干 R@5 也升，见下页）。", {"size": 12.5, "bold": True, "color": CORAL})],
], line=1.2, space_after=4)
notes(s, "刚才是离线、无 LLM 的隔离实验。这一页把它放回完整的'投票+图+LLM'流水线，看结论是否还成立——成立。\n\n把投票收窄到被执行的行，R@10 从 56.1 提升到 68.4，+12.3 个百分点，置信区间 [1.8, 22.8]，显著。\n\n但这一页真正重要的是右边的机理。增益几乎全集中在 R@10；R@1、R@5 都不显著。也就是说，覆盖率提升的是'可达性'——把金标送进 top-10；而不是'判别'——把它排第一。还有一个更硬的证据：覆盖率的'分数项'完全没用，M3 等于 M0，一模一样。因为过滤是个'成员关系'操作，而打分需要判别力，覆盖率里根本不含判别力。\n\n这就回到标题：覆盖率和自一致性撞的是同一道天花板。两者都买到可达性，都买不到判别。")

# ============================================================================
# Slide 10 — 跨骨干复现
# ============================================================================
s = slide()
title(s, "稳健性：过滤器增益在 4 个骨干上复现", "M4−M0 行 R@10，file-given, n=57，协议一致（含 3 个跨系列开源模型）")
cd = CategoryChartData()
cd.categories = ["Qwen2.5-Coder-32B", "Qwen3.6-27B", "DeepSeek-V3.2", "GLM-4.5-Air"]
cd.add_series("ΔR@10 (pp)", (12.3, 22.8, 8.8, 8.8))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MX), Inches(2.1), Inches(7.1), Inches(4.2), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = False
pl = ch.plots[0]; pl.has_data_labels = True; pl.gap_width = 70
pl.data_labels.number_format = '+0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.font.size = Pt(15); pl.data_labels.font.bold = True; pl.data_labels.font.color.rgb = C(NAVY)
for i, pt in enumerate(pl.series[0].points):
    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = C([TEAL, GREEN, TEAL, AMBER][i])
ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = 26
ch.category_axis.tick_labels.font.size = Pt(11); ch.category_axis.tick_labels.font.color.rgb = C(INK)
rect(s, 8.05, 2.1, 4.55, 4.2, fill=TINT, rounded=True, shadow=True)
text(s, 8.35, 2.35, 4.0, 3.8, [
    [("ΔR@10 ", {"size": 15, "bold": True, "color": NAVY}), ("4/4 为正", {"size": 15, "bold": True, "color": GREEN})],
    [("其中 ", {"size": 14}), ("3/4 显著", {"size": 14, "bold": True, "color": GREEN}), ("（CI 不含 0）", {"size": 13, "color": MUTED})],
    [("GLM-4.5-Air 点估计同样 +8.8，", {"size": 12.5})],
    [("仅因 n=57 未达显著。", {"size": 12.5})],
    [("", {"size": 8})],
    [("一点细节：", {"size": 13.5, "bold": True, "color": CORAL})],
    [("『只提 R@10』是 Qwen2.5 特有；", {"size": 12.5})],
    [("更强骨干上 R@5 也一起提升", {"size": 12.5})],
    [("（+15.8 / +8.8 / +17.5pp）。", {"size": 12.5})],
    [("→ 头条效应可泛化，", {"size": 12.5, "bold": True, "color": NAVY})],
    [("　 判别是否随之改善依赖骨干。", {"size": 12.5, "color": INK})],
], line=1.25, space_after=4)
notes(s, "这一页是稳健性，也是我这段时间新补的实验。我把头条的 M0 vs M4 对照，在另外三个横跨不同系列、不同规模的开源模型上重跑，协议完全一致。\n\n结论：过滤器增益复现——ΔR@10 在 4 个骨干上全部为正，其中 3 个显著、置信区间不含 0：Qwen2.5-Coder +12.3、Qwen3.6-27B +22.8、DeepSeek-V3.2 +8.8。第四个 GLM-4.5-Air 点估计也是 +8.8，只是 n=57 样本量下没达到显著。\n\n有一点要诚实说明：'增益只集中在 R@10'这个现象是 Qwen2.5-Coder 特有的；在更强的骨干上，R@5 也一起提升了。所以'过滤器提升可达性'这个头条结论是可泛化的；但它是否连带改善判别，则依赖具体骨干。")

# ============================================================================
# Slide 11 — 为何判别是难轴 + 异质验证器
# ============================================================================
s = slide()
title(s, "为何『判别』是难轴？异质验证器能破天花板吗", "生成器–验证器不对称：自一致性用的都是与候选同源的信号")
text(s, MX, 1.85, SW-2*MX, 0.6, [
    [("自一致性的信号（投票数、覆盖率成员、def-use 邻接）都", {"size": 13.5}),
     ("与候选同源", {"size": 13.5, "bold": True, "color": CORAL}),
     ("：能证明『到达』，却不能把出错行与其邻居区分开。", {"size": 13.5})],
], line=1.2)
cd = CategoryChartData()
cd.categories = ["基线\nQwen-M4", "+真实 DeepSeek\n重排(无金标)", "oracle 并集\n(上界)"]
cd.add_series("R@1 (%)", (35.1, 42.1, 49.1))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MX), Inches(2.75), Inches(7.0), Inches(3.65), cd)
ch = gf.chart; ch.has_title = False; ch.has_legend = False
pl = ch.plots[0]; pl.has_data_labels = True; pl.gap_width = 90
pl.data_labels.number_format = '0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.font.size = Pt(17); pl.data_labels.font.bold = True; pl.data_labels.font.color.rgb = C(NAVY)
for i, pt in enumerate(pl.series[0].points):
    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = C([MUTED, TEAL, GREEN][i])
ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = 56
ch.category_axis.tick_labels.font.size = Pt(11.5); ch.category_axis.tick_labels.font.color.rgb = C(INK)
text(s, MX, 6.45, 7.0, 0.4, [[("图示为 R@1（把出错行排到第一）——R@5 / R@10 详见备注", {"size": 11, "color": MUTED})]], align=PP_ALIGN.CENTER)
rect(s, 7.9, 2.55, 4.7, 3.9, fill=TINT, rounded=True, shadow=True)
text(s, 8.2, 2.8, 4.15, 3.5, [
    [("oracle 并集上界（换个异质模型）", {"size": 13, "bold": True, "color": GREEN})],
    [("R@1 +14.0pp 全显著", {"size": 13})],
    [("→ 天花板", {"size": 13}), ("并非同模型固有", {"size": 13, "bold": True, "color": GREEN})],
    [("", {"size": 6})],
    [("真实 DeepSeek 重排（不给金标）", {"size": 13, "bold": True, "color": TEAL})],
    [("+7.0 / +12.3 / +8.8pp", {"size": 13})],
    [("→ 实现了上界的约", {"size": 13}), ("一半", {"size": 13, "bold": True, "color": TEAL}),
     ("（n=57 未达显著）", {"size": 11.5, "color": MUTED})],
    [("", {"size": 6})],
    [("判别力可以挽回——但要靠", {"size": 13, "bold": True, "color": NAVY})],
    [("与覆盖率、与同模型自一致性", {"size": 13, "color": INK})],
    [("都正交的信号。", {"size": 13, "color": INK})],
], line=1.22, space_after=4)
notes(s, "这一页回答'为什么判别这么难'，也是新补的实验。原因和大模型推理里熟知的'生成器-验证器不对称'同源：流水线的排序是模型自己投票产生的，而它能用的信号——投票数、覆盖率成员、def-use 邻接——全都跟候选集同源，只能证明'到达'，没法把出错行和邻居区分开。\n\n那这道天花板是任务固有的，还是只是'同一个模型自己验自己'的局限？我做了两个实验。一是 oracle 上界：每个实例取基线模型和一个更强的异质模型 DeepSeek 的并集，R@1 直接 +14 个百分点，全显著——说明天花板不是同模型固有的，换个正交视角就能挽回。二是可部署版本：让 DeepSeek 只看 issue 和候选代码、不给金标，去重排，结果实现了上界的大约一半，+7/+12.3/+8.8，n=57 下还不显著。\n\n结论：判别力是可以挽回的，但必须靠与覆盖率、与同模型自一致性都正交的信号。这直接指向下一步。")

# ============================================================================
# Slide 12 — 贡献 + 信号类型学
# ============================================================================
s = slide()
title(s, "四大贡献：一条『信号类型学』串起全部结果", None)
items = [
    ("1", "刻画『行定位为何失败』", "六维分层：文件闸门、大文件精确率墙、强领域效应——被聚合数字掩盖的因素。", TEAL),
    ("2", "证伪『覆盖率作直接信号』", "机理性根因：粗粒度、83% 结构天花板、依缺陷而定且对数据层为空的 SBFL 差分。", CORAL),
    ("3", "覆盖率作过滤器 + 精确边界", "on-path +14pp R@10 / −55% 候选，4 骨干复现；路由必需，更精细用法全部失败。", GREEN),
    ("4", "统一信号类型学（核心）", "自一致性与覆盖率都是『成员关系信号』：证明可达、不含判别——故都撞 R@1 天花板。", NAVY),
]
y = 2.05; rh = 1.15
for i, (n, h, d, col) in enumerate(items):
    yy = y + i*(rh+0.12)
    rect(s, MX, yy, SW-2*MX, rh, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True, shadow=(i==3))
    rect(s, MX, yy, 0.14, rh, fill=col)
    chip(s, MX+0.35, yy+0.32, 0.55, 0.55, col, WHITE, n, size=18)
    text(s, MX+1.15, yy+0.12, 4.4, rh-0.2, [[(h, {"size": 15.5, "bold": True, "color": NAVY})]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, MX+5.7, yy+0.12, SW-2*MX-5.9, rh-0.2, [[(d, {"size": 13, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE, line=1.2)
notes(s, "把结果收拢成四大贡献。第一，刻画了行定位为什么失败——六维分层，暴露出被聚合数字掩盖的因素。第二，证伪了'覆盖率作直接信号'，并给出机理性根因。第三，给出唯一有效的用法'覆盖率作过滤器'，以及它精确的边界：on-path 上 +14pp、候选减半，4 个骨干复现，但路由是必需的，所有更精细的用法都失败了。\n\n第四是核心，也是把前三个串起来的那条主线——一套'信号类型学'：模型自身的自一致性和外部的执行覆盖率，本质上是同一类东西，都是'成员关系信号'，只能证明一条行可达、不含判别信息，所以它们都撞在同一道 R@1 天花板上。这一条区分，能预测前面每一个负面结果。")

# ============================================================================
# Slide 13 — 局限
# ============================================================================
s = slide()
title(s, "局限与有效性威胁（已在论文 §8 逐条交代）", None)
lims = [
    ("离线排序器构念", "RQ2/3 用无 LLM 的 def-use 隔离信号——但头条效应已在完整流水线确认（+12.3pp）且 4 骨干复现。", TEAL),
    ("oracle 路由（最关键）", "on/off-path 划分用了金标，不可直接部署；可部署下限 +4.5pp，需一个 gold-free 的 on-path 检测器。", CORAL),
    ("复现测试依赖", "过滤器需要失败测试存在并在 Docker 中执行；新 issue 上该测试要先被生成（开放问题）。", AMBER),
    ("单基准 / 单语言", "结论限于 SWE-bench-Lite / Python。在 Defects4J 等控制流可区分的崩溃基准上，SBFL 可能有效——已划界，非矛盾。", MUTED),
]
y = 2.05; rh = 1.12
for i, (h, d, col) in enumerate(lims):
    yy = y + i*(rh+0.12)
    rect(s, MX, yy, SW-2*MX, rh, fill=TINT, line="C9D6E0", lw=1.0, rounded=True)
    rect(s, MX, yy, 0.14, rh, fill=col)
    text(s, MX+0.45, yy+0.12, 3.5, rh-0.2, [[(h, {"size": 14.5, "bold": True, "color": NAVY})]], anchor=MSO_ANCHOR.MIDDLE, line=1.1)
    text(s, MX+4.1, yy+0.12, SW-2*MX-4.3, rh-0.2, [[(d, {"size": 13, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE, line=1.2)
notes(s, "局限我在论文第 8 节逐条交代，这里挑四个最重要的。\n\n第一，离线排序器是个构念简化，但头条效应已经在完整流水线里确认过、也在 4 个骨干上复现了，所以不是伪影。第二，也是最关键的：on/off-path 的路由用到了金标行，所以严格说不能直接部署；我给了一个可部署的下限 +4.5pp，真正落地需要一个不依赖金标的 on-path 检测器。第三，过滤器依赖失败测试存在并能在 Docker 里跑出覆盖率；对一个全新 issue，这个测试得先被生成，这本身是开放问题。第四，结论限于 SWE-bench-Lite 和 Python；在 Defects4J 这类控制流可区分的崩溃基准上，SBFL 可能就有效——我是在给它划界，而不是否定它。")

# ============================================================================
# Slide 14 — 下一步 RQ4
# ============================================================================
s = slide()
title(s, "下一步（RQ4）：什么信号能打破『判别天花板』", "可达性已近饱和，判别是墙——答案要向『正交信号』找")
rect(s, MX, 2.1, 5.75, 4.3, fill=TINT, rounded=True, shadow=True)
text(s, MX+0.35, 2.35, 5.1, 0.5, [[("方向一：与覆盖率正交的信号", {"size": 15.5, "bold": True, "color": TEAL})]])
text(s, MX+0.35, 3.0, 5.1, 3.2, [
    [("• 失败测试的", {"size": 13.5}), ("期望值 vs 观测值", {"size": 13.5, "bold": True, "color": NAVY}),
     ("（断言接地重排——已是初步的、依骨干的一步）", {"size": 13.5})],
    [("", {"size": 5})],
    [("• 更丰富的执行信号：", {"size": 13.5, "bold": True, "color": NAVY})],
    [("  变异测试、值 / 状态追踪、污点分析", {"size": 13.5})],
    [("  ——可能触及数据层缺陷，本文未检验。", {"size": 13, "color": MUTED})],
], line=1.3, space_after=5)
rect(s, 6.85, 2.1, 5.75, 4.3, fill=TINT, rounded=True, shadow=True)
text(s, 7.2, 2.35, 5.1, 0.5, [[("方向二：异质 / 更强的验证器", {"size": 15.5, "bold": True, "color": CORAL})]])
text(s, 7.2, 2.95, 5.1, 3.4, [
    [("• oracle 上界已证明：换个异质模型，", {"size": 13})],
    [("  判别天花板", {"size": 13}), ("可被打破", {"size": 13, "bold": True, "color": GREEN}),
     ("（R@1 +14pp）。", {"size": 13})],
    [("", {"size": 3})],
    [("• 把 oracle 上界变成", {"size": 13}), ("可部署", {"size": 13, "bold": True, "color": NAVY}),
     ("验证器：不给金标、", {"size": 13})],
    [("  路由到静态处理 off-path（真实版已实现约一半）。", {"size": 13})],
    [("", {"size": 3})],
    [("⚠ 早期证据诚实说：M5 断言重排 2/3 骨干抬 R@1/R@5，", {"size": 11.5, "color": INK})],
    [("　 DeepSeek 无效、均不显著——方向已验、量级待定。", {"size": 11.5, "color": MUTED})],
], line=1.2, space_after=3)
rect(s, MX, 6.6, SW-2*MX, 0.62, fill=NAVY, rounded=True)
text(s, MX, 6.6, SW-2*MX, 0.62, [[("本文有意只做『刻画 + 正确使用』，把『破天花板』留给 RQ4——使当前贡献独立于那个更难的目标成立。", {"size": 13.5, "color": WHITE, "bold": True})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "下一步就是 RQ4：既然可达性已经接近饱和，判别才是墙，那什么信号能打破它？我的类型学明确指向'正交信号'，有两个方向。\n\n方向一，与覆盖率正交的信号：比如利用失败测试的'期望值 vs 观测值'做断言接地重排——这一步我已经初步做了，效果依赖骨干；再往前是更丰富的执行信号，变异测试、值和状态追踪、污点分析，它们原则上能触及数据层缺陷，本文没检验。方向二，异质或更强的验证器：oracle 上界已经证明换个模型能把天花板打破 R@1 +14pp，接下来是把它做成一个真正可部署的、不给金标、并且路由到静态去处理 off-path 的验证器；真实版已经实现了大约一半，目标是继续缩小到 oracle 上界的差距。\n\n我有意把本文范围限定在'刻画 + 正确使用'，把'破天花板'留给 RQ4，这样当前的贡献独立于那个更难的目标就能成立。")

# ============================================================================
# Slide 15 — 研究现状 / 进展
# ============================================================================
s = slide()
title(s, "研究现状：论文与实验完成度", None)
cols = [
    ("论文", [("已成稿 21 页，", False), ("投稿目标 CCF-B", True),
             ("；已从『软件工程』视角上调到", False), ("『AI / LLM』视角", True), ("重构。", False)], TEAL),
    ("实验", [("主结果 + ", False), ("4 骨干跨模型复现", True), (" + ", False),
             ("异质验证器（oracle + 真实）", True), (" + 数据层占比，均已完成。", False)], GREEN),
    ("数据完整性", [("承重表格与头条数字", False), ("全部重跑并精确匹配", True),
                 ("；评审中发现的少量差异（子集 off-by-one、混合 schema 工件）均已追溯对齐。", False)], NAVY),
    ("模拟评审", [("5 审 + 反方 + 完整性核查：", False), ("Major Revision，总分 3/5", True),
                ("（面板偏保守，novelty 与草稿就绪度是被点名的实质弱点）——待补强定位 / 新意表述与 ARISE 锚点，无需新核心实验。", False)], CORAL),
]
y = 2.05; rh = 1.12
for i, (h, parts, col) in enumerate(cols):
    yy = y + i*(rh+0.12)
    rect(s, MX, yy, SW-2*MX, rh, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
    rect(s, MX, yy, 0.14, rh, fill=col)
    chip(s, MX+0.35, yy+0.28, 2.05, 0.56, col, WHITE, h, size=14)
    runs = [[(t, {"size": 13.5, "bold": b, "color": (col if b else INK)}) for (t, b) in parts]]
    text(s, MX+2.65, yy+0.12, SW-2*MX-2.85, rh-0.2, runs, anchor=MSO_ANCHOR.MIDDLE, line=1.25)
notes(s, "汇报到这里，专门用一页讲清楚'目前为止到底做到哪一步了'。\n\n论文：已经成稿 21 页，投稿目标 CCF-B；我最近还把叙事视角从纯软件工程上调到 AI / LLM 视角，突出'自一致性—可达性—判别'这条主线。实验：主结果、4 个骨干的跨模型复现、异质验证器的 oracle 上界和真实可部署版、以及数据层占比估计，都已经完成。数据完整性：所有的表、所有置信区间、所有内联数字，都能从脚本和 JSON 100% 精确复现，没有任何编造或转写错误——这一点我做过专门的交叉核查。模拟评审：我用多智能体模拟了一个 CCF-B 的评审面板，5 个审稿人加一个反方加完整性核查，结论是 Major Revision、总分 3/5——科学性是过线的，被压在录用线下的主要是草稿就绪度和 ARISE 这个对标锚点，都不需要新的核心实验就能修。")

# ============================================================================
# Slide 16 — 一句话总结
# ============================================================================
s = slide(NAVY)
text(s, MX, 1.15, SW-2*MX, 0.8, [[("一句话收尾", {"size": 20, "bold": True, "color": SKY})]])
text(s, MX, 2.0, SW-2*MX, 2.6, [
    [("执行覆盖率是", {"size": 27, "bold": True, "color": WHITE}),
     ("『召回侧过滤器』", {"size": 27, "bold": True, "color": AMBER}),
     ("，不是排序信号；", {"size": 27, "bold": True, "color": WHITE})],
    [("它的价值只在 on-path 子集。", {"size": 27, "bold": True, "color": WHITE})],
    [("", {"size": 10})],
    [("并非所有外部信号都同等有用——", {"size": 22, "color": SKY})],
    [("一个只能证明『可达』的信号，打不破『判别』的天花板。", {"size": 22, "bold": True, "color": WHITE})],
], line=1.25, space_after=10)
rect(s, MX, 5.35, 2.2, 0.05, fill=CORAL)
text(s, MX, 5.45, SW-2*MX, 1.6, [
    [("富有成效的设计 = ", {"size": 16, "color": SKY, "bold": True}),
     ("覆盖率作过滤器  +  强静态 / LLM 排序器  +  on/off-path 路由", {"size": 16, "bold": True, "color": WHITE})],
    [("破判别天花板，要靠与覆盖率、与同模型自一致性都正交的信号（RQ4）。", {"size": 14, "color": SKY})],
    [("可达性，而非判别 —— 这就是执行接地在行级定位里的位置。", {"size": 16, "bold": True, "color": AMBER})],
], line=1.3, space_after=6)
notes(s, "最后用一句话收尾，也就是标题的落地。\n\n第一，执行覆盖率是一个'召回侧过滤器'，不是排序信号；它的价值只在 on-path 子集。第二，也是更大的启示：并非所有外部信号都能同等地帮助大模型——一个只能证明'可达'的信号，打不破'判别'的天花板。\n\n落到可操作的设计上：富有成效的做法是'覆盖率作过滤器 + 一个强的静态或 LLM 排序器 + on/off-path 路由'。而真正要打破判别天花板，得靠一个与覆盖率、与同模型自一致性都正交的信号——这就是我下一步 RQ4 要做的。谢谢老师，请批评指正。")

prs.save("行级故障定位_汇报_AI版.pptx")
print("saved slides:", len(prs.slides._sldIdLst))
