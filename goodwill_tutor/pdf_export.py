"""
GOODWILL TUITION CENTRE — Playwright PDF Export
===============================================
Converts a saved HTML document into an A4 PDF with selectable text.

Geometry is fixed by RULE 2:
    @page margin 0  +  body padding 0.5cm  +  Playwright margin 0cm
The body padding is the only page margin. Nothing here may add another.

First-time setup on a new machine:
    pip install playwright
    playwright install chromium
"""

import json
import os
import pathlib


class PdfExportError(RuntimeError):
    """Raised when the PDF could not be produced, with a message fit for the status bar."""


def playwright_available():
    """True if the playwright package is importable."""
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def html_to_pdf(html_path, pdf_path=None, wait_ms=350):
    """Render an HTML file to A4 PDF via headless Chromium.

    html_path : path to a saved .html file (loaded over file:// so that
                base64 images and any relative assets resolve).
    pdf_path  : output path; defaults to the html path with a .pdf suffix.
    wait_ms   : settle time after load, for fonts and embedded images.

    Returns the pdf path on success. Raises PdfExportError on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise PdfExportError(
            "Playwright is not installed. Run:  pip install playwright  "
            "then:  playwright install chromium"
        )

    html_path = os.path.abspath(html_path)
    if not os.path.exists(html_path):
        raise PdfExportError(f"HTML file not found: {html_path}")

    if pdf_path is None:
        pdf_path = os.path.splitext(html_path)[0] + ".pdf"
    pdf_path = os.path.abspath(pdf_path)

    file_url = pathlib.Path(html_path).as_uri()

    # Windows refuses to overwrite a PDF that a viewer still has open, and the
    # failure would otherwise arrive as an opaque Chromium error after a long
    # render. Fail fast, with the fix in the message.
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "ab"):
                pass
        except OSError:
            raise PdfExportError(
                f"'{os.path.basename(pdf_path)}' is open in another program.\n\n"
                "Close it in your PDF reader and try again."
            )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(file_url, wait_until="load")
                page.wait_for_timeout(wait_ms)
                page.pdf(
                    path=pdf_path,
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=False,
                    margin={
                        "top": "0cm",
                        "right": "0cm",
                        "bottom": "0cm",
                        "left": "0cm",
                    },
                )
            finally:
                browser.close()
    except PdfExportError:
        raise
    except Exception as exc:
        msg = str(exc)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            raise PdfExportError(
                "Chromium is not installed for Playwright. Run:  playwright install chromium"
            )
        raise PdfExportError(f"PDF export failed: {msg}")

    if not os.path.exists(pdf_path):
        raise PdfExportError("Chromium finished but no PDF was written.")

    return pdf_path


# One entry per line of text a teacher would want to copy. Cells rather than
# rows, so a table row copies as columns.
_LINE_SELECTOR = (".header > div, .top-bar .title, .top-bar .pgref, .q > span, .adj > span, "
                  ".notes > span, .wn-text > span, .sub > span, .sol-label, .wn-label, .wn-sub, "
                  ".part-heading, .tbl-title, .dr-cr-row > span, th, td, .formula-box .line, "
                  ".rule-note, .quote-box, .ans, .hint, .final-ans, .verify-ok, .verify-bad")

_LINE_SCRIPT = """(sel) => Array.from(document.querySelectorAll(sel)).map(e => {
  const r = e.getBoundingClientRect();
  const c = e.cloneNode(true);
  c.querySelectorAll('.frac').forEach(f => {
    const n = f.querySelector('.num'), d = f.querySelector('.den');
    f.replaceWith(' ' + (n ? n.textContent : '') + '/' + (d ? d.textContent : '') + ' ');
  });
  c.querySelectorAll('sup').forEach(s => s.replaceWith('^' + s.textContent));
  const t = c.textContent.replace(/\\s+/g, ' ').trim();
  return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, t: t};
}).filter(b => b.t && b.w > 0 && b.h > 0)"""


def text_in(lines, x0, y0, x1, y1):
    """The text of the lines touching a box, a row per line, cells tab-apart.

    lines : [{x, y, w, h, t}] in the picture's own pixels.
    """
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    hit = [b for b in lines
           if b["x"] < x1 and b["x"] + b["w"] > x0 and b["y"] < y1 and b["y"] + b["h"] > y0]
    hit.sort(key=lambda b: (b["y"] + b["h"] / 2, b["x"]))
    rows = []
    for b in hit:
        middle = b["y"] + b["h"] / 2
        if rows and abs(rows[-1][0] - middle) < max(4, b["h"] / 3):
            rows[-1][1].append(b)
        else:
            rows.append([middle, [b]])
    return "\n".join("\t".join(c["t"] for c in sorted(cells, key=lambda c: c["x"]))
                     for _, cells in rows)


def html_to_png(html_path, png_path=None, width=880, wait_ms=300, scale=1.0, media="screen",
                lines=False):
    """Render an HTML file to a full-page PNG through the same Chromium that
    makes the PDF, so the preview cannot disagree with the printed page.

    media="print" draws the page with the print rules, as the PDF does.
    lines=True also writes <png>.json: where each line of text sits in the
    picture, so the Preview can copy the text under the mouse.
    scale shrinks the picture, not the layout: the page is laid out at the
    same width and drawn smaller, so it wraps where the print does.

    Returns the png path. Raises PdfExportError on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise PdfExportError(
            "Playwright is not installed. Run:  pip install playwright  "
            "then:  playwright install chromium"
        )

    html_path = os.path.abspath(html_path)
    if not os.path.exists(html_path):
        raise PdfExportError(f"HTML file not found: {html_path}")
    if png_path is None:
        png_path = os.path.splitext(html_path)[0] + "_preview.png"
    png_path = os.path.abspath(png_path)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": width, "height": 1000},
                                        device_scale_factor=scale)
                page.emulate_media(media=media)
                page.goto(pathlib.Path(html_path).as_uri(), wait_until="load")
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=png_path, full_page=True)
                if lines:
                    found = page.evaluate(_LINE_SCRIPT, _LINE_SELECTOR)
                    for b in found:
                        for k in ("x", "y", "w", "h"):
                            b[k] = round(b[k] * scale, 1)
                    with open(png_path + ".json", "w", encoding="utf-8") as fh:
                        json.dump(found, fh, ensure_ascii=False)
            finally:
                browser.close()
    except PdfExportError:
        raise
    except Exception as exc:
        msg = str(exc)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            raise PdfExportError(
                "Chromium is not installed for Playwright. Run:  playwright install chromium"
            )
        raise PdfExportError(f"Preview render failed: {msg}")

    return png_path


def open_file(path):
    """Open a file in the system's default application."""
    if os.name == "nt":
        os.startfile(path)  # noqa: S606
    elif os.uname().sysname == "Darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')
