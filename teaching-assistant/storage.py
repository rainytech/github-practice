"""Local SQLite storage: students and their last few stopping points."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from PIL import Image

KEEP = 5  # stopping points kept per student

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

    def student_id(self, name: str) -> int:
        name = name.strip()
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO students(name, created) VALUES (?, ?)",
                (name, datetime.now().isoformat(timespec="seconds")),
            )
        return self.db.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()[0]

    def rename_student(self, sid: int, name: str) -> None:
        with self.db:
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
