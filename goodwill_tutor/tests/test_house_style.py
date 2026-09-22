"""The document rules: cleaning, repairing, naming, validating.

No window, no network, no Chromium — this file is pure text handling.
"""

import sys
from support import Report, sandbox

sandbox()
import house_style as hs

r = Report("House style — cleaning what the model sent")


def frac(num, den):
    return (f'<span class="frac"><span class="num">{num}</span>'
            f'<span class="den">{den}</span></span>')


def text_of(html):
    import re
    return re.sub(r"<[^>]*>", "", html)


# ── the model's own notes, printed into the PDF as page one ──────────────
NOTES_FIRST = '''* Topic: Discounting. * `top-bar` (Title: DISCOUNTING)
* `part-heading` (not needed here, but I will use it if I split methods)
<div class="page-block"><div class="q"><span>Illustration 6.</span></div></div>
Let me know if you want the PVF method too!'''
body, dropped = hs.extract_document(NOTES_FIRST)
r.check("planning before the document is dropped", "Topic: Discounting" in dropped)
r.check("the sign-off after it is dropped too", "Let me know" in dropped)
r.check("the document itself is kept", body.startswith('<div class="page-block">'))
r.check("and ends where it should", body.endswith("</div>"))

CLEAN = '<div class="page-block"><div class="q"><span>x</span></div></div>'
r.check("a clean answer is left alone", hs.extract_document(CLEAN), (CLEAN, ""))

# ── a tag quoted in a sentence is an example, not a document ─────────────
RECITED = ('Okay. The HTML must start with `<div class="page-block">` and end '
           'with `</div>`. I will now solve it.')
r.check("a quoted tag is not mistaken for the document",
        hs.extract_document(RECITED), (RECITED, ""))
r.check("and that answer is refused", hs.looks_like_document(RECITED), False)
r.check("a real answer is accepted", hs.looks_like_document(CLEAN))

# ── divisions become stacked fractions, powers go under the line ─────────
BOX = ('<div class="formula-box">'
       '<span class="line">Present Value (P) = Future Value (F) / (1 + r)^n</span>'
       '<span class="line">P = <span class="amt">66,550</span> / (1 + '
       '<span class="amt">0.10</span>)^3</span>'
       '<span class="line">P = <span class="amt">66,550</span> / '
       '<span class="amt">1.331</span></span></div>')
fixed, notes = hs.repair_markup(BOX)
r.check("no slash survives", "/" in text_of(fixed), False)
r.check("the phrase stays with its bracket",
        frac("Future Value (F)", "(1 + r)<sup>n</sup>") in fixed)
den = fixed.split('<span class="den">')[2].split("</span></span>")[0]
r.check("the power sits under the line, with the bracket",
        den.startswith("(1 +") and "<sup>3</sup>" in den)
r.check("amounts keep their colour", 'class="amt"' in fixed)
r.check("three fractions counted", [n for n in notes if "fraction" in n], ["3 fractions"])
r.check("the markup is still sound", hs._balanced(fixed))

r.check("a single letter divides too",
        frac("F", "(1 + r)<sup>n</sup>") in hs.repair_markup(
            "<span>P = F / (1 + r)^n</span>")[0])
# A power the model left flat: "(1 + 0.10)3" reads as a multiplication.
raised, notes = hs.repair_markup('<span>P = 66,550 (1 + 0.10)3</span>')
r.check("a flat exponent is raised", "<sup>3</sup>" in raised)
r.check("and counted", any("exponent" in n for n in notes))
for name, src in [
        ("a question label", "<span>(a) 3 years of interest</span>"),
        ("a year", "<span>the year (2024) was good</span>"),
        ("a note in brackets", "<span>(Profit on revaluation) shared</span>"),
        ("a percentage", "<span>(1 + 0.10)%</span>"),
        ("one already raised", "<span>(1 + r)<sup>n</sup></span>"),
]:
    r.check(f"left flat — {name}", hs.repair_markup(src), (src, []))

r.check("a division sign is stacked",
        frac("66,550", "1.331") in hs.repair_markup("<span>66,550 ÷ 1.331</span>")[0])

# ── what must never be touched ──────────────────────────────────────────
for name, src in [
        ("a date", "<span>due on 21/09/2026</span>"),
        ("Bank A/c", "<span>To Bank A/c</span>"),
        ("P/L", "<span>transferred to P/L</span>"),
        ("w/o", "<span>stock w/o this year</span>"),
        ("Dr. / Cr.", "<span>Dr. / Cr.</span>"),
        ("a file path in an attribute", '<img src="a/b.png" alt="3/4">'),
        ("a fraction already stacked", "<span>" + frac("3", "4") + "</span>"),
        ("two cells of a table",
         '<tr><td class="right">66,550</td><td class="right">1.331</td></tr>'),
]:
    r.check(f"left alone — {name}", hs.repair_markup(src), (src, []))

# ── 'wn full' belongs to two-sided accounts only ─────────────────────────
STATEMENT = ('<table class="wn full"><tr><th>Particulars</th><th>Value</th></tr>'
             '<tr><td>Future Value</td><td>66,550</td></tr></table>')
fixed, notes = hs.repair_markup(STATEMENT)
r.check("a two-column statement loses 'full'", 'class="wn"' in fixed)
r.check("nothing of the old tag is left on the page", "ull\">" in fixed, False)
r.check("and it is reported", any("fitted" in n for n in notes))

LEDGER = ('<table class="wn full"><tr><th>Particulars</th><th>Amount</th>'
          '<th>Particulars</th><th>Amount</th></tr>'
          '<tr><td>To Stock</td><td>5,000</td><td>By Land</td><td>20,000</td></tr></table>')
r.check("a Dr./Cr. account keeps it", 'class="wn full"' in hs.repair_markup(LEDGER)[0])

# ── a model going round in circles ──────────────────────────────────────
LOOP = "\n\n".join([
    '* *Wait, the prompt says "No LaTeX: no \\times".* I will use "multiplied by".',
    '* *Wait, the prompt says "No LaTeX: no \\div".* I will use plain text.',
    '* *Wait, the prompt says "No LaTeX: no \\frac".* I will use a span.',
    '* *Wait, the prompt says "No LaTeX: no $ $".* I will use plain text.',
])
r.check("a loop is caught", hs.is_looping(LOOP))
r.check("two lines are not a loop", hs.is_looping("\n\n".join(LOOP.split("\n\n")[:2])), False)
JOURNAL = '<div class="page-block"><table class="wn">' + "".join(
    '<tr><td class="center">2026 Apr 1</td><td>To Bank A/c</td>'
    '<td class="right">4,00,000</td></tr>' for _ in range(40)) + "</table></div>"
r.check("a long journal is not a loop", hs.is_looping(JOURNAL), False)
r.check("thousands of words and no document is a loop", hs.is_looping("thinking. " * 1200))

# ── the document's own name ─────────────────────────────────────────────
ANSWER = ('<div class="page-block"><div class="top-bar">'
          '<span class="title">DISCOUNTING</span>'
          '<span class="pgref">Central Concepts | Pg. <span class="num">43</span></span></div>'
          '<div class="q"><span class="qno">Illustration <span class="num">6</span>.</span>'
          '<span>Suppose an investor expects Rs. 66,550.</span></div></div>')
r.check("named from the answer", hs.title_from_block(ANSWER),
        "Discounting — Illustration 6 (Pg. 43)")
r.check("falls back when there is nothing to read",
        hs.title_from_block("<div class='page-block'>x</div>", "Untitled"), "Untitled")

# ── the house rules themselves ──────────────────────────────────────────
page = hs.wrap_document([ANSWER])
errors, warnings = hs.validate_html(page)
r.check("our own stylesheet is clean", (errors, warnings), ([], []))
r.check("today's date is on the page", hs.today_stamp() in page)
r.check("the page colour is there", "#C8C8C8" in page)
r.check("cells cannot be whitened", "background-color: #C8C8C8 !important" in page)

white_page = hs.wrap_document([ANSWER]).replace("background:    #C8C8C8;",
                                                "background:    #FFFFFF;")
r.check("a white page is an error",
        any("RULE 6" in e for e in hs.validate_html(white_page)[0]))

broken = hs.wrap_document(['<div class="page-block" style="break-after: page">x</div>'])
r.check("a forced page break is an error",
        any("RULE 3" in e for e in hs.validate_html(broken)[0]))
white = hs.wrap_document(['<div class="page-block"><table class="wn">'
                          '<tr style="background:#fff"><td>x</td></tr></table></div>'])
r.check("white written into an answer is a warning",
        any(w.startswith("WHITE") for w in hs.validate_html(white)[1]))

sys.exit(r.finish())
