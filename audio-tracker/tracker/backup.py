"""Dated database backup and full JSON export."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from . import db


def _stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def backup_database(settings) -> Path:
    target = settings.backups_dir / f"tracker_{_stamp()}.db"
    src = sqlite3.connect(str(settings.db_path), timeout=15)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)          # safe even while the tracker is running
    finally:
        dst.close()
        src.close()
    return target


def export_json(settings) -> Path:
    with db.connect(settings.db_path) as con:
        data = {
            "exported_at": db.now_str(),
            "items": db.list_items(con),
            "categories": db.categories(con),
            "screenshots": [dict(r) for r in con.execute("SELECT * FROM screenshots ORDER BY id")],
            "possible_duplicates": [dict(r) for r in con.execute("SELECT * FROM possible_duplicates ORDER BY id")],
        }
    target = settings.exports_dir / f"tracker_export_{_stamp()}.json"
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return target
