"""
GOODWILL TUITION CENTRE — House Style Engine
============================================
Owns the canonical A4 stylesheet, the document header, and the validator.

Gemini returns ONLY .page-block body content.
This module supplies every line of CSS, so the house style can never drift.

Edit this file to change colours, fonts or spacing.
Nothing here depends on the API or the GUI.
"""

from datetime import date
import collections
import difflib
import html as html_lib
import re

# ═══════════════════════════════════════════════════════════════
#  INSTITUTE DETAILS
# ═══════════════════════════════════════════════════════════════

INSTITUTE_NAME = "GOODWILL TUITION CENTRE FOR ACCOUNTANCY &amp; INCOME TAX ONLINE"
INSTITUTE_LINE2_PREFIX = "Ernakulam, Kerala"
INSTITUTE_PHONE = "9567902805"
INSTITUTE_WEBSITE = "goodwilltuitioncentre.in"


def today_stamp():
    """RULE 11 — 'd Month YYYY', no ordinal, no comma, full month, 4-digit year."""
    d = date.today()
    return f"{d.day} {d.strftime('%B')} {d.year}"


# ═══════════════════════════════════════════════════════════════
#  CANONICAL STYLESHEET  (v4 — 31 August 2026)
#  Plain string, not an f-string: CSS braces must stay literal.
# ═══════════════════════════════════════════════════════════════

GOODWILL_CSS = """
/* ---------- RULE 2 : page geometry — single source of margin ---------- */
@page { size: A4; margin: 0; }

html, body {
  print-color-adjust:         exact;
  -webkit-print-color-adjust: exact;
}

body {
  background:    #C8C8C8;
  font-family:   "Times New Roman", Times, serif;
  font-size:     13pt;
  color:         #000000;
  line-height:   1.5;
  margin:        0;
  padding:       0.5cm;
  max-width:     210mm;
  overflow-x:    hidden;
}

/* ---------- HEADER — once only, top of document ---------- */
.header {
  text-align:    center;
  color:         #0057B8;
  font-weight:   bold;
  border-bottom: 3px solid #0057B8;
  margin-bottom: 14px;
  padding:       14px 0 10px 0;
}
.header .name    { font-size: 15pt; letter-spacing: 0.5pt; }
.header .contact { font-size: 11.5pt; font-weight: normal; margin-top: 5px; }
.header .contact .phone { color: #CC0000; font-weight: bold; }
.header .date    { font-size: 10.5pt; font-weight: normal; color: #CC0000; margin-top: 4px; }

/* ---------- TOP BAR — first .page-block of each question ---------- */
.top-bar {
  display:       flex;
  align-items:   center;
  border-bottom: 1px solid #000;
  padding:       4px 0;
  margin-bottom: 14px;
}
.top-bar .title {
  flex:           1;
  text-align:     center;
  font-weight:    bold;
  text-transform: uppercase;
  font-size:      14pt;
  color:          #00008B;
}
.top-bar .pgref {
  color:       #CC0000;
  font-weight: bold;
  white-space: nowrap;
  font-size:   13pt;
}
.top-bar .pgref .num { font-size: 20pt; }        /* RULE 12 — digit only */

/* ---------- PAGE BLOCK — per-question container ---------- */
.page-block {
  max-width:  210mm;
  margin:     0 auto 30px auto;
  padding:    0;
  background: #C8C8C8;
  overflow:   hidden;
  /* RULE 3 : no break-after / page-break-after  */
  /* RULE 4 : no break-inside on this selector   */
}

/* RULE 4 — the ONLY break-avoidance rule permitted.
   .final-ans added with the teacher's approval, 23 Sept 2026: a final answer
   printed alone at the top of a new page is cut off from the working it
   concludes. */
table.wn tr,
.formula-box,
.final-ans {
  break-inside:      avoid;
  page-break-inside: avoid;
}

/* Keep the final answer on the same page as the line above it. When the two
   will not fit, they move over together rather than leaving it stranded. */
.final-ans {
  break-before:      avoid;
  page-break-before: avoid;
}

/* Keep the question number on the same page as its question text — approved
   by the teacher, 24 Sept 2026. The sentence after the number refuses a break
   before it, so "Illustration 7." never ends a page on its own. */
.q > .qno + span {
  break-before:      avoid;
  page-break-before: avoid;
}

@media screen {
  .page-block + .page-block {
    margin-top:  40px;
    border-top:  3px dashed #888;
    padding-top: 30px;
  }
}
@media print {
  .page-block + .page-block {
    margin-top:  0;
    border-top:  none;
    padding-top: 0;
  }
  /* Nothing follows the last block on paper, and its 30px gap had to fit on
     the same page as the final answer — enough to push the answer over alone
     with a third of a page still free. */
  .page-block:last-child {
    margin-bottom: 0;
  }
}

/* ---------- RULES 5 & 10 : one sentence per line, direct child only ---------- */
.q       > span,
.notes   > span,
.adj     > span,
.wn-text > span { display: block; }

.qno      { font-weight: bold; }                     /* problem no. words: bold */
.qno .num { font-size: 20pt; font-weight: bold; }   /* RULE 12 */

.sub { margin-left: 40px; }

/* ---------- LABEL HIERARCHY ---------- */
.sol-label,
.part-heading {
  font-size:    13pt;
  font-weight:  bold;
  color:        #6A0DAD;
  border-left:  4px solid #6A0DAD;
  padding-left: 8px;
  margin:       14px 0 6px 0;
}
.wn-label { font-weight: bold; color: #0057B8; margin: 12px 0 4px 0; }
.wn-sub   { font-weight: bold; color: #6A0DAD; margin: 8px 0 2px 0; }

/* ---------- INLINE SPANS — must never be forced to their own line ---------- */
.amt    { color: #CC0000; }
.small  { font-size: 11pt; font-style: italic; color: #C2185B; }
.source { font-size: 12pt; font-style: italic; color: #555555; }

.ans  { font-size: 12pt; font-style: italic; color: #000000; margin-top: 6px; }
.hint { font-size: 12pt; font-style: italic; color: #CC0000; margin-top: 4px; }

/* ---------- FRACTIONS — stacked everywhere, never ÷ ---------- */
.frac {
  display:         inline-flex;
  flex-direction:  column;
  justify-content: center;
  align-items:     center;
  vertical-align:  middle;
  /* Vertical margin too: a stacked fraction is two lines tall inside one, and
     without room above and below it the line crowds its neighbours. On an
     inline-flex box the margin counts toward the line's height. */
  margin:          0.3em 0.15em;
  font-size:       0.85em;
  line-height:     1.1;
}
/* Both halves stretch to the wider of the two, so the bar spans the whole
   fraction: "Future Value (F)" over "(1 + r)" gets a full-width rule instead of
   a stub under the shorter line. */
.frac span.num,
.frac span.den { align-self: stretch; text-align: center; padding: 0 0.1em; }
.frac span.num { font-size: 1em; font-weight: inherit; }
.frac span.den { border-top: 1px solid currentColor; }

/* ---------- FORMULA BOX ---------- */
.formula-box {
  border:     1px solid #6A0DAD;
  padding:    8px 14px;
  width:      auto;
  display:    inline-block;
  font-size:  12.5pt;
  margin:     6px 0;
  background: #EFEFEF !important;
}
.formula-box .line  { display: block; margin: 6px 0; }
.formula-box .final { font-weight: bold; }

/* ---------- TABLE TITLES & Dr./Cr. ROW ---------- */
.tbl-title {
  text-align:      center;
  font-weight:     bold;
  font-size:       13pt;
  color:           #6A0DAD;
  text-decoration: underline;
  margin:          14px 0 2px 0;
}
.dr-cr-row {
  display:         flex;
  justify-content: space-between;
  font-size:       12pt;
  font-weight:     bold;
  color:           #6A0DAD;
  margin-bottom:   2px;
}

/* ---------- TABLES ---------- */
table.wn {
  /* Fits its own contents. A three-row statement no longer spreads across the
     page with an acre of blank space beside every amount. max-width keeps a
     wide journal on the paper, and word-wrap below stops any cropping. */
  width:           auto;
  max-width:       100%;
  table-layout:    auto;
  border-collapse: collapse;
  font-size:       12.5pt;
  margin:          8px 0;
  border-left:     3px solid #0057B8;
}
table.wn th, table.wn td {
  border:         1px solid #000;
  padding:        4px 10px;
  vertical-align: top;
  word-wrap:      break-word;
  overflow-wrap:  break-word;
}
/* Every cell is coloured explicitly. A model that writes style="background:#fff"
   on a row cannot turn the page white: an author rule marked !important beats
   an inline declaration that carries no !important. */
table.wn td,
.page-block table td { background-color: #C8C8C8 !important; }

table.wn th,
.page-block table th {
  font-style:  italic;
  font-weight: bold;
  text-align:  center;
  background:  #BDBDBD !important;
}
table.wn td.right    { text-align: right; }
table.wn td.center   { text-align: center; }
table.wn tr.total td    { font-weight: bold; border-top: 2px solid #000; }
table.wn tr.subtotal td { border-top: 1px solid #000; }
table.wn .small { color: #C2185B; font-style: italic; font-size: 11pt; }

/* A two-sided ledger account: both halves must match, so it spans the page and
   takes its column widths from the colgroup. */
table.wn.full {
  width:        100%;
  table-layout: fixed;
}

/* Was the opt-out when tables were full-width by default; now the default. */
table.wn.auto { width: auto; table-layout: auto; }

/* ---------- NARRATION IN JOURNALS ---------- */
.narration { color: #222222; font-style: italic; }

/* ---------- RULE NOTES ---------- */
.rule-note { font-style: italic; color: #6A0DAD; margin: 6px 0; }

/* ---------- QUOTE BOX ---------- */
.quote-box {
  background:  #4a90d9 !important;
  color:       #FFFFFF;
  border-left: 4px solid #00008B;
  padding:     10px 14px;
  margin:      10px 0;
  font-size:   12.5pt;
}

/* ---------- FINAL ANSWER ---------- */
.final-ans {
  font-weight: bold;
  font-size:   13pt;
  color:       #CC0000;
  margin-top:  12px;
  border-top:  1px solid #CC0000;
  padding-top: 4px;
}

/* ---------- VERIFICATION STRIP (screen + print) ---------- */
.verify-ok, .verify-bad {
  font-size:   12pt;
  padding:     8px 12px;
  margin:      10px 0;
  border-left: 4px solid;
}
.verify-ok  { border-color: #2d7a2d; color: #1d5c1d; background: #E4F0E4 !important; }
.verify-bad { border-color: #CC0000; color: #8B0000; background: #F7E2E2 !important; }
"""


# ═══════════════════════════════════════════════════════════════
#  DOCUMENT ASSEMBLY
# ═══════════════════════════════════════════════════════════════

_HEADER_HTML = """<div class="header">
  <div class="name">{name}</div>
  <div class="contact">{place} | Ph: <span class="phone">{phone}</span> | {site}</div>
  <div class="date">{stamp}</div>
</div>"""


def build_header():
    """The single document header — RULES 8, 11 and 13: text only, live date, no logo, no social links."""
    return _HEADER_HTML.format(
        name=INSTITUTE_NAME,
        place=INSTITUTE_LINE2_PREFIX,
        phone=INSTITUTE_PHONE,
        site=INSTITUTE_WEBSITE,
        stamp=today_stamp(),
    )


def wrap_document(body_blocks, title="Goodwill Solution"):
    """Wrap one or more .page-block strings into a complete A4 document.

    body_blocks: a single HTML string, or a list of .page-block strings.
    """
    if isinstance(body_blocks, str):
        body_blocks = [body_blocks]
    blocks = "\n\n".join(b.strip() for b in body_blocks if b and b.strip())
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
        f"<title>{title}</title>\n"
        f"<style>{GOODWILL_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{build_header()}\n\n{blocks}\n"
        "</body>\n</html>\n"
    )


_STYLE_BLOCK = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)


def restyle(html):
    """Put today's stylesheet into a document written by an older version.

    A document keeps the stylesheet it was born with: the page is saved whole,
    and later questions are spliced into it so that manual edits survive. That
    also means a document from last year — or from before this morning's fix —
    keeps last year's colours for ever, and looks wrong in every program that
    opens it. Only the <style> block is replaced; the questions, and any edit
    made by hand, are untouched.
    """
    if not html or not html.strip():
        return html
    html = drop_echoes(mend_numerals(html))
    if not _STYLE_BLOCK.search(html):
        blocks = re.findall(
            r'<div[^>]*class\s*=\s*"[^"]*page-block[^"]*"[^>]*>.*?</div>\s*(?=<div[^>]*class\s*=\s*"[^"]*page-block|</body>|\Z)',
            html, re.DOTALL | re.IGNORECASE)
        return wrap_document(blocks or [html])
    return _STYLE_BLOCK.sub(lambda m: f"<style>{GOODWILL_CSS}</style>", html, count=1)


def needs_restyle(html):
    """True if this document carries a stylesheet other than today's, or a
    question or page numeral printed at body size."""
    found = _STYLE_BLOCK.search(html or "")
    if not found:
        return bool((html or "").strip())
    return (GOODWILL_CSS.strip() not in found.group(0)
            or drop_echoes(mend_numerals(html)) != html)


def mend_numerals(html):
    """Set the question and page numerals of a stored document at 20pt — RULE 12.

    Only the body is read, never the stylesheet, and nothing else is changed.
    """
    if not html:
        return html
    body = re.search(r"<body[^>]*>", html, re.I)
    start = body.end() if body else 0
    return html[:start] + _number_sizes(html[start:], collections.Counter())


def append_block(existing_html, new_block):
    """Append a new .page-block to an existing document — RULE 9, one artifact per chapter.

    The stylesheet is brought up to date at the same time: a question added to
    an old document must not inherit an old page colour.
    """
    if not existing_html or "</body>" not in existing_html:
        return wrap_document(new_block)
    return restyle(existing_html).replace(
        "</body>", f"\n{new_block.strip()}\n</body>", 1
    )



# ═══════════════════════════════════════════════════════════════
#  VALIDATOR — enforces the pre-delivery checklist
# ═══════════════════════════════════════════════════════════════

# Anything inside these is exempt from the "slash fraction" check.
_SLASH_SAFE = re.compile(
    r"""(?xi)
      \bA/c\b            # account abbreviation
    | \bP/L\b
    | \bw\.?e\.?f\.?\b
    | \d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4}   # dates 1/4/2024
    | https?://\S+
    """
)

_BANNED_BREAKS = [
    ("break-after: page", r"break-after\s*:\s*page"),
    ("page-break-after: always", r"page-break-after\s*:\s*always"),
    ("break-before: page", r"break-before\s*:\s*page"),
    ("page-break-before: always", r"page-break-before\s*:\s*always"),
]

_ZERO = {"0", "0px", "0pt", "0cm", "0mm", "0in", "0 0 0 0"}


def _strip_comments(text):
    """Remove CSS and HTML comments so that commentary never trips the checks."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    return text


def _rules(css):
    """Yield (selector_list, declaration_block) for every rule in the stylesheet."""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [s.strip() for s in m.group(1).split(",") if s.strip()]
        yield selectors, m.group(2)


def _blocks_for(css, selector):
    """Every declaration block whose selector list names exactly `selector`.

    Exact match only: 'body' does not match 'table.wn td', and
    'tr' does not match 'table.wn tr'.
    """
    return [block for selectors, block in _rules(css) if selector in selectors]


def _declaration(blocks, prop):
    """Value of `prop` across the given blocks. The last one wins, as the cascade does."""
    if isinstance(blocks, str) or blocks is None:
        blocks = [blocks] if blocks else []
    value = None
    for block in blocks:
        m = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", block)
        if m:
            value = m.group(1).strip()
    return value


# ═══════════════════════════════════════════════════════════════
#  CLEANING WHAT THE MODEL SENT
# ═══════════════════════════════════════════════════════════════

_BLOCK_START = re.compile(r'<div[^>]*class\s*=\s*"[^"]*page-block', re.I)

# Markup a real solution carries. Prose about the rules carries none of it.
_DOCUMENT_MARKS = ('class="q"', 'class="qno"', 'class="wn', 'class="tbl-title"',
                   'class="formula-box"', 'class="final-ans"', 'class="sol-label"',
                   'class="part-heading"', 'class="top-bar"', '<table', 'class="adj"',
                   'class="notes"', 'class="rule-note"', 'class="ans"')


def _quoted(text, at):
    """True if this position sits inside a `code span`.

    A model that recites the contract writes: the HTML must start with
    `<div class="page-block">` and end with `</div>`. That tag is an example,
    not the document, and taking it left "` and end with `" as the whole page.
    """
    return text.count("`", 0, at) % 2 == 1


def looks_like_document(body):
    """True if this is a solution rather than the model talking about one."""
    if any(mark in (body or "").lower() for mark in _DOCUMENT_MARKS):
        return True
    return len(re.sub(r"\s+", " ", _TAG.sub("", body or "")).strip()) >= 200


def is_looping(text, repeats=4, prefix=34, cap=9000):
    """True when the model is repeating itself instead of writing the document.

    Gemma does this with the contract's own rules — fifteen lines of
    *Wait, the prompt says "No LaTeX: no \\times".* I'll use "multiplied by".
    each a little different, so counting identical lines misses it; the opening
    of each line is what repeats.

    Only prose is counted, and only before the document has begun: a real
    answer is full of rows that open alike, and repetition inside a document is
    the model's business, not ours.
    """
    body = text or ""
    if _BLOCK_START.search(body):
        return False
    if len(body) > cap:
        return True

    heads = collections.Counter()
    for line in body.splitlines():
        line = re.sub(r"\s+", " ", line).strip().lower()
        if len(line) < 20 or "<" in line:
            continue
        heads[line[:prefix]] += 1
    return any(n >= repeats for n in heads.values())


def extract_document(text):
    """Return (body, dropped) — the document, and what was thrown away.

    A weak model narrates before it writes: "* Topic: Discounting * `page-block`
    * `top-bar` (Title: DISCOUNTING) ...". That planning went straight into the
    PDF and filled a whole page. Everything before the first .page-block, and
    anything trailing the last closing tag, is not the document.
    """
    body = (text or "").strip()
    start = None
    for match in _BLOCK_START.finditer(body):
        if not _quoted(body, match.start()):
            start = match
            break
    if not start:
        return body, ""

    dropped = body[:start.start()].strip()
    body = body[start.start():]

    end = body.rfind("</div>")
    if end != -1:
        tail = body[end + 6:].strip()
        if tail:
            dropped = (dropped + "\n" + tail).strip()
        body = body[:end + 6]
    return body.strip(), dropped


_FRAC = ('<span class="frac"><span class="num">{n}</span>'
         '<span class="den">{d}</span></span>')

# A number as it is written on these pages: 1,23,456.75 or 0.7513 or 10%.
_NUM = r"(?:Rs\.?\s*)?\d[\d,]*(?:\.\d+)?%?"
# A name, a bracketed expression, or both together. "Future Value (F)" must be
# taken whole: splitting it leaves the words stranded beside the fraction with
# only "(F)" over the line.
# A single letter counts too: formulas are written "F / (1 + r)^n" and "P = ...".
# Only the spaced form admits letters, so "Bank A/c", "P/L" and "w/o" are safe.
# A name in a formula is written in capitals: "Future Value", "Net Profit",
# "Cost of Goods Sold", "EBIT". A sentence is not: "press the division key ÷
# twice" was stacked into a fraction until words had to be capitalised. Small
# joining words are allowed inside a name, never at either end; a single
# letter (F, P, r, n) is always a term.
_JOIN = r"(?:of|and|on|in|to|per|for)"
_NAME = r"[A-Z][A-Za-z]*"
_WORDS = rf"(?:{_NAME}(?: {_JOIN})?(?: {_NAME}){{0,4}}|[A-Za-z])"
_BRACKET = r"\([^()<>]{1,40}\)"
_TERM = rf"(?:{_WORDS}\s*{_BRACKET}|{_BRACKET}|{_WORDS})"

# An operand may carry its own power: (1 + 0.10)^3 belongs under the line, not
# beside it. The exponent is converted inside the fraction, never left outside.
# Written either way: a caret the model typed, "^3", or the superscript
# character itself, "³" — which is how Flash-Lite writes it.
_SUPERSCRIPTS = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207f"
_EXP = rf"(?:\^\{{?[A-Za-z0-9]{{1,4}}\}}?|[{_SUPERSCRIPTS}]{{1,3}})?"

# Digits either side, spaces optional: 66,550/1.331. Not a date, not 24/7/365.
_SLASH_NUM = re.compile(rf"(?<![\w/.])({_NUM}{_EXP})\s*/\s*({_NUM}{_EXP})(?![\w/])")
# Words or brackets either side, but only when the slash is spaced, so that
# "and/or", "w/o" and "P/L" are left alone.
_SLASH_TERM = re.compile(
    rf"(?<![\w/])((?:{_TERM}|{_NUM}){_EXP})\s+/\s+((?:{_TERM}|{_NUM}){_EXP})(?![\w/])")
# 10^3, (1 + r)^n, x^{12}
_CARET = re.compile(r"\^\{?([A-Za-z0-9]{1,4})\}?")
# A division sign is never anything but a division, so unlike the slash it
# takes any operand, spaced or not: "F ÷ (1 + r)ⁿ", "1 ÷ (1.10)³", "a÷b".
# "³" printed as a glyph is smaller than the house style's <sup>, and inside a
# fraction it shrinks again; turn it into the same <sup> everything else uses.
_UNICODE_POWER = re.compile(f"[{_SUPERSCRIPTS}]{{1,3}}")
_FROM_SUPERSCRIPT = str.maketrans(_SUPERSCRIPTS, "0123456789n")

# Neither side may start or end inside a word: without these edges the "y" of
# "key" and the "t" of "twice" were taken as single-letter terms.
_DIVIDE = re.compile(
    rf"(?<![\w/])((?:{_TERM}|{_NUM}){_EXP})\s*(?:\u00f7|&divide;)\s*"
    rf"((?:{_TERM}|{_NUM}){_EXP})(?![\w/])")

_TAG = re.compile(r"<[^>]+>")
# Text inside these is markup we must not touch.
_SKIP_INSIDE = re.compile(r"<(script|style|span class=\"frac\")", re.I)


def _on_text(html, fn):
    """Apply fn to the text between tags only, never inside a tag or a .frac."""
    out, pos, spans = [], 0, []      # is_frac for each open <span>
    for tag in _TAG.finditer(html):
        chunk = html[pos:tag.start()]
        hidden = any(spans)
        out.append(chunk if hidden else fn(chunk))
        low = tag.group(0).lower()
        if low.startswith("<span"):
            spans.append('class="frac"' in low)
        elif low.startswith("</span") and spans:
            spans.pop()
        out.append(tag.group(0))
        pos = tag.end()
    rest = html[pos:]
    out.append(rest if any(spans) else fn(rest))
    return "".join(out)


_TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.I | re.S)
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL = re.compile(r"<t[dh]\b", re.I)
_FULL_CLASS = re.compile(r'(class\s*=\s*"[^"]*?)\bfull\b\s*', re.I)


def _fit_tables(html, counts):
    """Keep 'wn full' for two-sided accounts only.

    class="wn full" spans the page so a Dr./Cr. account's halves match. A model
    that puts it on a two-column statement undoes the fitting the teacher asked
    for, so it is taken off anything narrower than four columns.
    """
    def one(m):
        table = m.group(0)
        cut = table.find(">") + 1
        head = table[:cut]
        if not _FULL_CLASS.search(head):
            return table
        widest = max((len(_CELL.findall(row)) for row in _ROW.findall(table)),
                     default=0)
        if widest >= 4:
            return table
        counts["table fitted to its contents"] += 1
        head = _FULL_CLASS.sub(r"\1", head, count=1)
        head = re.sub(r'(class\s*=\s*")\s+', r"\1", head)
        head = re.sub(r'\s+"', '"', head)
        # Slice by the ORIGINAL opening tag, never the shortened one, or the
        # tail of the old tag prints on the page as  ull">.
        return head + table[cut:]

    return _TABLE.sub(one, html)


# A fraction is written inside one line, so the flattener reads through inline
# markup only. An unclassed <span> is a block here — ".q > span" and
# ".formula-box .line" are display:block — so it ends a run like a <div> does.
_TRANSPARENT_TAGS = {"sup", "sub", "b", "i", "em", "strong", "u", "abbr", "font"}
_TRANSPARENT_CLASSES = {"amt", "small", "source", "narration"}
_CLASS_ATTR = re.compile(r'class\s*=\s*"([^"]*)"', re.I)


_TO_SUPERSCRIPT = str.maketrans("0123456789", _SUPERSCRIPTS[:10])


def _flatten(html):
    """The visible text, with a map from each character back into the HTML.

    An amount arrives wrapped — "66,550</span> / <span>1.331" — so a repair that
    reads one text run at a time never sees digits on both sides of the slash.
    Flattening lets the pattern read across inline tags; the map puts the fix
    back in the right place. A block boundary and anything already inside a
    .frac become one sentinel character, so nothing is re-read and no two lines
    are joined into one number.

    Text inside <sup> is read as the superscript it is: "1.10<sup>3</sup>" reads
    "1.10³", a number and its power. Read as plain "1.103" it was taken for a
    single number, and the factor printed as one point one zero three.
    """
    text, index, pos = [], [], 0
    spans = []                       # (transparent, is_frac) for each open <span>
    in_frac = 0                      # open .frac spans: their contents are hidden
    in_sup = 0

    def sentinel(at):
        if text and text[-1] != "\x01":
            text.append("\x01")
            index.append(at)

    def visible(chunk, at):
        for k, ch in enumerate(chunk):
            if in_sup:
                ch = ch.translate(_TO_SUPERSCRIPT)
                if ch.isalpha():
                    ch = "\u207f"          # any letter as a power reads as one
            text.append(ch)
            index.append(at + k)

    for tag in _TAG.finditer(html):
        chunk = html[pos:tag.start()]
        if in_frac:
            if chunk:
                sentinel(pos)
        else:
            visible(chunk, pos)

        raw = tag.group(0)
        low = raw.lower()
        name = re.match(r"</?([a-z0-9]+)", low)
        name = name.group(1) if name else ""
        closing = low.startswith("</")

        if name == "sup":
            in_sup = max(0, in_sup + (-1 if closing else 1))
        if name in _TRANSPARENT_TAGS:
            transparent = True
        elif name == "span":
            if closing:
                transparent, was_frac = spans.pop() if spans else (False, False)
                if was_frac:
                    in_frac = max(0, in_frac - 1)
            else:
                classes = _CLASS_ATTR.search(raw)
                names = set((classes.group(1) if classes else "").split())
                transparent = bool(names & _TRANSPARENT_CLASSES)
                is_frac = "frac" in names
                spans.append((transparent, is_frac))
                if is_frac:
                    in_frac += 1
        else:
            transparent = False
        if not transparent:
            sentinel(tag.start())
        pos = tag.end()

    if not in_frac:
        visible(html[pos:], pos)
    return "".join(text), index


def _balanced(fragment):
    """True if every tag opened in this fragment is closed inside it."""
    stack = []
    for closing, name in re.findall(r"<(/?)([A-Za-z]+)[^>]*>", fragment):
        if closing:
            if not stack or stack.pop() != name.lower():
                return False
        elif name.lower() not in ("br", "img", "col"):
            stack.append(name.lower())
    return not stack


_TAG_PARTS = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)[^>]*>")


def _mend(removed):
    """Tags to put back after a replacement, so the page stays well formed.

    A division often starts inside one amount and ends inside the next, so the
    replaced stretch swallows the first amount's </span> and opens the second's.
    What it consumed is reinstated after the fraction: the closers first, then
    the openers whose closing tags are still to come.
    """
    stack, orphan_closers, opened = [], [], []
    for m in _TAG_PARTS.finditer(removed):
        closing, name = m.group(1), m.group(2).lower()
        if name in ("br", "img", "col", "hr"):
            continue
        if closing:
            if stack and stack[-1][0] == name:
                stack.pop()
            else:
                orphan_closers.append(name)
        else:
            stack.append((name, m.group(0)))
    opened = [raw for _, raw in stack]
    return "".join(f"</{n}>" for n in orphan_closers) + "".join(opened)


def _apply_fractions(html, pattern, counts, powers):
    """Turn each division the pattern finds into a stacked fraction.

    The two sides keep their own markup — an amount stays red — unless taking
    the HTML would leave a tag unclosed, in which case the plain text is used.
    """
    while True:
        text, index = _flatten(html)
        m = pattern.search(text)
        if not m:
            return html

        def bounds(group):
            """The HTML for one side, closing any tag it ends inside —
            "1.10<sup>3" takes its "</sup>" rather than losing the power."""
            a, b = index[m.start(group)], index[m.end(group) - 1] + 1
            while not _balanced(html[a:b]) and html.startswith("</", b):
                b = html.index(">", b) + 1
            return a, b

        def piece(a, b):
            raw = html[a:b]
            if not _balanced(raw):
                raw = _TAG.sub("", raw)
            return _on_text(raw, powers).strip()

        num_a, num_b = bounds(1)
        den_a, den_b = bounds(2)
        counts["fraction"] += 1
        start, stop = index[m.start()], max(index[m.end() - 1] + 1, den_b)
        html = (html[:start]
                + _FRAC.format(n=piece(num_a, num_b), d=piece(den_a, den_b))
                + _mend(html[start:stop])
                + html[stop:])


# A power written without a caret: "(1 + 0.10)3", "(1 + r)n". Nothing marks it
# as an exponent, and printed flat it reads as a multiplication. Only a bracket
# closing immediately before it counts, so "(a) 3 years" and "(2024)" are safe.
_IMPLIED_POWER = re.compile(r"(?<=\))(\d{1,3}|[A-Za-z])(?![\w.,%)])")


def _apply_powers(html, counts):
    """Raise an exponent the model left sitting on the line."""
    done = 0
    while True:
        text, index = _flatten(html)
        found = None
        for match in _IMPLIED_POWER.finditer(text):
            if "<sup>" not in html[max(0, index[match.start()] - 12):index[match.start()]]:
                found = match
                break
        if not found or done > 40:
            return html
        done += 1
        counts["exponent"] += 1
        start = index[found.start()]
        stop = index[found.end() - 1] + 1
        raw = html[start:stop]
        if not _balanced(raw):
            raw = _TAG.sub("", raw)
        html = html[:start] + f"<sup>{raw}</sup>" + _mend(html[start:stop]) + html[stop:]


_POWER_BIT = rf"(?:<sup>[^<]{{1,6}}</sup>|[{_SUPERSCRIPTS}]{{1,3}})"
_TRAILING_POWER = re.compile(rf"^\s*({_POWER_BIT})\s*$")
_POWER_AFTER = re.compile(rf"^(\s*)({_POWER_BIT})")


def _span_end(html, start):
    """Index just past the </span> closing the <span> that opens at start."""
    depth = 0
    for tag in re.finditer(r"<(/?)span\b[^>]*>", html[start:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return start + tag.end()
    return -1


def _as_sup(power):
    """"ⁿ" or "<sup>n</sup>" -> "<sup>n</sup>"."""
    if power.startswith("<sup>"):
        return power
    return "<sup>" + power.translate(_FROM_SUPERSCRIPT) + "</sup>"


def _fix_fraction_powers(html, counts):
    """Put a power the model left beside a fraction into its denominator.

    Flash-Lite writes 1/(1 + r)ⁿ with the ⁿ inside the fraction but after the
    denominator — a stacked fraction is a column, so it printed as a third row
    under the line — or with the ³ after the fraction, beside it. A power after
    the denominator is the denominator's. One after the whole fraction is moved
    in only when the numerator is 1, where (1 ÷ x)³ and 1 ÷ x³ are the same
    number; any other fraction is left as written.
    """
    open_tag = '<span class="frac">'
    out, pos = [], 0
    while True:
        start = html.find(open_tag, pos)
        if start == -1:
            out.append(html[pos:])
            return "".join(out)
        end = _span_end(html, start)
        if end == -1:
            out.append(html[pos:])
            return "".join(out)
        inner = _fix_fraction_powers(html[start + len(open_tag):end - 7], counts)
        num_end = _span_end(inner, 0) if inner.startswith('<span class="num">') else -1
        den_start = inner.find('<span class="den">', max(num_end, 0))
        den_end = _span_end(inner, den_start) if num_end != -1 and den_start != -1 else -1
        rest = html[end:]
        if den_end != -1:
            numerator = _TAG.sub("", inner[:num_end]).strip()
            trailing = _TRAILING_POWER.match(inner[den_end:])
            after = _POWER_AFTER.match(rest)
            power = None
            if trailing:
                power = trailing.group(1)
            elif after and numerator == "1":
                power = after.group(2)
                rest = rest[after.end():]
            if power:
                counts["power moved into its denominator"] += 1
                inner = (inner[:den_end - 7] + _as_sup(power) + "</span>")
        out.append(html[pos:start] + open_tag + inner + "</span>")
        html, pos = rest, 0


# What may stand right before a fraction it multiplies, with the "×" missing.
_QUANTITY_BEFORE = re.compile(r"(?:Rs\.?\s*)?\d[\d,]*(?:\.\d+)?\s+$")
_NAME_BEFORE = re.compile(
    r"=[^=]*?\b[A-Z][A-Za-z]*(?: [A-Z][A-Za-z]*){0,4}(?:\s*\([A-Za-z]\))?\s+$")
_ALREADY_TIMES = re.compile(r"(?:\u00d7|&times;|\*|\bx)\s*$")


def _restore_times(html, counts):
    """Put back the "×" between a quantity and the fraction it multiplies.

    "66,550 1/1.331" reads to a student as a mixed number — sixty-six thousand
    and a fraction — the way "2 ½" means two and a half. It is added only where
    that reading is impossible: after a figure when the denominator has a
    decimal point, a bracket or a power (a mixed number's never does), or after
    a capitalised name that follows "=", as in Present Value = Future Value × ….
    "7 ½%" and "2 ½ years" are left exactly as written.
    """
    open_tag = '<span class="frac">'
    pos, out = 0, []
    while True:
        start = html.find(open_tag, pos)
        if start == -1:
            out.append(html[pos:])
            return "".join(out)
        end = _span_end(html, start)
        if end == -1:
            out.append(html[pos:])
            return "".join(out)
        text, _ = _flatten(html[:start])
        line = text.rsplit("\x01", 1)[-1]
        frac = html[start:end]
        den = frac.split('<span class="den">', 1)[-1]
        den_text = _TAG.sub("", den)
        not_mixed = bool(re.search(r"[.(A-Za-z]", den_text)) or "<sup>" in den
        wanted = not _ALREADY_TIMES.search(line) and (
            (_QUANTITY_BEFORE.search(line) and not_mixed)
            or _NAME_BEFORE.search(line))
        out.append(html[pos:start])
        if wanted:
            counts["multiplication sign restored"] += 1
            out.append("\u00d7 ")
        out.append(frac)
        pos = end


def _map_fraction_parts(html, fn):
    """Apply fn to the inside of the top and bottom of every fraction.

    A fraction the model built itself is hidden from the repair, so that one it
    has just made is not made again. What is written inside one still needs
    the same care — "1 over (1 + 10/100)³" has a division in its denominator —
    so each side is repaired on its own, as a line of its own.
    """
    open_tag = '<span class="frac">'
    out, pos = [], 0
    while True:
        start = html.find(open_tag, pos)
        if start == -1:
            out.append(html[pos:])
            return "".join(out)
        end = _span_end(html, start)
        if end == -1:
            out.append(html[pos:])
            return "".join(out)
        frac, cursor = html[start:end], 0
        for side in ("num", "den"):
            tag = f'<span class="{side}">'
            at = frac.find(tag, cursor)
            close = _span_end(frac, at) if at != -1 else -1
            if close == -1:
                continue
            inner = frac[at + len(tag):close - 7]
            fixed = fn(inner)
            frac = frac[:at + len(tag)] + fixed + frac[close - 7:]
            cursor = at + len(tag) + len(fixed) + 7
        out.append(html[pos:start] + frac)
        pos = end


# A power the model set in the note class instead of <sup>: a single figure or
# letter in .small, straight after a number or a closing bracket.
_SMALL_POWER = re.compile(
    r'<span class="small">\s*(\d{1,3}|[A-Za-z])\s*</span>', re.IGNORECASE)


def _small_powers(html, counts):
    """Turn a power written as <span class="small"> into the <sup> it means.

    Flash-Lite wrote 1/1.10³ as 1.10<span class="small">3</span>. .small is the
    house class for pink bracketed notes, so the 3 printed flat on the line and
    the factor read as 1.103 — a different number. A note in .small is words in
    brackets; a lone figure or letter touching a number or a bracket is a power.
    """
    def one(m):
        before = _TAG.sub("", html[max(0, m.start() - 80):m.start()])
        if before and (before[-1].isdigit() or before[-1] == ")"):
            counts["power written as a note"] += 1
            return f"<sup>{m.group(1)}</sup>"
        return m.group(0)

    return _SMALL_POWER.sub(one, html)


_NUMERAL = re.compile(r"(?<![\w.])(\d+(?:\.\d+)*[A-Za-z]?)(?![\w])")
_BIG = '<span class="num">{}</span>'
_QNO_SPAN = re.compile(r'(<(span|div|p|b|strong)\b[^>]*\bclass\s*=\s*["\'][^"\']*\bqno\b'
                       r'[^"\']*["\'][^>]*>)(.*?)(</\2>)', re.I | re.S)
_PGREF_SPAN = re.compile(r'(<span class="pgref"[^>]*>)(.*?)(</span>)', re.I | re.S)
_PG_MARK = re.compile(r"(\b(?:Pg|Page|P)\.?\s*)(\d+(?:\.\d+)*[A-Za-z]?)", re.I)
_SPACE = r"(?:\s|&nbsp;|&#160;)*"
_Q_WORD = rf"(?:Illustration|Question|Problem|Exercise|Example|Q\.){_SPACE}(?:No\.?{_SPACE})?"
_Q_BOLD = re.compile(rf'(<div class="q"[^>]*>\s*(?:<span>\s*)?)<(b|strong)>\s*'
                     rf'({_Q_WORD})(\d+[A-Za-z]?)\s*([.:]?)\s*</\2>', re.I)
# "Illustration 6." as the first words of any element: a div, a paragraph, a
# bold run, a span — wherever the model chose to put it.
_Q_PLAIN = re.compile(rf'(>\s*)({_Q_WORD})(\d+[A-Za-z]?)(?![\w.]\d)((?:\s*[.:])?)', re.I)
# The last resort: a tag or a non-breaking space between the word and the
# number — "<b>Illustration</b> 6", "Illustration&nbsp;6". Only the numeral is
# wrapped, so no tag is ever left unbalanced.
_GAP = r"(?:\s|&nbsp;|&#160;|<[^<>]*>)*"
_Q_LOOSE = re.compile(rf"\b(?:Illustration|Question|Problem|Exercise|Example)\b{_GAP}"
                      rf"(?:No\.{_GAP})?(\d+[A-Za-z]?)(?![\w]|\.\d)", re.I)
_WORD_OUTSIDE = re.compile(rf'({_Q_WORD})<span class="qno">(<span class="num">[^<]*</span>)'
                           rf'</span>([.:]?)', re.I)
# Gemini writes the numeral's own span but leaves out the qno round the label —
# "Illustration <span class="num">6</span>." — and the 20pt rule is ".qno .num".
_NUM_NO_QNO = re.compile(rf'({_Q_WORD})(<span class="num">[^<]*</span>)((?:\s*[.:])?)', re.I)
# What version 036b3c5 made of that: a second numeral span inside the first.
_NESTED_NUM = re.compile(r'<span class="num"><span class="qno">(<span class="num">[^<]*</span>)'
                         r'</span></span>', re.I)
_OPEN_TAG = re.compile(r'<([A-Za-z][\w-]*)\b([^<>]*)>\s*$')
_SOLUTION = re.compile(r'class\s*=\s*["\'][^"\']*\b(?:sol-label|wn-label|wn-sub|tbl-title|'
                       r'formula-box|part-heading|final-ans)\b', re.I)


def _number_sizes(html, counts):
    """Put the problem and page numerals in their 20pt span — RULE 12.

    A model often writes "Illustration 6." or "Pg. 43" as plain text, and the
    numeral then prints at body size. Only the numeral is wrapped; the words
    around it keep their size.
    """
    def qno_span(m):
        if 'class="num"' in m.group(3):
            return m.group(0)
        inner, n = _NUMERAL.subn(lambda d: _BIG.format(d.group(1)), m.group(3), count=1)
        counts["numeral set at 20pt"] += n
        return m.group(1) + inner + m.group(4)

    def pgref_span(m):
        inner = m.group(2)
        if 'class="num"' in inner:
            return m.group(0)
        marked = _PG_MARK.search(inner)
        if marked:
            inner = (inner[:marked.start(2)] + _BIG.format(marked.group(2))
                     + inner[marked.end(2):])
        else:
            last = list(_NUMERAL.finditer(inner))
            if not last:
                return m.group(0)
            d = last[-1]
            inner = inner[:d.start()] + _BIG.format(d.group(1)) + inner[d.end():]
        counts["numeral set at 20pt"] += 1
        return m.group(1) + inner + m.group(3)

    def plain(m, bold=False):
        counts["numeral set at 20pt"] += 1
        word, number, stop = (m.group(3), m.group(4), m.group(5)) if bold else \
                             (m.group(2), m.group(3), m.group(4))
        return m.group(1) + f'<span class="qno">{word}{_BIG.format(number)}{stop.strip()}</span>'

    def question(block):
        """The first "Illustration 6." in the question, before the solution."""
        if re.search(r'\bqno\b', block):
            return block
        end = _SOLUTION.search(block)
        end = end.start() if end else len(block)
        m = _NUM_NO_QNO.search(block, 0, end)
        if m:
            counts["numeral set at 20pt"] += 1
            return (block[:m.start()] + f'<span class="qno">{m.group(1)}{m.group(2)}'
                    f'{m.group(3).strip()}</span>' + block[m.end():])
        block = _Q_BOLD.sub(lambda m: plain(m, bold=True), block, count=1)
        if 'class="qno"' in block:
            return block
        end = _SOLUTION.search(block)
        end = end.start() if end else len(block)
        for m in _Q_PLAIN.finditer(block, 0, end):
            opener = _OPEN_TAG.search(block, 0, m.start() + 1)
            if opener and re.search(r'\b(?:title|pgref)\b', opener.group(2)):
                continue                       # the top bar, not the question
            return block[:m.start()] + plain(m) + block[m.end():]
        for m in _Q_LOOSE.finditer(block, 0, end):
            opener = _OPEN_TAG.search(block, 0, m.start())
            if opener and re.search(r'\b(?:title|pgref)\b', opener.group(2)):
                continue
            counts["numeral set at 20pt"] += 1
            return (block[:m.start(1)] + f'<span class="qno">{_BIG.format(m.group(1))}</span>'
                    + block[m.end(1):])
        return block

    # An earlier version wrapped the numeral alone, leaving "Illustration"
    # outside and not bold. Bring the word in beside its number.
    html = _NESTED_NUM.sub(r"\1", html)
    html = _WORD_OUTSIDE.sub(r'<span class="qno">\1\2\3</span>', html)
    html = _QNO_SPAN.sub(qno_span, html)
    html = _PGREF_SPAN.sub(pgref_span, html)
    # One block can hold two questions — "add one more question" often comes
    # back as a single page-block — so each question is looked at on its own.
    parts = re.split(r'(?=<div class="page-block")|(?=<div class="q"[\s>])', html)
    return "".join(question(part) for part in parts)


def repair_markup(html):
    """Fix what a weak model gets wrong, without touching its figures.

    Returns (html, notes). Slashes and division signs become stacked fractions
    and carets become superscripts — RULE: every division is a stacked .frac,
    and the arithmetic is never altered, only how it is written.
    """
    counts = collections.Counter({"fraction": 0, "exponent": 0})

    def sup(m):
        counts["exponent"] += 1
        return f"<sup>{m.group(1)}</sup>"

    def powers(text):
        text = _CARET.sub(sup, text)
        return _UNICODE_POWER.sub(unicode_sup, text)

    def unicode_sup(m):
        counts["exponent"] += 1
        return "<sup>" + m.group(0).translate(_FROM_SUPERSCRIPT) + "</sup>"

    def run(part):
        part = _map_fraction_parts(part, run)      # inside existing fractions first
        for pattern in (_DIVIDE, _SLASH_NUM, _SLASH_TERM):
            part = _apply_fractions(part, pattern, counts, powers)
        return _on_text(part, powers)

    html = _small_powers(html, counts)
    fixed = _fit_tables(_restore_times(_fix_fraction_powers(
        _apply_powers(run(html), counts), counts), counts), counts)
    fixed = _number_sizes(fixed, counts)
    def label(name, n):
        if n == 1:
            return f"1 {name}"
        first, _, rest = name.partition(" ")
        return f"{n} {first}s{' ' + rest if rest else ''}".replace("its", "their")

    notes = [label(name, n) for name, n in counts.items() if n]
    return fixed, notes


_BLOCK_OPEN = re.compile(r'<div class="page-block"[^>]*>', re.I)
_Q_START = re.compile(r'<div class="q"[\s>]', re.I)
_TOPBAR_START = re.compile(r'<div class="top-bar"[^>]*>', re.I)
_LABEL = re.compile(rf'(Illustration|Question|Problem|Exercise|Example){_SPACE}'
                    r'(?:<span class="num">)?(\d+[A-Za-z]?)', re.I)


def _div_end(html, start):
    """Index just past the </div> closing the <div> that opens at start."""
    depth = 0
    for tag in re.finditer(r"<(/?)div\b[^>]*>", html[start:], re.I):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return start + tag.end()
    return -1


def question_parts(html):
    """(start, end) of each question: its top bar, question and solution.

    Found inside each page-block, so a part never crosses a block's own tags.
    """
    return [part for block in _parts_by_block(html) for part in block]


def _parts_by_block(html):
    """question_parts, grouped by the page-block each question sits in."""
    blocks, after = [], 0
    for m in _BLOCK_OPEN.finditer(html):
        if m.start() < after:
            continue                              # a block inside a block
        end = _div_end(html, m.start())
        if end < 0:
            continue
        blocks.append((m.end(), html.rfind("</div>", 0, end)))
        after = end
    if not blocks:
        blocks = [(0, len(html))]
    parts = []
    for a, b in blocks:
        cuts = [a]
        for q in _Q_START.finditer(html, a, b):
            if q.start() == a or not html[a:q.start()].strip():
                continue                          # the block's first question
            cut = q.start()
            bars = [t for t in _TOPBAR_START.finditer(html, a, cut)]
            if bars:                              # its own top bar goes with it
                bar_end = _div_end(html, bars[-1].start())
                if 0 < bar_end <= cut and not html[bar_end:cut].strip():
                    cut = bars[-1].start()
            if cut > cuts[-1]:
                cuts.append(cut)
        cuts.append(b)
        parts.append([(x, y) for x, y in zip(cuts, cuts[1:]) if html[x:y].strip()])
    return parts


def _words(fragment):
    text = re.sub(r"&[A-Za-z0-9#]+;", " ", _TAG.sub(" ", fragment))
    return re.sub(r"\s+", " ", text).strip().lower()


_FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _work(fragment):
    """(words, the question's own figures) — what two questions are compared by.

    Words alone are not enough: "one more question in the same phrasing with
    other amounts" reads almost word for word like the first. The question
    number and its amounts tell them apart.
    """
    q = _Q_START.search(fragment)
    end = _div_end(fragment, q.start()) if q else -1
    figures = _FIGURE.findall(_words(fragment[q.start():end])) if q and end > 0 else None
    return _words(fragment), figures


def _same_work(new, old):
    """True if two questions, solution and all, are the same work."""
    (a, a_figures), (b, b_figures) = new, old
    if a_figures is None or a_figures != b_figures:
        return False
    if not a or not b or not 0.8 <= len(a) / len(b) <= 1.25:
        return False
    match = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return match.quick_ratio() >= 0.9 and match.ratio() >= 0.9


def drop_repeats(existing_html, body):
    """Leave out a question this document already holds.

    Asked for "one more question" with "the full merged HTML", a model sends
    the earlier question back along with the new one, and appended as it is,
    the document prints the earlier question twice. A part is left out only
    when it matches a question already in the document almost word for word,
    and only when something new remains — a question re-solved by another
    method reads differently and is kept.

    Returns (body, labels of what was left out).
    """
    if not (existing_html or "").strip() or not body:
        return body, []
    old = [_work(existing_html[a:b]) for a, b in question_parts(existing_html)]
    old = [w for w in old if len(w[0]) > 20 and w[1]]
    parts = question_parts(body)
    if len(parts) < 2 or not old:
        return body, []
    repeats = [(a, b) for a, b in parts
               if _balanced(body[a:b])
               and any(_same_work(_work(body[a:b]), o) for o in old)]
    if not repeats or len(repeats) == len(parts):
        return body, []
    labels = []
    for a, b in reversed(repeats):
        found = _LABEL.search(body, a, b)
        labels.insert(0, f"{found.group(1).title()} {found.group(2)}" if found
                      else "an earlier question")
        body = body[:a] + body[b:]
    body = re.sub(r'<div class="page-block"[^>]*>\s*</div>\s*', "", body)
    return body, labels


_PGREF_OPEN = re.compile(r'<span\b[^>]*class\s*=\s*"[^"]*\bpgref\b[^"]*"[^>]*>', re.I)
_TOPBAR_OPEN = re.compile(r'<div\b[^>]*class\s*=\s*"[^"]*\btop-bar\b[^"]*"[^>]*>', re.I)
_TEACHER_PAGE = re.compile(r"\b(?:pg|page|p)\b\.?\s*(?:no\.?\s*)?(\d+(?:\.\d+)*[A-Za-z]?)\b", re.I)


def _span_close(html, start):
    """Index just past the </span> closing the <span> that opens at start."""
    depth = 0
    for tag in re.finditer(r"<(/?)span\b[^>]*>", html[start:], re.I):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return start + tag.end()
    return -1


def _letters(text):
    return re.sub(r"[^a-z0-9]", "", html_lib.unescape(_TAG.sub("", text or "")).lower())


def _pgref_at(block):
    """(start, end) of the top bar's pgref span, or None."""
    found = _PGREF_OPEN.search(block or "")
    end = _span_close(block, found.start()) if found else -1
    return (found.start(), end) if found and end > 0 else None


def read_pgref(block):
    """(book, page) as the top bar prints them — "" for either that is absent."""
    at = _pgref_at(block)
    if not at:
        return "", ""
    inner = block[at[0]:at[1]]
    inner = inner[inner.index(">") + 1:-len("</span>")]
    text = re.sub(r"\s+", " ", html_lib.unescape(_TAG.sub("", inner))).strip()
    page = _PG_MARK.search(text)
    book = text.split("|", 1)[0].strip(" .|—-") if "|" in text else ""
    return book, (page.group(2) if page else "")


def set_pgref(block, book, page):
    """Write the top bar's book and page. With no page, the pgref goes."""
    at = _pgref_at(block)
    if not page:
        return block[:at[0]] + block[at[1]:] if at else block
    new = ('<span class="pgref">' + (f"{html_lib.escape(book)} | " if book else "")
           + f'Pg. <span class="num">{html_lib.escape(page)}</span></span>')
    if at:
        return block[:at[0]] + new + block[at[1]:]
    bar = _TOPBAR_OPEN.search(block or "")
    if bar:
        close = _div_end(block, bar.start())
        if close > 0:
            inside = block.rfind("</div>", 0, close)
            return block[:inside] + new + block[inside:]
    return block


def teacher_pgref(block, instruction):
    """The top bar's book and page, as the teacher gave them — or nothing.

    The book name and page print only when the teacher typed them. Gemini
    guessed "T.S. Grewal" once and "P.K. Lazar" the next time for the same
    page, so what it writes there is checked against his words, not trusted:
      - no page in his message   -> no pgref at all
      - a page                   -> "Pg. <his page>"
      - and a book he named      -> "<book> | Pg. <his page>"
    """
    page = _TEACHER_PAGE.search(instruction or "")
    book, _ = read_pgref(block)
    if not (book and _letters(book) and _letters(book) in _letters(instruction)):
        book = ""
    return set_pgref(block, book, page.group(1) if page else "")


_Q_OPEN = re.compile(r'<div\b[^>]*class\s*=\s*"q"[^>]*>', re.I)


_QNO_OPEN = re.compile(r'<span\b[^>]*class\s*=\s*"qno"[^>]*>', re.I)


def set_qno(block, word, number):
    """Put "Illustration 6." at the head of the question, or replace its number.

    Returns the block unchanged if it has no question.
    """
    qno = f'<span class="qno">{html_lib.escape(word)} <span class="num">{html_lib.escape(number)}</span>.</span>'
    old = _QNO_OPEN.search(block or "")
    if old:
        end = _span_close(block, old.start())
        if end > 0:
            return block[:old.start()] + qno + block[end:]
    q = _Q_OPEN.search(block or "")
    if not q:
        return block
    return block[:q.end()] + qno + block[q.end():]


def figures(html):
    """Every figure on the page, in order — what an edit is checked against."""
    body = re.search(r"<body[^>]*>", html or "", re.I)
    return _FIGURE.findall(_words((html or "")[body.end() if body else 0:]))


def teacher_pgrefs(body, instruction):
    """teacher_pgref for every block in an answer."""
    spans = block_spans(body) or [(0, len(body or ""))]
    for a, b in reversed(spans):
        body = body[:a] + teacher_pgref(body[a:b], instruction) + body[b:]
    return body


def block_spans(html):
    """(start, end) of each top-level .page-block, in document order."""
    spans, after = [], 0
    for m in _BLOCK_START.finditer(html or ""):
        if m.start() < after:
            continue                              # a block inside a block
        end = _div_end(html, m.start())
        if end < 0:
            continue
        spans.append((m.start(), end))
        after = end
    return spans


def blocks_of(html):
    """The .page-block fragments of a document, in order."""
    return [html[a:b] for a, b in block_spans(html)]


def question_label(fragment):
    """"Illustration 7" — what the chat calls a block. "" when it has no number."""
    found = _LABEL.search(fragment or "")
    return f"{found.group(1).title()} {found.group(2)}" if found else ""


def numbered_body(html):
    """The document's blocks, each after a <!-- block N --> comment.

    This is what the model is shown when asked to change the page in place, so
    it can say which block it changed without sending the rest back.
    """
    return "\n\n".join(f"<!-- block {i} -->\n{b}" for i, b in enumerate(blocks_of(html), 1))


_EDIT_MARK = re.compile(r"<!--\s*(remove\s+)?block\s+(\d+)\s*-->", re.I)


class EditError(ValueError):
    """An edit answer that cannot be applied; the message is fit for the chat."""


def apply_edits(html, answer):
    """Apply a changed-blocks answer to the document, in place.

    The answer holds "<!-- block N -->" followed by the whole new block N, or
    "<!-- remove block N -->". Blocks it does not mention are left exactly as
    they are, hand edits included.

    Returns (html, changed numbers, removed numbers). Raises EditError.
    """
    spans = block_spans(html)
    if not spans:
        raise EditError("There is no page to edit yet.")
    marks = list(_EDIT_MARK.finditer(answer or ""))
    changes, removed = {}, set()
    if marks:
        for i, mark in enumerate(marks):
            n = int(mark.group(2))
            if not 1 <= n <= len(spans):
                raise EditError(f"Gemini named block {n}, but the page has "
                                f"{len(spans)}. Nothing was changed.")
            if mark.group(1):
                removed.add(n)
                continue
            stop = marks[i + 1].start() if i + 1 < len(marks) else len(answer)
            segment = answer[mark.end():stop]
            found = block_spans(segment)
            new = segment[found[0][0]:found[0][1]] if found else segment.strip()
            if not looks_like_document(new):
                raise EditError(f"Gemini's new block {n} is not a page. Nothing was changed.")
            if not found:
                new = f'<div class="page-block">\n{new}\n</div>'
            changes[n] = new
    else:
        found = block_spans(answer or "")
        if not found or len(found) != len(spans):
            raise EditError("Gemini did not say which question it changed, so nothing "
                            "was edited. Press Retry, or name the question.")
        for n, (a, b) in enumerate(found, 1):
            if answer[a:b].strip() != html[spans[n - 1][0]:spans[n - 1][1]].strip():
                changes[n] = answer[a:b]
    if len(removed) == len(spans) and not changes:
        raise EditError("That would remove every question. Nothing was changed.")
    # The block's own opening tag is kept. Gemini is asked to change what is
    # inside a question, and once gave the wrapper a style="border:..." that
    # boxed the whole page in the PDF.
    for n in list(changes):
        a, _ = spans[n - 1]
        old_open = html[a:html.index(">", a) + 1]
        new = changes[n].strip()
        changes[n] = old_open + new[new.index(">") + 1:]
    for n in sorted(set(changes) | removed, reverse=True):
        a, b = spans[n - 1]
        if n in removed:
            while b < len(html) and html[b] in " \t\r\n":
                b += 1
            html = html[:a] + html[b:]
        else:
            html = html[:a] + changes[n].strip() + html[b:]
    return html, sorted(set(changes) - removed), sorted(removed)


def drop_echoes(html):
    """Take out an earlier question that came back in one block with a new one.

    What drop_repeats now stops at the door, in documents saved before it: the
    block holding the new question also holds a copy of an earlier one. Only
    that copy goes; a block that is all repeats is left alone.
    """
    body = re.search(r"<body[^>]*>", html or "", re.I)
    if not body:
        return html
    start = body.end()
    rest = html[start:]
    seen, removals = [], []
    for block in _parts_by_block(rest):
        works = [_work(rest[a:b]) for a, b in block]
        repeats = [i for i, w in enumerate(works) if w[1] and any(_same_work(w, o) for o in seen)]
        if repeats and len(repeats) < len(block):
            removals += [block[i] for i in repeats if _balanced(rest[block[i][0]:block[i][1]])]
        seen += [w for w in works if w[1] and len(w[0]) > 20]
    for a, b in reversed(removals):
        rest = rest[:a] + rest[b:]
    return html[:start] + rest


_TOPBAR = re.compile(r'class\s*=\s*"[^"]*\btitle\b[^"]*"[^>]*>(.*?)</', re.I | re.S)
_QNO = re.compile(r'class\s*=\s*"qno"[^>]*>(.*?)</span>\s*', re.I | re.S)
_PGREF = re.compile(r'Pg\.\s*<span class="num">([^<]+)</span>', re.I)


def title_from_block(html, fallback="Untitled"):
    """A document title taken from the answer itself.

    "Discounting — Illustration 6 (Pg. 43)" tells the teacher what a document
    holds. The instruction he typed — "solve it in a table format" — does not,
    and every document ends up with the same name.
    """
    def clean(text):
        return re.sub(r"\s+", " ", _TAG.sub("", text or "")).strip(" .|—-")

    topic = ""
    bar = _TOPBAR.search(html or "")
    if bar:
        topic = clean(bar.group(1)).title()

    number = ""
    qno = _QNO.search(html or "")
    if qno:
        number = clean(qno.group(1))

    page = ""
    pg = _PGREF.search(html or "")
    if pg:
        page = f"Pg. {clean(pg.group(1))}"

    parts = [p for p in (topic, number) if p]
    title = " — ".join(parts)
    if page:
        title = f"{title} ({page})" if title else page
    return title[:70] or fallback


def validate_html(html):
    """Check a document against the house rules.

    Returns (errors, warnings) — both lists of plain strings.
    Errors are rule violations. Warnings are things worth a look.
    """
    errors, warnings = [], []
    clean = _strip_comments(html)

    style = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", clean,
                                 flags=re.DOTALL | re.IGNORECASE))
    inline_styles = " ".join(re.findall(r'style\s*=\s*"([^"]*)"', clean))
    css = style + "\n" + inline_styles
    # The markup alone — the house stylesheet is ours and is not under suspicion.
    markup = re.sub(r"<style[^>]*>.*?</style>", "", clean,
                    flags=re.DOTALL | re.IGNORECASE)

    # --- RULE 3 : no forced page breaks anywhere ---
    for label, pattern in _BANNED_BREAKS:
        if re.search(pattern, css, flags=re.IGNORECASE):
            errors.append(f"RULE 3 — forced page break found: {label}")

    # --- RULE 4 : break-avoidance scope ---
    allowed = {"table.wn tr", ".formula-box", ".final-ans"}
    for selectors, block in _rules(css):
        if not re.search(r"(?:page-)?break-inside\s*:\s*avoid", block):
            continue
        for sel in selectors:
            if sel not in allowed:
                errors.append(
                    f"RULE 4 — break-inside on '{sel}'; "
                    "only table.wn tr and .formula-box may avoid breaks"
                )
    if re.search(r"thead[^{}]*\{[^}]*display\s*:\s*table-row-group", css):
        errors.append("RULE 4 — 'thead { display: table-row-group }' is malformed; remove it")

    # --- RULE 5 : direct-child selector only ---
    for parent in (".q", ".notes", ".adj", ".wn-text"):
        if re.search(rf"{re.escape(parent)}\s+span\s*(?:,|\{{)", css):
            errors.append(
                f"RULE 5 — bare descendant selector '{parent} span' found; "
                f"must be '{parent} > span'"
            )

    # --- RULE 2 : geometry ---
    page_blocks = [m.group(1) for m in re.finditer(r"@page\s*\{([^}]*)\}", css)]
    if not page_blocks:
        errors.append("RULE 2 — no @page rule found")
    else:
        margin = _declaration(page_blocks, "margin")
        if margin is None:
            errors.append("RULE 2 — @page has no margin declaration; it must be margin: 0")
        elif margin not in _ZERO:
            errors.append(f"RULE 2 — @page margin is '{margin}'; it must be 0")

    padding = _declaration(_blocks_for(css, "body"), "padding")
    if padding is None:
        errors.append("RULE 2 — body has no padding declaration; it must be 0.5cm")
    elif padding != "0.5cm":
        errors.append(f"RULE 2 — body padding is '{padding}'; it must be 0.5cm")

    # --- RULE 6 : page background ---
    # Read body's own background, not merely whether the colour appears
    # somewhere: a stylesheet that colours the cells and leaves the page white
    # passes a search and fails the eye.
    page_colour = (_declaration(_blocks_for(css, "body"), "background")
                   or _declaration(_blocks_for(css, "body"), "background-color")
                   or "")
    if not page_colour:
        errors.append("RULE 6 — body has no background; the page must be #C8C8C8")
    elif "#C8C8C8" not in page_colour.upper():
        errors.append(f"RULE 6 — the page is '{page_colour}'; it must be #C8C8C8")

    # --- FRACTIONS : no division sign, no slash fractions ---
    visible = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", clean,
                     flags=re.DOTALL | re.IGNORECASE)
    # A cell, a row or a line ends a quotation; an amount's own tag does not.
    visible = re.sub(r"</?(?:div|td|th|tr|table|p|li|br|h\d)\b[^>]*>", "\n",
                     visible, flags=re.IGNORECASE)
    visible = re.sub(r"<span[^>]*class=\"[^\"]*\bline\b[^>]*>", "\n", visible)
    visible = re.sub(r"<[^>]+>", "", visible)
    visible = re.sub(r"[ \t]+", " ", visible)

    def around(at, found):
        """The text either side of a hit, within its own cell or line."""
        window = visible[max(0, at - 28):at]
        before = window.split("\n")[-1]
        after = visible[at + len(found):at + len(found) + 28].split("\n")[0]
        # Cut mid-line, the window may open inside a word; start on a whole one.
        if at - 28 > 0 and "\n" not in window and " " in before:
            before = before[before.index(" ") + 1:]
        return before.lstrip(), after.rstrip()

    def where(at, found):
        """The words around a hit, so it can be found on the page."""
        before, after = around(at, found)
        return f"'{before}{found}{after}'"

    for sign in re.finditer(r"\u00f7|&divide;", visible):
        # "Press the division key ÷ twice" names a key on the calculator; it
        # is not a division, and there is nothing to stack.
        before, after = around(sign.start(), sign.group(0))
        if re.search(r"\b(key|button)s?\b", before[-16:] + " " + after[:16], re.I):
            continue
        errors.append("FRACTIONS — a division sign in "
                      f"{where(sign.start(), sign.group(0))}; it must be a stacked fraction")
        if len(errors) > 8:
            break

    scrubbed = _SLASH_SAFE.sub(lambda m: " " * len(m.group(0)), visible)
    for slash in list(re.finditer(r"(?<![\w/])\d[\d,.]*\s*/\s*\d[\d,.]*(?![\w/])",
                                  scrubbed))[:6]:
        warnings.append("FRACTIONS — a slash fraction in "
                        f"{where(slash.start(), slash.group(0))}")

    # --- TABLES ---
    if re.search(r"<table(?![^>]*class=)", clean, flags=re.IGNORECASE):
        warnings.append("TABLES — a <table> without class='wn' found; it will miss the house style")
    # Tables size themselves to their contents; max-width is what keeps a wide
    # one on the paper, so that is the guard worth checking.
    if "table.wn" in css and not re.search(r"max-width\s*:\s*100%", css):
        errors.append("TABLES — table.wn is missing max-width: 100%; a wide table would crop")

    # --- WHITE ---
    # White inside the page is painful to read from and never house style.
    for hit in set(re.findall(
            r"(?:background(?:-color)?\s*:\s*|bgcolor\s*=\s*[\"']\s*)"
            r"(#fff(?:fff)?\b|white\b)", markup, re.I)):
        warnings.append(
            f"WHITE — a background of '{hit}' was written into the answer; "
            "the page colour is #C8C8C8")

    # --- STRUCTURE ---
    if 'class="page-block"' not in clean:
        warnings.append("STRUCTURE — no .page-block container found")
    if clean.count('class="header"') > 1:
        errors.append("STRUCTURE — header repeated; only one header per document")
    top_bars = clean.count('class="top-bar"')
    blocks = clean.count('class="page-block"')
    if blocks and top_bars > blocks:
        warnings.append("STRUCTURE — more top-bars than page-blocks; it should appear once per question")

    # --- RULES 8 & 13 : no social links ---
    for host in ("whatsapp", "wa.me", "facebook", "instagram", "telegram", "t.me", "youtube"):
        if re.search(rf'href\s*=\s*["\'][^"\']*{re.escape(host)}', clean, flags=re.IGNORECASE):
            errors.append(f"RULE 8 — social link found: {host}")

    return errors, warnings


def format_validation(errors, warnings):
    """Render the validator result as a short plain-text report."""
    if not errors and not warnings:
        return "House style: clean — no rule violations."
    out = []
    if errors:
        out.append("ERRORS")
        out += [f"  x {e}" for e in errors]
    if warnings:
        out.append("WARNINGS")
        out += [f"  ! {w}" for w in warnings]
    return "\n".join(out)
