"""The window: every control reachable, the file cards honest."""

import os
import sys
import time
from support import Report, gui

r = Report("The window")
app = gui()

app.ensure_target("solve this question in a table format, working notes first")
app.refresh_title()
app.refresh_file_cards()
app.root.update()


def inside(widget, panel):
    """Is the whole widget within the panel's box?"""
    app.root.update()
    left, width = widget.winfo_rootx(), widget.winfo_width()
    edge, span = panel.winfo_rootx(), panel.winfo_width()
    return left >= edge - 1 and left + width <= edge + span + 1


# ── both Open buttons stay reachable as the window narrows ──────────────
for width in (1500, 1200, 1000, 860):
    app.root.geometry(f"{width}x780")
    app.root.update()
    r.check(f"PDF Open reachable at {width}px", inside(app.pdf_open_btn, app.files_row))
    r.check(f"HTML Open reachable at {width}px", inside(app.html_open_btn, app.files_row))

app.LIB.rename_document(app.current_chapter, app.current_doc,
                        "Discounting — Illustration 6 (Pg. 43) with working notes")
app.refresh_file_cards()
r.check("still reachable with a long name", inside(app.html_open_btn, app.files_row))

# ── the cards say what is true ──────────────────────────────────────────
name = app.current_title()[:20]
r.check("both cards name the document",
        app.pdf_label.cget("text").startswith(name)
        and app.html_label.cget("text").startswith(name))
r.check("no PDF yet, and it says so", "not made yet" in app.pdf_label.cget("text"))
r.check("Open is disabled until there is one", str(app.pdf_open_btn.cget("state")), "disabled")

app.save_current(html="<html><body>x</body></html>")
r.check("the HTML card turns black", app.html_label.cget("text").endswith("HTML"))
r.check("and its Open works", str(app.html_open_btn.cget("state")), "normal")

# A PDF written now is current; a later edit makes it stale.
open(app.LIB.pdf_path(app.current_chapter, app.current_doc), "wb").write(b"%PDF-1.4\n")
app.refresh_file_cards()
r.check("the PDF card is current", "out of date" in app.pdf_label.cget("text"), False)

time.sleep(1.2)
app.save_current(html="<html><body>y</body></html>")
r.check("editing makes the PDF stale", "out of date" in app.pdf_label.cget("text"))
r.check("and it is marked in red", app.pdf_label.cget("fg"), app.RED)

# ── the interface has no white in it ────────────────────────────────────
def near_white(colour):
    try:
        red, green, blue = app.root.winfo_rgb(colour)
    except Exception:
        return False
    return min(red, green, blue) > 63000        # 0-65535 per channel

for name, widget in (("chat", app.chat), ("editor", app.editor), ("typing box", app.entry)):
    r.check(f"no white — {name}", near_white(widget.cget("bg")), False)

# ── closing waits for a PDF instead of cutting Chromium's pipe ──────────
r.check("a close handler is installed", bool(app.root.protocol("WM_DELETE_WINDOW")))

sys.exit(r.finish())
