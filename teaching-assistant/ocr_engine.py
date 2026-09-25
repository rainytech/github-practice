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


def ocr_number(img: Image.Image, box: tuple) -> int | None:
    """Reads the right-most number inside box (x, y, w, h), zoomed and padded."""
    import re

    x, y, w, h = box
    crop = img.convert("RGB").crop((int(x), int(y), int(x + w), int(y + h)))
    g = ImageOps.grayscale(crop)
    if ImageStat.Stat(g).mean[0] < 128:
        g = ImageOps.invert(g)
    scale = max(1, round(120 / max(g.height, 1)))
    g = ImageOps.autocontrast(g).resize((g.width * scale, g.height * scale), Image.LANCZOS)
    g = g.point(lambda v: 0 if v < 110 else 255)  # drop grey box borders, keep dark digits
    g = ImageOps.expand(g, border=40, fill=255)
    text = " ".join(ln.text for ln in _ocr(g, psm=7))
    nums = re.findall(r"\d{1,4}", text)
    return int(nums[-1]) if nums else None
