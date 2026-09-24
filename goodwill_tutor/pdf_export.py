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


# Every word on the page, where Chromium drew it, in reading order — what lets
# the Preview select text as a browser does. For each word:
#   x y w h  its box        t  the word          s  a space came before it
#   b  the line or cell it sits in (a fraction counts as part of its line)
#   r  its table row, or -1
#   f  "n"/"d" inside a fraction's top/bottom    u  1 inside a superscript
_WORD_SCRIPT = """() => {
  const out = [], ids = new Map();
  const idOf = e => { if (!ids.has(e)) ids.set(e, ids.size); return ids.get(e); };
  const blockOf = e => {
    while (e && e !== document.body) {
      const d = getComputedStyle(e).display;
      if (!d.startsWith('inline') && d !== 'contents') return e;
      e = e.parentElement;
    }
    return document.body;
  };
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let pending = false, node;
  while ((node = walk.nextNode())) {
    const text = node.textContent, p = node.parentElement;
    if (!text.trim()) { if (text.length) pending = true; continue; }
    const fr = p.closest('.frac');
    const f = fr ? (p.closest('.den') ? 'd' : 'n') : '';
    const u = p.closest('sup') ? 1 : 0;
    const blk = idOf(blockOf(fr ? fr.parentElement : p)), tr = p.closest('tr'), row = tr ? idOf(tr) : -1;
    const re = /\\S+/g; let m;
    while ((m = re.exec(text))) {
      const r = document.createRange();
      r.setStart(node, m.index); r.setEnd(node, m.index + m[0].length);
      const box = r.getClientRects()[0];
      if (!box || !box.width) continue;
      const s = m.index > 0 ? /\\s/.test(text[m.index - 1]) : pending;
      out.push({x: box.left + scrollX, y: box.top + scrollY, w: box.width, h: box.height,
                t: m[0], s: s ? 1 : 0, b: blk, r: row, f: f, u: u});
    }
    pending = /\\s$/.test(text);
  }
  return out;
}"""


def words_text(words, first, last):
    """The text of words[first..last] as it reads on the page.

    Lines break where the page breaks them, table cells are tab-apart, a
    fraction reads 66,550/1.331 and a power 1.10^3.
    """
    first, last = sorted((first, last))
    out, prev = [], None
    for w in words[first:last + 1]:
        if prev is not None:
            if w["u"] and not prev["u"]:
                sep = "^"
            elif w["f"] == "d" and prev["f"] == "n":
                sep = "/"
            elif w["b"] != prev["b"]:
                sep = "\t" if w["r"] >= 0 and w["r"] == prev["r"] else "\n"
            else:
                sep = " " if w["s"] else ""
            out.append(sep)
        out.append(w["t"])
        prev = w
    return "".join(out)


def word_at(words, x, y):
    """The word under a point, or the nearest one to it; None on an empty page."""
    if not words:
        return None
    for i, w in enumerate(words):
        if w["x"] <= x <= w["x"] + w["w"] and w["y"] <= y <= w["y"] + w["h"]:
            return i
    on_line = [i for i, w in enumerate(words) if w["y"] <= y <= w["y"] + w["h"]]
    if on_line:
        return min(on_line, key=lambda i: min(abs(x - words[i]["x"]),
                                              abs(x - words[i]["x"] - words[i]["w"])))

    def distance(i):
        w = words[i]
        dy = 0 if w["y"] <= y <= w["y"] + w["h"] else min(abs(y - w["y"]), abs(y - w["y"] - w["h"]))
        dx = 0 if w["x"] <= x <= w["x"] + w["w"] else min(abs(x - w["x"]), abs(x - w["x"] - w["w"]))
        return (dy, dx)
    return min(range(len(words)), key=distance)


def hit_word(words, x, y):
    """True when the point is on a word — for the text cursor."""
    return any(w["x"] <= x <= w["x"] + w["w"] and w["y"] <= y <= w["y"] + w["h"] for w in words)


def html_to_png(html_path, png_path=None, width=880, wait_ms=300, scale=1.0, media="screen",
                lines=False):
    """Render an HTML file to a full-page PNG through the same Chromium that
    makes the PDF, so the preview cannot disagree with the printed page.

    media="print" draws the page with the print rules, as the PDF does.
    lines=True also writes <png>.json: where every word sits in the picture,
    so the Preview can select and copy text as a browser does.
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
                    found = page.evaluate(_WORD_SCRIPT)
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
