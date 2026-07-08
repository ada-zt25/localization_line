# -*- coding: utf-8 -*-
# RQ-oriented progress report deck: what experiments RQ1-3 ran, what methods were
# designed, what results were obtained; SOTA-chase framed as RQ4/future work.
# Reuses the toolchain of build_ppt.py. ~13 slides for a 10-15 min talk.
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
def title(s, t, sub=None, dark=False, tag=None):
    tc = WHITE if dark else NAVY
    x0 = MX
    if tag:
        chip(s, MX, 0.45, 1.15, 0.6, CORAL, WHITE, tag, size=17); x0 = MX + 1.4
    text(s, x0, 0.40, SW - x0 - MX, 0.8, [[(t, {"size": 28, "bold": True, "color": tc})]])
    if sub:
        text(s, MX, 1.16, SW - 2 * MX, 0.5, [[(sub, {"size": 14.5, "color": (TEAL if not dark else SKY)})]])
    rect(s, MX, 1.60, 1.5, 0.05, fill=CORAL)

def box(s, x, y, w, h, label, fill=TINT, tcolor=INK, line="C9D6E0", size=13, bold=True, sub=None):
    rect(s, x, y, w, h, fill=fill, line=line, lw=1.0, rounded=True)
    if sub:
        text(s, x, y, w, h, [[(label, {"bold": bold, "color": tcolor, "size": size})],
                             [(sub, {"color": MUTED, "size": size-3})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=2, line=1.0)
    else:
        text(s, x, y, w, h, [[(label, {"bold": bold, "color": tcolor, "size": size})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

def col_chart(s, x, y, w, h, cats, series, colors, maxv, fmt='0.0', legend=False, dlsize=13, catsize=11):
    cd = CategoryChartData(); cd.categories = cats
    for name, vals in series: cd.add_series(name, vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart; ch.has_title = False
    ch.has_legend = legend
    if legend:
        ch.legend.position = 2; ch.legend.include_in_layout = False; ch.legend.font.size = Pt(11)
    pl = ch.plots[0]; pl.has_data_labels = True; pl.gap_width = 80
    pl.data_labels.number_format = fmt; pl.data_labels.number_format_is_linked = False
    pl.data_labels.font.size = Pt(dlsize); pl.data_labels.font.bold = True; pl.data_labels.font.color.rgb = C(NAVY)
    if len(series) == 1:
        for i, pt in enumerate(pl.series[0].points):
            pt.format.fill.solid(); pt.format.fill.fore_color.rgb = C(colors[i])
    else:
        for i, sr in enumerate(ch.series):
            sr.format.fill.solid(); sr.format.fill.fore_color.rgb = C(colors[i])
    ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
    ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = maxv
    ch.category_axis.tick_labels.font.size = Pt(catsize); ch.category_axis.tick_labels.font.color.rgb = C(INK)
    return ch

# ============================================================================
# S1 — 封面
# ============================================================================
s = slide(NAVY)
text(s, MX, 1.7, SW - 2 * MX, 2.2, [
    [("执行接地何时帮助 LLM 行级故障定位？", {"size": 36, "bold": True, "color": WHITE})],
    [("可达性，而非判别 · Reachability, Not Discrimination", {"size": 20, "color": SKY})],
], space_after=12)
rect(s, MX, 3.9, 2.2, 0.06, fill=CORAL)
text(s, MX, 4.2, SW - 2 * MX, 1.6, [
    [("RQ1–RQ3：做了什么实验 · 设计了什么方法 · 得到什么结果", {"size": 17, "color": WHITE, "bold": True})],
    [("冲 SOTA 作为 RQ4 / future work", {"size": 15, "color": AMBER, "bold": True})],
    [("基准 SWE-bench-Lite · 骨干 Qwen2.5-Coder-32B + 3 个开源模型复现 · 目标 CCF-B", {"size": 12.5, "color": "9FB3C8"})],
], space_after=8)
notes(s, "老师好。这次汇报围绕论文的三个研究问题 RQ1–RQ3，逐题讲清楚：做了什么实验、设计了什么方法、得到了什么结果。核心结论是标题这六个字——执行信号能买到'可达性'，买不到'判别'。而'冲 SOTA、打破判别天花板'我明确留作 RQ4、future work。全程约 13 分钟。")

# ============================================================================
# S2 — 背景 + 核心问题 + RQ 路线图
# ============================================================================
s = slide()
title(s, "背景与核心问题", "定位召回是修复的硬上界；行级是最弱环——本文只做刻画+正确用法，冲 SOTA 留作 RQ4")
# left: two lenses
rect(s, MX, 2.0, 5.7, 2.05, fill=TINT, rounded=True)
text(s, MX+0.3, 2.2, 5.1, 1.7, [
    [("LLM 修 repo issue：先定位、后修复。", {"size": 14, "bold": True, "color": NAVY})],
    [("定位召回 = 修复上界（找不到的行修不了）；", {"size": 13})],
    [("文件级已≈0.9，", {"size": 13}), ("行级最弱（端到端 R@10≈47%）", {"size": 13, "bold": True, "color": CORAL}), ("。", {"size": 13})],
], line=1.25, space_after=3)
box(s, MX, 4.25, 2.75, 1.5, "可达性 Reachability", fill=TINT2, tcolor=TEAL, line="AECBD8", size=14, sub="进 top-k（进没进候选池）")
box(s, MX+2.95, 4.25, 2.75, 1.5, "判别 Discrimination", fill=TINT2, tcolor=CORAL, line="E6C6C4", size=14, sub="排第一（顶没顶到最前）")
# right: question + RQ roadmap
rect(s, 6.75, 2.0, 5.85, 1.35, fill=NAVY, rounded=True)
text(s, 7.05, 2.0, 5.3, 1.35, [
    [("核心问题", {"size": 13, "color": SKY, "bold": True})],
    [("执行接地能否在自一致性之上，补上它缺的『判别力』？", {"size": 15, "bold": True, "color": WHITE})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.2, space_after=4)
rqs = [("RQ1", "地形：召回丢在哪", TEAL), ("RQ2", "证伪：覆盖率作直接信号行不行", CORAL),
       ("RQ3", "正确用法：覆盖率作过滤器", GREEN), ("RQ4", "冲 SOTA / 破判别天花板（future work）", AMBER)]
for i, (tag, d, col) in enumerate(rqs):
    y = 3.55 + i*0.72
    chip(s, 6.75, y, 1.05, 0.56, col, WHITE, tag, size=13)
    text(s, 7.95, y, 4.6, 0.56, [[(d, {"size": 13.5, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE)
notes(s, "先立背景。大模型修真实仓库的 bug，必须先定位要改哪几行；定位召回是修复的硬上界。文件级定位已基本解决（≈0.9），瓶颈在行级，端到端召回只有约 47%。\n\n请老师记住两个词：可达性=把正确行送进 top-k；判别=把它排到第一。核心问题就是：执行接地能不能在模型自身自一致性之上，补上它缺的判别力。\n\n我把它拆成四个 RQ：RQ1 画地图、RQ2 证伪、RQ3 找正确用法——这三题这篇都做完了；RQ4=冲 SOTA、打破判别天花板，明确留作 future work。这样这篇现在就能投，未来还能做更高水平的工作。")

# ============================================================================
# S3 — 研究设计 & 基线方法(共享实验设置)
# ============================================================================
s = slide()
title(s, "研究设计：基线方法 + 干净隔离覆盖率的实验口径", "所有 RQ 共享的实验设置")
py = 2.1
labels = ["文件定位", "区域收窄\n2000→~200 行", "自一致性投票\nk 采样取并集", "RRF 排序\n投票+图+共识"]
bw = 2.55; gap = 0.42; x0 = MX
for i, lab in enumerate(labels):
    box(s, x0 + i*(bw+gap), py, bw, 1.05, lab, fill=TINT, tcolor=NAVY, size=13.5)
    if i < 3: arrow(s, x0 + i*(bw+gap)+bw+0.02, py+0.33, gap-0.04, 0.4, fill=TEAL)
text(s, MX, py+1.15, SW-2*MX, 0.4, [[("方法：先把范围缩到 ~200 行，再用『投票挣召回 + RRF 定序』——这是被评测的定位流水线。", {"size": 12.5, "color": MUTED})]])
yb = 3.9
cols = [
    ("基准", "SWE-bench-Lite 300 例\n100% 单一金标文件", TEAL),
    ("口径 file-given", "只在金标文件内排序\n旁路文件定位噪声", CORAL),
    ("分层", "crash / on-path\n执行原则上能帮之处", AMBER),
    ("稳健性", "4 个骨干模型\n复现主结果", GREEN),
]
cwid = (SW-2*MX-3*0.35)/4
for i, (h, d, col) in enumerate(cols):
    x = MX + i*(cwid+0.35)
    rect(s, x, yb, cwid, 1.5, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
    rect(s, x, yb, cwid, 0.45, fill=col)
    text(s, x, yb, cwid, 0.45, [[(h, {"size": 12.5, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x+0.12, yb+0.55, cwid-0.24, 0.9, [[(d, {"size": 12, "color": INK})]], align=PP_ALIGN.CENTER, line=1.15)
rect(s, MX, 5.7, SW-2*MX, 1.0, fill=NAVY, rounded=True)
text(s, MX+0.35, 5.7, SW-2*MX-0.7, 1.0, [
    [("关键设计：file-given 口径 = 只在给定的正确文件内排序。", {"size": 14.5, "bold": True, "color": WHITE})],
    [("→ 带/不带覆盖率的差异只能归因于『执行接地』本身，与文件定位、模型能力无关。", {"size": 13, "color": SKY})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.25, space_after=3)
notes(s, "这一页是所有 RQ 共享的实验设置。上面是被评测的基线方法：文件定位→区域收窄（2000 行缩到约 200 行）→自一致性投票（多次采样取并集，负责挣召回）→RRF 排序（融合投票、def-use 图分数、跨采样共识来定序）。\n\n实验口径上有四个决定，最关键的是 file-given：只在给定的正确文件内部排序。这样做的目的，是把文件定位那层噪声旁路掉——带覆盖率和不带覆盖率的任何差异，就只能归因于执行接地本身。基准是 SWE-bench-Lite 全 300 例；重点分析 crash 且 on-path 子集；主结果在 4 个骨干模型上复现。")

# ============================================================================
# S4 — RQ1 实验设计 + 结果(地形)
# ============================================================================
s = slide()
title(s, "召回丢在哪：六维分层刻画", "实验：300 实例、六维分层，报 R@10 与『给定命中文件』召回", tag="RQ1")
col_chart(s, MX, 2.05, 3.9, 3.0, ["文件命中", "文件未命中"], [("行 R@10", (63.3, 0.0))],
          [GREEN, RED], 70, fmt='0.0"%"', dlsize=15)
text(s, MX, 5.15, 3.9, 0.9, [[("文件级定位 = 一阶闸门", {"size": 13, "bold": True, "color": NAVY})],
                             [("多文件下全金标命中仅 35% → 全局召回 0.277", {"size": 11.5, "color": MUTED})]],
     align=PP_ALIGN.CENTER, line=1.2, space_after=2)
rect(s, 5.0, 2.05, 7.6, 4.55, fill=TINT, rounded=True, shadow=True)
text(s, 5.35, 2.3, 6.9, 4.1, [
    [("结果与分析（Table 1）", {"size": 15, "bold": True, "color": CORAL})],
    [("① 文件闸门主导：", {"size": 13.5, "bold": True, "color": NAVY}), ("命中 63.3% vs 未命中 0%——文件没找对，行排序无能为力。", {"size": 13})],
    [("② 大文件精确率墙：", {"size": 13.5, "bold": True, "color": NAVY}), ("R@10 随规模 51.3→29.4，即便给定文件也降。", {"size": 13})],
    [("③ 领域效应强：", {"size": 13.5, "bold": True, "color": NAVY}), ("scikit-learn 26% ≪ django 54%。", {"size": 13})],
    [("④ 多行修复伤『找全』：", {"size": 13.5, "bold": True, "color": NAVY}), ("金标行越多，给定命中召回 45→38。", {"size": 13})],
    [("⑤ 缺陷类型不影响可达召回：", {"size": 13.5, "bold": True, "color": NAVY}), ("crash 46.8% ≈ behavioral 46.6%。", {"size": 13})],
    [("", {"size": 5})],
    [("→ 分析：⑤是关键伏笔——缺陷类型改变的是执行『如何』帮忙，", {"size": 13, "color": CORAL, "bold": True})],
    [("　 而非一行『是否』可定位。直接引出 RQ2。", {"size": 13, "color": CORAL, "bold": True})],
], line=1.28, space_after=5)
notes(s, "RQ1 的实验：对 SWE-bench-Lite 全 300 个实例，沿六个维度分层，同时报端到端 R@10 和'给定命中文件'的行召回——后者把文件定位那层剥掉，单看'行'这一步。\n\n结果分析五点。第一也是最重要：文件级定位是一阶闸门，文件命中行召回 63.3%、未命中直接 0，没有中间地带；多文件下把该改文件全找齐只有 35%，导致全局召回坍到 0.277。第二，大文件是精确率墙，即便给定正确文件，文件越大召回越低。第三，领域差异很大。第四，多行修复更难找全。\n\n第五点是关键伏笔：crash 和 behavioral 的可达召回几乎相同。这说明缺陷类型改变的不是'能不能定位'，而是'执行信息怎么帮忙'——这正好把问题交给 RQ2。")

# ============================================================================
# S5 — RQ2 实验设计 + 结果(证伪)
# ============================================================================
s = slide()
title(s, "证伪『覆盖率作直接信号』：三个子实验", "『直接信号』只有两种用法（候选集 / 排序分数）→ 拆成三个必要条件，三个子实验各封死一个（Docker 内采真实覆盖）", tag="RQ2")
cards = [
    ("① 粗粒度统计 → 否『候选集』", "中位 259 行 / 金标文件", "覆盖率无内部排序——\n约 259 行的『大草垛』；\ncrash vs behav 仅差 +6.5pp", RED),
    ("② 83% 天花板 → 否『召回上界』", "只有 57/68 有金标被执行", "16% 改在没跑过的代码：\n漏分支 6 + 插入 4 + 未达 1\n（任何执行方法都救不了）", RED),
    ("③ SBFL 差分(9 例) → 否『排序』", "堵最强反驳：差分谱能排序吗", "仅 3/9 控制流可区分；\n数据层『仅失败』集为空、\n不含金标(Table 3)", RED),
]
cw = (SW-2*MX-2*0.4)/3
for i, (h, big, d, col) in enumerate(cards):
    x = MX + i*(cw+0.4)
    rect(s, x, 2.05, cw, 3.35, fill=WHITE, line="E6C6C4", lw=1.2, rounded=True, shadow=True)
    rect(s, x, 2.05, cw, 0.6, fill=col)
    text(s, x, 2.05, cw, 0.6, [[(h, {"size": 14, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x+0.22, 2.82, cw-0.44, 0.7, [[(big, {"size": 13.5, "bold": True, "color": NAVY})]], line=1.1)
    text(s, x+0.22, 3.65, cw-0.44, 1.6, [[(d, {"size": 12.5, "color": INK})]], line=1.25)
rect(s, MX, 5.7, SW-2*MX, 1.0, fill=NAVY, rounded=True)
text(s, MX+0.35, 5.7, SW-2*MX-0.7, 1.0, [
    [("结果：把执行覆盖率用作『直接候选集』或『排序信号』——在真实 issue 上被证伪。", {"size": 14.5, "bold": True, "color": WHITE})],
    [("分析：①③递进（平面集合无从排序→差分仍空）、②正交封召回——共同根因：覆盖率只记录『哪些行跑过』。", {"size": 13, "color": SKY})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.25, space_after=3)
notes(s, "先明确证伪对象：不是笼统说'覆盖率无用'，而是'覆盖率可作行级定位的直接信号'这个具体命题。直接信号只有两种用法——当候选集、当排序分数；命题成立至少要满足三个必要条件之一：候选集粒度够精、召回上界够高、最强排序形态（失败/通过差分谱）带判别信息。三个子实验各封死一个。数据统一在官方 SWE-bench Docker 镜像内采集：跑失败测试取真实行级覆盖；子实验三额外采 PASS_TO_PASS 与隔离 FAIL_TO_PASS 的成对覆盖。\n\n子实验一封'当候选集'：金标文件中位数 259 行被执行、集合内部零排序信息；金标执行率 crash 85.7% 对 behavioral 79.2% 只差 6.5 个点——连'崩溃类更受益'的直觉都不成立。粒度条件被否。\n\n子实验二封'召回上界'：退一步只求兜住金标，68 例 crash 里也只有 57 例（83%）有金标行被执行；缺口 11 例逐个归类——6 个漏分支（修复在'本该走却没走'的路上，如 django-14017）、4 个纯插入、1 个未达函数。这 16% 对覆盖、SBFL、切片都结构性不可见，是覆盖率的内在属性不是采集缺陷。上界条件被否，也确立了 RQ3 路由的必要性。\n\n子实验三封'当排序分数'的最强形态：评审必然反问'没人拿 raw coverage 排序，经典 SBFL 用失败/通过差分谱'——这是覆盖率能给的最精细排序信息，不测它证伪不完整，所以这一步是堵最强反驳。在四个仓库 9 个实例上算 failing 减 passing 差分（n=9 是采集限制：Django/SymPy 的 PASS_TO_PASS 不是 pytest 格式采不了，不是抽样设计）。结果只有 3/9（全是 matplotlib 控制流类）差分非空且含金标；其余 6 例失败执行的行是通过测试的子集（astropy-14182：25 行包含于 28 行），差分为空必不含金标；且即便非空也粗——matplotlib-22711 的 93 行仅失败集里只有 5 条金标。排序条件被否。\n\n逻辑闭环：①③递进——平面集合无从排序，唯一经典补救是差分谱，而差分对多数缺陷为空；②正交封召回侧。三条独立机制收敛到同一根因：覆盖率是成员关系/控制流信号，SWE-bench 缺陷多为数据层——行跑了、值错了。所以'覆盖率作直接信号'被证伪；唯一幸存的用法是过滤器，这就是 RQ3 的出发点。")

# ============================================================================
# S6 — RQ2 机理：控制流 vs 数据层
# ============================================================================
s = slide()
title(s, "机理：控制流缺陷 vs 数据层缺陷", "覆盖率 / 回溯 / SBFL 都只是『成员关系(控制流)信号』——只告诉你哪些行跑过", tag="RQ2")
rect(s, MX, 2.0, 5.75, 3.9, fill=LGREEN, line="BFE0CC", lw=1.2, rounded=True, shadow=True)
text(s, MX+0.35, 2.22, 5.1, 0.5, [[("(a) 控制流可区分 ✔ 信号生效", {"size": 15, "bold": True, "color": GREEN})]])
text(s, MX+0.35, 2.8, 5.1, 2.9, [
    [("失败输入走了一条", {"size": 13.5}), ("不同的路径", {"size": 13.5, "bold": True, "color": GREEN}), ("，", {"size": 13.5})],
    [("金标行出现在『仅失败』覆盖里。", {"size": 13.5})],
    [("", {"size": 4})],
    [("→ 覆盖率过滤、SBFL 差分、回溯栈全生效。", {"size": 13})],
    [("", {"size": 4})],
    [("例：matplotlib-22711（5/13 金标在仅失败集）", {"size": 12, "color": GREEN, "bold": True})],
], line=1.25, space_after=4)
rect(s, 6.85, 2.0, 5.75, 3.9, fill=LRED, line="E6C6C4", lw=1.2, rounded=True, shadow=True)
text(s, 7.2, 2.22, 5.1, 0.5, [[("(b) 数据层 ✘ 信号失效", {"size": 15, "bold": True, "color": RED})]])
text(s, 7.2, 2.8, 5.1, 2.9, [
    [("同样的行", {"size": 13.5, "bold": True, "color": RED}), ("在通过和失败测试都跑到，", {"size": 13.5})],
    [("→ SBFL 差分为空；或修复落在", {"size": 13}), ("跳过的分支", {"size": 13, "bold": True, "color": RED}), ("上。", {"size": 13})],
    [("", {"size": 4})],
    [("→ 覆盖率只剩『成员关系』= 一个过滤器。", {"size": 13})],
    [("", {"size": 4})],
    [("例：astropy-14182（0/14）· django-14017（漏分支）", {"size": 12, "color": RED, "bold": True})],
], line=1.25, space_after=4)
rect(s, MX, 6.05, SW-2*MX, 0.75, fill=NAVY, rounded=True)
text(s, MX, 6.05, SW-2*MX, 0.75, [[("SWE-bench 以 (b) 数据层为主导（可计算差分的 9 例中 6/9）——这条区分统一解释了 RQ2 的每个负面结果。", {"size": 14, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "RQ2 的所有失败，都能用一条区分解释：控制流缺陷 vs 数据层缺陷。关键洞察——覆盖率、回溯栈、SBFL 本质都是控制流信号，只告诉你哪些行跑过。\n\n左边(a)：bug 改变了控制流，失败走不同的路，金标出现在'仅失败'覆盖里，三种信号全生效（如 matplotlib-22711）。右边(b)：bug 是数据层的，同样的行在通过和失败都跑、只是值错了，差分就空了；或修复落在跳过的分支上。这时覆盖率只剩'成员关系'，只能当过滤器。\n\n分析：SWE-bench 绝大多数是(b)——可计算差分的 9 例里 6/9 是数据层。这条区分预测了 RQ2 的每个负面结果，也预告了 RQ3 为什么只有'过滤器'这一种用法能work。\n\n口径提醒（不念）：旧稿曾写 9/12=75%，与 Table 3 的 n=9 分母矛盾（评审 P0-1）；汇报统一按 Table 3 用 6/9。被问'为何只有 9 例'→ 采集限制：Django/SymPy 的 PASS_TO_PASS 非 pytest 格式无法采集。")

# ============================================================================
# S7 — RQ3 方法设计：覆盖率作过滤器 + 四臂消融
# ============================================================================
s = slide()
title(s, "方法：覆盖率作『召回侧过滤器』+ on/off-path 路由", "设计四臂消融，干净拆出『过滤』与『打分』的贡献", tag="RQ3")
# method flow
rect(s, MX, 2.0, 5.7, 2.5, fill=TINT, rounded=True, shadow=True)
text(s, MX+0.3, 2.2, 5.1, 2.2, [
    [("方法", {"size": 14, "bold": True, "color": CORAL})],
    [("• on-path：把候选/投票限制到失败测试", {"size": 13})],
    [("  真执行到的行（删非执行干扰项）。", {"size": 13})],
    [("• off-path：金标不在执行集 → ", {"size": 13}), ("回退纯静态", {"size": 13, "bold": True, "color": NAVY}), ("。", {"size": 13})],
    [("→ 路由是必需的：盲过滤会删掉 off-path 金标。", {"size": 12.5, "color": MUTED})],
], line=1.3, space_after=4)
# 4-arm ablation design
rect(s, 6.75, 2.0, 5.85, 2.5, fill=WHITE, line="C9D6E0", lw=1.2, rounded=True, shadow=True)
text(s, 7.05, 2.2, 5.3, 0.4, [[("四臂消融设计（隔离过滤 vs 打分）", {"size": 14, "bold": True, "color": NAVY})]])
arms = [("Static", "无覆盖（基线）", MUTED), ("+score", "覆盖率作额外排序分", AMBER),
        ("+filter", "投票限制到执行行", TEAL), ("+filter+score", "两者都加", GREEN)]
for i, (a, d, col) in enumerate(arms):
    y = 2.68 + i*0.44
    chip(s, 7.05, y, 1.9, 0.36, col, WHITE, a, size=11.5)
    text(s, 9.05, y, 3.4, 0.36, [[(d, {"size": 12, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE)
rect(s, MX, 4.75, SW-2*MX, 1.95, fill=TINT2, rounded=True)
text(s, MX+0.35, 4.95, SW-2*MX-0.7, 1.6, [
    [("为什么这样设计（分析）", {"size": 14, "bold": True, "color": NAVY})],
    [("• 覆盖率有两种可能用法：当『排序分』(+score) 或当『过滤器』(+filter)。四臂 2×2 把二者干净分开。", {"size": 13})],
    [("• 若 +score ≈ Static 而 +filter 明显更高 → 证明有用的是『过滤』这个成员关系操作，不是『打分』。", {"size": 13})],
    [("• 先在无 LLM 的 def-use 排序器上做（隔离信号），再放回完整流水线复核（下两页）。", {"size": 13})],
], line=1.3, space_after=4)
notes(s, "RQ3 找到唯一有效的用法，并把它设计成一个可检验的方法。\n\n方法本身：on-path 时，把候选（在完整流水线里是投票）限制到失败测试真执行到的行，删掉非执行的干扰项；off-path 时金标不在执行集，必须回退纯静态。所以路由是方法的必需部分——盲目过滤会把 off-path 的金标删掉。\n\n关键是右边的四臂消融设计。覆盖率有两种可能用法：当额外的排序分数(+score)，或当过滤器(+filter)。我用 2×2 四臂把这两种用法干净分开：Static、+score、+filter、+filter+score。设计意图是——如果 +score 约等于 Static、而 +filter 明显更高，就证明真正有用的是'过滤'这个成员关系操作，而不是'打分'。而且我先在无 LLM 的 def-use 排序器上做，隔离信号；再放回完整流水线复核。")

# ============================================================================
# S8 — RQ3 结果① 离线过滤器
# ============================================================================
s = slide()
title(s, "结果①：过滤器显著有效（离线 def-use）", "crash on-path · 无 LLM：R@10 +14.1pp（CI [3.5, 24.6]）、候选集 −55%（Table 4/5）", tag="RQ3")
col_chart(s, MX, 2.1, 4.0, 3.1, ["静态 def-use", "+filter"], [("R@10", (29.8, 43.9))],
          [MUTED, TEAL], 50, fmt='0.0', dlsize=16)
text(s, MX, 5.3, 4.0, 0.7, [[("+14.1pp", {"size": 21, "bold": True, "color": CORAL})],
                            [("95% CI [3.5, 24.6]，候选集 −55%（837→378）", {"size": 11, "color": MUTED})]],
     align=PP_ALIGN.CENTER, space_after=2)
rect(s, 5.05, 2.1, 7.55, 4.6, fill=TINT, rounded=True, shadow=True)
text(s, 5.4, 2.3, 6.9, 4.3, [
    [("机理（工作实例 django-16873，982 行）", {"size": 14, "bold": True, "color": NAVY})],
    [("静态给 656 候选，金标排 ", {"size": 13}), ("第 40 位", {"size": 13, "bold": True, "color": RED}),
     ("（漏）→ 限到执行的 75 行 → ", {"size": 13}), ("第 6 位", {"size": 13, "bold": True, "color": GREEN}), ("（命中）", {"size": 13})],
    [("排序器没变；纯靠删非执行行让召回与精度一起升。", {"size": 12.5, "color": MUTED})],
    [("", {"size": 5})],
    [("分析要点", {"size": 14, "bold": True, "color": CORAL})],
    [("• 召回", {"size": 13}), ("与", {"size": 13}), ("精度同升", {"size": 13, "bold": True, "color": GREEN}),
     ("：候选减半的同时 R@10 反升——化解 RQ1 的大文件精度墙。", {"size": 13})],
    [("• behavioral on-path 也 +6.9pp；off-path 归零（静态仍 45.5）→ ", {"size": 13}), ("路由必需", {"size": 13, "bold": True, "color": RED}), ("。", {"size": 13})],
    [("• 诚实标注：+14pp 是 ", {"size": 13}), ("oracle 路由机理上界", {"size": 13, "bold": True, "color": NAVY}),
     ("；可部署下限 ", {"size": 13}), ("+4.5pp", {"size": 13, "bold": True, "color": NAVY}), ("。", {"size": 13})],
], line=1.28, space_after=5)
notes(s, "RQ3 第一个结果，在离线、无 LLM 的 def-use 排序器上做，目的是干净隔离覆盖率信号。\n\n结果：crash on-path 子集，R@10 从 29.8 升到 43.9，+14.1 个百分点，置信区间 [3.5, 24.6]，同时候选集缩小 55%。用一个实例讲机理：django-16873，982 行文件，静态把金标排第 40 位、R@10 漏掉；限制到失败测试真跑的 75 行，删掉干扰项后金标升到第 6 位命中——排序器本身没变。\n\n分析三点。第一，召回和精度一起上升——候选减半的同时召回反而升，这恰好化解了 RQ1 那个大文件精度墙。第二，behavioral on-path 也 +6.9pp，但 off-path 会归零、静态在那里还有 45.5，所以路由是必需的。第三，我诚实标注：+14pp 是 oracle 路由下的机理上界，今天真能部署的下限是 +4.5pp——这个可部署缺口我留作 future work。")

# ============================================================================
# S9 — RQ3 结果② 完整流水线 + 可达性≠判别
# ============================================================================
s = slide()
title(s, "结果②：完整流水线 +12.3pp，且『打分』毫无贡献", "四臂消融的关键读数：+score≡Static，+filter 才是功臣（Table 7 / Fig 4）", tag="RQ3")
col_chart(s, MX, 2.15, 6.5, 4.0,
          ["Static", "+score", "+filter", "+filter+score"], [("R@10", (56.1, 56.1, 68.4, 68.4))],
          [MUTED, MUTED, TEAL, TEAL], 78, fmt='0.0', dlsize=15, catsize=12)
text(s, MX, 6.2, 6.5, 0.4, [[("R@10（crash on-path, n=57, 完整投票+图+LLM 流水线）", {"size": 11, "color": MUTED})]], align=PP_ALIGN.CENTER)
rect(s, 7.4, 2.15, 5.2, 4.55, fill=TINT, rounded=True, shadow=True)
text(s, 7.7, 2.35, 4.65, 4.15, [
    [("+12.3pp", {"size": 24, "bold": True, "color": CORAL}), ("  CI [1.8,22.8] 显著", {"size": 11, "color": MUTED})],
    [("", {"size": 4})],
    [("分析", {"size": 14, "bold": True, "color": NAVY})],
    [("• +score ", {"size": 13, "bold": True, "color": AMBER}), ("≡", {"size": 13, "bold": True}),
     (" Static（打分项零贡献）", {"size": 13})],
    [("• +filter ", {"size": 13, "bold": True, "color": TEAL}), ("=", {"size": 13, "bold": True}),
     (" +filter+score（过滤=功臣）", {"size": 13})],
    [("→ 有用的是『过滤(成员关系)』", {"size": 12.5, "color": INK})],
    [("　 不是『打分(需判别)』。", {"size": 12.5, "color": INK})],
    [("", {"size": 5})],
    [("• 增益只在 R@10；R@1/R@5 不显著", {"size": 13})],
    [("→ 提升", {"size": 13}), ("可达性", {"size": 13, "bold": True, "color": TEAL}),
     ("，不提", {"size": 13}), ("判别", {"size": 13, "bold": True, "color": CORAL})],
    [("＝ 和自一致性撞同一道天花板。", {"size": 12.5, "bold": True, "color": CORAL})],
], line=1.24, space_after=4)
notes(s, "RQ3 第二个结果，把过滤器放回完整的'投票+图+LLM'流水线复核——四臂消融的读数极其干净。\n\n看这张 R@10 四臂图：Static 56.1、+score 也是 56.1、+filter 跳到 68.4、+filter+score 还是 68.4。也就是 +12.3 个百分点，置信区间 [1.8, 22.8]，显著。\n\n分析。第一个关键读数：+score 恒等于 Static——覆盖率作为'打分项'零贡献；而 +filter 等于 +filter+score——过滤才是功臣。这直接证明有用的是'过滤'这个成员关系操作，而不是'打分'（打分需要判别力，覆盖率里没有）。第二个关键读数：增益几乎全在 R@10，R@1、R@5 都不显著——所以过滤器提升的是可达性，不是判别，跟自一致性撞的是同一道天花板。这两点合起来就是全篇标题：可达性，而非判别。")

# ============================================================================
# S10 — RQ3 结果③ 跨骨干复现
# ============================================================================
s = slide()
title(s, "结果③：过滤器增益在 4 个骨干上复现", "M（+filter+score）− Static 的 ΔR@10，协议一致（Table 8）", tag="RQ3")
col_chart(s, MX, 2.15, 7.1, 4.2, ["Qwen2.5-Coder-32B", "Qwen3.6-27B", "DeepSeek-V3.2", "GLM-4.5-Air"],
          [("ΔR@10 (pp)", (12.3, 22.8, 8.8, 8.8))], [TEAL, GREEN, TEAL, AMBER], 26, fmt='+0.0', dlsize=15, catsize=11)
rect(s, 8.05, 2.15, 4.55, 4.2, fill=TINT, rounded=True, shadow=True)
text(s, 8.35, 2.4, 4.0, 3.8, [
    [("ΔR@10 ", {"size": 15, "bold": True, "color": NAVY}), ("4/4 为正", {"size": 15, "bold": True, "color": GREEN})],
    [("其中 ", {"size": 14}), ("3/4 显著", {"size": 14, "bold": True, "color": GREEN}), ("（CI 不含 0）。", {"size": 13})],
    [("GLM 点估计同为 +8.8，n=57 未达显著。", {"size": 12.5})],
    [("", {"size": 8})],
    [("分析", {"size": 14, "bold": True, "color": CORAL})],
    [("• 效应", {"size": 13}), ("方向稳（4/4 正）", {"size": 13, "bold": True, "color": GREEN}),
     ("，量级为松界。", {"size": 13})],
    [("• '只提 R@10' 是 Qwen 特有；更强骨干", {"size": 12.5})],
    [("  R@5 也升 → 头条效应可泛化。", {"size": 12.5})],
], line=1.26, space_after=4)
notes(s, "RQ3 第三个结果是稳健性。我把头条的 Static vs +filter+score 对照，在另外三个横跨不同系列、不同规模的开源模型上重跑，协议完全一致。\n\n结果：ΔR@10 在 4 个骨干上全部为正，3 个显著、置信区间不含 0——Qwen2.5-Coder +12.3、Qwen3.6-27B +22.8、DeepSeek-V3.2 +8.8；第四个 GLM 点估计也是 +8.8，只是这个样本量下没到显著。\n\n分析：这告诉我们效应的方向是稳的（4/4 正），但量级是松界（两个承重 CI 下界都贴近 0）。我也诚实说明：'增益只集中在 R@10'是 Qwen2.5-Coder 特有的，更强骨干上 R@5 也一起提升。所以'过滤器提升可达性'这个头条结论可泛化。")

# ============================================================================
# S11 — 贡献 + 类型学
# ============================================================================
s = slide()
title(s, "RQ1–RQ3 小结：一条『信号类型学』串起全部结果", None)
items = [
    ("RQ1", "刻画『行定位为何失败』", "六维分层：文件闸门、大文件精度墙、强领域效应。", TEAL),
    ("RQ2", "证伪『覆盖率作直接信号』", "机理根因：粗粒度、83% 结构天花板、SBFL 差分对数据层为空。", CORAL),
    ("RQ3", "覆盖率作过滤器 + 精确边界", "on-path +14pp / 候选 −55%，完整流水线 +12.3pp，4 骨干复现；路由必需。", GREEN),
    ("核心", "统一信号类型学", "自一致性与覆盖率都是『成员关系信号』：证明可达、不含判别——故都撞 R@1 天花板。", NAVY),
]
y = 2.0; rh = 1.12
for i, (n, h, d, col) in enumerate(items):
    yy = y + i*(rh+0.12)
    rect(s, MX, yy, SW-2*MX, rh, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True, shadow=(i==3))
    rect(s, MX, yy, 0.14, rh, fill=col)
    chip(s, MX+0.35, yy+0.28, 1.15, 0.56, col, WHITE, n, size=14)
    text(s, MX+1.75, yy+0.12, 4.0, rh-0.2, [[(h, {"size": 15, "bold": True, "color": NAVY})]], anchor=MSO_ANCHOR.MIDDLE, line=1.05)
    text(s, MX+5.9, yy+0.12, SW-2*MX-6.1, rh-0.2, [[(d, {"size": 13, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE, line=1.2)
notes(s, "把 RQ1–RQ3 收拢。RQ1 刻画了行定位为什么失败；RQ2 证伪了覆盖率作直接信号并给出机理根因；RQ3 给出唯一有效用法'覆盖率作过滤器'及其精确边界——离线 +14pp、完整流水线 +12.3pp、四骨干复现，路由必需。\n\n最后一条是把前三个串起来的核心主线：一套信号类型学。模型自身的自一致性、和外部的执行覆盖率，本质是同一类东西——都是'成员关系信号'，只能证明一条行可达、不含判别信息，所以都撞在同一道 R@1 天花板上。这也解释了为什么'冲 SOTA'必须换一类信号——引出 RQ4。")

# ============================================================================
# S12 — RQ4 / Future work: 冲 SOTA
# ============================================================================
s = slide()
title(s, "冲 SOTA 作为 RQ4：换正交信号，打破判别天花板", "本文不追求 SOTA 绝对值；RQ4 才是冲 SOTA 的路——已有初步证据", tag="RQ4")
col_chart(s, MX, 2.15, 6.4, 3.7, ["基线\n+filter+score", "真实异质验证器\n(不给金标)", "oracle 并集\n(上界)"],
          [("R@1", (35.1, 42.1, 49.1))], [MUTED, TEAL, GREEN], 56, fmt='0.0', dlsize=16, catsize=11)
text(s, MX, 5.95, 6.4, 0.4, [[("R@1（把出错行排到第一 = 判别）", {"size": 11, "color": MUTED})]], align=PP_ALIGN.CENTER)
rect(s, 7.3, 2.15, 5.3, 4.55, fill=TINT, rounded=True, shadow=True)
text(s, 7.6, 2.35, 4.75, 4.2, [
    [("为什么这是冲 SOTA 的路", {"size": 14, "bold": True, "color": CORAL})],
    [("判别是墙；破它要靠与覆盖率、与同", {"size": 13})],
    [("模型自一致性都", {"size": 13}), ("正交", {"size": 13, "bold": True, "color": NAVY}), ("的信号。", {"size": 13})],
    [("", {"size": 5})],
    [("初步证据（Table 9）", {"size": 13.5, "bold": True, "color": NAVY})],
    [("• oracle 上界：R@1 ", {"size": 13}), ("+14.0pp 全显著", {"size": 13, "bold": True, "color": GREEN})],
    [("→ 天花板", {"size": 13}), ("并非固有、可破", {"size": 13, "bold": True, "color": GREEN}), ("。", {"size": 13})],
    [("• 真实异质验证器（不给金标）：+7.0pp，", {"size": 13})],
    [("  实现约一半（n=57 未显著）。", {"size": 13})],
    [("", {"size": 6})],
    [("→ RQ4 目标：做成可部署验证器，", {"size": 13, "bold": True, "color": NAVY})],
    [("　 把行级 R@1 顶上去、逼近/超过 SOTA。", {"size": 13, "bold": True, "color": CORAL})],
], line=1.24, space_after=3)
notes(s, "这一页把'冲 SOTA'放到它该在的位置——RQ4、future work。我要讲清楚为什么这样安排，以及它不是空谈。\n\n先说清楚：本文有意不追求 SOTA 的绝对分数，我们只做刻画+证伪+正确用法+类型学，并且只用'带/不带覆盖率的配对内部对照'，不与 ARISE 比绝对值。冲 SOTA 是 RQ4 的事。\n\n为什么 RQ4 才是冲 SOTA 的路？因为判别是墙，而 RQ1-3 证明了覆盖率和自一致性都破不了它。破它要靠正交信号。而我已经有初步证据：看这张 R@1 图——把基线和一个更强异质模型 DeepSeek 取 oracle 并集，R@1 从 35.1 升到 49.1，+14 个百分点、全显著，说明判别天花板不是固有的、是可破的；而真实可部署版本（只看 issue 和代码、不给金标）实现了大约一半，+7.0pp，n=57 下还不显著。\n\n所以 RQ4 的目标很明确：把这个异质/正交验证器做成真正可部署的，把行级 R@1 顶上去，逼近甚至超过 SOTA。这就是这篇之后能做成更高水平论文的方向。")

# ============================================================================
# S13 — 一句话总结
# ============================================================================
s = slide(NAVY)
text(s, MX, 1.1, SW-2*MX, 0.8, [[("一句话总结", {"size": 19, "bold": True, "color": SKY})]])
text(s, MX, 1.95, SW-2*MX, 2.5, [
    [("执行覆盖率是", {"size": 26, "bold": True, "color": WHITE}),
     ("『召回侧过滤器』", {"size": 26, "bold": True, "color": AMBER}),
     ("，不是排序信号。", {"size": 26, "bold": True, "color": WHITE})],
    [("", {"size": 8})],
    [("只能证明『可达』的信号，打不破『判别』的天花板；", {"size": 20, "color": SKY})],
    [("冲 SOTA 要换一类正交信号——这是 RQ4。", {"size": 20, "bold": True, "color": WHITE})],
], line=1.25, space_after=8)
rect(s, MX, 4.9, 2.2, 0.05, fill=CORAL)
text(s, MX, 5.15, SW-2*MX, 1.7, [
    [("退可投：", {"size": 17, "bold": True, "color": AMBER}),
     ("RQ1 刻画 + RQ2 证伪 + RQ3 过滤方法 + 类型学，三组实验做完、数字可精确复现，自洽可投 CCF-B。", {"size": 15, "color": WHITE})],
    [("", {"size": 5})],
    [("进可攻：", {"size": 17, "bold": True, "color": AMBER}),
     ("RQ4 用正交/异质验证器破判别天花板、冲 SOTA（oracle 上界 R@1 +14pp 已证可行）。", {"size": 15, "color": WHITE})],
], line=1.3, space_after=7)
notes(s, "总结。第一，执行覆盖率是召回侧过滤器，不是排序信号。第二，更大的启示：一个只能证明'可达'的信号，打不破'判别'的天花板；冲 SOTA 得换一类正交信号——这就是 RQ4。\n\n最后回到战略：退可投——RQ1 刻画、RQ2 证伪、RQ3 过滤方法加类型学，三组实验都做完、数字都能从脚本精确复现，这本身是自洽、可投 CCF-B 的完整贡献；进可攻——RQ4 用正交或异质验证器去破判别天花板、冲 SOTA，而 oracle 上界 R@1 +14pp 已经证明这条路可行。谢谢老师，请指导。")

# ============================================================================
# S14 — RQ4(新增)：迁移到可复现 SOTA 基线 Agentless + 两个评测指标
# ============================================================================
s = slide()
title(s, "把方法迁移到可复现 SOTA 基线：Agentless", "S12 曾把冲 SOTA 列为 future work；本节给出一个已完成的具体 RQ4 实验（准确度↑ + 精确度↑）", tag="RQ4")
rect(s, MX, 2.0, 5.95, 2.6, fill=TINT, rounded=True)
text(s, MX+0.3, 2.18, 5.35, 2.3, [
    [("为什么换基线？", {"size": 15, "bold": True, "color": NAVY})],
    [("· ARISE（行级 SOTA）闭源、不可复现 → 无法做受控对比。", {"size": 13})],
    [("· Agentless（FSE’25，开源、被广泛复现、端到端）→ 作同底座基线，把我们的方法叠上去。", {"size": 13})],
    [("· 红利：复现 Agentless = 端到端（不给金标文件），", {"size": 13}),
     ("顺带消除了 file-given 绝对值虚高的质疑。", {"size": 13, "bold": True, "color": TEAL})],
], line=1.32, space_after=5)
box(s, 6.9, 2.0, 5.72, 0.9, "Agentless 的两个评测指标（不是 R@k）", fill=NAVY, tcolor=WHITE, size=13.5)
box(s, 6.9, 3.05, 2.78, 1.55, "superset = 准确度", fill=TINT2, tcolor=TEAL, line="AECBD8", size=14,
    sub="候选集是否装下『全部』金标行\n越高 = 定位越完整")
box(s, 9.85, 3.05, 2.77, 1.55, "LoC = 精确度/成本", fill=TINT2, tcolor=CORAL, line="E6C6C4", size=14,
    sub="候选集有多少行\n越小 = 越精、下游修复越省")
rect(s, MX, 4.85, SW-2*MX, 1.75, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
text(s, MX+0.35, 5.0, SW-2*MX-0.7, 1.55, [
    [("范围（同前）：", {"size": 13, "bold": True, "color": NAVY}),
     ("crash·on-path，n=57，backbone = DeepSeek-V3；只解决这一类 issue。", {"size": 13})],
    [("目标（一句话）：", {"size": 13, "bold": True, "color": CORAL}),
     ("在 Agentless 的定位结果上，用执行覆盖率同时做到两件事——", {"size": 13})],
    [("　① 准确度上升（superset↑：把 Agentless 漏掉的『对的行』捞回来）", {"size": 13.5, "bold": True, "color": TEAL})],
    [("　② 精确度上升（LoC↓：把没执行的『多余行』筛掉）", {"size": 13.5, "bold": True, "color": CORAL})],
], line=1.3, space_after=3)
notes(s, "这一节把之前列为 future work 的 RQ4，落成一个已经做完的具体实验。\n\n为什么换基线：ARISE 是行级 SOTA，但闭源、不可复现，我们没法在同一套代码里做受控对比。所以我们换成 Agentless——开源、被广泛复现、端到端。把我们的覆盖率方法作为增量叠上去。顺带一个红利：复现 Agentless 是端到端的，不给金标文件，这就把之前 file-given 口径下绝对值虚高的质疑也消掉了。\n\n关键：Agentless 不用 R@k，它用两个指标。superset=准确度，就是候选集有没有装下全部金标行，越高越完整；LoC=精确度/成本，就是候选集有多少行，越小越精、下游修复越省。\n\n我们的目标用一句话说：用执行覆盖率同时做到准确度上升（把漏掉的对的行捞回来）和精确度上升（把多余的行筛掉）。")

# ============================================================================
# S15 — RQ4 方法：漏斗诊断 + 覆盖率三处注入
# ============================================================================
s = slide()
title(s, "方法：先找瓶颈，再把覆盖率放对位置", "诊断=瓶颈在 Agentless『区域收窄』(−21pp，在我们上游)；据此三处注入覆盖率", tag="RQ4")
# left: funnel
text(s, MX, 1.95, 5.6, 0.4, [[("准确度(superset)逐层漏斗：", {"size": 13.5, "bold": True, "color": NAVY})]])
fun = [("① Agentless 文件层", "86.0", TEAL, 5.6),
       ("② 区域收窄·相关元素", "64.9", CORAL, 4.2),
       ("③ 排序·编辑集", "61.4", MUTED, 3.98)]
for i, (lab, val, col, wv) in enumerate(fun):
    y = 2.45 + i*0.72
    rect(s, MX, y, wv, 0.56, fill=col, rounded=True)
    text(s, MX+0.15, y, wv-1.2, 0.56, [[(lab, {"size": 12.5, "bold": True, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, MX+wv-1.15, y, 1.0, 0.56, [[(val+"%", {"size": 13, "bold": True, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
text(s, MX, 4.65, 5.9, 0.6, [[("→ 最大损失 −21pp 在②『区域收窄』——", {"size": 12.5, "bold": True, "color": CORAL}),
                              ("而这是我们投票的上游，投票救不回已掉出区域的金标。", {"size": 12.5, "color": INK})]], line=1.2)
# right: three injections
box(s, 6.85, 2.0, 5.75, 0.7, "覆盖率的三处注入（按阶段分工）", fill=NAVY, tcolor=WHITE, size=13.5)
inj = [("上游 · 选择性扩展", "覆盖率当 score：给执行行打分，把最像金标的行捞回区域 → 抬 superset", TEAL),
       ("生成 · 通道①", "覆盖率当证据：投票 prompt 标注执行行 + 前置 crash traceback", AMBER),
       ("下游 · frontier", "覆盖率当 filter：投票结果 ∩ 执行±2，筛掉多余行 → 砍 LoC", CORAL)]
for i, (h, d, col) in enumerate(inj):
    y = 2.9 + i*1.18
    rect(s, 6.85, y, 5.75, 1.05, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
    rect(s, 6.85, y, 0.14, 1.05, fill=col)
    text(s, 7.15, y+0.1, 5.35, 0.9, [[(h, {"size": 13, "bold": True, "color": col})],
                                      [(d, {"size": 12, "color": INK})]], line=1.2, space_after=2)
notes(s, "方法怎么设计的？先诊断瓶颈。把准确度 superset 逐层拆开：Agentless 文件层能装下全部金标的有 86%，到了区域收窄这一步掉到 64.9%——一步掉了 21 个点，这是最大瓶颈；而再往下的排序阶段只掉 3.5 个点。\n\n关键：这 −21pp 在『区域收窄』，是我们投票的上游。投票只在区域内部操作，救不回已经掉出区域的金标。所以想抬准确度，必须在上游动手。\n\n据此把覆盖率放到三个位置、各司其职：上游当 score——给执行行打分，把最像金标的行捞回区域，负责抬 superset；生成阶段当证据——标注执行行、喂 crash traceback；下游当 filter——投票结果和执行±2 求交，筛掉多余行，负责砍 LoC。")

# ============================================================================
# S15b — 上游『扩区域』的两种做法：崩溃帧 vs 打分
# ============================================================================
s = slide()
title(s, "上游『扩区域』的两种做法：崩溃帧 vs 打分", "两者都用执行覆盖率把漏掉的金标行捞回候选池；区别在『补哪些行』", tag="RQ4")
rect(s, MX, 1.82, SW-2*MX, 0.82, fill=TINT, line="C9D6E0", lw=1.0, rounded=True)
text(s, MX+0.3, 1.82, SW-2*MX-0.6, 0.82, [
    [("『崩溃帧』是什么：", {"size": 12.5, "bold": True, "color": NAVY}),
     ("崩溃时失败测试打印的 Traceback，每行 “File X, line N, in 某函数” 就是一个帧——记录崩溃那刻程序停在哪个函数。", {"size": 12, "color": INK})],
    [("整条栈 = 从入口一路调到出错点的『案发现场路线』上的那几个函数。", {"size": 12, "color": MUTED})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.2, space_after=2)
ax, c1x, c2x = MX, 2.85, 7.75
aw, c1w, c2w = 2.05, 4.8, 4.85
hy, hh = 2.85, 0.62
box(s, ax, hy, aw, hh, "对比项", fill=INK, tcolor=WHITE, size=12.5)
box(s, c1x, hy, c1w, hh, "崩溃帧扩区域", fill=CORAL, tcolor=WHITE, size=14)
box(s, c2x, hy, c2w, hh, "打分扩区域　★推荐", fill=GREEN, tcolor=WHITE, size=14)
grows = [("补哪些\n执行行", "只补 traceback 里点名的函数的执行行", "给所有执行行按『和 issue/崩溃的相关度』\n打分，取 top-30"),
         ("能捞回多少\n(区域天花板)", "68.4 → 70.2", "68.4 → 75.4"),
         ("局限 / 为何推荐", "只覆盖『栈上直接点名』的函数；\n修复在 helper、或不在栈上就捞不到", "视野更广、天花板更高\n→ 故作推荐")]
ry, rh = hy+hh, 0.94
for i, (a, b, c) in enumerate(grows):
    y = ry + i*rh
    rect(s, ax, y, aw, rh, fill=TINT2, line="C9D6E0", lw=0.75)
    text(s, ax+0.08, y, aw-0.16, rh, [[(a, {"size": 11.5, "bold": True, "color": NAVY})]], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, line=1.05)
    rect(s, c1x, y, c1w, rh, fill=WHITE, line="C9D6E0", lw=0.75)
    text(s, c1x+0.15, y, c1w-0.3, rh, [[(b, {"size": 11.5, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE, line=1.12)
    rect(s, c2x, y, c2w, rh, fill=(LGREEN if i == 2 else WHITE), line="C9D6E0", lw=0.75)
    text(s, c2x+0.15, y, c2w-0.3, rh, [[(c, {"size": 11.5, "color": (GREEN if i == 2 else INK), "bold": (i == 2)})]], anchor=MSO_ANCHOR.MIDDLE, line=1.12)
yb = ry + 3*rh + 0.14
rect(s, MX, yb, SW-2*MX, 0.7, fill=NAVY, rounded=True)
text(s, MX+0.35, yb, SW-2*MX-0.7, 0.7, [
    [("一句话：", {"size": 13, "bold": True, "color": AMBER}),
     ("崩溃帧 = 顺着报错栈补行(简单、视野窄)；打分 = 按相关度补最像金标的执行行(更全、天花板更高) → 推荐打分。", {"size": 13, "bold": True, "color": WHITE})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.15)
notes(s, "这一页解释上游『扩区域』的两种具体做法，也就是结果表里『投票+崩溃帧扩区域』和『投票+打分扩区域』的区别。\n\n先解释崩溃帧：崩溃时失败测试会打印 Traceback，每一行 File X line N in 某函数就是一个帧，记录崩溃那一刻程序停在哪个函数；整条栈就是从入口一路调用到出错点的『案发现场路线』上的那几个函数。\n\n崩溃帧扩区域：只把 traceback 里点名的那几个函数的执行行补回候选池。简单直接，但视野只到崩溃栈——如果修复在栈上函数调用的 helper 里、或在 issue 提到但不在栈上的函数里，就补不到。区域天花板从 68.4 抬到 70.2。\n\n打分扩区域（推荐）：不局限于栈，给所有执行行按『和 issue、崩溃的相关度』打分，取最相关的 top-30 补回。视野更广，区域天花板抬到 75.4，比崩溃帧更高。所以我们推荐打分扩区域。\n\n一句话：崩溃帧是顺着报错栈补行，打分是按相关度补最像金标的执行行、更全。")

# ============================================================================
# S15c — 覆盖率的另两处作用：生成·通道① 与 下游·frontier
# ============================================================================
s = slide()
title(s, "覆盖率的另两处作用：生成·通道① 与 下游·frontier", "上游『扩区域』已讲(前页)；这两处是覆盖率在【生成】和【过滤】阶段怎么起作用", tag="RQ4")
b1y = 1.95
rect(s, MX, b1y, SW-2*MX, 2.05, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
rect(s, MX, b1y, 0.16, 2.05, fill=AMBER)
text(s, MX+0.38, b1y+0.14, SW-2*MX-0.75, 1.8, [
    [("生成 · 通道① —— 覆盖率当【证据 / 探照灯】，喂给 LLM 生成", {"size": 15, "bold": True, "color": "B07000"})],
    [("机制：", {"size": 12.5, "bold": True, "color": NAVY}),
     ("投票 prompt 给执行行标『>』+ 前置 crash traceback + “沿执行路径反推根因”指令。", {"size": 12.5, "color": INK})],
    [("覆盖率的角色：", {"size": 12.5, "bold": True, "color": TEAL}),
     ("不删也不选，而是把『这些行真跑过、崩在哪』当证据喂给生成 → 让投票聚焦执行路径、生成更可能命中金标的候选。", {"size": 12.5, "color": INK})],
    [("效果：", {"size": 12.5, "bold": True, "color": GREEN}),
     ("file-given 实验里通道①独立抬 Line R@5 / R@10 各 +5.3；在 Agentless 上让投票充分 realize 扩展后的区域天花板。", {"size": 12.5, "color": INK})],
], line=1.3, space_after=3)
b2y = 4.15
rect(s, MX, b2y, SW-2*MX, 2.05, fill=WHITE, line="C9D6E0", lw=1.0, rounded=True)
rect(s, MX, b2y, 0.16, 2.05, fill=CORAL)
text(s, MX+0.38, b2y+0.14, SW-2*MX-0.75, 1.8, [
    [("下游 · frontier —— 覆盖率当【筛子】，过滤候选、砍 LoC", {"size": 15, "bold": True, "color": "B03A20"})],
    [("机制：", {"size": 12.5, "bold": True, "color": NAVY}),
     ("投票结果 ∩ 执行±2（±2 = 保住紧邻执行行的插入锚点，避免误删未执行的金标）。", {"size": 12.5, "color": INK})],
    [("覆盖率的角色：", {"size": 12.5, "bold": True, "color": TEAL}),
     ("当筛子，把区域里『没被执行』的上下文行筛掉 → 候选集更小、更精。", {"size": 12.5, "color": INK})],
    [("效果：", {"size": 12.5, "bold": True, "color": GREEN}),
     ("挂 Agentless 自己的输出上砍 −40% LoC（早期信号 299→180）；crash·on-path 金标必被执行，过滤安全、不误伤召回。", {"size": 12.5, "color": INK})],
], line=1.3, space_after=3)
ty2 = 6.35
rect(s, MX, ty2, SW-2*MX, 0.72, fill=NAVY, rounded=True)
text(s, MX+0.35, ty2, SW-2*MX-0.7, 0.72, [
    [("同一个覆盖率信号、三种分工：", {"size": 13.5, "bold": True, "color": AMBER}),
     ("上游 score『抬召回』(捞回漏的金标) · 生成通道①『提准度』(照亮执行路径) · 下游 filter『砍成本』(筛掉没跑的行)。", {"size": 13, "bold": True, "color": WHITE})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.15)
notes(s, "这一页补上覆盖率在另两处注入怎么起作用——前面详细讲了上游扩区域，这里讲生成通道①和下游 frontier。\n\n生成通道①：覆盖率不删也不选，而是当证据、当探照灯。投票的 prompt 里给执行过的行标个 > 号，再把 crash 的 traceback 放前面，让模型沿执行路径反推根因。这样投票就聚焦到真正跑过的路径上，生成更可能是金标的候选。效果上，在 file-given 的实验里，光通道①就把 Line R@5 和 R@10 各抬了 5.3 个点；在 Agentless 上，它让投票能充分兑现扩展后的区域天花板。\n\n下游 frontier：覆盖率当筛子。投票出结果后，和执行±2 求交——±2 是为了保住紧邻执行行的插入锚点、避免把未执行的金标误删。它把区域里没被执行的上下文行筛掉，候选集更小更精。效果上，挂在 Agentless 自己的输出上能砍 40% 的候选行（299 降到 180）；而且在 crash·on-path 上金标必被执行，所以这个过滤是安全的、不误伤召回。\n\n一句话：同一个覆盖率信号，三种分工——上游打分抬召回、生成通道①提准度、下游过滤砍成本。")

# ============================================================================
# S16 — RQ4 关键：score 与 filter 的和解(为什么 RQ3 score 无用、这里有用)
# ============================================================================
s = slide()
title(s, "关键：为什么 RQ3 的『打分』无用，这里却有用？", "同一个覆盖率——区别不在『score 还是 filter』，而在『作用在哪层、改召回还是改排序』", tag="RQ4")
# two columns
cw = 5.85
heads = [("RQ3 的 +score（页9）", "下游 · 重排一个已固定的池", RED, LRED),
         ("RQ4 的 score（本节）", "上游 · 决定往池里加哪些行", GREEN, LGREEN)]
rows = [("作用位置", "在已有候选池里重排", "构建候选池、选新成员"),
        ("改变什么", "只改『次序』(池里有啥不变)", "改『成员』(把池外金标捞进来)"),
        ("针对的瓶颈", "判别(金标已在池、排不到前)", "召回(金标被窄区域漏掉 −21pp)"),
        ("结果", "≡ Static，零贡献", "抬 superset(+7pp 天花板)")]
for c, (h, sub, col, lfill) in enumerate(heads):
    x = MX + c*(cw+0.35)
    rect(s, x, 2.0, cw, 0.85, fill=col, rounded=True)
    text(s, x, 2.0, cw, 0.85, [[(h, {"size": 14, "bold": True, "color": WHITE})],
                               [(sub, {"size": 11.5, "color": WHITE})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=1, line=1.1)
    for r, row in enumerate(rows):
        y = 3.0 + r*0.72
        rect(s, x, y, cw, 0.66, fill=(lfill if r == 3 else WHITE), line="C9D6E0", lw=0.75, rounded=False)
        text(s, x+0.15, y, 1.5, 0.66, [[(row[0], {"size": 11, "bold": True, "color": MUTED})]], anchor=MSO_ANCHOR.MIDDLE)
        text(s, x+1.65, y, cw-1.8, 0.66, [[(row[1+c], {"size": 12, "bold": (r == 3), "color": (col if r == 3 else INK)})]], anchor=MSO_ANCHOR.MIDDLE, line=1.05)
rect(s, MX, 5.98, SW-2*MX, 0.95, fill=NAVY, rounded=True)
text(s, MX+0.35, 5.98, SW-2*MX-0.7, 0.95, [
    [("和解：覆盖率是『可达性』信号。", {"size": 14.5, "bold": True, "color": AMBER}),
     ("RQ3 拿它做『判别』(重排)→ 无用；RQ4 拿它做『可达性』(扩池)→ 有用。", {"size": 14.5, "bold": True, "color": WHITE})],
    [("这不矛盾，正是 RQ1–3 主线的两半：区别在宿主变了——我们自己的区域已很全(无可救)，Agentless 的区域更窄有损(有 −21pp 可救)。", {"size": 12, "color": SKY})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.25, space_after=3)
notes(s, "这是本节最关键的一页，专门回答一个尖锐的问题：RQ3 里我们做过消融，覆盖率当打分项 +score 完全无用、等于 Static；为什么这里当 score 又有用了？\n\n关键不在『score 还是 filter』这个名字，而在它作用在哪一层、改的是召回还是排序。\n\nRQ3 的 +score 是在一个『已经固定、已经有金标』的候选池里重排——它只能改次序，改不了池里有没有金标。而 RQ3 的瓶颈是判别：金标 85% 已经在池里，只是排不到第一。覆盖率是可达性信号、没有判别力，拿它去做判别的活，自然等于没做。这恰恰印证了我们的主线：覆盖率证明可达、不含判别。\n\nRQ4 的 score 是在『构建候选池』时决定加哪些行——它改的是池的成员，把 Agentless 漏在池外的执行金标捞回来。这是召回问题，正好是覆盖率可达性的强项。重排永远做不到把池外的金标弄进池，扩展可以。\n\n所以两个实验不矛盾，是同一条主线的两半：RQ3 证明覆盖率不能当判别信号，RQ4 证明它能当可达性信号。区别在宿主变了——我们自己的区域已经很全，没什么可救；Agentless 的区域更窄、有损，有 21 个点可救。把可达性信号用在可达性是瓶颈的地方，它就有用了。")

# ============================================================================
# S17 — RQ4 结果：横向方法对比 + Pareto 占优
# ============================================================================
s = slide()
title(s, "结果：横向方法对比(基于 Agentless 基线)", "crash·on-path n=57 · DeepSeek-V3 · 指标 = Agentless 原生的 superset(准确度) 与 LoC(精确度)", tag="RQ4")
# 方法名按机制命名（不用 V1/V2/框架/N 等内部术语）；只保留 Agentless 两个原生指标 superset/LoC
tbl = [
    ("方法（含义见下方说明）", "superset · 准确度", "LoC · 精确度", None),
    ("Agentless 基线", "66.7", "341", "base"),
    ("只换投票 · 不扩区域", "63.2", "233", None),
    ("投票 + 崩溃帧扩区域", "68.4 (+1.8)", "290 (−15%)", None),
    ("投票 + 打分扩区域　★推荐", "68.4 (+1.8)", "292 (−14%)", "star"),
    ("并入 Agentless 预测(崩溃帧)", "71.9 (+5.3)", "410 (+20%)", None),
]
tx, ty = MX, 1.9
cws = [6.4, 2.75, 2.78]
rh = 0.5
for r, row in enumerate(tbl):
    y = ty + r*rh
    for c in range(3):
        x = tx + sum(cws[:c])
        if r == 0:
            fill = NAVY; tc = WHITE; bold = True
        elif row[3] == "star":
            fill = LGREEN; tc = (GREEN if c > 0 else NAVY); bold = True
        elif row[3] == "base":
            fill = TINT2; tc = INK; bold = (c == 0)
        else:
            fill = WHITE; tc = INK; bold = False
        rect(s, x, y, cws[c], rh, fill=fill, line="C9D6E0", lw=0.75)
        al = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
        text(s, x+(0.15 if c == 0 else 0), y, cws[c]-(0.2 if c == 0 else 0), rh,
             [[(row[c], {"size": (12 if r == 0 else 12), "bold": bold, "color": tc})]], anchor=MSO_ANCHOR.MIDDLE, align=al, line=0.95)
# 方法说明（把命名讲清楚）
yd = ty + len(tbl)*rh + 0.12
rect(s, MX, yd, SW-2*MX, 1.15, fill=TINT, line="C9D6E0", lw=1.0, rounded=True)
text(s, MX+0.3, yd+0.08, SW-2*MX-0.6, 1.0, [
    [("方法说明（都以 Agentless 定位结果为基础，只改『编辑位置』这一步）：", {"size": 12, "bold": True, "color": NAVY})],
    [("· 只换投票 = 用我们的自洽投票替换 Agentless 的定位（不扩区域）→ 反而更差，说明瓶颈在上游区域。", {"size": 11.5, "color": INK})],
    [("· 扩区域 = 用执行覆盖率把『可能是金标的执行行』补回候选池(准确度↑)；", {"size": 11.5, "color": TEAL}),
     ("崩溃帧/打分两种做法见上页（打分天花板更高、故推荐）。", {"size": 11.5, "color": INK})],
    [("· 并入 Agentless 预测 = 保留 Agentless 定位再『并上』投票（不替换）；用崩溃帧投票完整度最高(71.9)。", {"size": 11.5, "color": INK})],
    [("　替换 vs 并入是两个 Pareto 点：替换·打分『省候选』(−14%)，并入·崩溃帧『更全』(+5.3)——详见下页。", {"size": 11.5, "color": MUTED})],
], line=1.16, space_after=1)
yb = yd + 1.27
rect(s, MX, yb, SW-2*MX, 0.85, fill=NAVY, rounded=True)
text(s, MX+0.35, yb, SW-2*MX-0.7, 0.85, [
    [("通俗读法：", {"size": 14, "bold": True, "color": AMBER}),
     ("推荐法(投票+打分扩区域)相对 Agentless——准确度↑(66.7→68.4)、精确度↑(341→292，少 14% 候选行)。", {"size": 14, "bold": True, "color": WHITE})],
    [("两个轴都严格更好 = Pareto 占优；核心叙事 =『用更少的候选行，拿到相等或更高的定位完整度』。", {"size": 11.5, "color": SKY})],
], anchor=MSO_ANCHOR.MIDDLE, line=1.2, space_after=2)
notes(s, "结果表，指标只用 Agentless 自己汇报的两个：superset（准确度=候选集是否装下全部金标）和 LoC（精确度/成本=候选集有多少行）。方法名按『做了什么』命名。\n\nAgentless 基线：superset 66.7、候选 341 行。\n\n只换投票、不扩区域：superset 反而掉到 63.2——瓶颈在上游区域收窄，光替换定位没用，反面对照。\n\n投票+崩溃帧扩区域 / 投票+打分扩区域：都用执行覆盖率把可能是金标的执行行补回候选池，两者数值接近（都到 68.4），区别在天花板——打分的区域天花板更高（75.4 vs 70.2），故作推荐，细节见上一页。\n\n★推荐『投票+打分扩区域』：superset 68.4（比基线高 1.8）、候选 292 行（比基线少 14%）——两个轴都严格更好，Pareto 占优。通俗说：用更少 14% 的候选行，拿到更高的定位完整度。\n\n『并入 Agentless 预测』：不替换、而是保留 Agentless 定位再并上投票（真实实验 agentless/union_eval.py）。用崩溃帧投票并入，superset 能到 71.9（+5.3），候选 410 行（+20%）——这是想要最高完整度时的选择，和替换式的『省候选』是两个不同的 Pareto 点，不是谁支配谁。下一页专门讲两种投票并入的对比、以及为什么崩溃帧在并入里反而更好。")

# ============================================================================
# S17b — 并入式结果：两种投票并入 Agentless + 为何崩溃帧更好
# ============================================================================
s = slide()
title(s, "并入式：两种投票并入 Agentless，为何崩溃帧更好", "『并入』= 保留 Agentless 定位再并上投票(不替换)；均为 并集∩frontier，n=57", tag="RQ4")
utbl = [
    ("方法", "superset", "LoC", "vs 基线", None),
    ("Agentless 基线", "66.7", "341", "—", "base"),
    ("并入·崩溃帧(V1)  N=40", "70.2", "363", "+3.5 / +7%", "v1"),
    ("并入·崩溃帧(V1)  N=100 ★", "71.9", "410", "+5.3 / +20%", "star"),
    ("并入·打分(V2)  N=40", "68.4", "389", "+1.8 / +14%", None),
    ("并入·打分(V2)  N=150", "70.2", "512", "+3.5 / +50%", None),
]
tx, ty = MX, 1.85
cws = [5.3, 2.3, 2.2, 2.13]
rh = 0.46
for r, row in enumerate(utbl):
    y = ty + r*rh
    for c in range(4):
        x = tx + sum(cws[:c])
        if r == 0: fill, tc, bold = NAVY, WHITE, True
        elif row[4] == "star": fill, tc, bold = LGREEN, (GREEN if c > 0 else NAVY), True
        elif row[4] == "v1": fill, tc, bold = "EAF3E9", INK, False
        elif row[4] == "base": fill, tc, bold = TINT2, INK, (c == 0)
        else: fill, tc, bold = WHITE, INK, False
        rect(s, x, y, cws[c], rh, fill=fill, line="C9D6E0", lw=0.75)
        al = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
        text(s, x+(0.15 if c == 0 else 0), y, cws[c]-(0.2 if c == 0 else 0), rh,
             [[(row[c], {"size": 12, "bold": bold, "color": tc})]], anchor=MSO_ANCHOR.MIDDLE, align=al)
yb = ty + len(utbl)*rh + 0.18
rect(s, MX, yb, SW-2*MX, 2.35, fill=TINT, line="C9D6E0", lw=1.0, rounded=True)
text(s, MX+0.35, yb+0.14, SW-2*MX-0.7, 2.1, [
    [("为什么『并入』里崩溃帧反而更好？（替换式里却是打分更好）", {"size": 14, "bold": True, "color": NAVY})],
    [("① 数据（N=100）：投票补进来的『新增行』——", {"size": 12.5, "bold": True, "color": INK}),
     ("崩溃帧 133 行救回 4 个实例的金标；打分 202 行只救回 2 个。", {"size": 12.5, "color": CORAL})],
    [("　→ 崩溃帧补得『少而准』，打分补得『多而散』(多加的行大多没金标，徒增 LoC)。", {"size": 12, "color": MUTED})],
    [("② 机理：两个框架对投票的需求相反——", {"size": 12.5, "bold": True, "color": INK})],
    [("　• 替换式：投票是唯一来源 → 需要『广』(视野宽才捞得全) → ", {"size": 12, "color": INK}),
     ("打分(top-30 相关执行行)胜。", {"size": 12, "bold": True, "color": TEAL})],
    [("　• 并入式：Agentless 已经很『广』、只缺它漏的那几行 → 需要『准』(聚焦崩溃路径) → ", {"size": 12, "color": INK}),
     ("崩溃帧胜。", {"size": 12, "bold": True, "color": CORAL})],
    [("一句话：并入时看重的是『和 Agentless 互补』而非『自己更全』——崩溃帧顺着报错栈补，正好补在 Agentless 漏的点上。", {"size": 12.5, "bold": True, "color": NAVY})],
], line=1.2, space_after=2)
notes(s, "这一页专门讲『并入式』——保留 Agentless 自己的定位、再并上我们的投票，不替换。表里对比两种投票并入的结果，都和基线比。\n\n基线 66.7 / 341。用崩溃帧投票并入：N=40 到 70.2、候选 363（多 7%）；N=100 到 71.9、候选 410（多 20%）——完整度最高。用打分投票并入：N=40 只到 68.4，要到 70.2 得 N=150、候选涨到 512（多 50%）。所以并入这个框架里，崩溃帧明显比打分好。\n\n为什么？这跟替换式相反——替换式里是打分更好。我算了一个数：N=100 时，崩溃帧投票补进来 133 个新行，救回了 4 个实例的金标；打分补进来 202 个新行，却只救回 2 个。也就是崩溃帧补得少而准，打分补得多而散、多加的行大多不是金标，白涨 LoC。\n\n机理是两个框架对投票的需求相反。替换式里投票是唯一来源，需要『广』——视野宽才能把金标都捞进来，所以打分（在所有执行行里按相关度取 top-30）更好。并入式里 Agentless 已经提供了很广的覆盖，缺的只是它漏掉的那几行，需要的是『准』——聚焦崩溃路径的崩溃帧投票，正好补在 Agentless 漏的点上，所以崩溃帧更好。\n\n一句话：并入时看重的是和 Agentless 的『互补』，而不是投票自己更全。")

# ============================================================================
# S18 — RQ4 小结 + 后续方向
# ============================================================================
s = slide(NAVY)
text(s, MX, 1.0, SW-2*MX, 0.7, [[("RQ4 小结", {"size": 19, "bold": True, "color": SKY})]])
text(s, MX, 1.75, SW-2*MX, 1.6, [
    [("一句话：", {"size": 22, "bold": True, "color": WHITE}),
     ("用执行覆盖率把漏掉的对的行『捞回来』(更准) + 把多余的行『筛掉』(更精)。", {"size": 22, "bold": True, "color": AMBER})],
    [("在可复现的 Agentless 上，同时做到准确度↑(superset +1.8) 与 精确度↑(LoC −14%)，Pareto 占优基线。", {"size": 15, "color": SKY})],
], line=1.3, space_after=8)
rect(s, MX, 3.75, 2.2, 0.05, fill=CORAL)
box(s, MX, 4.1, 5.85, 2.4, "", fill="1B3A5C", line=None)
text(s, MX+0.35, 4.3, 5.2, 2.0, [
    [("后续优化方向", {"size": 15, "bold": True, "color": AMBER})],
    [("· 瓶颈已从『区域召回』转到『判别』：『打分扩区域』把区域天花板抬到 75.4%，但预算内 realized 仍卡 68.4——", {"size": 12.5, "color": WHITE})],
    [("　投票没能在少候选下把新捞进来的金标排到前面。下一步攻判别力(缩池精排 + 覆盖率分档)。", {"size": 12.5, "color": SKY})],
    [("· 扩样固化：+1.8 与 −14% 均在 n=57，欠功效 → 跑 SWE-bench Verified 的 crash·on-path 做显著性。", {"size": 12.5, "color": WHITE})],
], line=1.28, space_after=4)
box(s, 6.85, 4.1, 5.75, 2.4, "", fill="1B3A5C", line=None)
text(s, 7.2, 4.3, 5.1, 2.0, [
    [("诚实边界", {"size": 15, "bold": True, "color": AMBER})],
    [("· 结果在 crash·on-path(oracle 定义子集)上，须作为 scope 假设披露。", {"size": 12.5, "color": WHITE})],
    [("· 覆盖率来自失败测试(FAIL_TO_PASS 可能是 patch 新增测试的 oracle 嫌疑，须审计)。", {"size": 12.5, "color": WHITE})],
    [("· superset +1.8 @ n=57 欠功效；", {"size": 12.5, "color": SKY}),
     ("LoC 效率(−14~28%)是更硬、更可复现的卖点。", {"size": 12.5, "bold": True, "color": AMBER})],
], line=1.28, space_after=4)
notes(s, "RQ4 小结。一句话：用执行覆盖率把漏掉的对的行捞回来（更准），把多余的行筛掉（更精）。在可复现的 Agentless 上，我们同时做到准确度上升——superset 加 1.8，和精确度上升——LoC 减 14%，Pareto 占优基线。\n\n后续方向：瓶颈已经从区域召回转到判别了。『打分扩区域』把区域天花板抬到 75.4%，但在 LoC 不超基线的预算内，实际只兑现到 68.4——因为投票没能在少候选的前提下，把新捞进来的金标排到前面。所以下一步该攻判别力：缩池精排加覆盖率分档。另外，加 1.8 和减 14% 都在 57 例上、还欠统计功效，需要跑 SWE-bench Verified 扩样做显著性。\n\n诚实边界：结果在 crash·on-path 这个 oracle 定义的子集上，要披露；覆盖率来自失败测试，有 oracle 嫌疑要审计；superset 加 1.8 在 57 例上不显著，所以我更愿意把 LoC 效率——少 14% 到 28% 的候选行——当成更硬、更经得起审稿的卖点。")

prs.save("行级故障定位_RQ汇报.pptx")
print("saved slides:", len(prs.slides._sldIdLst))
