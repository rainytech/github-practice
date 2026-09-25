"""Local SQLite storage: students and their last few stopping points."""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from PIL import Image

KEEP = 5  # stopping points kept per student
TITLES = {"sir", "madam", "mam", "maam", "miss", "mr", "mrs", "ms", "teacher", "chechi", "chettan"}


def name_key(name: str) -> str:
    """'Akhil Sir' and 'akhil' -> 'akhil': case, punctuation and titles ignored."""
    words = [w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in TITLES]
    return " ".join(words) or name.strip().lower()

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stops (
    id         INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    saved      TEXT NOT NULL,
    pdf_path   TEXT NOT NULL,
    page       INTEGER,
    total      INTEGER,
    point      TEXT,
    chapter    TEXT,
    note       TEXT,
    shot       TEXT
);
CREATE INDEX IF NOT EXISTS stops_student ON stops(student_id, saved);
CREATE TABLE IF NOT EXISTS schedule (
    day        TEXT NOT NULL,
    start      TEXT NOT NULL,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    PRIMARY KEY (day, start)
);
"""


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "TeachMark"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Store:
    def __init__(self, folder: Path | None = None):
        self.dir = Path(folder) if folder else data_dir()
        self.shots = self.dir / "shots"
        self.shots.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "teachmark.db")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(students)")}
        for col in ("phone", "book", "book_page"):  # added in v1.9
            if col not in cols:
                self.db.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        self.db.commit()

    # ---- students
    def students(self) -> list[sqlite3.Row]:
        """All students with their latest stop (if any), alphabetical."""
        return self.db.execute(
            """SELECT s.id, s.name, t.pdf_path, t.page, t.total, t.saved
               FROM students s
               LEFT JOIN stops t ON t.id = (
                   SELECT id FROM stops WHERE student_id = s.id ORDER BY saved DESC, id DESC LIMIT 1)
               ORDER BY s.name COLLATE NOCASE"""
        ).fetchall()

    def match_student(self, name: str) -> str:
        """The existing student this name means, else the name itself.
        Among look-alikes the one with the most recent stop wins."""
        key = name_key(name)
        rows = self.db.execute(
            """SELECT s.name, (SELECT MAX(saved) FROM stops WHERE student_id = s.id) AS last
               FROM students s"""
        ).fetchall()
        same = [r for r in rows if name_key(r["name"]) == key]
        if not same:
            return name.strip()
        same.sort(key=lambda r: (r["last"] or "", r["name"].lower() == name.strip().lower()), reverse=True)
        return same[0]["name"]

    def student_id(self, name: str) -> int:
        name = self.match_student(name)
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO students(name, created) VALUES (?, ?)",
                (name, datetime.now().isoformat(timespec="seconds")),
            )
        return self.db.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()[0]

    def student(self, sid: int) -> sqlite3.Row:
        return self.db.execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()

    def update_contact(self, sid: int, phone: str, book: str, book_page: str) -> None:
        with self.db:
            self.db.execute("UPDATE students SET phone = ?, book = ?, book_page = ? WHERE id = ?",
                            (phone.strip(), book.strip(), book_page.strip(), sid))

    def schedule_of(self, sid: int, from_day: str) -> list[tuple[str, str]]:
        return [tuple(r) for r in self.db.execute(
            "SELECT day, start FROM schedule WHERE student_id = ? AND day >= ? ORDER BY day, start",
            (sid, from_day))]

    def find(self, name: str) -> int | None:
        row = self.db.execute("SELECT id FROM students WHERE name = ?", (name.strip(),)).fetchone()
        return row[0] if row else None

    def rename_student(self, sid: int, name: str) -> None:
        """Renames; if another student already has that name, merges this one into it."""
        other = self.find(name)
        with self.db:
            if other is not None and other != sid:
                self.db.execute("UPDATE stops SET student_id = ? WHERE student_id = ?", (other, sid))
                self.db.execute("UPDATE schedule SET student_id = ? WHERE student_id = ?", (other, sid))
                self.db.execute("DELETE FROM students WHERE id = ?", (sid,))
            else:
                self.db.execute("UPDATE students SET name = ? WHERE id = ?", (name.strip(), sid))

    def delete_student(self, sid: int) -> None:
        for row in self.stops(sid, limit=-1):
            self._remove_shot(row["shot"])
        with self.db:
            self.db.execute("DELETE FROM students WHERE id = ?", (sid,))

    # ---- stops
    def stops(self, sid: int, limit: int = KEEP) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM stops WHERE student_id = ? ORDER BY saved DESC, id DESC LIMIT ?",
            (sid, limit),
        ).fetchall()

    def last_path_owner(self) -> dict[str, str]:
        """lower-cased PDF path -> student who most recently used it."""
        rows = self.db.execute(
            """SELECT t.pdf_path, s.name FROM stops t JOIN students s ON s.id = t.student_id
               ORDER BY t.saved, t.id"""
        ).fetchall()
        return {r["pdf_path"].lower(): r["name"] for r in rows}

    def known_paths(self) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT DISTINCT pdf_path FROM stops")]

    def add_stop(self, student: str, pdf_path: str, page: int | None, total: int | None,
                 point: str, chapter: str, note: str, image: Image.Image | None) -> None:
        sid = self.student_id(student)
        now = datetime.now()
        shot = ""
        if image is not None:
            shot = f"{sid}_{now:%Y%m%d_%H%M%S_%f}.jpg"
            img = image.convert("RGB")
            img.thumbnail((1600, 1600))
            img.save(self.shots / shot, quality=80)
        with self.db:
            self.db.execute(
                """INSERT INTO stops(student_id, saved, pdf_path, page, total, point, chapter, note, shot)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, now.isoformat(timespec="seconds"), pdf_path, page, total,
                 point, chapter, note, shot),
            )
        for old in self.db.execute(
            "SELECT id, shot FROM stops WHERE student_id = ? ORDER BY saved DESC, id DESC LIMIT -1 OFFSET ?",
            (sid, KEEP),
        ).fetchall():
            self._remove_shot(old["shot"])
            with self.db:
                self.db.execute("DELETE FROM stops WHERE id = ?", (old["id"],))

    # ---- timetable
    def set_schedule(self, entries: list[tuple[str, str, str]]) -> None:
        """entries: [(day 'YYYY-MM-DD', start 'HH:MM', student name)]; replaces those days."""
        ids = {name: self.student_id(name) for _d, _s, name in entries}
        with self.db:
            for day in {d for d, _s, _n in entries}:
                self.db.execute("DELETE FROM schedule WHERE day = ?", (day,))
            self.db.executemany("INSERT OR REPLACE INTO schedule(day, start, student_id) VALUES (?, ?, ?)",
                                [(d, s, ids[n]) for d, s, n in entries])
            # drop empty look-alikes left behind (no stops, no classes)
            self.db.execute("""DELETE FROM students WHERE id NOT IN (SELECT student_id FROM stops)
                               AND id NOT IN (SELECT student_id FROM schedule)
                               AND phone = '' AND book = ''""")

    def classes_on(self, day: str) -> list[sqlite3.Row]:
        """That day's classes with each student's latest stop."""
        return self.db.execute(
            """SELECT c.start, s.id, s.name, t.pdf_path, t.page, t.total, t.point, t.id AS stop_id
               FROM schedule c JOIN students s ON s.id = c.student_id
               LEFT JOIN stops t ON t.id = (
                   SELECT id FROM stops WHERE student_id = s.id ORDER BY saved DESC, id DESC LIMIT 1)
               WHERE c.day = ? ORDER BY c.start""",
            (day,),
        ).fetchall()

    def shot_path(self, shot: str) -> Path | None:
        p = self.shots / shot if shot else None
        return p if p and p.is_file() else None

    def _remove_shot(self, shot: str) -> None:
        p = self.shot_path(shot)
        if p:
            p.unlink(missing_ok=True)
