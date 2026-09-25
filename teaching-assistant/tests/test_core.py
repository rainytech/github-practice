import os
import sys
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reader  # noqa: E402
from ocr_engine import Line, Word  # noqa: E402
from storage import KEEP, Store  # noqa: E402

SAMPLE = os.environ.get("TEACHMARK_SAMPLE")  # optional real screenshot for an end-to-end check


def line(text, y, x=0, h=20):
    words, cx = [], x
    for t in text.split():
        words.append(Word(t, cx, y, len(t) * 9, h))
        cx += len(t) * 9 + 6
    return Line(words)


def make_pdf(path: Path, pages: int):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(100, 100)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        w.write(f)


@pytest.fixture
def desktop(tmp_path):
    make_pdf(tmp_path / "23 sept akhil sir" / "combined_akhil_sir_document Compressed.pdf", 26)
    make_pdf(tmp_path / "other" / "Partnership Ch-3.pdf", 10)
    return tmp_path


# Lines as they come from the Icecream PDF Editor screenshot (with typical OCR slips).
ICECREAM = [
    line("Icecream PDF Editor 3.32 - PRO", 10),
    line("CHAPTER 8: ACCOUNTING FOR SHARE CAPITAL", 400),
    line("Illustration 9", 470), line("OVER SUBSCRIPTION", 470, x=600),
    line("Kamal & Co. Ltd., issued for public subscription 40,000 equity shares", 520),
    line("Illustration 10", 900),
    line(r"C.\Users\Admin\Desktop\23 sept akhil sir\combined_akhil_sir_ document Compressed.pdf", 980),
    line("8", 980, x=940), line("/ 26", 980, x=975),
    line("6:05 AM 25/09/2026", 1040, x=1700),
]


def test_parse_icecream(desktop):
    r = reader.parse([ICECREAM], search_roots=[str(desktop)])
    assert r.path_found
    assert r.file == "combined_akhil_sir_document Compressed.pdf"
    assert r.folder == "23 sept akhil sir"
    assert (r.page, r.total) == (8, 26)
    assert r.headings == ["Illustration 9", "Illustration 10"]
    assert r.chapter == "Chapter 8: Accounting For Share Capital"


def test_page_not_confused_by_dates():
    r = reader.parse([[line("Today 25/09/2026", 10)]], search_roots=[])
    assert r.page is None


def test_page_of_style_and_unknown_file():
    r = reader.parse([[line(r"D:\Notes\Tax.pdf", 10), line("Page 3 of 12", 10, x=400)]], search_roots=[])
    assert r.path == r"D:\Notes\Tax.pdf" and not r.path_found
    assert (r.page, r.total) == (3, 12)


def test_real_total_overrides_misread(desktop):
    lines = [line(r"C:\x\23 sept akhil sir\combined_akhil_sir_document Compressed.pdf 8 / 28", 10)]
    r = reader.parse([lines], search_roots=[str(desktop)])
    assert (r.page, r.total) == (8, 26)


def test_walk_tolerates_misreads(desktop):
    hit = reader._walk(str(desktop), ("23 sept akhi1 sir", "combined_akhil_sir_ document Compressed.pdf"))
    assert hit and hit.endswith("combined_akhil_sir_document Compressed.pdf")


def test_suggest_student():
    r = reader.Reading(path=r"C:\D\23 sept akhil sir\x.pdf")
    assert reader.suggest_student(r, ["Anu", "Akhil Sir", "Akhil"], {}) == "Akhil Sir"
    assert reader.suggest_student(r, ["Anu"], {r.path.lower(): "Anu"}) == "Anu"
    assert reader.suggest_student(r, ["Anu"], {}) == ""


def test_store_keeps_last_five(tmp_path):
    s = Store(tmp_path)
    img = Image.new("RGB", (50, 50), "white")
    for p in range(1, 8):
        s.add_stop("Akhil sir", r"C:\a.pdf", p, 26, f"Illustration {p}", "", "", img)
    sid = s.student_id("akhil SIR")  # case-insensitive
    stops = s.stops(sid)
    assert len(stops) == KEEP and stops[0]["page"] == 7
    assert len(list((tmp_path / "shots").iterdir())) == KEEP
    assert s.students()[0]["page"] == 7
    assert s.last_path_owner() == {r"c:\a.pdf": "Akhil sir"}
    s.delete_student(sid)
    assert s.students() == [] and not list((tmp_path / "shots").iterdir())


@pytest.mark.skipif(not SAMPLE, reason="set TEACHMARK_SAMPLE to a screenshot to run")
def test_real_screenshot(desktop):
    from ocr_engine import read_screenshot

    r = reader.parse(read_screenshot(Image.open(SAMPLE)), search_roots=[str(desktop)])
    assert r.path_found and (r.page, r.total) == (8, 26)
    assert r.headings[0] == "Illustration 9"
