"""Runs RapidOCR on a screenshot and groups the text into rows (top to bottom)."""
import logging

import numpy as np
from PIL import Image

_engine = None


class OCRUnavailable(Exception):
    pass


def engine():
    global _engine
    if _engine is None:
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise OCRUnavailable(
                "The OCR library is not installed. Open a Command Prompt in the tracker folder and run:\n"
                "  py -m pip install -r requirements.txt"
            ) from exc
        # RapidOCR prints INFO lines while loading; keep the console window quiet.
        logging.getLogger("RapidOCR").addFilter(lambda record: record.levelno >= logging.ERROR)
        _engine = RapidOCR()
    return _engine


def _to_bgr(img):
    return np.ascontiguousarray(np.asarray(img.convert("RGB"))[:, :, ::-1])


def _read_piece(piece, scale):
    if scale != 1.0:
        piece = piece.resize((max(1, int(piece.width * scale)), max(1, int(piece.height * scale))),
                             Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (piece.width + 100, piece.height + 100), piece.getpixel((1, 1)))
    canvas.paste(piece, (50, 50))
    result = engine()(_to_bgr(canvas))
    if result is None or not result.txts or not any(str(t).strip() for t in result.txts):
        return None, 0.0
    return "  ".join(str(t).strip() for t in result.txts if str(t).strip()), float(min(result.scores))


def _ink_segments(line, min_gap=15):
    g = np.asarray(line.convert("L"), dtype=np.int16)
    ink = (np.abs(g - np.median(g)) > 60).any(axis=0)
    xs = np.nonzero(ink)[0]
    segs, start, last = [], None, None
    for x in xs:
        if start is None:
            start = x
        elif x - last > min_gap:
            segs.append((int(start), int(last)))
            start = x
        last = x
    if start is not None:
        segs.append((int(start), int(last)))
    return [s for s in segs if s[1] - s[0] > 20]


def reread_line(img, row, accept, pad=10):
    """Second, closer look at one line (whole line, then each word-group, at a few sizes).

    Reading a line on its own often recovers a ₹ sign that was lost when the whole
    screenshot was read. Returns the first reading that `accept(text)` approves, as
    (text, score), or (None, 0). Nothing is invented: the text is exactly what OCR saw.
    """
    w, h = img.size
    line = img.crop((0, max(0, int(row["y0"]) - pad), w, min(h, int(row["y1"]) + pad)))
    pieces = [line] + [line.crop((max(0, a - 10), 0, min(w, b + 10), line.height))
                       for a, b in _ink_segments(line)[:3]]
    for piece in pieces:
        for scale in (1.0, 0.9, 0.75, 1.25):
            text, score = _read_piece(piece, scale)
            if text and accept(text):
                return text, score
    return None, 0.0


def read_rows(img):
    """img: PIL RGB image. Returns a list of rows: dict(text, x0, y0, x1, y1, yc, h, score)."""
    result = engine()(_to_bgr(img))
    if result is None or result.boxes is None or result.txts is None:
        return []
    boxes = []
    for pts, text, score in zip(result.boxes, result.txts, result.scores):
        text = str(text).strip()
        if not text:
            continue
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        y0, y1 = min(ys), max(ys)
        boxes.append({"text": text, "x0": min(xs), "x1": max(xs), "y0": y0, "y1": y1,
                      "yc": (y0 + y1) / 2, "h": max(1.0, y1 - y0), "score": float(score)})
    return group_rows(boxes)


def group_rows(boxes):
    boxes = sorted(boxes, key=lambda b: (b["yc"], b["x0"]))
    rows = []
    for b in boxes:
        if rows and abs(b["yc"] - rows[-1]["yc"]) < 0.5 * min(b["h"], rows[-1]["h"]):
            rows[-1]["parts"].append(b)
            r = rows[-1]
            r["y0"], r["y1"] = min(r["y0"], b["y0"]), max(r["y1"], b["y1"])
            r["yc"] = (r["y0"] + r["y1"]) / 2
        else:
            rows.append({"parts": [b], "y0": b["y0"], "y1": b["y1"], "yc": b["yc"], "h": b["h"]})
    out = []
    for r in rows:
        parts = sorted(r["parts"], key=lambda b: b["x0"])
        out.append({
            "text": "  ".join(p["text"] for p in parts),
            "x0": min(p["x0"] for p in parts), "x1": max(p["x1"] for p in parts),
            "y0": r["y0"], "y1": r["y1"], "yc": r["yc"], "h": max(p["h"] for p in parts),
            "score": min(p["score"] for p in parts),
        })
    return out
