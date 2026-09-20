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


def open_file(path):
    """Open a file in the system's default application."""
    if os.name == "nt":
        os.startfile(path)  # noqa: S606
    elif os.uname().sysname == "Darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')
