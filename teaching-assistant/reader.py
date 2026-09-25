"""Turns OCR text from a PDF-viewer screenshot into: PDF path, page, total pages,
visible headings (e.g. "Illustration 9") and chapter."""
from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath

from ocr_engine import Line

PATH_RE = re.compile(r"(\b[A-Za-z])\s*[:.;]\s*[\\/|]\s*(.*?\.\s*p\s*d\s*f)", re.I)
PAGE_RE = re.compile(r"(?<![\d/.:])(\d{1,4})[\s|\[\]()]{0,4}(?:/|\bof\b)\s*(\d{1,4})(?![\d/])", re.I)
SLASH_TOTAL_RE = re.compile(r"^[/|lI]\s*(\d{1,4})\D{0,3}$")  # "/9", "/9D", "|9>"
HEAD_RE = re.compile(
    r"\b(Illustration|Illus\.?|Question|Problem|Example|Exercise|Q\.\s*No\.?)"
    r"\s*[:.\-]?\s*(\d{1,3}[A-Za-z]?)\b",
    re.I,
)
CHAP_RE = re.compile(r"\b(chapter|unit|lesson)\s*[-:]?\s*(\d{1,3})\b\s*[:.\-–—]?\s*(.*)", re.I)


@dataclass
class Reading:
    path: str = ""
    path_found: bool = False
    page: int | None = None
    total: int | None = None
    headings: list[str] = field(default_factory=list)
    chapter: str = ""
    page_box: tuple | None = None    # where the page number should be, if it could not be read
    status_box: tuple | None = None  # the rest of the row right of the file path

    @property
    def folder(self) -> str:
        return PureWindowsPath(self.path).parent.name if self.path else ""

    @property
    def file(self) -> str:
        return PureWindowsPath(self.path).name if self.path else ""


# ---------------------------------------------------------------- helpers

def _norm(s: str) -> str:
    return re.sub(r"[\s_\-.]+", "", s.lower())


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _rows(lines: list[Line]) -> list[list[Line]]:
    """Groups OCR lines that sit on the same horizontal row, left to right."""
    rows: list[list[Line]] = []
    for ln in sorted(lines, key=lambda l: l.cy):
        for row in rows:
            ref = row[0]
            if abs(ref.cy - ln.cy) < max(ref.h, ln.h) * 0.6:
                row.append(ln)
                break
        else:
            rows.append([ln])
    return [sorted(r, key=lambda l: l.x) for r in rows]


def _row_text(row: list[Line]) -> str:
    return " ".join(l.text for l in row)


def _clean_path(drive: str, body: str) -> str:
    body = re.sub(r"\s*[\\/|]\s*", r"\\", body)
    body = re.sub(r"\s*\.\s*p\s*d\s*f$", ".pdf", body, flags=re.I)
    return f"{drive.upper()}:\\{body.strip()}"


def _page_box(passes: list[list[Line]], total: int | None) -> tuple | None:
    """Region just left of a "/ 26" token — the page-number box the OCR missed."""
    for lines in passes:
        for ln in lines:
            ws = ln.words
            for i, w in enumerate(ws):
                m = SLASH_TOTAL_RE.match(w.text)
                if not m and w.text in ("/", "|", "l", "I") and i + 1 < len(ws) and ws[i + 1].text[:1].isdigit():
                    m = SLASH_TOTAL_RE.match(w.text + ws[i + 1].text)
                if not m or (total and int(m.group(1)) != total) or (not total and w.text[0] != "/"):
                    continue
                h = max(w.h, 8)
                return (max(0, w.x - 2.2 * h), w.y - 0.4 * h, 2.2 * h, 1.8 * h)
    return None


def page_from_text(text: str, total: int | None) -> int | None:
    """Finds the page in loose OCR text such as "4d 6 /9D" (total 9 -> 6)."""
    for m in PAGE_RE.finditer(text):
        page, tot = int(m.group(1)), int(m.group(2))
        if 1 <= page <= tot and (not total or tot == total):
            return page
    if total:
        for m in re.finditer(rf"(?<!\d)(\d{{1,4}})\D{{1,6}}?{total}(?!\d)", text):
            if 1 <= int(m.group(1)) <= total:
                return int(m.group(1))
    return None


def read_image(image, known_paths=(), passes=None, search_roots=None, log_dir=None) -> Reading:
    """Screenshot -> Reading. If the page number was missed, looks again, zoomed in:
    first at the box left of "/ 26", then at the whole row right of the file path."""
    from ocr_engine import ocr_number, ocr_text, read_screenshot

    passes = read_screenshot(image) if passes is None else passes
    r = parse(passes, search_roots=search_roots, known_paths=known_paths)
    extra = []
    if r.page is None and r.page_box:
        n = ocr_number(image, r.page_box)
        extra.append(f"page box -> {n}")
        if n and (not r.total or 1 <= n <= r.total):
            r.page = n
    if r.page is None and r.status_box:
        text = ocr_text(image, r.status_box)
        extra.append(f"status row -> {text!r}")
        r.page = page_from_text(text, r.total)
    if log_dir:
        try:
            with open(os.path.join(log_dir, "last_read.txt"), "w", encoding="utf-8") as f:
                for i, lines in enumerate(passes):
                    f.write(f"--- pass {i}\n" + "".join(f"  {_row_text(row)}\n" for row in _rows(lines)))
                f.write("\n".join(extra) + f"\n{r}\n")
        except OSError:
            pass
    return r


def pdf_page_count(path: str) -> int | None:
    try:
        from pypdf import PdfReader

        return len(PdfReader(path).pages)
    except Exception:
        return None


# ---------------------------------------------------------------- path resolving

def _walk(start: str, parts: tuple[str, ...]) -> str | None:
    """Follows an OCR'd path one folder at a time, tolerating small misreads."""
    cur = start
    for i, comp in enumerate(parts):
        last = i == len(parts) - 1
        try:
            names = os.listdir(cur)
        except OSError:
            return None
        if comp in names:
            cur = os.path.join(cur, comp)
            continue
        options = [
            n for n in names
            if (n.lower().endswith(".pdf") if last else os.path.isdir(os.path.join(cur, n)))
        ]
        best = max(options, key=lambda n: _ratio(n, comp), default=None)
        if best is None or _ratio(best, comp) < 0.8:
            return None
        cur = os.path.join(cur, best)
    return cur if os.path.isfile(cur) else None


def _scan(roots: list[str], max_depth: int = 5):
    for root in roots:
        base = root.rstrip("\\/").count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.count(os.sep) - base >= max_depth:
                dirnames[:] = []
            for f in filenames:
                if f.lower().endswith(".pdf"):
                    yield os.path.join(dirpath, f)


def resolve_pdf(raw: str, search_roots: list[str], known_paths: list[str] = ()) -> str | None:
    """Finds the real PDF on disk that best matches an OCR'd path."""
    if not raw:
        return None
    if os.path.isfile(raw):
        return raw
    win = PureWindowsPath(raw)
    if os.path.isdir(win.anchor):
        hit = _walk(win.anchor, win.parts[1:])
        if hit:
            return hit

    def score(cand: str) -> float:
        c = PureWindowsPath(cand)
        return 0.7 * _ratio(c.name, win.name) + 0.3 * _ratio(c.parent.name, win.parent.name)

    seen, best, best_score = set(), None, 0.0
    for cand in list(known_paths) + list(_scan(search_roots)):
        if cand in seen or not os.path.isfile(cand):
            continue
        seen.add(cand)
        s = score(cand)
        if s > best_score:
            best, best_score = cand, s
    return best if best_score >= 0.75 else None


def default_roots() -> list[str]:
    roots = [Path.home() / "Desktop"]
    if os.environ.get("OneDrive"):
        roots.append(Path(os.environ["OneDrive"]) / "Desktop")
    return [str(r) for r in roots if r.is_dir()]


# ---------------------------------------------------------------- main entry

def parse(passes: list[list[Line]], search_roots: list[str] | None = None,
          known_paths: list[str] = ()) -> Reading:
    """passes: OCR results, most detailed first (see ocr_engine.read_screenshot)."""
    roots = default_roots() if search_roots is None else search_roots
    r = Reading()

    # 1. File path — take the first candidate that exists on disk, else the first seen.
    raw_paths: list[str] = []
    path_rows: list[str] = []
    for lines in passes:
        for row in _rows(lines):
            text = _row_text(row)
            m = PATH_RE.search(text)
            if m:
                raw_paths.append(_clean_path(*m.groups()))
                path_rows.append(text[m.end():])
                if r.status_box is None:
                    pdf_line = next((l for l in row if ".pdf" in l.text.lower().replace(" ", "")), row[0])
                    right = max(w.x + w.w for w in pdf_line.words)
                    h = max(pdf_line.h, 8)
                    r.status_box = (right, pdf_line.y - 0.4 * h, 40 * h, 1.8 * h)
    for raw in dict.fromkeys(raw_paths):
        hit = resolve_pdf(raw, roots, known_paths)
        if hit:
            r.path, r.path_found = hit, True
            break
    if not r.path and raw_paths:
        r.path = raw_paths[0]
    real_total = pdf_page_count(r.path) if r.path_found else None

    # 2. Page "8 / 26" — prefer the text next to the path, then anywhere else.
    candidates = []
    for text in path_rows:
        candidates += [(3, m) for m in PAGE_RE.finditer(text)]
    for lines in passes:
        for row in _rows(lines):
            candidates += [(0, m) for m in PAGE_RE.finditer(_row_text(row))]
    best = None
    for bonus, m in candidates:
        page, total = int(m.group(1)), int(m.group(2))
        if not 1 <= page <= total:
            continue
        s = bonus + (5 if real_total and total == real_total else 0)
        if best is None or s > best[0]:
            best = (s, page, total)
    if best:
        r.page, r.total = best[1], best[2]
    if real_total:
        r.total = real_total
    if r.page is None:
        r.page_box = _page_box(passes, r.total)

    # 3. Headings (topmost first) and chapter — from the whole-image pass.
    content = passes[-1] if passes else []
    for ln in sorted(content, key=lambda l: (round(l.cy / 10), l.x)):
        if PATH_RE.search(ln.text):
            continue
        for m in HEAD_RE.finditer(ln.text):
            label = f"{m.group(1).strip().capitalize()} {m.group(2)}"
            if label not in r.headings:
                r.headings.append(label)
        if not r.chapter:
            m = CHAP_RE.search(ln.text)
            if m:
                title = m.group(3).strip()
                if title.isupper():
                    title = title.title()
                r.chapter = f"Chapter {m.group(2)}" + (f": {title}" if title else "")
    return r


def suggest_student(reading: Reading, names: list[str], last_path_owner: dict[str, str]) -> str:
    """Guesses the student: same PDF as last time, else a name found in folder/file."""
    if reading.path and reading.path.lower() in last_path_owner:
        return last_path_owner[reading.path.lower()]
    hay = _norm(reading.folder + " " + reading.file)
    hits = [n for n in names if _norm(n) and all(_norm(t) in hay for t in n.split())]
    return max(hits, key=len) if hits else ""


if __name__ == "__main__":  # debug: python reader.py screenshot.png
    import sys

    from PIL import Image

    from ocr_engine import read_screenshot

    passes = read_screenshot(Image.open(sys.argv[1]))
    for i, p in enumerate(passes):
        print(f"--- pass {i}")
        for row in _rows(p):
            print("  ", _row_text(row))
    print(parse(passes))
