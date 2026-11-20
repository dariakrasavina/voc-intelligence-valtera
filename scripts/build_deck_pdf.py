"""Render docs/deck.md to docs/deck.pdf (one slide per page) using headless Chrome.
Usage: uv run --no-project --with markdown python scripts/build_deck_pdf.py"""
import os
import re
import subprocess
import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "docs", "deck.md")).read()
src = re.sub(r"^---\n.*?\n---\n", "", src, count=1, flags=re.S)          # drop front matter
slides = [s.strip() for s in re.split(r"\n---\n", src) if s.strip()]
body = "\n".join('<section class="slide">%s</section>' % markdown.markdown(s, extensions=["tables", "fenced_code"])
                 for s in slides)
css = """
@page { size: 13.33in 7.5in; margin: 0; }
body { margin: 0; font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; color: #1b1f24; }
.slide { box-sizing: border-box; width: 13.33in; height: 7.5in; padding: 0.55in 0.7in; page-break-after: always; overflow: hidden; }
h1 { font-size: 30px; margin: 0 0 18px; border-bottom: 4px solid #c8102e; padding-bottom: 10px; }
p, li { font-size: 17px; line-height: 1.45; }
table { border-collapse: collapse; width: 100%; font-size: 14.5px; margin-top: 8px; }
th, td { border-bottom: 1px solid #d0d7de; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #f3f4f6; }
pre { background: #f6f8fa; padding: 12px; font-size: 12.5px; line-height: 1.35; border-radius: 6px; }
.slide:last-of-type { page-break-after: auto; }
.footer { position: fixed; bottom: 0.25in; right: 0.7in; font-size: 11px; color: #6b7280; }
"""
html = ("<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s"
        "<div class='footer'>Valtera Motors is fictional · synthetic data · value figures are estimates</div></body></html>") % (css, body)
out_html = os.path.join(ROOT, "docs", "deck.html")
open(out_html, "w").write(html)
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--print-to-pdf=" + os.path.join(ROOT, "docs", "deck.pdf"), "file://" + out_html],
               check=True, capture_output=True)
os.remove(out_html)
print("wrote docs/deck.pdf with %d slides" % len(slides))
