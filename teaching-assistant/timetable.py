"""Weekly timetable: read it from a picture, decide today's classes and their status.

The picture is a grid: a header row of times ("4.3" = 4:30 PM) and one row per
day starting with the date and weekday ("25 Fri"), with student names in the
time columns.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from PIL import Image

CLASS_MINUTES = 60
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TIME_RE = re.compile(r"^(\d{1,2})\s*[.:]\s*(\d{1,2})$")
PREPARE_AT = 0.8  # share of the PDF done when "Prepare next PDF" shows


@dataclass
class Item:
    text: str
    x: float  # left edge
    cy: float  # vertical centre
    h: float


@dataclass
class Entry:
    day: date
    start: str  # "18:30"
    name: str


def parse_time(text: str) -> str | None:
    """'4.3' -> '16:30', '4.30' -> '16:30', '7:45' -> '19:45'. Hours 1–11 are PM."""
    m = TIME_RE.match(text.strip())
    if not m:
        return None
    hour, mins = int(m.group(1)), m.group(2)
    minute = int(mins) * 10 if len(mins) == 1 else int(mins)
    if not (1 <= hour <= 23 and 0 <= minute < 60):
        return None
    if hour < 12:
        hour += 12
    return f"{hour:02d}:{minute:02d}"


def resolve_date(day_num: int, weekday: str | None, today: date) -> date | None:
    """Nearest date to today (a week back to six weeks ahead) with this day number and weekday."""
    wd = WEEKDAYS.index(weekday[:3].lower()) if weekday and weekday[:3].lower() in WEEKDAYS else None
    for delta in sorted(range(-7, 43), key=abs):
        d = today + timedelta(days=delta)
        if d.day == day_num and (wd is None or d.weekday() == wd):
            return d
    return None


def _rows(items: list[Item]) -> list[list[Item]]:
    rows: list[list[Item]] = []
    for it in sorted(items, key=lambda i: i.cy):
        if rows and abs(rows[-1][0].cy - it.cy) < max(rows[-1][0].h, it.h) * 0.6:
            rows[-1].append(it)
        else:
            rows.append([it])
    return [sorted(r, key=lambda i: i.x) for r in rows]


def parse_items(items: list[Item], today: date) -> list[Entry]:
    rows = _rows(items)
    # header: the row with the most time-like cells
    header, columns = None, []
    for row in rows:
        cols = [(it.x, parse_time(it.text)) for it in row if parse_time(it.text)]
        if len(cols) > len(columns):
            header, columns = row, cols
    if len(columns) < 1:
        return []
    col_width = min((b[0] - a[0] for a, b in zip(columns, columns[1:])), default=200)

    entries: list[Entry] = []
    for row in rows:
        if row is header or not row[0].text.strip().isdigit():
            continue
        day_num = int(row[0].text.strip())
        weekday = row[1].text if len(row) > 1 and row[1].text[:3].lower() in WEEKDAYS else None
        d = resolve_date(day_num, weekday, today)
        if d is None:
            continue
        cells: dict[str, list[str]] = {}
        for it in row[1 + (weekday is not None):]:
            x, start = min(columns, key=lambda c: abs(c[0] - it.x))
            if abs(x - it.x) <= col_width * 0.6:
                cells.setdefault(start, []).append(it.text.strip())
        for start, words in cells.items():
            name = " ".join(words).strip()
            if name and not parse_time(name):
                entries.append(Entry(d, start, name))
    return sorted(entries, key=lambda e: (e.day, e.start))


def read_timetable(img: Image.Image, today: date | None = None) -> list[Entry]:
    from ocr_engine import page_items

    return parse_items([Item(*t) for t in page_items(img)], today or date.today())


def class_status(page: int | None, total: int | None, has_stop: bool) -> str:
    if not has_stop:
        return "⚪ No stop saved yet"
    if page and total:
        if page >= total:
            return "🔴 PDF finished"
        if page / total >= PREPARE_AT:
            return "🟠 Prepare next PDF"
    return "🟢 Ready"


def current_index(starts: list[str], now: datetime) -> int | None:
    """Row to highlight: the class running now, else the next one today."""
    for i, s in enumerate(starts):
        begin = datetime.combine(now.date(), datetime.strptime(s, "%H:%M").time())
        if now < begin + timedelta(minutes=CLASS_MINUTES):
            return i
    return None


def class_for_screenshot(classes: list[tuple[str, str]], taken: datetime,
                         preferred: set[str] = frozenset()) -> str | None:
    """Which student a screenshot belongs to. classes: [(start 'HH:MM', name)] of that day.

    Screenshots are taken around the end of a class, so the class whose end is
    nearest wins — unless the PDF itself points to one of the nearby classes.
    """
    near = []
    for start, name in classes:
        begin = datetime.combine(taken.date(), datetime.strptime(start, "%H:%M").time())
        if begin - timedelta(minutes=15) <= taken <= begin + timedelta(minutes=2 * CLASS_MINUTES):
            end = begin + timedelta(minutes=CLASS_MINUTES)
            near.append((abs((taken - end).total_seconds()), name))
    for _gap, name in sorted(near):
        if name.lower() in preferred:
            return name
    return min(near)[1] if near else None
