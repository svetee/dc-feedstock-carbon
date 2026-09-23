"""Render article/*.md and README.md to PDF (Georgia, copper accents, page numbers).

pandoc -> HTML fragment -> PyMuPDF Story -> PDF. Run from the repo root:
    python3 build_pdf.py
Outputs to dist/.
"""
import subprocess, os, re, fitz

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist"); os.makedirs(DIST, exist_ok=True)

CSS = """
body{font-family:Georgia,serif;font-size:10.2pt;line-height:1.45;color:#26221E}
h1{font-size:19pt;line-height:1.2;color:#8C4220;margin:0 0 6pt}
h2{font-size:13pt;color:#8C4220;margin:16pt 0 5pt;border-bottom:0.6pt solid #E0D5C4;padding-bottom:2pt}
h3{font-size:11pt;color:#A86040;margin:10pt 0 3pt}
p{margin:0 0 7pt} li{margin:0 0 3pt}
em{color:#5C4A3A}
table{border-collapse:collapse;width:100%;font-size:8.8pt;margin:6pt 0 9pt}
th{background:#F5EFE6;text-align:left;padding:3pt 5pt;border-bottom:0.8pt solid #8C4220;color:#5C331C}
td{padding:3pt 5pt;border-bottom:0.4pt solid #E0D5C4;vertical-align:top}
img{width:100%}
blockquote{border-left:2pt solid #8C4220;padding-left:8pt;color:#5C4A3A}
code{font-family:Menlo,monospace;font-size:8.6pt;background:#F5EFE6}
pre{font-family:Menlo,monospace;font-size:8.2pt;background:#F5EFE6;padding:6pt}
hr{border:0;border-top:0.5pt solid #E0D5C4;margin:10pt 0}
"""


def md_to_html(md_path: str) -> str:
    html = subprocess.run(["pandoc", md_path, "-f", "gfm", "-t", "html"], check=True, capture_output=True, text=True).stdout
    # image paths relative to the md file -> absolute
    base = os.path.dirname(os.path.abspath(md_path))
    html = re.sub(r'src="(?!https?://)([^"]+)"', lambda m: f'src="{os.path.normpath(os.path.join(base, m.group(1)))}"', html)
    return html


def render(md_path: str, out_pdf: str, footer: str):
    html = md_to_html(md_path)
    story = fitz.Story(html=html, user_css=CSS, archive=fitz.Archive(ROOT))
    writer = fitz.DocumentWriter(out_pdf)
    page = fitz.paper_rect("letter"); where = page + (54, 54, -54, -60)
    more = 1; n = 0
    while more:
        n += 1
        dev = writer.begin_page(page)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    # footer pass
    doc = fitz.open(out_pdf); total = len(doc)
    for i, p in enumerate(doc):
        p.insert_text((54, page.height - 36), footer, fontsize=7.5, fontname="tiro", color=(0.54, 0.51, 0.47))
        p.insert_text((page.width - 54 - 40, page.height - 36), f"Page {i+1} of {total}", fontsize=7.5, fontname="tiro", color=(0.54, 0.51, 0.47))
    doc.save(out_pdf, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    print(out_pdf, total, "pages")


if __name__ == "__main__":
    render(os.path.join(ROOT, "article", "low-carbon-feedstock-for-data-centres.md"),
           os.path.join(DIST, "Telle - Who pays for the electrons - working paper 2026.pdf"),
           "Svenja Telle · Who pays for the electrons? · Working paper, September 2026 · github.com/svetee/dc-feedstock-carbon")
    render(os.path.join(ROOT, "README.md"),
           os.path.join(DIST, "dc-feedstock-carbon - README.pdf"),
           "Svenja Telle · dc-feedstock-carbon · README")
