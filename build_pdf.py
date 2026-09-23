"""Render the working paper (and README / statement) to a designed PDF with ReportLab.

Consulting-report conventions: action titles that state the conclusion, numbered
exhibits with a source line, a key-takeaways box on the cover, generous margins.
Palette: burnt orange, copper, brown. pandoc (gfm -> html) -> small HTML tree ->
ReportLab flowables.  Run from the repo root:  python3 build_pdf.py   (outputs to dist/)
"""
import subprocess, os, re, sys
from html.parser import HTMLParser
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image, KeepTogether, ListFlowable, ListItem)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.abspath(__file__)); DIST = os.path.join(ROOT, "dist"); os.makedirs(DIST, exist_ok=True)
FD = os.path.expanduser("~/Documents/workbench/Claude Repo/career/fonts")
for n, f in [("Inter", "Inter-Regular.ttf"), ("Inter-Medium", "Inter-Medium.ttf"), ("Inter-Semi", "Inter-SemiBold.ttf"), ("Inter-Bold", "Inter-Bold.ttf"), ("Inter-Italic", "Inter-Italic.ttf")]:
    pdfmetrics.registerFont(TTFont(n, os.path.join(FD, f)))
pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-Semi", italic="Inter-Italic", boldItalic="Inter-Semi")
SYS = "/System/Library/Fonts/Supplemental/"
for n, f in [("Georgia", "Georgia.ttf"), ("Georgia-Bold", "Georgia Bold.ttf"), ("Georgia-Italic", "Georgia Italic.ttf"), ("Georgia-BoldItalic", "Georgia Bold Italic.ttf")]:
    pdfmetrics.registerFont(TTFont(n, SYS + f))
pdfmetrics.registerFontFamily("Georgia", normal="Georgia", bold="Georgia-Bold", italic="Georgia-Italic", boldItalic="Georgia-BoldItalic")

# palette: burnt orange, copper, brown
ORANGE = colors.HexColor("#B5451B"); COPPER = colors.HexColor("#C8844B"); BROWN = colors.HexColor("#5A3A28")
INK = colors.HexColor("#2A2015"); SLATE = colors.HexColor("#6B5A4C"); MUT = colors.HexColor("#9A8B7C")
PAPER = colors.HexColor("#F6F0E6"); LINE = colors.HexColor("#D9CDBD"); ROW = colors.HexColor("#FBF8F3"); WHITE = colors.white

PW, PH = letter; ML = 1.3 * inch; MR = 1.3 * inch; MT = 0.95 * inch; MB = 0.95 * inch; W = PW - ML - MR
S = dict(
    body=ParagraphStyle("body", fontName="Georgia", fontSize=10, leading=15, textColor=INK, spaceAfter=8, allowWidows=0, allowOrphans=0),
    lead=ParagraphStyle("lead", fontName="Georgia", fontSize=11, leading=17, textColor=INK, spaceAfter=8),
    byline=ParagraphStyle("byline", fontName="Inter", fontSize=8.6, leading=12, textColor=SLATE, spaceAfter=0),
    kick=ParagraphStyle("kick", fontName="Inter-Medium", fontSize=8, leading=10, textColor=ORANGE, spaceBefore=22, spaceAfter=4, keepWithNext=1),
    h2=ParagraphStyle("h2", fontName="Georgia-Bold", fontSize=15, leading=19, textColor=BROWN, spaceBefore=0, spaceAfter=9, keepWithNext=1),
    h3=ParagraphStyle("h3", fontName="Inter-Semi", fontSize=10.2, leading=13, textColor=ORANGE, spaceBefore=10, spaceAfter=3, keepWithNext=1),
    li=ParagraphStyle("li", fontName="Georgia", fontSize=10, leading=15, textColor=INK, spaceAfter=5),
    box=ParagraphStyle("box", fontName="Georgia", fontSize=9.8, leading=14.6, textColor=INK, spaceAfter=5),
    boxh=ParagraphStyle("boxh", fontName="Inter-Semi", fontSize=8, leading=10, textColor=ORANGE, spaceAfter=6),
    ref=ParagraphStyle("ref", fontName="Inter", fontSize=7.8, leading=10.6, textColor=SLATE, leftIndent=16, firstLineIndent=-16, spaceAfter=3),
    th=ParagraphStyle("th", fontName="Inter-Semi", fontSize=7.8, leading=9.8, textColor=BROWN),
    td=ParagraphStyle("td", fontName="Inter", fontSize=8.2, leading=10.8, textColor=INK),
    exh=ParagraphStyle("exh", fontName="Inter-Semi", fontSize=8, leading=10, textColor=ORANGE, spaceBefore=10, spaceAfter=1),
    exht=ParagraphStyle("exht", fontName="Inter-Medium", fontSize=9.6, leading=12.5, textColor=BROWN, spaceAfter=5),
    src=ParagraphStyle("src", fontName="Inter", fontSize=7.8, leading=10.4, textColor=SLATE, spaceBefore=4, spaceAfter=14),
    quote=ParagraphStyle("quote", fontName="Georgia-Italic", fontSize=10, leading=14.5, textColor=SLATE, leftIndent=14, spaceAfter=8),
    note=ParagraphStyle("note", fontName="Georgia-Italic", fontSize=8.8, leading=12.6, textColor=SLATE, spaceAfter=6),
    covert=ParagraphStyle("covert", fontName="Georgia-Bold", fontSize=24, leading=29, textColor=BROWN, spaceAfter=10),
    covers=ParagraphStyle("covers", fontName="Georgia-Italic", fontSize=12, leading=16, textColor=SLATE, spaceAfter=14),
)
INLINE = {"strong": ("<b>", "</b>"), "b": ("<b>", "</b>"), "em": ("<i>", "</i>"), "i": ("<i>", "</i>"), "sub": ("<sub>", "</sub>"),
          "sup": ("<super>", "</super>"), "code": ('<font face="Courier" size="8.8" color="#5A3A28">', "</font>"), "a": ("", "")}

# Action titles (state the conclusion), keyed by section number; exhibit titles and sources in order of appearance.
ACTION = {1: "Load is arriving before generation, and the rules on who pays are being written without a way to measure it",
          2: "At the site, carbon intensity is a contract term, not a property of the technology",
          3: "The captured tonne is a product, and it can pay for decarbonising firm power",
          4: "Across a portfolio, carbon accounting is a chain-of-custody problem",
          5: "A clean-power contract that covers the year covers fewer than half the hours",
          6: "Proposed research: measure the residual, compare the mechanisms, specify the audit layer"}
EXHIBITS = [("Storing the captured tonne and keeping the claim is the only route to a low figure", "src/figures.py; per tonne of fossil methanol, kgCO₂e; 95 % capture; fuel factor IRENA (2021), illustrative", "Carbon flow per tonne of methanol under two CO₂ fates"),
            ("Every rule for captured CO₂ is broken somewhere in practice", "Author's analysis of advisory engagements, 2024–26", "Four accounting rules, and where each fails"),
            ("The same plant reports 251 or 708 kgCO₂e/MWh depending on CO₂ fate and claim holder", "src/feedstock_ci.py. Note: stoichiometry 1.374 t CO₂ per t methanol; 55 % LHV efficiency, 95 % capture, 6 % parasitic; fuel factors IRENA (2021), illustrative", "Electricity carbon intensity by feedstock, CO₂ fate and claim holder, kgCO₂e per MWh, well to plug"),
            ("Sold as feedstock, the captured tonne is worth 45–115 $/MWh of the power that made it; only a durable fate earns a claim", "src/feedstock_ci.py coproduct_value(); 0.46 t CO₂ per MWh at 95 % capture; price ranges IEA (2019) and 2025 removal offtakes, illustrative", "Captured CO₂ as a product: value per MWh by fate, and what the power may still claim"),
            ("Chains break at the first handover, where a proof is kept and sold twice", "src/attribute_ledger.py worked chain; serials as printed by the audit trail", "Custody chain from producer to retired claim, and the failure the ledger rejects"),
            ("One record serves four claims, and the rules it must satisfy arrive before the sites do", "Author's proposal to a US data-centre platform, 2026; rule dates from refs. 4, 6, 9, 10", "The portfolio ledger, and the rule timeline 2025–2028"),
            ("A solar PPA covering the year leaves 49–67 % of location-based emissions unmatched by the hour", "EIA Form 930 hourly net generation by fuel; EIA fleet-average emission rates; src/hourly_match.py. Annual-matched = 0 in every region", "100 MW flat load, six US balancing authorities, July–December 2025, tCO₂"),
            ("Three accounting answers for one physical load", "src/hourly_match.py on EIA Form 930; solar PPA sized to 100 % of period energy on each BA's own solar shape", "tCO₂, July–December 2025, 100 MW flat load"),
            ("In PJM the unmatched hours are served by gas and coal, 89 kt CO₂ in six months", "src/figures.py on EIA Form 930, PJM, July–December 2025; fuel shares of the unmatched hours", "Where a 100 MW load's energy goes under hourly matching")]
KEY = ["The same on-site power plant reports 251 or 708 kgCO₂e/MWh depending on one clause in the CO₂ offtake contract.",
       "The captured tonne is a product: sold as industrial feedstock it is worth 45–115 $/MWh of the power that made it, enough to fund firm low-carbon supply, and the claim rules are what keep that value honest.",
       "A solar PPA covering 100 % of a data centre's annual energy matches 42–48 % of its hours; the unmatched hours carry 49–67 % of the location-based emissions.",
       "Data-centre load added about US$9.3 billion to one PJM capacity auction; 25 states have large-load tariffs and FERC has opened proceedings against all six RTOs, yet no developer pledge names a method, a data source or an auditor.",
       "Proposed: measure the residual for announced AI capacity, compare the cost-allocation mechanisms by who bears what, and specify the audit layer."]


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(); self.blocks = []; self.buf = None; self.table = None; self.row = None; self.list_stack = []; self.in_quote = False; self.cur = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h1", "h2", "h3", "p"): self.buf = ""; self.cur = tag
        elif tag in ("ul", "ol"): self.list_stack.append((tag, []))
        elif tag == "li": self.buf = ""; self.cur = "li"
        elif tag == "table": self.table = []
        elif tag == "tr": self.row = []
        elif tag in ("th", "td"): self.buf = ""; self.cur = tag
        elif tag == "img": self.blocks.append(("img", a.get("src"), a.get("alt", "")))
        elif tag == "blockquote": self.in_quote = True
        elif tag == "hr": self.blocks.append(("hr", None, None))
        elif tag in INLINE and self.buf is not None: self.buf += INLINE[tag][0]
    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "p"):
            t = (self.buf or "").strip(); self.buf = None
            if not t: return
            if tag == "p" and self.list_stack: self.list_stack[-1][1].append(t)
            elif tag == "p" and self.in_quote: self.blocks.append(("quote", t, None))
            else: self.blocks.append((tag, t, None))
        elif tag == "li":
            if self.buf is not None and self.buf.strip(): self.list_stack[-1][1].append(self.buf.strip())
            self.buf = None
        elif tag in ("ul", "ol"):
            kind, items = self.list_stack.pop(); self.blocks.append((kind, items, None))
        elif tag in ("th", "td"): self.row.append((tag, (self.buf or "").strip())); self.buf = None
        elif tag == "tr": self.table.append(self.row); self.row = None
        elif tag == "table": self.blocks.append(("table", self.table, None)); self.table = None
        elif tag == "blockquote": self.in_quote = False
        elif tag in INLINE and self.buf is not None: self.buf += INLINE[tag][1]
    def handle_data(self, d):
        if self.buf is not None: self.buf += d.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse(md_path):
    html = subprocess.run(["pandoc", md_path, "-f", "gfm", "-t", "html"], check=True, capture_output=True, text=True).stdout
    t = Tree(); t.feed(html); return t.blocks


def table_flow(rows, width):
    ncol = max(len(r) for r in rows)
    data = [[Paragraph(txt, S["th"] if kind == "th" else S["td"]) for kind, txt in r] + [""] * (ncol - len(r)) for r in rows]
    lens = [max((len(re.sub("<[^>]+>", "", r[i][1])) if i < len(r) else 0) for r in rows) for i in range(ncol)]
    w = [max(l, 8) ** 0.7 for l in lens]; tot = sum(w); cw = [width * x / tot for x in w]
    t = Table(data, colWidths=cw, repeatRows=1)
    st = [("LINEABOVE", (0, 0), (-1, 0), 1.2, ORANGE), ("LINEBELOW", (0, 0), (-1, 0), 0.6, BROWN), ("BACKGROUND", (0, 0), (-1, 0), PAPER),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE), ("LINEBELOW", (0, -1), (-1, -1), 0.8, BROWN)]
    t.setStyle(TableStyle(st)); return t


def callout(paras, width, head=None):
    inner = ([Paragraph(head, S["boxh"])] if head else []) + paras
    t = Table([[inner]], colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PAPER), ("LINEBEFORE", (0, 0), (0, -1), 3, ORANGE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def build(md_path, out_pdf, kicker, running, cover=True, key=None, actions=None, exhibits=None):
    blocks = parse(md_path); title = re.sub("<[^>]+>", "", next((b[1] for b in blocks if b[0] == "h1"), ""))
    doc = BaseDocTemplate(out_pdf, pagesize=letter, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB, title=title, author="Svenja Telle")
    frame = Frame(ML, MB, W, PH - MB - MT, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def on_first(c, d):
        c.setFillColor(ORANGE); c.setFont("Inter-Medium", 7.6); c.drawString(ML, PH - 0.58 * inch, kicker.upper())
        c.setFillColor(MUT); c.setFont("Inter", 7.6); c.drawRightString(PW - MR, PH - 0.58 * inch, "SEPTEMBER 2026")
        c.setStrokeColor(ORANGE); c.setLineWidth(0.8); c.line(ML, PH - 0.66 * inch, ML + 0.35 * inch, PH - 0.66 * inch)
        c.setStrokeColor(LINE); c.setLineWidth(0.4); c.line(ML + 0.35 * inch, PH - 0.66 * inch, PW - MR, PH - 0.66 * inch); footer(c, d)

    def on_rest(c, d):
        c.setFillColor(MUT); c.setFont("Inter", 7.6); c.drawString(ML, PH - 0.58 * inch, running)
        c.setStrokeColor(ORANGE); c.setLineWidth(0.8); c.line(ML, PH - 0.66 * inch, ML + 0.35 * inch, PH - 0.66 * inch)
        c.setStrokeColor(LINE); c.setLineWidth(0.4); c.line(ML + 0.35 * inch, PH - 0.66 * inch, PW - MR, PH - 0.66 * inch); footer(c, d)

    def footer(c, d):
        c.setFillColor(MUT); c.setFont("Inter", 7.4); c.drawString(ML, 0.58 * inch, "Svenja Telle  ·  github.com/svetee/dc-feedstock-carbon")
        c.drawRightString(PW - MR, 0.58 * inch, str(d.page))

    doc.addPageTemplates([PageTemplate(id="first", frames=[frame], onPage=on_first, autoNextPageTemplate="rest"), PageTemplate(id="rest", frames=[frame], onPage=on_rest)])

    el = [Spacer(1, 0.55 * inch), Paragraph(title, S["covert"])]
    in_abs = False; refs = False; first_p = True; ex = 0; sec = 0
    for tag, val, extra in blocks:
        if tag == "h1": continue
        if tag == "p" and first_p:
            first_p = False
            if val.startswith("<i>"):
                el.append(Paragraph(re.sub(r"</?i>", "", val), S["byline"])); el.append(Paragraph("Denominator Pte. Ltd., Singapore  ·  Version 1.0  ·  svenjatelle@gmail.com", S["byline"])); el.append(Spacer(1, 10))
                el.append(Table([[""]], colWidths=[1.2 * inch], rowHeights=[3], style=[("BACKGROUND", (0, 0), (-1, -1), ORANGE)], hAlign="LEFT")); el.append(Spacer(1, 12))
                if key: el.append(callout([Paragraph(f"<font color='#B5451B' name='Inter-Semi'>{i}</font>&nbsp;&nbsp;&nbsp;{k}", ParagraphStyle("box2", parent=S["box"], leftIndent=14, firstLineIndent=-14)) for i, k in enumerate(key, 1)], W, "KEY TAKEAWAYS")); el.append(Spacer(1, 14)); continue
        if tag == "h2":
            plain = re.sub("<[^>]+>", "", val); refs = plain.lower().startswith("references")
            if plain.lower() == "summary":
                in_abs = True; el.append(Paragraph("SUMMARY", S["kick"])); continue
            m = re.match(r"(\d+)\.\s+(.*)", plain)
            if m and actions:
                sec = int(m.group(1)); el.append(Paragraph(f"SECTION {sec}", S["kick"])); el.append(Paragraph(actions.get(sec, m.group(2)), S["h2"]))
            else:
                el.append(Spacer(1, 14)); el.append(Paragraph(plain if not refs else "References", ParagraphStyle("h2s", parent=S["h2"], fontSize=13)))
            continue
        if tag == "hr":
            in_abs = False; continue
        if tag == "h3": el.append(Paragraph(val, S["h3"])); continue
        if tag == "p":
            if refs: continue
            st = S["lead"] if in_abs else (S["note"] if val.startswith("<i>Author") else S["body"])
            m = re.match(r"<b>([^<]{3,40})\.</b>\s*(.*)", val, re.S)
            if m and not in_abs:
                el.append(KeepTogether([Paragraph(m.group(1).upper(), ParagraphStyle("sk", parent=S["h3"], fontSize=8, textColor=ORANGE, spaceBefore=8, spaceAfter=2)), Paragraph(m.group(2), st)])); continue
            el.append(Paragraph(val, st)); continue
        if tag == "quote": el.append(Paragraph(val, S["quote"])); continue
        if tag in ("ul", "ol"):
            if refs:
                for i, it in enumerate(val, 1): el.append(Paragraph(f"{i}.&nbsp;&nbsp;{it}", S["ref"]))
                continue
            items = [ListItem(Paragraph(it, S["li"]), leftIndent=16, **({"value": i + 1} if tag == "ol" else {})) for i, it in enumerate(val)]
            el.append(ListFlowable(items, bulletType="1" if tag == "ol" else "bullet", start="▪" if tag == "ul" else None, leftIndent=16, bulletFontName="Georgia", bulletFontSize=8, bulletColor=ORANGE, bulletOffsetY=0, spaceAfter=6)); continue
        if tag in ("table", "img"):
            ex += 1; head = []
            if exhibits and ex <= len(exhibits):
                head = [Paragraph(f"EXHIBIT {ex}", S["exh"]), Paragraph(exhibits[ex - 1][0], S["exht"])] + ([Paragraph(exhibits[ex - 1][2], ParagraphStyle("exsub", parent=S["src"], textColor=SLATE, spaceBefore=0, spaceAfter=6))] if len(exhibits[ex - 1]) > 2 else [])
                srcp = [Paragraph("<b>Source:</b> " + exhibits[ex - 1][1], S["src"])]
            else: srcp = [Spacer(1, 10)]
            if tag == "table": body = [table_flow(val, W)]
            else:
                src = val if os.path.isabs(val) else os.path.normpath(os.path.join(os.path.dirname(md_path), val))
                if not os.path.exists(src): ex -= 1; continue
                im = Image(src); r = im.imageHeight / im.imageWidth; im.drawWidth = W; im.drawHeight = W * r; body = [im]
            el.append(KeepTogether(head + body + srcp)); continue
    doc.build(el); print(out_pdf)


if __name__ == "__main__":
    build(os.path.join(ROOT, "article", "low-carbon-feedstock-for-data-centres.md"),
          os.path.join(DIST, "Telle - Who pays for the electrons - working paper 2026.pdf"),
          "Working paper", "Who pays for the electrons?  ·  Working paper, September 2026", key=KEY, actions=ACTION, exhibits=EXHIBITS)
    build(os.path.join(ROOT, "README.md"), os.path.join(DIST, "dc-feedstock-carbon - README.pdf"), "Repository", "dc-feedstock-carbon  ·  README")
    if len(sys.argv) > 2:
        build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
