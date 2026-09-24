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


# ── the header keeps every control on screen as the window narrows ──────
HEADER = ("preview_tab", "code_tab", "pdf_make_btn", "pdf_open_btn", "more_btn", "output_btn")


def header_fits():
    return [name for name in HEADER if not inside(getattr(app, name), app.right)]


app.save_current(html="<html><body>x</body></html>")
open(app.LIB.pdf_path(app.current_chapter, app.current_doc), "wb").write(b"%PDF-1.4\n")
time.sleep(1.2)
app.save_current(html="<html><body>y</body></html>")    # the longest label: out of date
for width in (1500, 1200, 1000):
    app.root.geometry(f"{width}x780")
    app.root.update()
    r.check(f"header controls on screen at {width}px", header_fits(), [])
os.remove(app.LIB.pdf_path(app.current_chapter, app.current_doc))
os.remove(app.LIB.html_path(app.current_chapter, app.current_doc))
app.refresh_file_cards()

# ── the PDF buttons say what is true ────────────────────────────────────
r.check("no PDF yet: Open PDF is disabled", str(app.pdf_open_btn.cget("state")), "disabled")
r.check("no page yet: Make PDF is disabled", str(app.pdf_make_btn.cget("state")), "disabled")

app.save_current(html="<html><body>x</body></html>")
r.check("a saved page can be made into a PDF", str(app.pdf_make_btn.cget("state")), "normal")

# A PDF written now is current; a later edit makes it stale.
open(app.LIB.pdf_path(app.current_chapter, app.current_doc), "wb").write(b"%PDF-1.4\n")
app.refresh_file_cards()
r.check("the PDF is current", app.pdf_open_btn.cget("text"), "Open PDF")
r.check("and Open PDF works", str(app.pdf_open_btn.cget("state")), "normal")

time.sleep(1.2)
app.save_current(html="<html><body>y</body></html>")
r.check("editing makes the PDF stale", "out of date" in app.pdf_open_btn.cget("text"))
r.check("and it is marked in red", app.pdf_open_btn.cget("fg"), app.RED)

# ── Preview | Code ──────────────────────────────────────────────────────
app.show_tab("code")
app.root.update()
r.check("Code shows the HTML editor", bool(app.code_frame.winfo_ismapped()))
r.check("and hides the preview", bool(app.preview_frame.winfo_ismapped()), False)
app.show_tab("preview")
app.root.update()
r.check("Preview shows the page", bool(app.preview_frame.winfo_ismapped()))

# ── what Send will do is said above it ──────────────────────────────────
r.check("Send's intent sits above Send",
        app.intent_label.winfo_rooty() < app.send_btn.winfo_rooty())

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
