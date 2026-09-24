"""The printed page: A4, selectable text, and no white anywhere.

This one runs Chromium, so it takes a few seconds. If Playwright is not
installed it says so and passes, rather than failing for the wrong reason.
"""

import os
import pathlib
import re
import sys
from support import ROOT, Report, sandbox

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

# ── the final answer never sits alone on a page ─────────────────────────
# The layout that showed the fault: at 18 to 21 lines of question, the page
# still had room, yet the final answer was pushed over by itself.
TAIL = ('<div class="tbl-title">Calculation of Present Value</div>'
        '<table class="wn"><tr><th>Particulars</th><th>Amount (Rs.)</th></tr>'
        '<tr><td>Future Value (F)</td><td class="right">66,550</td></tr>'
        '<tr><td>Discount Rate (r)</td><td class="right">10%</td></tr>'
        '<tr><td>Time Period (n)</td><td class="right">3 years</td></tr>'
        '<tr><td>Present Value Factor</td><td class="right">0.7513</td></tr>'
        '<tr class="total"><td>Present Value (P)</td><td class="right">50,000</td></tr></table>'
        '<div class="formula-box">'
        '<span class="line">Present Value = Future Value \u00d7 1 / (1 + r)^n</span>'
        '<span class="line">Present Value = 66,550 \u00d7 1 / (1 + 0.10)^3</span>'
        '<span class="line final">Present Value = 50,000</span></div>'
        '<div class="final-ans">\u2234 The present value of Rs. 66,550 receivable '
        'after three years is Rs. 50,000.</div>')
stranded, blank = [], []
for lines in range(18, 22):
    filler = "".join(f'<div class="q"><span>Line {i} of the question text.</span></div>'
                     for i in range(lines))
    body, _ = hs.repair_markup(f'<div class="page-block">{filler}{TAIL}</div>')
    path = os.path.join(folder, f"break{lines}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(hs.wrap_document([body]))
    doc = pdfium.PdfDocument(pdf_export.html_to_pdf(path))
    texts = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    for number, text in enumerate(texts):
        if "\u2234" in text and number > 0 and "Present Value = 50,000" not in text:
            stranded.append(lines)
        if not text.strip():
            blank.append(lines)
r.check("the final answer is never alone on a page", stranded, [])
r.check("no blank page is left at the end", blank, [])

# ── the question number never ends a page on its own ────────────────────
# At 35 lines of earlier working, "Illustration 9." printed as the last line
# of page one and its question began page two.
QUESTION = ('<div class="q"><span class="qno">Illustration <span class="num">9</span>.</span>'
            '<span>Find the present value of Rs. 66,550 receivable after three years.</span>'
            '<span>The rate of interest is 10% per annum.</span></div>')
alone = []
for lines in range(33, 38):
    filler = "".join(f'<div class="notes"><span>Line {i} of the earlier working.</span></div>'
                     for i in range(lines))
    path = os.path.join(folder, f"qno{lines}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(hs.wrap_document([f'<div class="page-block">{filler}{QUESTION}</div>']))
    doc = pdfium.PdfDocument(pdf_export.html_to_pdf(path))
    for i in range(len(doc)):
        if doc[i].get_textpage().get_text_range().strip().endswith("Illustration 9."):
            alone.append(lines)
r.check("the question number stays with its question", alone, [])

# ── the Preview wraps lines where the PDF does ──────────────────────────
# At 880px the institute name sat on one line in Preview and broke onto two
# in the PDF. The Preview is now drawn at A4 width with the print rules.
from playwright.sync_api import sync_playwright
wide = os.path.join(folder, "wide.html")
with open(wide, "w", encoding="utf-8") as fh:
    fh.write(hs.wrap_document(['<div class="page-block"><div class="q"><span>x</span></div></div>']))
pdf_lines = (pdfium.PdfDocument(pdf_export.html_to_pdf(wide))[0].get_textpage()
             .get_text_range().split("Ernakulam")[0].strip().count("\n") + 1)
# Read from the source: importing the app would open its window.
with open(os.path.join(ROOT, "goodwill_tutor.py"), encoding="utf-8") as fh:
    width = int(re.search(r"^PREVIEW_WIDTH = (\d+)", fh.read(), re.M).group(1))
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": width, "height": 1000})
    page.emulate_media(media="print")
    page.goto(pathlib.Path(wide).as_uri())
    preview_lines = round(page.eval_on_selector(
        ".header .name",
        "e => e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)"))
    browser.close()
r.check("the Preview breaks lines where the PDF does", preview_lines, pdf_lines)

# ── text can be copied from the Preview ─────────────────────────────────
import json
shot = pdf_export.html_to_png(html, os.path.join(folder, "copy.png"), width=794,
                              scale=0.6, media="print", lines=True)
lines = json.load(open(shot + ".json", encoding="utf-8"))
everything = pdf_export.text_in(lines, 0, 0, 10 ** 6, 10 ** 6)
r.check("the Preview knows where its text is", len(lines) > 5)
r.check("all its text can be copied", "Present Value" in everything and "Discounting".upper() in everything.upper())
r.check("a fraction copies as 66,550/1.331", "66,550/1.331" in everything.replace(" ", ""))
row = next(b for b in lines if b["t"].startswith("Future Value"))
got = pdf_export.text_in(lines, row["x"] + 2, row["y"] + 2, row["x"] + 3, row["y"] + 3)
r.check("a click copies the one cell under it", got, "Future Value (F)")
across = pdf_export.text_in(lines, row["x"] + 2, row["y"] + 2, 10 ** 6, row["y"] + 3)
r.check("a table row copies as columns", across, "Future Value (F)\tRs. 66,550")

sys.exit(r.finish())
