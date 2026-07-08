#!/usr/bin/env python3
"""RQ2 falsification — THREE separate figures, one per sub-experiment, each falsified by
one concrete SWE-bench-Lite instance. Run:
  uv run --python 3.12 --with matplotlib --with numpy python fig_rq2_falsification.py
Outputs: fig_rq2_1_candidate_set, fig_rq2_2_recall_ceiling, fig_rq2_3_ranking  (.pdf + .png)
Numbers verified against egl_cov_cache*.json, rq3_subsets.json, rq3/datalevel_classifier.py, main.tex Table 3."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

GREEN="#16a34a"; GREEN_F="#dcfce7"; RED="#dc2626"; RED_F="#fee2e2"
BLUE="#2563eb"; INK="#0f172a"; GRAY="#64748b"; MUT="#94a3b8"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,
    "axes.edgecolor":"#334155","axes.linewidth":0.9,"pdf.fonttype":42})

CACHE="/Users/zt25/coding/localization_line/prelim_localization/egl_cov_cache.json"
exec_sizes={"matplotlib__matplotlib-24149":2104,"sympy__sympy-13471":1822,"sympy__sympy-21171":1657}
try:
    cm=json.load(open(CACHE))
    for iid in list(exec_sizes):
        k=next((k for k in cm if iid in k),None)
        if k: exec_sizes[iid]=max(len(v) for v in cm[k].values())
except Exception as e:
    print("cache reconfirm skipped:",e,file=sys.stderr)

def despine(ax,keep=("bottom","left")):
    for s in ("top","right","left","bottom"): ax.spines[s].set_visible(s in keep)

def frame(fig,rqtag,title,cond,verdict_txt,footer):
    fig.text(0.065,0.935,rqtag,fontsize=12.5,fontweight="bold",color=GREEN,va="center")
    fig.text(0.065,0.885,title,fontsize=16.5,fontweight="bold",color=INK,va="center")
    fig.text(0.065,0.840,cond,fontsize=10.6,color="#475569",va="center")
    fig.text(0.065,0.125,verdict_txt,fontsize=12,fontweight="bold",color=RED,va="center")
    axb=fig.add_axes([0.065,0.028,0.905,0.058]); axb.axis("off")
    axb.add_patch(FancyBboxPatch((0,0),1,1,boxstyle="round,pad=0.01,rounding_size=0.06",
                  transform=axb.transAxes,facecolor="#0f172a",edgecolor="none"))
    axb.text(0.012,0.5,"Root cause",fontsize=10,fontweight="bold",color="#fbbf24",va="center")
    axb.text(0.125,0.5,footer,fontsize=9.2,color="white",va="center")

def focal_box(fig,rect,head,lines):
    ax=fig.add_axes(rect); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0,0),1,1,boxstyle="round,pad=0.015,rounding_size=0.04",
                 transform=ax.transAxes,facecolor="#f8fafc",edgecolor="#cbd5e1",linewidth=1.2))
    ax.text(0.06,0.90,head,fontsize=11,fontweight="bold",color=BLUE,va="top",transform=ax.transAxes)
    ax.text(0.06,0.74,lines,fontsize=10.2,color=INK,va="top",transform=ax.transAxes,linespacing=1.5)
    return ax

# ============================================================ FIGURE 1
def fig1():
    fig=plt.figure(figsize=(10.6,5.6))
    ax=fig.add_axes([0.135,0.22,0.49,0.55])
    inst=["matplotlib-24149","sympy-13471","sympy-21171"]
    keys=["matplotlib__matplotlib-24149","sympy__sympy-13471","sympy__sympy-21171"]
    ex=[exec_sizes[k] for k in keys]; gold=[2,2,4]
    y=np.arange(len(inst))[::-1]
    bars=ax.barh(y,ex,height=0.5,color="#cbd5e1",edgecolor="#475569",linewidth=1.0,zorder=3)
    bars[0].set_color("#93c5fd"); bars[0].set_edgecolor(BLUE)
    for yi,e,g in zip(y,ex,gold):
        ax.barh(yi,max(e*0.006,12),height=0.5,color=RED,zorder=4)
        ax.text(e+55,yi,f"{g} gold / {e:,} exec  =  {100*g/e:.2f}%",va="center",ha="left",fontsize=10,color=INK)
    ax.axvline(259,color=GRAY,ls="--",lw=1.3,zorder=2)
    ax.text(300,2.72,"median crash executed set = 259 lines",color=GRAY,fontsize=9,ha="left",va="center")
    ax.set_yticks(y); ax.set_yticklabels(inst,fontsize=10)
    ax.get_yticklabels()[0].set_color(BLUE); ax.get_yticklabels()[0].set_fontweight("bold")
    ax.set_xlim(0,3450); ax.set_ylim(-0.6,3.0)
    ax.set_xlabel("lines in the gold file executed by the failing test",fontsize=10)
    despine(ax); ax.tick_params(length=3)
    focal_box(fig,[0.655,0.30,0.29,0.42],"Focal — matplotlib-24149",
        "Gold = 2 lines.\nExecuted in the gold file = 2,104 lines.\n\n"
        "‘In coverage’ ⇒ 1 needle in a\n2,104-line haystack (0.10% precision).\n\n"
        "Even the median crash instance\nleaves a 259-line haystack.")
    frame(fig,"RQ2.1","Coverage is not a candidate set",
        "Necessary condition tested: the executed lines form a usably small answer set.",
        "✗  selecting from ‘executed’ ≈ picking from a haystack  (crash vs. behavioral: only +6.5pp)",
        "Data-level faults sit on ordinary executed lines → the executed set stays a ~259-line haystack, not a candidate set.")
    fig.savefig("fig_rq2_1_candidate_set.pdf"); fig.savefig("fig_rq2_1_candidate_set.png",dpi=200); plt.close(fig)

# ============================================================ FIGURE 2
def fig2():
    fig=plt.figure(figsize=(10.6,5.6))
    ax=fig.add_axes([0.135,0.22,0.49,0.55])
    onp,offp=57,11
    ax.barh(1.05,onp,height=0.5,color=GREEN_F,edgecolor=GREEN,linewidth=1.5,zorder=3)
    ax.barh(1.05,offp,left=onp,height=0.5,color=RED_F,edgecolor=RED,linewidth=1.5,zorder=3)
    ax.text(onp/2,1.05,"57 on-path\n(gold executed)",ha="center",va="center",fontsize=10,color="#166534")
    ax.text(onp+offp/2,1.05,"11",ha="center",va="center",fontsize=10.5,color="#991b1b",fontweight="bold")
    ax.annotate("recall ceiling = 57 / 68 = 83.8%",xy=(onp,1.33),xytext=(26,1.74),
                ha="left",fontsize=11,color=INK,fontweight="bold",
                arrowprops=dict(arrowstyle="-",color=GRAY,lw=1))
    seg=[("missed-branch",6,"#ef4444"),("insertion",4,"#f97316"),("unreached",1,"#7f1d1d")]
    left=0
    for name,n,c in seg:
        ax.barh(0.12,n,left=onp+left,height=0.34,color=c,edgecolor="white",linewidth=1.0,zorder=3)
        ax.text(onp+left+n/2,0.12,str(n),ha="center",va="center",fontsize=9,color="white",fontweight="bold")
        left+=n
    ax.text(onp+offp/2,0.62,"11 off-path = never-run code",ha="center",fontsize=9,color="#991b1b")
    for i,(name,n,c) in enumerate(seg):
        ax.text(1.5,0.40-i*0.20,f"■ {name} ({n})",color=c,fontsize=9.4,va="center")
    ax.set_xlim(0,74); ax.set_ylim(-0.15,2.05)
    ax.set_yticks([0.12,1.05]); ax.set_yticklabels(["off-path\nbreakdown","crash w/ cov\n(n = 68)"],fontsize=9.2)
    ax.set_xlabel("number of crash instances",fontsize=10)
    despine(ax); ax.tick_params(length=3)
    focal_box(fig,[0.655,0.30,0.29,0.42],"Focal — django-14017",
        "The fix edits a branch-guard\n(gold lines 43–44).\n\n"
        "The gold function _combine runs,\nbut the failing input never takes\nthat branch → gold 0/2 executed.\n\n"
        "Filtering to executed lines\ndeletes the gold entirely.")
    frame(fig,"RQ2.2","Coverage is not a recall upper bound",
        "Necessary condition tested: every gold line is executed, so filtering to executed lines is lossless.",
        "✗  filtering deletes off-path gold  →  recall ceiling is 83.8%, not 100%",
        "16% of crash faults edit never-run code (missed branch / insertion / unreached) — structurally outside any coverage set.")
    fig.savefig("fig_rq2_2_recall_ceiling.pdf"); fig.savefig("fig_rq2_2_recall_ceiling.png",dpi=200); plt.close(fig)

# ============================================================ FIGURE 3
def fig3():
    fig=plt.figure(figsize=(10.6,5.6))
    ax=fig.add_axes([0.135,0.22,0.49,0.55])
    t3=[("astropy-14182",0,14,"DL"),("astropy-7746",0,4,"DL"),("astropy-14995",0,4,"DL"),
        ("astropy-14365",0,4,"DL"),("scikit-learn-10508",0,4,"DL"),("seaborn-3010",0,2,"DL"),
        ("matplotlib-22835",1,7,"CF"),("matplotlib-23299",2,4,"CF"),("matplotlib-22711",5,13,"CF")]
    labels=[r[0] for r in t3]; fo=[r[1] for r in t3]; tot=[r[2] for r in t3]; kind=[r[3] for r in t3]
    y=np.arange(len(t3)); cols=[GREEN if k=="CF" else RED for k in kind]
    ax.barh(y,fo,height=0.62,color=cols,edgecolor="white",linewidth=0.6,zorder=3)
    for yi,f,t,k in zip(y,fo,tot,kind):
        if f==0:
            ax.plot(0.06,yi,marker="x",color=RED,ms=7,mew=2,zorder=5)
            ax.text(0.24,yi,f"0 / {t}",va="center",fontsize=9,color="#991b1b")
        else:
            ax.text(f+0.14,yi,f"{f} / {t} gold",va="center",fontsize=9.4,color="#166534",fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels,fontsize=9.2)
    for i,lab in enumerate(labels):
        if lab=="astropy-14182": ax.get_yticklabels()[i].set_color(RED); ax.get_yticklabels()[i].set_fontweight("bold")
        if lab=="matplotlib-22711": ax.get_yticklabels()[i].set_color(GREEN); ax.get_yticklabels()[i].set_fontweight("bold")
    ax.set_xlim(0,6.2); ax.set_ylim(-0.7,8.7)
    ax.axhline(5.5,color=MUT,ls=":",lw=1.1)
    ax.set_xlabel("gold lines in failing-only coverage (SBFL signal)",fontsize=10)
    def bracket(y0,y1,txt,color):
        x=6.32
        ax.plot([x,x+0.06,x+0.06,x],[y0,y0,y1,y1],color=color,lw=1.4,clip_on=False)
        ax.text(x+0.14,(y0+y1)/2,txt,rotation=90,va="center",ha="left",color=color,
                fontsize=9,fontweight="bold",clip_on=False)
    bracket(-0.3,5.3,"6/9 data-level\n(no signal)",RED)
    bracket(5.7,8.3,"3/9 ctrl-flow\n(works)",GREEN)
    focal_box(fig,[0.70,0.30,0.245,0.42],"Focal — astropy-14182",
        "failing cov = 25 lines\npassing cov = 28 lines\nfailing ⊆ passing\n\n"
        "⇒ fail-only = ∅, gold 0/14\n⇒ SBFL has nothing to rank.\n\n"
        "Contrast matplotlib-22711:\nfail-only 93 lines, gold 5/13\n→ the signal works.")
    frame(fig,"RQ2.3","The coverage differential does not rank",
        "Necessary condition tested: gold is in the failing∖passing spectrum, so SBFL floats it up.",
        "✗  the failing−passing differential is empty on 6/9 — it cannot rank the fault",
        "Data-level faults run under BOTH failing and passing tests → empty differential; it fires only for the control-flow minority (3/9).")
    fig.savefig("fig_rq2_3_ranking.pdf"); fig.savefig("fig_rq2_3_ranking.png",dpi=200); plt.close(fig)

fig1(); fig2(); fig3()
print("wrote fig_rq2_1_candidate_set, fig_rq2_2_recall_ceiling, fig_rq2_3_ranking (.pdf/.png)")
print("exec sizes:",exec_sizes)
