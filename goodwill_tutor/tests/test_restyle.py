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

app.ensure_target("an old document")
app.last_full_html = OLD_PAGE
app.save_html(silent=True)
app.refresh_artifact()
app.restyle_document()
fixed = app.last_full_html

r.check("the page is grey now", "background:    #C8C8C8;" in fixed)
r.check("the white page colour is gone", "background: #FFFFFF" in fixed, False)
r.check("cells are pinned grey", "background-color: #C8C8C8 !important" in fixed)
r.check("the question is kept", "Illustration 6" in fixed)
r.check("the table is kept", "Future Value" in fixed)
r.check("my own note is kept", "a note I typed myself" in fixed)
r.check("it is saved to disk", "#C8C8C8" in open(
    app.LIB.html_path(app.current_chapter, app.current_doc), encoding="utf-8").read())
r.check("and it no longer needs restyling", hs.needs_restyle(fixed), False)
r.check("the chat explains", "older stylesheet" in app.chat.get("1.0", "end"))

errors, warnings = hs.validate_html(fixed)
r.check("the restyled page passes the house rules", errors, [])

# A new question added to an old document must not inherit old colours.
app.last_full_html = OLD_PAGE
joined = hs.append_block(app.last_full_html,
                         '<div class="page-block"><div class="q"><span>Two.</span></div></div>')
r.check("appending brings the stylesheet up to date", "background:    #C8C8C8;" in joined)
r.check("both questions are there",
        "Illustration 6" in joined and "Two." in joined)

sys.exit(r.finish())
