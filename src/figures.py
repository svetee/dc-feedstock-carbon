"""Flow figures for the working paper: two Sankeys, a custody flowchart, and the
portfolio ledger with the rule timeline. Pure matplotlib so the repository has no
browser or rendering dependency.  Run from the repo root: python src/figures.py
Writes figures/fig_plant_sankey.png, fig_match_sankey.png, fig_custody_flow.png, fig_ledger_rules.png
"""
from __future__ import annotations
import os, sys, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, PathPatch, FancyArrowPatch
from matplotlib.path import Path

sys.path.insert(0, os.path.dirname(__file__))
ORANGE, COPPER, BROWN, TAN, INK, MUT, PAPER, LINE = "#B5451B", "#C8844B", "#5A3A28", "#E3C9A8", "#2A2015", "#8A7B6C", "#F6F0E6", "#D9CDBD"
plt.rcParams.update({"font.family": "Helvetica", "font.size": 8.5, "axes.edgecolor": LINE, "mathtext.default": "regular"})
_txt = plt.Axes.text
def _text(self, *a, **k):
    a = list(a)
    if len(a) > 2 and isinstance(a[2], str): a[2] = a[2].replace("₂", "$_2$").replace("³", "$^3$")
    return _txt(self, *a, **k)
plt.Axes.text = _text
OUT = "figures"; os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- generic sankey
def sankey(ax, stages, flows, colors, x_gap=1.0, node_w=0.06, pad=0.045, label_side=None):
    """stages: list of lists of (name, value). flows: list of (stage_i, name_from, name_to, value).
    Draws ribbons as cubic beziers between vertically stacked nodes."""
    pos = {}
    for si, nodes in enumerate(stages):
        total = sum(v for _, v in nodes) + pad * (len(nodes) - 1)
        y = 0.5 + total / 2
        for name, v in nodes:
            pos[(si, name)] = (si * x_gap, y - v, y); y -= v + pad
    ax.set_xlim(-0.62, (len(stages) - 1) * x_gap + 0.75); ax.set_ylim(-0.04, 1.16); ax.axis("off")
    used_out = {k: v[2] for k, v in pos.items()}; used_in = {k: v[2] for k, v in pos.items()}
    for si, a, b, v in flows:
        x0, _, _ = pos[(si, a)]; x1, _, _ = pos[(si + 1, b)]
        ya = used_out[(si, a)]; yb = used_in[(si + 1, b)]
        used_out[(si, a)] -= v; used_in[(si + 1, b)] -= v
        x0 += node_w; xm = (x0 + x1) / 2
        verts = [(x0, ya), (xm, ya), (xm, yb), (x1, yb), (x1, yb - v), (xm, yb - v), (xm, ya - v), (x0, ya - v), (x0, ya)]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=colors.get((si, a), colors.get((si + 1, b), COPPER)), alpha=0.55, lw=0))
    for (si, name), (x, y0, y1) in pos.items():
        ax.add_patch(FancyBboxPatch((x, y0), node_w, y1 - y0, boxstyle="square,pad=0", fc=colors.get((si, name), BROWN), ec="none"))
        side = "left" if (label_side or {}).get(si, "right" if si == len(stages) - 1 else "left") == "left" else "right"
        if si == 0: ax.text(x - 0.03, (y0 + y1) / 2, name, ha="right", va="center", fontsize=7.6, color=INK, linespacing=1.2)
        elif si == len(stages) - 1: ax.text(x + node_w + 0.03, (y0 + y1) / 2, name, ha="left", va="center", fontsize=7.6, color=INK, linespacing=1.2)
        else: ax.text(x + node_w / 2, y1 + 0.015, name, ha="center", va="bottom", fontsize=7.4, color=INK, linespacing=1.15)


def fig_plant():
    """Per tonne of fossil methanol, kgCO2e. A: stored, power holds the claim. B: captured and sold."""
    WTT, COMB, CAP = 650, 1374, 0.95
    cap, esc = COMB * CAP, COMB * (1 - CAP); sc = 1 / 2300
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7)); fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.03, wspace=0.08)
    U0, C0, U1, E1, K1 = "Upstream,\nwell to tank\n650", "Carbon in\nthe fuel\n1,374", "Upstream 650", "Escaped 69", "Captured 1,305"
    for ax, sold in zip(axes, (False, True)):
        counted = "Counted against\nthe electricity\n2,024 kg/t\n= 708 kg/MWh" if sold else "Counted against\nthe electricity\n719 kg/t\n= 251 kg/MWh"
        other = "Sold: merchant\nor e-fuel use,\nre-released,\ncounted" if sold else "Stored, claim\nheld by the power:\nnot counted"
        s0 = [(U0, WTT * sc), (C0, COMB * sc)]; s1 = [(U1, WTT * sc), (E1, esc * sc), (K1, cap * sc)]
        s2 = [(counted, (WTT + esc + (cap if sold else 0)) * sc)] + ([] if sold else [(other, cap * sc)])
        flows = [(0, U0, U1, WTT * sc), (0, C0, E1, esc * sc), (0, C0, K1, cap * sc), (1, U1, counted, WTT * sc), (1, E1, counted, esc * sc), (1, K1, counted if sold else other, cap * sc)]
        colors = {(0, U0): TAN, (0, C0): BROWN, (1, U1): TAN, (1, E1): ORANGE, (1, K1): COPPER, (2, counted): ORANGE, (2, other): COPPER}
        sankey(ax, [s0, s1, s2], flows, colors, x_gap=1.0)
        ax.set_title(("B.  Captured CO₂ sold: fate not durable" if sold else "A.  Captured CO₂ stored, power keeps the claim").replace("₂", "$_2$"), fontsize=9, loc="left", color=BROWN)
        if sold: ax.text(1.0 + 0.03, 0.02, "Rule B: a tonne that is\nre-released counts as emitted", fontsize=7.2, color=ORANGE, ha="left", va="bottom")
    fig.savefig(f"{OUT}/fig_plant_sankey.png", dpi=170); plt.close(fig)


def fig_match(ba="PJM"):
    import hourly_match as hm
    df = hm.load(ba); L = hm.LOAD_MW; H = len(df)
    S = df["solar"] / df["solar"].sum() * L * H
    unmatched = np.maximum(0.0, L - S); matched = L - unmatched
    fuel_groups = {"Gas": ["Net Generation (MW) from Natural Gas"], "Coal": ["Net Generation (MW) from Coal"],
                   "Nuclear": ["Net Generation (MW) from Nuclear"], "Wind, hydro,\nother": [c for c in hm.FUEL_COLS if not any(k in c for k in ("Natural Gas", "Coal", "Nuclear"))]}
    served = {}
    for g, cols in fuel_groups.items():
        share = df[cols].sum(axis=1) / df["gen"]; served[g] = float((unmatched * share).sum())
    emis = {g: float((unmatched * df[cols].sum(axis=1) / df["gen"] * sum(hm.FUEL_COLS[c] for c in cols) / len(cols)).sum()) for g, cols in fuel_groups.items()}
    # emissions per group: use group-level factor weighted properly
    emis = {}
    for g, cols in fuel_groups.items():
        e = 0.0
        for c in cols: e += float((unmatched * df[c] / df["gen"] * hm.FUEL_COLS[c]).sum())
        emis[g] = e / 1000
    tot = L * H; sc = 1 / tot
    s0 = [(f"Data-centre load\n{tot/1000:,.0f} GWh", 1.0)]
    s1 = [(f"Matched in-hour\nby solar  {matched.sum()/tot:.0%}", matched.sum() * sc), (f"Unmatched\nhours  {unmatched.sum()/tot:.0%}", unmatched.sum() * sc)]
    s2 = [(f"{g}  {v/1000:,.0f} GWh" + (f"\n{emis[g]/1000:,.0f} kt CO₂" if emis[g] > 500 else ""), v * sc) for g, v in served.items()] + [("Covered by certificates", matched.sum() * sc)]
    flows = [(0, s0[0][0], s1[0][0], matched.sum() * sc), (0, s0[0][0], s1[1][0], unmatched.sum() * sc), (1, s1[0][0], "Covered by certificates", matched.sum() * sc)]
    flows += [(1, s1[1][0], n, v) for n, v in s2[:-1]]
    colors = {(0, s0[0][0]): BROWN, (1, s1[0][0]): COPPER, (1, s1[1][0]): ORANGE, (2, "Covered by certificates"): COPPER}
    for n, _ in s2[:-1]: colors[(2, n)] = ORANGE if n.startswith(("Gas", "Coal")) else TAN
    fig, ax = plt.subplots(figsize=(9.2, 3.8)); fig.subplots_adjust(left=0.02, right=0.98, top=0.97, bottom=0.03); sankey(ax, [s0, s1, s2], flows, colors, x_gap=1.25, pad=0.06)
    fig.savefig(f"{OUT}/fig_match_sankey.png", dpi=170); plt.close(fig)


def box(ax, x, y, w, h, text, fc=PAPER, ec=BROWN, fs=8, tc=INK, lw=0.9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, linespacing=1.25)


def arrow(ax, x0, y0, x1, y1, color=BROWN, ls="-", lw=1.0, text=None, ty=0.03):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9, color=color, lw=lw, linestyle=ls, shrinkA=2, shrinkB=2))
    if text: ax.text((x0 + x1) / 2, (y0 + y1) / 2 + ty, text, ha="center", va="bottom", fontsize=7.2, color=color)


def fig_custody():
    fig, ax = plt.subplots(figsize=(9.2, 3.5)); ax.set_xlim(0, 10); ax.set_ylim(0, 3.4); ax.axis("off")
    y = 2.2; w, h = 1.55, 0.85
    nodes = [(0.3, "Producer, country A\nbio-methanol batch\nproof SP-00001"), (2.45, "Ship\n(mass balance)"), (4.6, "Plant, country B\nconverts to power\nSP-00002"),
             (6.75, "Certificate issuer\n286 MWh, hourly\nREC-00003"), (8.4, "Data-centre buyer\nretires REC-00003\nScope 2 claim")]
    for i, (x, t) in enumerate(nodes):
        box(ax, x, y, w if i != 4 else 1.4, h, t, fc=PAPER if i % 2 == 0 else "white")
    labels = ["cancel SP-00001\nissue SP-00002", "reconcile books\nat the site", "cancel SP-00002\nissue REC-00003", "retire\nonce"]
    for i in range(4):
        x0 = nodes[i][0] + (w if i != 4 else 1.4); x1 = nodes[i + 1][0]
        arrow(ax, x0, y + h / 2, x1, y + h / 2, text=labels[i], ty=0.08)
    ax.text(0.3, 3.25, "The rule at every handover: cancel the incoming serial, issue the outgoing one carrying it as parent. One claim per serial.", fontsize=8.5, color=BROWN, va="center")
    # break
    yb = 0.45
    box(ax, 0.3, yb, w, h, "Producer keeps a copy\nof proof SP-00001", fc="#FBEDE6", ec=ORANGE, tc=ORANGE)
    box(ax, 4.6, yb, w, h, "Second buyer certifies\nthe same molecule again", fc="#FBEDE6", ec=ORANGE, tc=ORANGE)
    box(ax, 8.4, yb, 1.4, h, "Two claims,\none tonne", fc=ORANGE, ec=ORANGE, tc="white")
    arrow(ax, 0.3 + w, yb + h / 2, 4.6, yb + h / 2, color=ORANGE, ls="--", text="sold twice", ty=0.08)
    arrow(ax, 4.6 + w, yb + h / 2, 8.4, yb + h / 2, color=ORANGE, ls="--", text="no registry sees both", ty=0.08)
    ax.text(0.3, 1.5, "Where chains break in practice (rejected by the ledger: BrokenChain, DoubleClaim)", fontsize=8.5, color=ORANGE, va="center")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02); fig.savefig(f"{OUT}/fig_custody_flow.png", dpi=170); plt.close(fig)


def fig_ledger_rules():
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.9), gridspec_kw={"width_ratios": [1.25, 1]})
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.2); ax.axis("off")
    inputs = [("Electricity\nMWh, hourly certificate", 5.1), ("Fuel\ngas, RNG, methanol, H₂", 3.7), ("Captured CO₂\ntonne, fate", 2.3), ("Water\nm³, consumptive", 0.9)]
    for t, yy in inputs: box(ax, 0.2, yy, 2.6, 1.0, t, fs=7.2)
    box(ax, 3.6, 1.6, 2.7, 3.4, "Ledger record\n\nserial\nfactor (kgCO₂e or litres)\norigin\ncustody model\nfate\nclaim flag\nparent serial", fc="white", fs=7.6)
    claims = [("Ratepayer\nupgrades + price effects", 5.1), ("Electricity carbon\nScope 2, hourly, deliverable", 3.7), ("Fuel carbon\nScope 1 / 3, AMI rule", 2.3), ("Water\nstate reporting", 0.9)]
    for t, yy in claims: box(ax, 7.3, yy, 2.6, 1.0, t, fs=7.2, fc="#FBEDE6", ec=ORANGE)
    for _, yy in inputs: arrow(ax, 2.8, yy + 0.5, 3.6, 3.3)
    for _, yy in claims: arrow(ax, 6.3, 3.3, 7.3, yy + 0.5, color=ORANGE)
    ax.set_ylim(0, 6.7); ax.text(0.2, 6.35, "Inputs", fontsize=8.5, color=BROWN); ax.text(3.6, 6.35, "One record, meter to claim", fontsize=8.5, color=BROWN); ax.text(7.4, 6.35, "Four claims a portfolio makes", fontsize=8.5, color=ORANGE)
    # timeline
    ax2.set_xlim(2025.4, 2028.7); ax2.set_ylim(0, 6.7); ax2.axis("off")
    ax2.plot([2025.5, 2028.6], [0.8, 0.8], color=BROWN, lw=1.2)
    for yr in (2026, 2027, 2028): ax2.plot([yr, yr], [0.7, 0.9], color=BROWN, lw=1); ax2.text(yr, 0.35, str(yr), ha="center", fontsize=8, color=BROWN)
    events = [(2025.8, 5.4, "Scope 2 revision:\nfirst consultation\n(Oct 2025–Jan 2026)", COPPER), (2026.45, 4.2, "FERC §206 orders to\nsix RTOs; 25 states\nwith large-load tariffs", ORANGE),
              (2026.75, 2.9, "Scope 2: second\nconsultation", COPPER), (2027.0, 5.4, "Dominion GS-5 in force;\nVirginia water reporting", ORANGE),
              (2027.6, 4.2, "Scope 2 final:\nhourly + deliverable", COPPER), (2027.75, 2.9, "AMI standard draft\n(book-and-claim fuel)", TAN), (2028.3, 5.4, "AMI final;\nowner net-zero\ninventories due", TAN)]
    for x, yy, t, c in events:
        ax2.plot([x, x], [0.9, yy - 0.05], color=c, lw=0.8, ls=":"); ax2.text(x, yy, t, ha="center", va="bottom", fontsize=7, color=INK,
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=c, lw=0.8))
    ax2.text(2025.45, 6.35, "The rules the record has to satisfy, and when", fontsize=8.5, color=BROWN)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02, wspace=0.05); fig.savefig(f"{OUT}/fig_ledger_rules.png", dpi=170); plt.close(fig)


if __name__ == "__main__":
    fig_plant(); fig_match(); fig_custody(); fig_ledger_rules(); print("wrote 4 figures to", OUT)
