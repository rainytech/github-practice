"""Finds screenshots, hashes them, and works out the observation date. Read-only."""
import hashlib
import re
from datetime import datetime
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
UNSUPPORTED_EXTS = {".heic", ".heif"}

# Screenshot_20261112-083000_Facebook.jpg, IMG_20261112_083000.jpg, PXL_20261112_083000123.jpg
_DT_COMPACT = re.compile(r"(20\d{2})(\d{2})(\d{2})[-_ T]?(\d{2})(\d{2})(\d{2})")
# Screenshot_2026-11-12-08-30-00-123_com.facebook.katana.jpg, "Screenshot 2026-11-12 at 08.30.00"
_DT_SEPARATED = re.compile(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})(?:[-_ T]|\s+at\s+)(\d{2})[-_.:](\d{2})[-_.:](\d{2})")
_DATE_ONLY = re.compile(r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})")


def list_images(folder: Path):
    """All image files in the folder and its sub-folders (sorted, oldest name first)."""
    found, unsupported = [], []
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.name.startswith((".", "~$")):
            continue
        ext = p.suffix.lower()
        if ext in IMAGE_EXTS:
            found.append(p)
        elif ext in UNSUPPORTED_EXTS:
            unsupported.append(p)
    return found, unsupported


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _valid(*parts):
    try:
        return datetime(*[int(x) for x in parts])
    except ValueError:
        return None


def date_from_filename(name: str):
    for rx in (_DT_SEPARATED, _DT_COMPACT):
        m = rx.search(name)
        if m:
            dt = _valid(*m.groups())
            if dt:
                return dt
    m = _DATE_ONLY.search(name)
    if m:
        return _valid(*m.groups())
    return None


def date_from_exif(img: Image.Image):
    try:
        exif = img.getexif()
        value = exif.get_ifd(0x8769).get(36867) or exif.get(306)   # DateTimeOriginal, DateTime
        if value:
            return datetime.strptime(str(value).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None
    return None


def observation_date(path: Path, img: Image.Image):
    """Returns ('YYYY-MM-DD HH:MM:SS', where the date came from)."""
    dt = date_from_filename(path.name)
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S"), "file name"
    dt = date_from_exif(img)
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S"), "image date"
    dt = datetime.fromtimestamp(path.stat().st_mtime)
    return dt.strftime("%Y-%m-%d %H:%M:%S"), "file modified time"
