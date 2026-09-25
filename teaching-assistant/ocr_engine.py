"""Reads text, with positions, from a screenshot.

Primary engine: the OCR built into Windows 10/11 (fully offline, nothing to
install). Fallback: Tesseract via pytesseract, if installed.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from PIL import Image, ImageOps, ImageStat


@dataclass
class Word:
    text: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class Line:
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def x(self) -> float:
        return min(w.x for w in self.words)

    @property
    def y(self) -> float:
        return min(w.y for w in self.words)

    @property
    def h(self) -> float:
        return max(w.y + w.h for w in self.words) - self.y

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class OcrError(RuntimeError):
    pass


def _windows_ocr(img: Image.Image) -> list[Line]:
    import asyncio
    import ctypes

    ctypes.windll.ole32.CoInitializeEx(None, 0)  # this worker thread joins the MTA

    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import FileAccessMode, StorageFile

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        engine = OcrEngine.try_create_from_language(Language("en-US"))
    if engine is None:
        raise OcrError(
            "Windows OCR has no English language pack.\n"
            "Settings > Time & language > Language > add 'English (United States)'."
        )

    scale = 1.0
    limit = OcrEngine.max_image_dimension
    if max(img.size) > limit:
        scale = limit / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        img.convert("RGB").save(tmp)

        async def run():
            f = await StorageFile.get_file_from_path_async(os.path.abspath(tmp))
            stream = await f.open_async(FileAccessMode.READ)
            decoder = await BitmapDecoder.create_async(stream)
            bitmap = await decoder.get_software_bitmap_async()
            return await engine.recognize_async(bitmap)

        result = asyncio.run(run())
    finally:
        os.remove(tmp)

    lines = []
    for ln in result.lines:
        words = []
        for wd in ln.words:
            r = wd.bounding_rect
            words.append(Word(wd.text, r.x / scale, r.y / scale, r.width / scale, r.height / scale))
        if words:
            lines.append(Line(words))
    return lines


def _tesseract_ocr(img: Image.Image, psm: int = 11) -> list[Line]:
    try:
        import pytesseract
    except ImportError as e:
        raise OcrError("No OCR engine available (Windows OCR or Tesseract).") from e

    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=f"--psm {psm}")
    groups: dict[tuple, list[Word]] = {}
    for i, text in enumerate(d["text"]):
        if not text.strip():
            continue
        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        groups.setdefault(key, []).append(
            Word(text, d["left"][i], d["top"][i], d["width"][i], d["height"][i])
        )
    return [Line(ws) for ws in groups.values()]


def _ocr(img: Image.Image, psm: int = 11) -> list[Line]:
    if os.name == "nt":
        try:
            return _windows_ocr(img)
        except ImportError:
            pass
    return _tesseract_ocr(img, psm)


def _shift(lines: list[Line], factor: float, dx: float, dy: float) -> list[Line]:
    for ln in lines:
        for w in ln.words:
            w.x, w.y = w.x / factor + dx, w.y / factor + dy
            w.w, w.h = w.w / factor, w.h / factor
    return lines


def _enhance(img: Image.Image) -> Image.Image:
    """Grayscale, light-on-dark flipped to dark-on-light, enlarged 2x."""
    g = ImageOps.grayscale(img)
    if ImageStat.Stat(g).mean[0] < 128:
        g = ImageOps.invert(g)
    return g.resize((g.width * 2, g.height * 2), Image.LANCZOS)


def read_screenshot(img: Image.Image) -> list[list[Line]]:
    """Returns OCR passes, most detailed first: [bottom strip, top strip, whole image].

    The strips are enlarged so small status-bar / title-bar text (file path,
    page number) is read accurately.
    """
    img = img.convert("RGB")
    band = max(40, int(img.height * 0.15))
    bottom = img.crop((0, img.height - band, img.width, img.height))
    top = img.crop((0, 0, img.width, band))
    return [
        _shift(_ocr(_enhance(bottom)), 2, 0, img.height - band),
        _shift(_ocr(_enhance(top)), 2, 0, 0),
        _ocr(img),
    ]


def ocr_text(img: Image.Image, box: tuple) -> str:
    """Reads one line of text inside box (x, y, w, h): zoomed, black-and-white, padded."""
    x, y, w, h = box
    img = img.convert("RGB")
    crop = img.crop((max(0, int(x)), max(0, int(y)), min(img.width, int(x + w)), min(img.height, int(y + h))))
    g = ImageOps.grayscale(crop)
    if ImageStat.Stat(g).mean[0] < 128:
        g = ImageOps.invert(g)
    scale = max(1, round(120 / max(g.height, 1)))
    g = ImageOps.autocontrast(g).resize((g.width * scale, g.height * scale), Image.LANCZOS)
    g = g.point(lambda v: 0 if v < 110 else 255)  # drop grey box borders, keep dark digits
    g = ImageOps.expand(g, border=40, fill=255)
    if os.name == "nt":  # Windows OCR limits image size
        try:
            from winrt.windows.media.ocr import OcrEngine

            limit = OcrEngine.max_image_dimension
            if max(g.size) > limit:
                f = limit / max(g.size)
                g = g.resize((int(g.width * f), int(g.height * f)), Image.LANCZOS)
        except ImportError:
            pass
    return " ".join(ln.text for ln in sorted(_ocr(g, psm=7), key=lambda l: l.x))


def ocr_number(img: Image.Image, box: tuple) -> int | None:
    """Reads the right-most number inside box (x, y, w, h)."""
    import re

    nums = re.findall(r"\d{1,4}", ocr_text(img, box))
    return int(nums[-1]) if nums else None


_rapid = None


def _rapid_rec(img: Image.Image) -> tuple[str, float]:
    """RapidOCR (offline, models ship with the package) recognising one small text crop."""
    global _rapid
    import numpy as np
    from rapidocr import RapidOCR

    if _rapid is None:
        _rapid = RapidOCR()
    out = _rapid(np.array(img.convert("RGB")), use_det=False, use_cls=False, use_rec=True)
    if not out.txts:
        return "", 0.0
    return out.txts[0], float(out.scores[0])


def find_boxes(img: Image.Image, box: tuple) -> list[tuple[int, int, int, int]]:
    """Input boxes (a faint rectangle with text inside) within region box (x, y, w, h).

    Finds e.g. the page-number box of a PDF viewer's status bar. Returns
    [(left, top, right, bottom)] in image coordinates, left to right.
    """
    import numpy as np

    x, y, w, h = box
    x0, y0 = max(0, int(x)), max(0, int(y - h * 0.5))
    x1, y1 = min(img.width, int(x + w)), min(img.height, int(y + h * 1.5))
    if x1 - x0 < 10 or y1 - y0 < 10:
        return []
    a = np.asarray(ImageOps.grayscale(img.crop((x0, y0, x1, y1))), dtype=int)
    d = np.abs(a - int(np.median(a)))
    line = (d >= 10) & (d <= 90)  # faint border, not text or icons

    runs = []  # per column: (longest vertical run of border pixels, where it starts)
    for c in range(a.shape[1]):
        best = cur = start = bstart = 0
        for r, on in enumerate(line[:, c]):
            if on:
                start = r if cur == 0 else start
                cur += 1
                if cur > best:
                    best, bstart = cur, start
            else:
                cur = 0
        runs.append((best, bstart))

    edges, prev = [], -2
    for c, (run, _s) in enumerate(runs):
        if run >= max(12, int(h * 0.6)):
            if c - prev > 1:
                edges.append(c)
            prev = c
    found = []
    for left, right in zip(edges, edges[1:]):
        if not h * 0.8 <= right - left <= h * 8:
            continue
        top = runs[left][1]
        bottom = top + runs[left][0]
        inner = d[top + 2:bottom - 2, left + 3:right - 2]
        if inner.size and (inner > 100).sum() >= 10:  # something written inside
            found.append((x0 + left, y0 + top, x0 + right, y0 + bottom))
    return found


def read_box_number(img: Image.Image, region: tuple, total: int | None) -> int | None:
    """Finds input boxes in region and returns the first whole number read inside one."""
    import re

    img = img.convert("RGB")
    for left, top, right, bottom in find_boxes(img, region):
        inner = img.crop((left + 3, top + 3, right - 2, bottom - 2))
        bg = inner.getpixel((1, 1))
        inner = ImageOps.expand(inner.resize((inner.width * 2, inner.height * 2), Image.LANCZOS),
                                border=16, fill=bg)
        texts = []
        try:
            text, score = _rapid_rec(inner)
            if score >= 0.8:
                texts.append(text)
        except ImportError:
            pass
        texts.append(ocr_text(img, (left + 3, top + 3, right - left - 5, bottom - top - 5)))
        for text in texts:
            t = text.strip()
            if re.fullmatch(r"\d{1,4}", t) and 1 <= int(t) <= (total or 9999):
                return int(t)
    return None


_rapid_page = None


def page_items(img: Image.Image) -> list[tuple[str, float, float, float]]:
    """All text on an image as (text, left x, centre y, height) — for grids like a timetable.

    RapidOCR keeps table cells apart; the Windows/Tesseract fallback returns words.
    """
    global _rapid_page
    img = img.convert("RGB")
    try:
        import numpy as np
        from rapidocr import RapidOCR

        if _rapid_page is None:
            _rapid_page = RapidOCR()
        out = _rapid_page(np.array(img))
        return [(t, float(b[:, 0].min()), float(b[:, 1].mean()), float(b[:, 1].max() - b[:, 1].min()))
                for t, b in zip(out.txts or (), out.boxes if out.boxes is not None else ())]
    except ImportError:
        return [(w.text, w.x, w.y + w.h / 2, w.h) for ln in _ocr(img) for w in ln.words]
