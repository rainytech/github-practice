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

/* RULE 4 — the ONLY break-avoidance rule permitted */
table.wn tr,
.formula-box {
  break-inside:      avoid;
  page-break-inside: avoid;
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
}

/* ---------- RULES 5 & 10 : one sentence per line, direct child only ---------- */
.q       > span,
.notes   > span,
.adj     > span,
.wn-text > span { display: block; }

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
  margin:          0 0.15em;
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
.formula-box .line  { display: block; margin: 2px 0; }
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
    if not _STYLE_BLOCK.search(html):
        blocks = re.findall(
            r'<div[^>]*class\s*=\s*"[^"]*page-block[^"]*"[^>]*>.*?</div>\s*(?=<div[^>]*class\s*=\s*"[^"]*page-block|</body>|\Z)',
            html, re.DOTALL | re.IGNORECASE)
        return wrap_document(blocks or [html])
    return _STYLE_BLOCK.sub(lambda m: f"<style>{GOODWILL_CSS}</style>", html, count=1)


def needs_restyle(html):
    """True if this document carries a stylesheet other than today's."""
    found = _STYLE_BLOCK.search(html or "")
    if not found:
        return bool((html or "").strip())
    return GOODWILL_CSS.strip() not in found.group(0)


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
_WORDS = r"(?:[A-Za-z][A-Za-z ]{0,28}[A-Za-z]|[A-Za-z])"
_BRACKET = r"\([^()<>]{1,40}\)"
_TERM = rf"(?:{_WORDS}\s*{_BRACKET}|{_BRACKET}|{_WORDS})"

# An operand may carry its own power: (1 + 0.10)^3 belongs under the line, not
# beside it. The exponent is converted inside the fraction, never left outside.
_EXP = r"(?:\^\{?[A-Za-z0-9]{1,4}\}?)?"

# Digits either side, spaces optional: 66,550/1.331. Not a date, not 24/7/365.
_SLASH_NUM = re.compile(rf"(?<![\w/.])({_NUM}{_EXP})\s*/\s*({_NUM}{_EXP})(?![\w/])")
# Words or brackets either side, but only when the slash is spaced, so that
# "and/or", "w/o" and "P/L" are left alone.
_SLASH_TERM = re.compile(
    rf"(?<![\w/])((?:{_TERM}|{_NUM}){_EXP})\s+/\s+((?:{_TERM}|{_NUM}){_EXP})(?![\w/])")
# 10^3, (1 + r)^n, x^{12}
_CARET = re.compile(r"\^\{?([A-Za-z0-9]{1,4})\}?")
_DIVIDE = re.compile(rf"({_NUM})\s*(?:\u00f7|&divide;)\s*({_NUM})")

_TAG = re.compile(r"<[^>]+>")
# Text inside these is markup we must not touch.
_SKIP_INSIDE = re.compile(r"<(script|style|span class=\"frac\")", re.I)


def _on_text(html, fn):
    """Apply fn to the text between tags only, never inside a tag or a .frac."""
    out, pos, depth = [], 0, 0
    for tag in _TAG.finditer(html):
        chunk = html[pos:tag.start()]
        out.append(chunk if depth else fn(chunk))
        raw = tag.group(0)
        low = raw.lower()
        if 'class="frac"' in low:
            depth += 1
        elif depth and low.startswith("</span"):
            depth -= 1
        out.append(raw)
        pos = tag.end()
    rest = html[pos:]
    out.append(rest if depth else fn(rest))
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


def _flatten(html):
    """The visible text, with a map from each character back into the HTML.

    An amount arrives wrapped — "66,550</span> / <span>1.331" — so a repair that
    reads one text run at a time never sees digits on both sides of the slash.
    Flattening lets the pattern read across inline tags; the map puts the fix
    back in the right place. A block boundary and anything already inside a
    .frac become one sentinel character, so nothing is re-read and no two lines
    are joined into one number.
    """
    text, index, pos, depth = [], [], 0, 0
    spans = []                       # is each open <span> transparent?

    def sentinel(at):
        if text and text[-1] != "\x01":
            text.append("\x01")
            index.append(at)

    for tag in _TAG.finditer(html):
        chunk = html[pos:tag.start()]
        if depth:
            if chunk:
                sentinel(pos)
        else:
            for k, ch in enumerate(chunk):
                text.append(ch)
                index.append(pos + k)

        raw = tag.group(0)
        low = raw.lower()
        name = re.match(r"</?([a-z0-9]+)", low)
        name = name.group(1) if name else ""
        closing = low.startswith("</")

        if name in _TRANSPARENT_TAGS:
            transparent = True
        elif name == "span":
            if closing:
                transparent = spans.pop() if spans else False
            else:
                classes = _CLASS_ATTR.search(raw)
                transparent = bool(
                    set((classes.group(1) if classes else "").split())
                    & _TRANSPARENT_CLASSES)
                spans.append(transparent)
        else:
            transparent = False
        if not transparent:
            sentinel(tag.start())

        if 'class="frac"' in low:
            depth += 1
        elif depth and closing and name == "span":
            depth -= 1
        pos = tag.end()

    if not depth:
        for k, ch in enumerate(html[pos:]):
            text.append(ch)
            index.append(pos + k)
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

        def piece(group):
            raw = html[index[m.start(group)]:index[m.end(group) - 1] + 1]
            if not _balanced(raw):
                raw = _TAG.sub("", raw)
            return _on_text(raw, powers).strip()

        counts["fraction"] += 1
        start, stop = index[m.start()], index[m.end() - 1] + 1
        html = (html[:start]
                + _FRAC.format(n=piece(1), d=piece(2))
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
        return _CARET.sub(sup, text)

    for pattern in (_DIVIDE, _SLASH_NUM, _SLASH_TERM):
        html = _apply_fractions(html, pattern, counts, powers)

    fixed = _fit_tables(_apply_powers(_on_text(html, powers), counts), counts)
    notes = [f"{n} {name}{'s' if n > 1 and not name.endswith('contents') else ''}"
             for name, n in counts.items() if n]
    return fixed, notes


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
    allowed = {"table.wn tr", ".formula-box"}
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
    visible = re.sub(r"<[^>]+>", " ", visible)

    if "\u00f7" in visible or "&divide;" in visible:
        errors.append("FRACTIONS — a division sign was found; every division must be a stacked .frac")

    scrubbed = _SLASH_SAFE.sub(" ", visible)
    slash_hits = re.findall(r"(?<![\w/])\d+\s*/\s*\d+(?![\w/])", scrubbed)
    if slash_hits:
        warnings.append(
            f"FRACTIONS — possible slash fraction(s): {', '.join(sorted(set(slash_hits))[:6])}"
        )

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
