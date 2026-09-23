"""Render article/*.md and README.md to PDF.

pandoc -> HTML fragment -> PyMuPDF Story -> PDF, then a drawn title band, running
header, footer and page numbers. Run from the repo root:
    python3 build_pdf.py
Outputs to dist/.
"""
import subprocess, os, re, fitz

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist"); os.makedirs(DIST, exist_ok=True)

NAVY = (0.03, 0.035, 0.10); COPPER = (0.55, 0.26, 0.125); PAPER = (0.96, 0.94, 0.90); GREY = (0.45, 0.42, 0.38)

CSS = """
body{font-family:Georgia,serif;font-size:10pt;line-height:1.5;color:#26221E}
h1{display:none}
h2{font-family:Helvetica,Arial,sans-serif;font-size:9pt;letter-spacing:0.12em;text-transform:uppercase;color:#8C4220;margin:20pt 0 6pt;padding-bottom:3pt;border-bottom:0.7pt solid #8C4220}
h3{font-family:Helvetica,Arial,sans-serif;font-size:10.5pt;color:#07091A;margin:12pt 0 3pt}
p{margin:0 0 7pt;text-align:justify} li{margin:0 0 4pt}
p.byline{font-family:Helvetica,Arial,sans-serif;font-size:8.5pt;color:#5C4A3A;text-align:left}
strong{color:#07091A}
table{border-collapse:collapse;width:100%;font-family:Helvetica,Arial,sans-serif;font-size:8.4pt;margin:8pt 0 4pt}
th{color:#8C4220;text-align:left;padding:4pt 6pt;font-weight:bold;border-bottom:1pt solid #8C4220}
td{padding:4pt 6pt;border-bottom:0.4pt solid #D8CFC0;vertical-align:top}
tr:nth-child(even) td{background:#F7F3EC}
img{width:100%;margin:6pt 0 2pt}
blockquote{border-left:2.5pt solid #8C4220;padding:2pt 0 2pt 10pt;color:#3E3229;margin:8pt 0}
code{font-family:Menlo,monospace;font-size:8.4pt;color:#8C4220}
pre{font-family:Menlo,monospace;font-size:8pt;background:#F5EFE6;padding:6pt}
hr{border:0;border-top:0.5pt solid #D8CFC0;margin:12pt 0}
p.caption{font-family:Helvetica,Arial,sans-serif;font-size:8pt;color:#5C4A3A;text-align:left;margin:0 0 10pt}
div.abstract{background:#F5EFE6;border-left:3pt solid #8C4220;padding:8pt 12pt;margin:0 0 12pt}
"""


def md_to_html(md_path: str) -> str:
    html = subprocess.run(["pandoc", md_path, "-f", "gfm", "-t", "html"], check=True, capture_output=True, text=True).stdout
    base = os.path.dirname(os.path.abspath(md_path))
    html = re.sub(r'src="(?!https?://)([^"]+)"', lambda m: f'src="{os.path.normpath(os.path.join(base, m.group(1)))}"', html)
    # first italic paragraph after the title = byline
    html = re.sub(r'<p><em>(.*?)</em></p>', r'<p class="byline">\1</p>', html, count=1)
    # a paragraph starting with an image gets a caption class on the following italic line if any
    html = html.replace('<h2>Summary</h2>', '<h2>Summary</h2><div class="abstract">', 1)
    if '<div class="abstract">' in html:
        html = html.replace('<hr />', '</div><hr />', 1)
    return html


def render(md_path: str, out_pdf: str, title: str, footer: str, band=True):
    html = md_to_html(md_path)
    story = fitz.Story(html=html, user_css=CSS, archive=fitz.Archive(ROOT))
    writer = fitz.DocumentWriter(out_pdf)
    page = fitz.paper_rect("letter")
    first_top = 150 if band else 60
    n = 0; more = 1
    while more:
        n += 1
        top = first_top if n == 1 else 66
        where = fitz.Rect(58, top, page.width - 58, page.height - 62)
        dev = writer.begin_page(page)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    doc = fitz.open(out_pdf); total = len(doc)
    for i, p in enumerate(doc):
        if i == 0 and band:
            p.draw_rect(fitz.Rect(0, 0, page.width, 118), color=None, fill=NAVY)
            p.draw_rect(fitz.Rect(0, 118, page.width, 121), color=None, fill=COPPER)
            p.insert_text((58, 40), "WORKING PAPER  ·  SEPTEMBER 2026", fontsize=7.5, fontname="helv", color=(0.79, 0.51, 0.31))
            p.insert_textbox(fitz.Rect(58, 50, page.width - 58, 114), title, fontsize=17, fontname="hebo", color=(0.93, 0.91, 0.87), lineheight=1.15)
        else:
            p.insert_text((58, 40), footer, fontsize=7.2, fontname="helv", color=GREY)
            p.draw_line((58, 46), (page.width - 58, 46), color=(0.85, 0.81, 0.75), width=0.5)
        p.insert_text((58, page.height - 34), "Svenja Telle  ·  github.com/svetee/dc-feedstock-carbon", fontsize=7.2, fontname="helv", color=GREY)
        p.insert_text((page.width - 58 - 46, page.height - 34), f"{i+1} / {total}", fontsize=7.2, fontname="helv", color=GREY)
    doc.save(out_pdf, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    print(out_pdf, total, "pages")


if __name__ == "__main__":
    render(os.path.join(ROOT, "article", "low-carbon-feedstock-for-data-centres.md"),
           os.path.join(DIST, "Telle - Who pays for the electrons - working paper 2026.pdf"),
           "Who pays for the electrons? Carbon, custody and the missing measurement layer under AI infrastructure",
           "Who pays for the electrons?  ·  Working paper")
    render(os.path.join(ROOT, "README.md"),
           os.path.join(DIST, "dc-feedstock-carbon - README.pdf"),
           "dc-feedstock-carbon: accounting, custody, and who pays", "dc-feedstock-carbon  ·  README")
