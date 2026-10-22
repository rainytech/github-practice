"""An old document gets today's stylesheet without losing its questions."""

import sys
from support import Report, gui

OLD_PAGE = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Goodwill Solution</title>
<style>
body { background: #FFFFFF; font-family: Arial; font-size: 12pt; }
table.wn td { background: #FFFFFF; }
</style></head><body>
<div class="header">GOODWILL TUITION CENTRE</div>
<div class="page-block"><div class="q"><span class="qno">Illustration 6.</span>
<span>Find the present value of Rs. 66,550.</span></div>
<table class="wn"><tr><td>Future Value</td><td>66,550</td></tr></table></div>
<!-- a note I typed myself -->
</body></html>'''

r = Report("An older document")
app = gui()
hs = app.hs

r.check("an old page is spotted", hs.needs_restyle(OLD_PAGE))
r.check("today's page is not", hs.needs_restyle(hs.wrap_document(["<div class='page-block'>x</div>"])), False)
r.check("an empty document needs nothing", hs.needs_restyle(""), False)

# Three old documents on disk, as if written by last year's version.
chapter = app.LIB.create_chapter("Old chapter")
ids = [app.LIB.create_document(chapter, f"Old {n}") for n in range(3)]
for doc in ids:
    app.LIB.write_document(chapter, doc, html=OLD_PAGE)
current = app.LIB.create_document(chapter, "Today's")
app.LIB.write_document(chapter, current, html=hs.wrap_document(
    ['<div class="page-block"><div class="q"><span>New.</span></div></div>']))

r.check("three need repair", app.restyle_everything(), 3)
r.check("and none the second time", app.restyle_everything(), 0)

fixed = app.LIB.read_document(chapter, ids[0])["html"]
r.check("today's document was not rewritten",
        "New." in app.LIB.read_document(chapter, current)["html"])

app.open_document(chapter, ids[1])
r.check("opening one shows the repaired page", hs.needs_restyle(app.last_full_html), False)

r.check("the page is grey now", "background:    #C8C8C8;" in fixed)
r.check("the white page colour is gone", "background: #FFFFFF" in fixed, False)
r.check("cells are pinned grey", "background-color: #C8C8C8 !important" in fixed)
r.check("the question is kept", "Find the present value" in fixed)
r.check("its number is at 20pt now", 'Illustration <span class="num">6</span>' in fixed)
r.check("the table is kept", "Future Value" in fixed)
r.check("my own note is kept", "a note I typed myself" in fixed)
r.check("it is saved to disk", "#C8C8C8" in open(
    app.LIB.html_path(chapter, ids[0]), encoding="utf-8").read())
r.check("and it no longer needs restyling", hs.needs_restyle(fixed), False)
r.check("nothing was announced in the chat",
        "stylesheet" in app.chat.get("1.0", "end"), False)

errors, warnings = hs.validate_html(fixed)
r.check("the restyled page passes the house rules", errors, [])

# A new question added to an old document must not inherit old colours.
app.last_full_html = OLD_PAGE
joined = hs.append_block(app.last_full_html,
                         '<div class="page-block"><div class="q"><span>Two.</span></div></div>')
r.check("appending brings the stylesheet up to date", "background:    #C8C8C8;" in joined)
r.check("both questions are there",
        "Find the present value" in joined and "Two." in joined)

# Today's stylesheet, but the numeral printed small — the 9.25 document.
SMALL_SIX = hs.wrap_document(['<div class="page-block"><div class="q">'
                              '<div>Illustration 6.</div><span>Suppose.</span></div></div>'])
r.check("a small question number is spotted", hs.needs_restyle(SMALL_SIX))
r.check("and set at 20pt", 'Illustration <span class="num">6</span>' in hs.restyle(SMALL_SIX))
r.check("the stylesheet itself is not touched",
        hs.restyle(SMALL_SIX).split("</style>")[0] == SMALL_SIX.split("</style>")[0])

# The 9.33 document: Illustration 6, then an answer holding 6 again and 7.
def _question(n, fv, pv):
    return (f'<div class="q"><span class="qno">Illustration <span class="num">{n}</span>.</span>'
            f'<span>Suppose an investor expects to receive Rs. {fv} after three years.</span></div>'
            f'<div class="sol-label">Solution:-</div>'
            f'<div class="final-ans">&there4; The present value of Rs. {fv} is Rs. {pv}.</div>')
SIX, SEVEN = _question(6, "66,550", "50,000"), _question(7, "1,33,100", "1,00,000")
TWICE = hs.wrap_document(['<div class="page-block">' + SIX + '</div>',
                          '<div class="page-block">' + SIX + SEVEN + '</div>'])
r.check("a question printed twice is spotted", hs.needs_restyle(TWICE))
once = hs.restyle(TWICE)
r.check("the second copy is taken out", once.count("66,550"), 2)
r.check("the first copy and the new question stay", "1,33,100" in once and "Illustration" in once)
r.check("and it stays settled", hs.needs_restyle(once), False)
ASKED_AGAIN = hs.wrap_document(['<div class="page-block">' + SIX + '</div>',
                                '<div class="page-block">' + SIX + '</div>'])
r.check("a question you asked for again on its own is left alone",
        hs.needs_restyle(ASKED_AGAIN), False)

sys.exit(r.finish())
