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
# ── the division sign, in every form Flash-Lite has used ────────────────
for name, src in [
        ("F ÷ (1 + r)ⁿ", "<span>P = F \u00f7 (1 + r)\u207f</span>"),
        ("1 ÷ (1.10)³", "<span>PV Factor = 1 \u00f7 (1.10)\u00b3</span>"),
        ("words ÷ bracket^n", "<span>Future Value \u00f7 (1 + r)^n</span>"),
        ("no spaces", "<span>Profit\u00f7Sales</span>"),
        ("a slash with ³", "<span>P = 66,550 / (1 + 0.10)\u00b3</span>"),
]:
    out, _ = hs.repair_markup(src)
    flat = text_of(out)
    r.check(f"stacked — {name}", "\u00f7" in flat or "/" in flat, False)

out, _ = hs.repair_markup("<span>P = F \u00f7 (1 + r)\u207f</span>")
r.check("a superscript glyph becomes the house <sup>", "<sup>n</sup>" in out)

# ── a sentence is not a formula ─────────────────────────────────────────
KEY = "<span>Step 2: Press the division key \u00f7 twice.</span>"
r.check("a sentence about the ÷ key is left as a sentence",
        'class="frac"' in hs.repair_markup(KEY)[0], False)
r.check("and is not reported as an error", hs.validate_html(hs.wrap_document(
    [f'<div class="page-block"><div class="q">{KEY}</div></div>']))[0], [])
r.check("nor a spaced slash between lowercase words",
        'class="frac"' in hs.repair_markup("<span>press the key / twice</span>")[0], False)
out, _ = hs.repair_markup("<span>Cost of Goods Sold \u00f7 Average Stock</span>")
r.check("a capitalised name with 'of' is taken whole",
        frac("Cost of Goods Sold", "Average Stock") in out)

# ── the final answer stays with its working ─────────────────────────────
css = hs.GOODWILL_CSS
r.check("the final answer is kept with the line above",
        ".final-ans {\n  break-before:      avoid;" in css)
r.check("RULE 4 permits it", "break-inside: avoid" not in " ".join(
    e for e in hs.validate_html(hs.wrap_document(["<div class='page-block'>x</div>"]))[0]))
r.check("the last block leaves no gap on paper", ".page-block:last-child" in css)
r.check("fraction lines have room above and below", "margin:          0.3em 0.15em;" in css)

# ── a power left beside a fraction goes into its denominator ────────────
F = '<span class="frac"><span class="num">{n}</span><span class="den">{d}</span>{t}</span>'
out, notes = hs.repair_markup("<span>" + F.format(n="1", d="(1 + r)", t="\u207f") + "</span>")
r.check("a power after the denominator is put inside it",
        '<span class="den">(1 + r)<sup>n</sup></span></span>' in out)
out, _ = hs.repair_markup("<span>66,550 \u00d7 " + F.format(n="1", d="1.10", t="") + "\u00b3</span>")
r.check("a power after 1 over x goes under the line",
        '<span class="den">1.10<sup>3</sup></span></span>' in out)
r.check("and nothing is left beside the fraction", out.endswith("</span></span></span>"))
two = "<span>" + F.format(n="2", d="3", t="") + "<sup>2</sup></span>"
r.check("a power after any other fraction is left alone",
        hs.repair_markup(two)[0].endswith("</span></span><sup>2</sup></span>"))
r.check("the note reads well for two",
        hs.repair_markup("<span>" + F.format(n="1", d="a", t="\u00b2") + " and "
                         + F.format(n="1", d="b", t="\u00b3") + "</span>")[1][-1],
        "2 powers moved into their denominator")

# ── the "×" a model left out, and the mixed numbers that must not get one ─
def restored(src):
    return "multiplication sign restored" in " ".join(hs.repair_markup(src)[1])

r.check("× restored: 66,550 then 1/1.331",
        restored("<span>P = <span class=\"amt\">66,550</span> " + F.format(n="1", d="1.331", t="") + "</span>"))
r.check("× restored: Future Value then 1/(1 + r)ⁿ",
        restored("<span>PV = Future Value " + F.format(n="1", d="(1 + r)<sup>n</sup>", t="") + "</span>"))
r.check("no × in a mixed number, 2 ½ years",
        restored("<span>Goodwill at 2 " + F.format(n="1", d="2", t="") + " years</span>"), False)
r.check("no × in a mixed number, 7 ½ %",
        restored("<span>Interest @ 7 " + F.format(n="1", d="2", t="") + "%</span>"), False)
r.check("no × in a sentence about the factor",
        restored("<span>To calculate the factor " + F.format(n="1", d="1.10<sup>3</sup>", t="") + " here</span>"), False)
r.check("no second × when one is there",
        restored("<span>P = 66,550 \u00d7 " + F.format(n="1", d="1.331", t="") + "</span>"), False)

# ── a power written as a <sup> tag stays a power ────────────────────────
out, _ = hs.repair_markup("<span>the factor 1/1.10<sup>3</sup> on a calculator</span>")
r.check("1/1.10³ keeps its power — never 1/1.103",
        '<span class="den">1.10<sup>3</sup></span>' in out)
r.check("and leaves no empty <sup> behind", "<sup></sup>" in out, False)
out, _ = hs.repair_markup("<span>P = 66,550 / (1 + 0.10)<sup>3</sup></span>")
r.check("a bracket with a <sup> power is stacked whole",
        '<span class="den">(1 + 0.10)<sup>3</sup></span>' in out)

# ── a power written in the note class — his 9:08 page, lines 306 and 330 ─
L306 = ('<span>To calculate the factor <span class="frac"><span class="num">1</span>'
        '<span class="den"><span class="amt">1.10</span><span class="small">3</span>'
        '</span></span> on a normal calculator</span>')
L330 = ('<td>P = F &times; <span class="frac"><span class="num">1</span>'
        '<span class="den"><span class="amt">(1 + r)</span><span class="small">n</span>'
        '</span></span></td>')
r.check("1.10 with a .small 3 becomes 1.10³, never 1.103",
        '<span class="amt">1.10</span><sup>3</sup>' in hs.repair_markup(L306)[0])
r.check("(1 + r) with a .small n becomes (1 + r)ⁿ",
        '<span class="amt">(1 + r)</span><sup>n</sup>' in hs.repair_markup(L330)[0])
NOTE = '<td>To Revaluation A/c <span class="small">(Profit on revaluation)</span></td>'
r.check("a real bracketed note stays a note", hs.repair_markup(NOTE), (NOTE, []))
WORD = '<td>Salary <span class="small">3</span> months</td>'
r.check("a lone figure after a word is not a power", hs.repair_markup(WORD), (WORD, []))

# ── inside a fraction the model built itself ────────────────────────────
out, _ = hs.repair_markup("<span>PVF = " + F.format(n="1", d="(1 + 10/100)\u00b3", t="") + "</span>")
r.check("a division inside a denominator is stacked",
        '<span class="num">10</span><span class="den">100</span>' in out)
r.check("and the power inside it is raised", "<sup>3</sup>" in out)
kept = "<span>" + F.format(n="66,550", d="1.331", t="") + "</span>"
r.check("a finished fraction is not touched", hs.repair_markup(kept), (kept, []))

# ── an error that says where it is ──────────────────────────────────────
page = hs.wrap_document(['<div class="page-block"><table class="wn"><tr>'
                         '<td>Present Value Factor (1 \u00f7 x)</td></tr></table>'
                         '<div class="q"><span>Share is 3/5 of it.</span></div></div>'])
errors, warnings = hs.validate_html(page)
r.check("the error quotes the cell it is in",
        any("'Present Value Factor (1 \u00f7 x)'" in e for e in errors))
r.check("the warning quotes its own line only",
        any("'Share is 3/5 of it.'" in w for w in warnings))

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

# ── RULE 12: the numeral at 20pt, the words at normal size ──────────────
BIG6 = '<span class="qno">Illustration <span class="num">6</span>.</span>'
fixed, notes = hs.repair_markup('<div class="q"><span>Illustration 6. Find the value.</span></div>')
r.check("a plain question number is enlarged", BIG6 + " Find the value." in fixed)
r.check("and it is reported", notes, ["1 numeral set at 20pt"])
r.check("a bold question number is enlarged",
        hs.repair_markup('<div class="q"><b>Illustration 6.</b><span>x</span></div>')[0],
        '<div class="q">' + BIG6 + '<span>x</span></div>')
r.check("a qno span without its numeral span is mended",
        hs.repair_markup('<div class="q"><span class="qno">Illustration 6.</span></div>')[0],
        '<div class="q">' + BIG6 + '</div>')
r.check("the page numeral is enlarged",
        '| Pg. <span class="num">43</span></span>' in
        hs.repair_markup('<span class="pgref">Central Concepts | Pg. 43</span>')[0])
r.check("a correct number is left alone",
        hs.repair_markup('<div class="q">' + BIG6 + '</div>'),
        ('<div class="q">' + BIG6 + '</div>', []))
r.check("a question number in a div of its own is enlarged",
        'class="qno">Illustration <span class="num">6</span>.' in
        hs.repair_markup('<div class="q"><div class="qno">Illustration 6.</div></div>')[0])
r.check("so is one in a plain paragraph",
        BIG6 in hs.repair_markup('<div class="q"><p>Illustration 6.</p></div>')[0])
r.check("a tag between the word and the number is no hiding place",
        '<span class="qno"><span class="num">6</span></span>' in
        hs.repair_markup('<div class="q"><span><b>Illustration</b> 6.</span></div>')[0])
r.check("nor is a non-breaking space",
        '<span class="qno">Illustration&nbsp;<span class="num">6</span>.</span>' in
        hs.repair_markup('<div class="q"><span>Illustration&nbsp;6.</span></div>')[0])
r.check("a numeral wrapped alone by an older version gets its word back",
        hs.repair_markup('<div class="q"><span>Illustration&nbsp;<span class="qno">'
                         '<span class="num">6</span></span>.</span></div>')[0],
        '<div class="q"><span><span class="qno">Illustration&nbsp;<span class="num">6</span>.'
        '</span></span></div>')
r.check("the words of the question number are bold", ".qno      { font-weight: bold; }" in hs.GOODWILL_CSS)
r.check("the top bar title is not a question number",
        hs.repair_markup('<span class="title">Illustration 6</span>')[1], [])
r.check("a number in the working is not a question number",
        hs.repair_markup('<div class="sol-label">Solution</div>'
                         '<div class="wn-text"><span>Question 3 said so.</span></div>')[1], [])
r.check("a figure in the question text is not touched",
        hs.repair_markup('<div class="q"><span>A had 6 partners.</span></div>')[1], [])

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
