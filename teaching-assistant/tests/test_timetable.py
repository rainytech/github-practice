import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import timetable as tt  # noqa: E402
from storage import Store  # noqa: E402

TIMETABLE = os.environ.get("TEACHMARK_TIMETABLE")  # picture of the weekly timetable
FRI = date(2026, 9, 25)


def test_parse_time():
    assert tt.parse_time("4.3") == "16:30"
    assert tt.parse_time("8.3") == "20:30"
    assert tt.parse_time("4.45") == "16:45"
    assert tt.parse_time("7:00") == "19:00"
    assert tt.parse_time("Thomas") is None


def test_resolve_date_crosses_month():
    assert tt.resolve_date(25, "Fri", FRI) == FRI
    assert tt.resolve_date(1, "Thu", FRI) == date(2026, 10, 1)
    assert tt.resolve_date(30, "Wed", FRI) == date(2026, 9, 30)


def grid():
    items = [tt.Item(t, x, 45, 20) for t, x in (("4.3", 195), ("5.3", 316), ("6.3", 437), ("7.3", 558), ("8.3", 676))]
    rows = [("25", "Fri", {437: "Thomas", 558: "Akhil Sir", 675: "Sivani"}),
            ("27", "Sun", {316: "Renosh", 676: "Sivani"}),
            ("1", "Thu", {436: "Thomas", 555: "Mehul"})]
    for i, (d, wd, cells) in enumerate(rows):
        y = 105 + 60 * i
        items += [tt.Item(d, 20, y, 20), tt.Item(wd, 86, y, 20)]
        items += [tt.Item(n, x, y, 20) for x, n in cells.items()]
    return items


def test_parse_grid():
    e = tt.parse_items(grid(), FRI)
    assert [(x.day.day, x.start, x.name) for x in e] == [
        (25, "18:30", "Thomas"), (25, "19:30", "Akhil Sir"), (25, "20:30", "Sivani"),
        (27, "17:30", "Renosh"), (27, "20:30", "Sivani"),
        (1, "18:30", "Thomas"), (1, "19:30", "Mehul")]
    assert e[-1].day == date(2026, 10, 1)


def test_name_split_in_two_words():
    items = grid() + [tt.Item("Joel", 432, 285, 20), tt.Item("K", 480, 285, 20),
                      tt.Item("28", 20, 285, 20), tt.Item("Mon", 86, 285, 20)]
    names = [x.name for x in tt.parse_items(items, FRI) if x.day.day == 28]
    assert names == ["Joel K"]


def test_status():
    assert tt.class_status(None, None, False) == "⚪ No stop saved yet"
    assert tt.class_status(6, 9, True) == "🟢 Ready"
    assert tt.class_status(8, 10, True) == "🟠 Prepare next PDF"
    assert tt.class_status(9, 9, True) == "🔴 PDF finished"
    assert tt.class_status(None, 9, True) == "🟢 Ready"


def test_current_index():
    starts = ["18:30", "19:30", "20:30"]
    at = lambda h, m: datetime(2026, 9, 25, h, m)  # noqa: E731
    assert tt.current_index(starts, at(16, 0)) == 0   # next class
    assert tt.current_index(starts, at(19, 10)) == 0  # 18:30 class still running
    assert tt.current_index(starts, at(19, 40)) == 1
    assert tt.current_index(starts, at(21, 40)) is None


def test_class_for_screenshot():
    today = [("18:30", "Thomas"), ("19:30", "Akhil Sir"), ("20:30", "Sivani")]
    at = lambda h, m: datetime(2026, 9, 25, h, m)  # noqa: E731
    assert tt.class_for_screenshot(today, at(19, 32)) == "Thomas"      # just after Thomas ended
    assert tt.class_for_screenshot(today, at(19, 25)) == "Thomas"
    assert tt.class_for_screenshot(today, at(20, 28)) == "Akhil Sir"
    assert tt.class_for_screenshot(today, at(19, 32), {"akhil sir"}) == "Akhil Sir"  # PDF says Akhil
    assert tt.class_for_screenshot(today, at(10, 0)) is None


def test_schedule_storage(tmp_path):
    s = Store(tmp_path)
    s.add_stop("Akhil sir", r"C:\a.pdf", 21, 26, "Q 34", "", "", None)
    s.set_schedule([("2026-09-25", "19:30", "Akhil Sir"), ("2026-09-25", "18:30", "Thomas")])
    rows = s.classes_on("2026-09-25")
    assert [(r["start"], r["name"], r["page"]) for r in rows] == [("18:30", "Thomas", None), ("19:30", "Akhil sir", 21)]
    s.set_schedule([("2026-09-25", "20:30", "Sivani")])  # re-import replaces the day
    assert [r["name"] for r in s.classes_on("2026-09-25")] == ["Sivani"]


@pytest.mark.skipif(not TIMETABLE, reason="set TEACHMARK_TIMETABLE")
def test_real_timetable_picture():
    pytest.importorskip("rapidocr")
    e = tt.read_timetable(Image.open(TIMETABLE), FRI)
    got = {(x.day.isoformat(), x.start, x.name) for x in e}
    assert len(e) == 19
    assert ("2026-09-25", "18:30", "Thomas") in got
    assert ("2026-09-25", "19:30", "Akhil Sir") in got
    assert ("2026-09-27", "17:30", "Renosh") in got
    assert ("2026-10-01", "19:30", "Mehul") in got
    assert not any(x.start == "16:30" for x in e)
