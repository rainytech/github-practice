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
.frac span.num { padding: 0 0.1em; font-size: 1em; font-weight: inherit; }
.frac span.den { border-top: 1px solid currentColor; padding: 0 0.1em; }

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
  width:           100%;
  table-layout:    fixed;
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
table.wn th {
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

/* Opt-out for short working-note tables that would look stretched */
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


def append_block(existing_html, new_block):
    """Append a new .page-block to an existing document — RULE 9, one artifact per chapter.

    Falls back to building a fresh document if the input is not a full page.
    """
    if not existing_html or "</body>" not in existing_html:
        return wrap_document(new_block)
    return existing_html.replace(
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
    if "#C8C8C8" not in css.upper():
        errors.append("RULE 6 — page background #C8C8C8 missing")

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
    if "table.wn" in css and not re.search(r"table-layout\s*:\s*fixed", css):
        errors.append("TABLES — table.wn is missing table-layout: fixed")

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
