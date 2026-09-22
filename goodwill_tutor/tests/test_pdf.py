"""The printed page: A4, selectable text, and no white anywhere.

This one runs Chromium, so it takes a few seconds. If Playwright is not
installed it says so and passes, rather than failing for the wrong reason.
"""

import os
import sys
from support import Report, sandbox

sandbox()
import house_style as hs
import pdf_export

r = Report("The printed page")

if not pdf_export.playwright_available():
    print("\nThe printed page")
    print("  SKIP  Playwright is not installed — run:  pip install playwright")
    sys.exit(0)

# Only needed where Chromium is not where Playwright expects it.
_where = os.environ.get("GOODWILL_TEST_CHROMIUM")
if _where:
    import playwright.sync_api as pw
    _launch = pw.BrowserType.launch
    pw.BrowserType.launch = lambda self, **k: _launch(
        self, executable_path=_where, args=["--no-sandbox"], **k)

BLOCK = '''<div class="page-block">
<div class="top-bar"><span class="title">Discounting</span>
<span class="pgref">Central Concepts | Pg. <span class="num">43</span></span></div>
<div class="wn-sub">WN 1 — Given</div>
<table class="wn">
<tr><th>Particulars</th><th>Value</th></tr>
<tr><td>Future Value (F)</td><td class="right"><span class="amt">Rs. 66,550</span></td></tr>
<tr class="total"><td>Present Value (P)</td><td class="right"><span class="amt">Rs. 50,000</span></td></tr>
</table>
<div class="formula-box"><span class="line">P = <span class="amt">66,550</span>
 / <span class="amt">1.331</span></span></div>
<div class="final-ans">Present Value = Rs. 50,000</div></div>'''

body, _ = hs.repair_markup(BLOCK)
folder = sandbox()
html = os.path.join(folder, "page.html")
with open(html, "w", encoding="utf-8") as fh:
    fh.write(hs.wrap_document([body]))

try:
    pdf = pdf_export.html_to_pdf(html)
except pdf_export.PdfExportError as exc:
    print("\nThe printed page")
    print(f"  SKIP  Chromium could not run: {exc}")
    sys.exit(0)

r.check("a PDF is written", os.path.exists(pdf))
r.check("it is a real PDF", open(pdf, "rb").read(5), b"%PDF-")

raw = open(pdf, "rb").read()
# A page of text carries a ToUnicode map; a scan of a page does not.
r.check("the text is selectable, not a picture", b"/ToUnicode" in raw)

try:
    import pypdfium2 as pdfium
except ImportError:
    print("\nThe printed page")
    print("  (install pypdfium2 to also check the page size and colours)")
    sys.exit(r.finish())

page = pdfium.PdfDocument(pdf)[0]
width_mm = page.get_width() * 25.4 / 72
height_mm = page.get_height() * 25.4 / 72
r.check("A4 wide", 209 < width_mm < 212, True)
r.check("A4 tall", 296 < height_mm < 299, True)


words = page.get_textpage().get_text_range()
r.check("the words are really in the file", "Present Value" in words and "66,550" in words)

image = page.render(scale=1.2).to_pil().convert("RGB")
colours = image.getcolors(maxcolors=1 << 24) or []
page_colour = max(colours)[1] if colours else None
r.check("the page is #C8C8C8 throughout", page_colour, (200, 200, 200))
white = sum(n for n, colour in colours if min(colour) > 245)
r.check("almost nothing is white", white < image.size[0] * 3)

sys.exit(r.finish())
