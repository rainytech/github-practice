"""Perceptual hash of the listing photo (the picture above the title).

A 64-bit "difference hash": the photo is shrunk to 9x8 grey pixels and each bit
says whether a pixel is brighter than its right-hand neighbour. Two screenshots
of the same listing give nearly the same hash even if the price, scroll position
or compression differ.
"""
import numpy as np
from PIL import Image


def find_photo_box(img: Image.Image, bottom_limit=None):
    """Find the listing photo: the tallest band of rows that differ from the page background."""
    grey = img.convert("L")
    w, h = grey.size
    arr = np.asarray(grey, dtype=np.int16)
    limit = int(bottom_limit) if bottom_limit and bottom_limit > 0.15 * h else int(0.60 * h)
    strip = arr[min(h - 1, limit):min(h, limit + 60), :]
    bg = float(np.median(strip)) if strip.size else float(np.median(arr[-60:, :]))
    differs = np.abs(arr[:limit] - bg) > 25
    frac = differs.mean(axis=1)
    if len(frac) > 15:
        frac = np.convolve(frac, np.ones(15) / 15, mode="same")
    mask = frac > 0.30
    best, start = (0, 0, 0), None
    for y, on in enumerate(list(mask) + [False]):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if y - start > best[0]:
                best = (y - start, start, y)
            start = None
    length, y0, y1 = best
    if length < 0.12 * h:
        return (0, int(0.08 * h), w, max(int(0.08 * h) + 10, limit))
    cols = differs[y0:y1].mean(axis=0) > 0.20
    xs = np.nonzero(cols)[0]
    x0, x1 = (int(xs[0]), int(xs[-1]) + 1) if len(xs) else (0, w)
    return (x0, y0, x1, y1)


def dhash(img: Image.Image) -> str:
    small = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    a = np.asarray(small, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return f"{value:016x}"


def listing_photo_hash(img: Image.Image, bottom_limit=None) -> str:
    box = find_photo_box(img, bottom_limit)
    return dhash(img.crop(box))


def distance(a: str, b: str):
    if not a or not b:
        return None
    return bin(int(a, 16) ^ int(b, 16)).count("1")
