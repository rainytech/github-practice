"""An answer from end to end: cleaned, repaired, saved, named."""

import sys
from support import Report, gui

GOOD = ('<div class="page-block"><div class="top-bar">'
        '<span class="title">DISCOUNTING</span>'
        '<span class="pgref">Central Concepts | Pg. <span class="num">43</span></span></div>'
        '<div class="q"><span class="qno">Illustration <span class="num">6</span>.</span>'
        '<span>Suppose an investor expects Rs. 66,550 after three years.</span></div>'
        '<div class="formula-box"><span class="line">P = '
        '<span class="amt">66,550</span> / <span class="amt">1.331</span></span></div>'
        '<div class="final-ans">Present Value = Rs. 50,000</div></div>')

NOISY = "I will follow the contract carefully.\nHere is the document.\n\n" + GOOD


def stream_of(text):
    def stream(conv, model, system_prompt="", on_chunk=None, stop_event=None, **kw):
        if on_chunk:
            on_chunk(text)
        return text, 4000, 900, 0
    return stream


r = Report("A whole answer")
app = gui(stream=stream_of(NOISY))
from support import wait_for_models, settle

r.check("a model is available", bool(wait_for_models(app)))
app.entry.insert("1.0", "solve it in a table format, working notes first")
app.send_message()
settle(app)

page = app.last_full_html
r.check("the answer is in the editor", "Illustration" in page)
r.check("the model's preamble is gone", "I will follow the contract" in page, False)
r.check("the slash is stacked", 'class="frac"' in page)
# The question block only: the stylesheet above it is full of /* comments */.
block_text = __import__("re").sub(r"<[^>]*>", "", app.doc_blocks[0])
r.check("no slash is left in the text", "/" in block_text, False)
r.check("one block so far", len(app.doc_blocks), 1)
r.check("one header only", page.count('class="header"'), 1)

title = next(d["title"] for d in app.LIB.list_documents(app.current_chapter)
             if d["id"] == app.current_doc)
r.check("the document is named from the answer", title,
        "Discounting — Illustration 6 (Pg. 43)")

saved = open(app.LIB.html_path(app.current_chapter, app.current_doc),
             encoding="utf-8").read()
r.check("it is saved to disk", "Illustration" in saved)

errors, warnings = app.hs.validate_html(page)
r.check("the page passes the house rules", (errors, warnings), ([], []))

# A second question appends, keeping the first.
app.entry.insert("1.0", "and the PVF method")
app.send_message()
settle(app)
r.check("two blocks now", len(app.doc_blocks), 2)
r.check("still one header", app.last_full_html.count('class="header"'), 1)

# An edit of your own survives the next answer.
app.editor.insert("1.0", "<!-- my note -->\n")
app.apply_edited_html()
app.entry.insert("1.0", "one more")
app.send_message()
settle(app)
r.check("your edit survives the next answer", "<!-- my note -->" in app.last_full_html)
r.check("three blocks", len(app.doc_blocks), 3)

sys.exit(r.finish())
