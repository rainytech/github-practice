"""
GOODWILL TUITION CENTRE — Free edits
====================================
Edits the app makes itself, without asking the model. Each is a fixed change
to the page — undo a step, swap Rs. for ₹, add an answer line, strip the
solutions for a worksheet — so sending the whole page to Gemini for it costs
paise and can only go wrong.

    parse(text)             -> (kind, args) or None
    apply(kind, args, html) -> (html, card title)     for changes to the page
    HELP                    -> what the teacher can type, for the chat

Kinds the window handles itself (undo, redo, PDF, tabs, renaming the
document, help) are parsed here too, so the one parser decides what is free.

Pure text: no Tkinter, no network.
"""

import html as html_lib
import re

import house_style as hs

_I = re.I
_WORD = r"(illustration|question|problem|exercise|example)"
_LABEL = rf"(?:the\s+)?{_WORD}\s*(?:no\.?\s*)?(\d+[a-z]?)"
_WHICH = rf"(?:\s+(?:in|of|from|for|to|on)\s+{_LABEL})?"
_END = r"\s*\.?\s*$"
_Q = r"[\"'“‘]"          # an opening quote
_QE = r"[\"'”’]"         # a closing quote


def _target(m, first):
    """("Illustration", "6") from the groups starting at `first`, or None."""
    word, number = m.group(first), m.group(first + 1)
    return (word.title(), number) if word else None


# ═══════════════════════════════════════════════════════════════
#  WHAT THE TEACHER CAN TYPE
# ═══════════════════════════════════════════════════════════════

_RULES = [
    ("undo", re.compile(r"^\s*(?:undo|go\s+back|undo\s+(?:that|it|the\s+last\s+(?:change|edit)))" + _END, _I)),
    ("redo", re.compile(r"^\s*(?:redo|go\s+forward|redo\s+(?:that|it))" + _END, _I)),
    ("help", re.compile(r"^\s*(?:help|free\s+edits|what\s+can\s+i\s+(?:say|type|do)|commands)\s*\??\s*$", _I)),
    ("pdf", re.compile(r"^\s*(?:make|create|generate|save|export|print)\s+(?:the\s+|a\s+)?pdf(?:\s+now)?" + _END, _I)),
    ("open_pdf", re.compile(r"^\s*(?:open|show)\s+(?:the\s+)?pdf" + _END, _I)),
    ("tab", re.compile(r"^\s*(?:show|open|switch\s+to)\s+(?:me\s+)?(?:the\s+)?(code|html|preview|page)(?:\s+tab)?" + _END, _I)),
    ("rename_doc", re.compile(r"^\s*rename\s+(?:the\s+|this\s+)?document\s+(?:to|as)\s*:?\s*(.+?)" + _END, _I)),
    ("replace", re.compile(
        rf"^\s*(?:replace|change|str_replace)\s+{_Q}(.+?){_QE}\s+(?:with|to|by|into)\s+{_Q}(.*?){_QE}"
        rf"{_WHICH}" + _END, _I)),
    ("to_rupee", re.compile(
        r"^\s*(?:(?:change|convert|replace)\s+(?:all\s+)?(?:the\s+)?rs\.?\s+(?:to|with|into|by)\s+"
        r"(?:the\s+)?(?:₹|rupee\s+(?:symbol|sign))|use\s+(?:the\s+)?(?:₹|rupee\s+(?:symbol|sign))"
        r"(?:\s+instead\s+of\s+rs\.?)?)" + _END, _I)),
    ("to_rs", re.compile(
        r"^\s*(?:(?:change|convert|replace)\s+(?:all\s+)?(?:the\s+)?(?:₹|rupee\s+(?:symbol|sign)s?)\s+"
        r"(?:to|with|into|by)\s+rs\.?|use\s+rs\.?(?:\s+instead\s+of\s+(?:₹|the\s+rupee\s+(?:symbol|sign)))?)"
        + _END, _I)),
    ("title", re.compile(
        rf"^\s*(?:change|set|rename|make)\s+(?:the\s+)?(?:top.?bar\s+)?(?:title|topic|heading)"
        rf"{_WHICH}\s+(?:to|as)\s*:?\s*(.+?)" + _END, _I)),
    ("add_source", re.compile(
        rf"^\s*(?:add|put|insert)\s+(?:the\s+)?(?:source(?:\s+tag)?\s*:?\s*)?\(([^()]+)\){_WHICH}" + _END, _I)),
    ("remove_source", re.compile(
        rf"^\s*(?:remove|delete|drop)\s+(?:the\s+|all\s+(?:the\s+)?)?source(?:\s+tags?|s)?{_WHICH}" + _END, _I)),
    ("add_ans", re.compile(
        rf"^\s*(?:add|put|insert|set)\s+(?:the\s+|an?\s+)?ans(?:wer)?(?:\s+line)?{_WHICH}\s*[:\-]\s*(.+?)\s*$", _I)),
    ("add_hint", re.compile(
        rf"^\s*(?:add|put|insert|set)\s+(?:the\s+|a\s+)?hint{_WHICH}\s*[:\-]\s*(.+?)\s*$", _I)),
    ("remove_ans", re.compile(
        rf"^\s*(?:remove|delete|drop)\s+(?:the\s+)?ans(?:wer)?\s+lines?{_WHICH}" + _END, _I)),
    ("remove_hint", re.compile(
        rf"^\s*(?:remove|delete|drop)\s+(?:the\s+|all\s+(?:the\s+)?)?hints?{_WHICH}" + _END, _I)),
    ("final", re.compile(
        rf"^\s*(?:change|set|make)\s+(?:the\s+)?final\s+answer{_WHICH}\s+(?:to|as)\s*:?\s*(.+?)\s*$", _I)),
    ("remove_rule", re.compile(
        rf"^\s*(?:remove|delete|drop)\s+(?:the\s+|all\s+(?:the\s+)?)?(?:rule\s+notes?|►\s*notes?|"
        rf"arrow\s+notes?){_WHICH}" + _END, _I)),
    ("worksheet", re.compile(
        rf"^\s*(?:(?:remove|delete|drop|hide)\s+(?:the\s+|all\s+(?:the\s+)?)?(?:solutions?|working)"
        rf"{_WHICH}|keep\s+only\s+the\s+questions?|make\s+(?:it|this)\s+a\s+worksheet|"
        r"questions?\s+only)" + _END, _I)),
    ("renumber_all", re.compile(
        r"^\s*(?:re)?number\s+(?:all\s+)?(?:the\s+)?(?:questions|illustrations)"
        r"(?:\s+(?:from|starting\s+(?:at|from)))?\s*(\d+)?" + _END, _I)),
    ("move", re.compile(
        rf"^\s*move\s+{_LABEL}\s+(above|before|below|after)\s+{_LABEL}" + _END, _I)),
    ("move_end", re.compile(
        rf"^\s*move\s+(?:{_LABEL}|(?:the\s+)?(last|first)\s+question)\s+to\s+the\s+"
        r"(top|start|beginning|end|bottom)" + _END, _I)),
    ("remove_topbar", re.compile(
        rf"^\s*(?:remove|delete|drop)\s+(?:the\s+)?top.?bar{_WHICH}" + _END, _I)),
]

# Kinds the window carries out; the rest change the page and go through apply().
WINDOW_KINDS = {"undo", "redo", "help", "pdf", "open_pdf", "tab", "rename_doc"}

HELP = """Free — done by the app, nothing sent to Gemini:

  undo  ·  redo
  make the pdf  ·  open the pdf  ·  show the code  ·  show the preview
  rename the document to Discounting — Set 1

  replace 'Find' with 'Calculate'            (quotes needed; add  in Illustration 6  for one question)
  change Rs. to ₹   ·   change ₹ to Rs.
  change the title to ADMISSION OF A PARTNER
  add (CBSE 2019) to Illustration 6   ·   remove the source
  add answer: Rs. 50,000   ·   remove the answer line
  add hint: use 1.10 × 1.10   ·   remove the hint
  change the final answer to The present value is Rs. 50,000.
  remove the rule note
  remove the solutions   ·   remove the solution from Illustration 6   (a worksheet)
  renumber the questions from 1
  move Illustration 7 above Illustration 6   ·   move the last question to the top
  remove the top bar

  remove Illustration 7  ·  remove the last question
  number it Illustration 6  ·  rename illustration no. 10
  change the book name to P.K. Lazar, Pg. 43  ·  remove the book name and page
  change the date to 25th sept

Anything else is sent to Gemini as an edit."""


def parse(text):
    """(kind, match) for a free edit, else None."""
    for kind, pattern in _RULES:
        found = pattern.match(text or "")
        if found:
            return kind, found
    return None


# ═══════════════════════════════════════════════════════════════
#  CHANGING THE PAGE
# ═══════════════════════════════════════════════════════════════

class QuickEditError(ValueError):
    """The edit could not be made; the message is fit for the chat."""


def _spans(html, target, default="all"):
    """The page-blocks an edit applies to: the named question, or all / the last."""
    spans = hs.block_spans(html)
    if not spans:
        raise QuickEditError("There is no page to change yet.")
    if target:
        want = f"{target[0]} {target[1]}".lower()
        picked = [s for s in spans if hs.question_label(html[s[0]:s[1]]).lower() == want]
        if not picked:
            raise QuickEditError(f"There is no {target[0]} {target[1]} on this page.")
        return picked
    return spans if default == "all" else spans[-1:]


def _each(html, spans, fn):
    """Apply fn to each block, from the last, so earlier offsets stay good."""
    for a, b in reversed(spans):
        html = html[:a] + fn(html[a:b]) + html[b:]
    return html


def _on_text(html, fn, start=0):
    """Change the words of the page, never its tags, from `start` on."""
    parts = re.split(r"(<[^>]+>)", html[start:])
    return html[:start] + "".join(p if p.startswith("<") else fn(p) for p in parts)


def _class_open(cls):
    # Whole class names only: "ans" must not find "final-ans".
    return re.compile(rf'<(div|span)\b[^>]*class\s*=\s*"(?:[^"]*\s)?{re.escape(cls)}(?:\s[^"]*)?"[^>]*>', _I)


def _element_end(block, m):
    """End of the div or span opened by match m."""
    tag = m.group(1).lower()
    depth = 0
    for t in re.finditer(rf"<(/?){tag}\b[^>]*>", block[m.start():], _I):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return m.start() + t.end()
    return -1


def _remove_all(block, cls):
    pattern = _class_open(cls)
    while True:
        m = pattern.search(block)
        if not m:
            return block
        end = _element_end(block, m)
        if end < 0:
            return block
        while end < len(block) and block[end] in " \t\r\n":
            end += 1
        block = block[:m.start()] + block[end:]


def _after_question(block, new):
    """Put a line straight after the question (and its adjustments and notes)."""
    anchor = None
    for cls in ("q", "adj", "notes"):
        m = _class_open(cls).search(block)
        while m:
            end = _element_end(block, m)
            if end > 0 and (anchor is None or end > anchor):
                anchor = end
            m = _class_open(cls).search(block, m.end())
            if cls == "q":
                break
    if anchor is None:
        raise QuickEditError("That question has no question text to put it under.")
    return block[:anchor] + "\n" + new + block[anchor:]


def _set_line(block, cls, text, wrap):
    block = _remove_all(block, cls)
    return _after_question(block, f'<div class="{cls}">{wrap.format(html_lib.escape(text))}</div>')


_SOLUTION_START = re.compile(
    r'<(?:div|table)\b[^>]*class\s*=\s*"[^"]*\b(?:sol-label|wn-label|wn-sub|wn-text|tbl-title|'
    r'dr-cr-row|wn|formula-box|part-heading|final-ans|rule-note|quote-box|verify-ok|verify-bad)\b', _I)


def _strip_solution(block):
    q = _class_open("q").search(block)
    start = _element_end(block, q) if q else 0
    m = _SOLUTION_START.search(block, max(start, 0))
    if not m:
        return block
    close = block.rfind("</div>")
    return block[:m.start()].rstrip() + "\n" + block[close:]


def apply(kind, m, html):
    """Make a free edit. Returns (html, card title). Raises QuickEditError."""
    if kind == "replace":
        old, new, target = m.group(1), m.group(2), _target(m, 3)
        body = re.search(r"<body[^>]*>", html, _I)
        start = body.end() if body else 0
        if target:
            spans = _spans(html, target)
            count = sum(html_lib.unescape(html[a:b]).count(old) for a, b in spans)
            html = _each(html, spans, lambda blk: _on_text(blk, lambda t: _swap(t, old, new)))
        else:
            count = html_lib.unescape(re.sub(r"<[^>]+>", "", html[start:])).count(old)
            html = _on_text(html, lambda t: _swap(t, old, new), start)
        if not count:
            raise QuickEditError(f"'{old}' is not on the page. Check the spelling and capitals.")
        return html, f"Replaced {count} × '{old[:24]}'"

    if kind in ("to_rupee", "to_rs"):
        body = re.search(r"<body[^>]*>", html, _I)
        start = body.end() if body else 0
        if kind == "to_rupee":
            fn = lambda t: re.sub(r"\bRs\.?\s?(?=\d)", "₹ ", re.sub(r"\bRs\.(?!\s?\d)", "₹", t))
            title = "Rs. changed to ₹"
        else:
            fn = lambda t: re.sub(r"₹\s?", "Rs. ", t.replace("&#8377;", "₹"))
            title = "₹ changed to Rs."
        new = _on_text(html, fn, start)
        if new == html:
            raise QuickEditError("There was nothing to change.")
        return new, title

    if kind == "title":
        target, value = _target(m, 1), m.group(3).strip().upper()
        pattern = re.compile(r'(<span\b[^>]*class\s*=\s*"[^"]*\btitle\b[^"]*"[^>]*>)(.*?)(</span>)', _I | re.S)
        spans = _spans(html, target)
        new = _each(html, spans, lambda blk: pattern.sub(
            lambda x: x.group(1) + html_lib.escape(value) + x.group(3), blk, count=1))
        if new == html:
            raise QuickEditError("That question has no top bar title to change.")
        return new, f"Title set to {value.title()}"

    if kind == "add_source":
        source, target = m.group(1).strip(), _target(m, 2)
        tag = f' <span class="source">({html_lib.escape(source)})</span>'

        def put(block):
            q = _class_open("q").search(block)
            if not q:
                return block
            end = _element_end(block, q)
            inside = block.rfind("</span>", q.end(), end)
            if inside < 0:
                return block
            return block[:inside] + tag + block[inside:]
        return _each(html, _spans(html, target, "last"), put), f"Source ({source}) added"

    if kind == "remove_source":
        new = _each(html, _spans(html, _target(m, 1)), lambda blk: _remove_all(blk, "source"))
        if new == html:
            raise QuickEditError("There is no source tag to remove.")
        return new, "Source removed"

    if kind in ("add_ans", "add_hint"):
        target, text = _target(m, 1), m.group(3).strip()
        cls, wrap = ("ans", "[Ans.: {}]") if kind == "add_ans" else ("hint", "[Hint: {}]")
        new = _each(html, _spans(html, target, "last"), lambda blk: _set_line(blk, cls, text, wrap))
        return new, ("Answer line added" if cls == "ans" else "Hint added")

    if kind in ("remove_ans", "remove_hint", "remove_rule", "remove_topbar"):
        cls = {"remove_ans": "ans", "remove_hint": "hint", "remove_rule": "rule-note",
               "remove_topbar": "top-bar"}[kind]
        new = _each(html, _spans(html, _target(m, 1)), lambda blk: _remove_all(blk, cls))
        if new == html:
            raise QuickEditError("There was nothing like that to remove.")
        return new, {"ans": "Answer line removed", "hint": "Hint removed",
                     "rule-note": "Rule note removed", "top-bar": "Top bar removed"}[cls]

    if kind == "final":
        target, text = _target(m, 1), m.group(3).strip()
        if not text.startswith(("∴", "&there4;")):
            text = "∴ " + text
        pattern = re.compile(r'(<div\b[^>]*class\s*=\s*"[^"]*\bfinal-ans\b[^"]*"[^>]*>)(.*?)(</div>)', _I | re.S)
        new = _each(html, _spans(html, target, "last"), lambda blk: pattern.sub(
            lambda x: x.group(1) + html_lib.escape(text) + x.group(3), blk, count=1))
        if new == html:
            raise QuickEditError("That question has no final answer line.")
        return new, "Final answer changed"

    if kind == "worksheet":
        target = _target(m, 1) if m.lastindex and m.group(1) else None
        new = _each(html, _spans(html, target), _strip_solution)
        if new == html:
            raise QuickEditError("There is no solution to remove.")
        return new, "Solutions removed — a worksheet"

    if kind == "renumber_all":
        n = int(m.group(1) or 1)
        spans = hs.block_spans(html)

        def renumber(block):
            nonlocal n
            label = hs.question_label(block)
            if not label:
                return block
            word = label.split(" ")[0]
            n_here = str(n)
            n += 1
            return hs.set_qno(block, word, n_here)
        # numbered in page order, so walk forwards and rebuild
        out, last = [], 0
        for a, b in spans:
            out.append(html[last:a])
            out.append(renumber(html[a:b]))
            last = b
        out.append(html[last:])
        return "".join(out), f"Questions renumbered from {m.group(1) or 1}"

    if kind in ("move", "move_end"):
        spans = hs.block_spans(html)
        labels = [hs.question_label(html[a:b]).lower() for a, b in spans]

        def index_of(word, number):
            want = f"{word} {number}".lower()
            if want not in labels:
                raise QuickEditError(f"There is no {word.title()} {number} on this page.")
            return labels.index(want)
        if kind == "move":
            src = index_of(m.group(1), m.group(2))
            dst = index_of(m.group(4), m.group(5))
            after = m.group(3).lower() in ("below", "after")
        else:
            src = (index_of(m.group(1), m.group(2)) if m.group(1)
                   else (len(spans) - 1 if m.group(3).lower() == "last" else 0))
            to_top = m.group(4).lower() in ("top", "start", "beginning")
            dst, after = (0, False) if to_top else (len(spans) - 1, True)
        if src == dst:
            raise QuickEditError("That question is already there.")
        blocks = [html[a:b] for a, b in spans]
        moving = blocks.pop(src)
        if src < dst:
            dst -= 1
        blocks.insert(dst + 1 if after else dst, moving)
        head, tail = html[:spans[0][0]], html[spans[-1][1]:]
        return head + "\n\n".join(blocks) + tail, f"{hs.question_label(moving) or 'Question'} moved"

    raise QuickEditError("That edit is not one the app makes itself.")


def _swap(text, old, new):
    """Replace in text that may carry entities, as the teacher sees it."""
    plain = html_lib.unescape(text)
    if old not in plain:
        return text
    return html_lib.escape(plain.replace(old, new), quote=False)
