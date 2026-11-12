"""SQLite storage: items, price history, categories, screenshots, possible duplicates."""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from . import dealscore, transport

STATUSES = ["Watching", "Negotiating", "Bought", "Sold-Gone", "Rejected"]
HIDDEN_STATUSES = ["Sold-Gone", "Rejected"]

CATEGORIES = [
    "Speakers and full-range drivers",
    "Amplifier boards",
    "Power supplies and adapters",
    "Speaker cabinets and enclosures",
    "Electronic components and accessories",
]

# Fields the catalogue page may change directly (price is handled separately).
EDITABLE_TEXT = [
    "title", "brand_model", "seller", "seller_profile", "location",
    "listed_ago", "description", "condition_notes", "notes",
]
EDITABLE_PRICE = ["new_price", "target_price", "porter_fare"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id               INTEGER PRIMARY KEY,
    category_id      INTEGER REFERENCES categories(id),
    brand_model      TEXT NOT NULL DEFAULT '',
    title            TEXT NOT NULL DEFAULT '',
    seller           TEXT NOT NULL DEFAULT '',
    seller_profile   TEXT NOT NULL DEFAULT '',
    location         TEXT NOT NULL DEFAULT '',
    listed_ago       TEXT NOT NULL DEFAULT '',
    description      TEXT NOT NULL DEFAULT '',
    condition_notes  TEXT NOT NULL DEFAULT '',
    notes            TEXT NOT NULL DEFAULT '',
    new_price        INTEGER,
    target_price     INTEGER,
    status           TEXT NOT NULL DEFAULT 'Watching'
                     CHECK (status IN ('Watching','Negotiating','Bought','Sold-Gone','Rejected')),
    needs_checking   INTEGER NOT NULL DEFAULT 0,
    check_reasons    TEXT NOT NULL DEFAULT '',
    date_added       TEXT NOT NULL,
    last_checked     TEXT NOT NULL,
    screenshot_path  TEXT NOT NULL DEFAULT '',
    thumb            TEXT NOT NULL DEFAULT '',
    photo_hash       TEXT NOT NULL DEFAULT '',
    distance_km      REAL,
    vehicle          TEXT NOT NULL DEFAULT '',
    porter_fare      INTEGER
);

CREATE TABLE IF NOT EXISTS screenshots (
    id            INTEGER PRIMARY KEY,
    file_hash     TEXT UNIQUE NOT NULL,
    path          TEXT NOT NULL,
    observed_at   TEXT NOT NULL,
    date_source   TEXT NOT NULL DEFAULT '',
    processed_at  TEXT NOT NULL,
    item_id       INTEGER REFERENCES items(id),
    state         TEXT NOT NULL DEFAULT 'item',   -- item | pending | error
    error         TEXT NOT NULL DEFAULT '',
    raw_text      TEXT NOT NULL DEFAULT '',
    parsed_json   TEXT NOT NULL DEFAULT '',
    photo_hash    TEXT NOT NULL DEFAULT '',
    thumb         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS price_history (
    id             INTEGER PRIMARY KEY,
    item_id        INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    price          INTEGER NOT NULL,
    observed_at    TEXT NOT NULL,
    source         TEXT NOT NULL,                -- screenshot | manual edit
    screenshot_id  INTEGER REFERENCES screenshots(id)
);

CREATE TABLE IF NOT EXISTS possible_duplicates (
    id                 INTEGER PRIMARY KEY,
    screenshot_id      INTEGER NOT NULL REFERENCES screenshots(id),
    candidate_item_id  INTEGER NOT NULL REFERENCES items(id),
    score              REAL NOT NULL DEFAULT 0,
    reasons            TEXT NOT NULL DEFAULT '',
    created_at         TEXT NOT NULL,
    resolved           TEXT                       -- NULL | same | different
);

CREATE INDEX IF NOT EXISTS idx_history_item ON price_history(item_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_shots_item ON screenshots(item_id);
"""


class UserError(Exception):
    """A problem caused by input; the message is shown to the user as-is."""


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def connect(db_path: Path):
    con = sqlite3.connect(str(db_path), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# Columns added after the first version - added to older databases automatically.
NEW_ITEM_COLUMNS = {
    "distance_km": "REAL",
    "vehicle": "TEXT NOT NULL DEFAULT ''",
    "porter_fare": "INTEGER",
}


def init(db_path: Path) -> None:
    with connect(db_path) as con:
        con.executescript(SCHEMA)
        have = {r["name"] for r in con.execute("PRAGMA table_info(items)")}
        for col, decl in NEW_ITEM_COLUMNS.items():
            if col not in have:
                con.execute(f"ALTER TABLE items ADD COLUMN {col} {decl}")
        for name in CATEGORIES:
            con.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,))


# ---------------------------------------------------------------- helpers

def parse_rupees(value, field_label="Price", allow_blank=True):
    """Turn '₹1,250', '1250', 'Rs. 950' into an int. Blank -> None (if allowed)."""
    if value is None:
        text = ""
    else:
        text = str(value).strip()
    if text == "":
        if allow_blank:
            return None
        raise UserError(f"{field_label} cannot be blank.")
    cleaned = text.replace("₹", "").replace(",", "").replace(" ", "")
    for prefix in ("rs.", "rs", "inr"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
    if cleaned.endswith(".00"):
        cleaned = cleaned[:-3]
    if not cleaned.isdigit():
        raise UserError(f"{field_label} must be a whole number of rupees, for example 1250 (you typed '{text}').")
    amount = int(cleaned)
    if amount > 100_000_000:
        raise UserError(f"{field_label} looks too large: {text}")
    return amount


def category_id_by_name(con, name):
    if not name:
        return None
    row = con.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    return row["id"] if row else None


def categories(con):
    return [dict(r) for r in con.execute("SELECT id, name FROM categories ORDER BY id")]


# ---------------------------------------------------------------- screenshots

def get_screenshot_by_hash(con, file_hash):
    return con.execute("SELECT * FROM screenshots WHERE file_hash = ?", (file_hash,)).fetchone()


def get_screenshot(con, screenshot_id):
    return con.execute("SELECT * FROM screenshots WHERE id = ?", (screenshot_id,)).fetchone()


def save_screenshot(con, *, file_hash, path, observed_at, date_source, state,
                    error="", raw_text="", parsed=None, photo_hash="", thumb="", item_id=None):
    """Insert a screenshot row, or replace a previous failed attempt for the same file."""
    parsed_json = json.dumps(parsed, ensure_ascii=False) if parsed is not None else ""
    con.execute(
        """INSERT INTO screenshots (file_hash, path, observed_at, date_source, processed_at, item_id,
                                    state, error, raw_text, parsed_json, photo_hash, thumb)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(file_hash) DO UPDATE SET
               path=excluded.path, observed_at=excluded.observed_at, date_source=excluded.date_source,
               processed_at=excluded.processed_at, item_id=excluded.item_id, state=excluded.state,
               error=excluded.error, raw_text=excluded.raw_text, parsed_json=excluded.parsed_json,
               photo_hash=excluded.photo_hash, thumb=excluded.thumb""",
        (file_hash, str(path), observed_at, date_source, now_str(), item_id,
         state, error, raw_text, parsed_json, photo_hash, thumb),
    )
    return con.execute("SELECT id FROM screenshots WHERE file_hash = ?", (file_hash,)).fetchone()["id"]


# ---------------------------------------------------------------- items & prices

def create_item(con, parsed, shot):
    """Create a new item from a parsed screenshot. Returns the item id."""
    reasons = parsed.get("problems") or []
    cur = con.execute(
        """INSERT INTO items (category_id, brand_model, title, seller, location, listed_ago, description,
                              condition_notes, status, needs_checking, check_reasons, date_added,
                              last_checked, screenshot_path, thumb, photo_hash)
           VALUES (?,?,?,?,?,?,?,?, 'Watching', ?,?,?,?,?,?,?)""",
        (
            category_id_by_name(con, parsed.get("category")),
            parsed.get("brand_model", ""),
            parsed.get("title", ""),
            parsed.get("seller", ""),
            parsed.get("location", ""),
            parsed.get("listed_ago", ""),
            parsed.get("description", ""),
            parsed.get("condition", ""),
            1 if reasons else 0,
            "; ".join(reasons),
            shot["observed_at"],
            shot["observed_at"],
            shot["path"],
            shot["thumb"],
            shot["photo_hash"],
        ),
    )
    item_id = cur.lastrowid
    if parsed.get("price") is not None:
        add_price(con, item_id, parsed["price"], shot["observed_at"], "screenshot", shot["id"])
    con.execute("UPDATE screenshots SET item_id = ?, state = 'item' WHERE id = ?", (item_id, shot["id"]))
    return item_id


def add_price(con, item_id, price, observed_at, source, screenshot_id=None):
    """Add a price-history line unless the price is the same as the one just before it.

    Always moves 'last checked' forward. Returns True if a new line was added.
    """
    prev = con.execute(
        """SELECT price FROM price_history WHERE item_id = ? AND observed_at <= ?
           ORDER BY observed_at DESC, id DESC LIMIT 1""",
        (item_id, observed_at),
    ).fetchone()
    added = False
    if prev is None or prev["price"] != price:
        con.execute(
            "INSERT INTO price_history (item_id, price, observed_at, source, screenshot_id) VALUES (?,?,?,?,?)",
            (item_id, price, observed_at, source, screenshot_id),
        )
        added = True
    touch_last_checked(con, item_id, observed_at)
    return added


def touch_last_checked(con, item_id, when):
    con.execute("UPDATE items SET last_checked = MAX(last_checked, ?) WHERE id = ?", (when, item_id))


def apply_repeat_screenshot(con, item_id, parsed, shot):
    """A new screenshot of a listing already in the catalogue."""
    item = con.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        raise UserError("That item no longer exists.")
    # Fill only blank fields - never overwrite something you typed or corrected.
    fill = {}
    for field, key in (("title", "title"), ("seller", "seller"), ("location", "location"),
                       ("description", "description"), ("condition_notes", "condition"),
                       ("brand_model", "brand_model")):
        if not item[field] and parsed.get(key):
            fill[field] = parsed[key]
    if parsed.get("listed_ago"):
        fill["listed_ago"] = parsed["listed_ago"]          # this one naturally changes over time
    if shot["observed_at"] >= item["last_checked"]:
        fill["screenshot_path"] = shot["path"]
        fill["thumb"] = shot["thumb"]
    if fill:
        sets = ", ".join(f"{k} = ?" for k in fill)
        con.execute(f"UPDATE items SET {sets} WHERE id = ?", (*fill.values(), item_id))

    if parsed.get("price") is not None:
        add_price(con, item_id, parsed["price"], shot["observed_at"], "screenshot", shot["id"])
    else:
        touch_last_checked(con, item_id, shot["observed_at"])
        flag(con, item_id, "Price on the latest screenshot was not readable")
    con.execute("UPDATE screenshots SET item_id = ?, state = 'item' WHERE id = ?", (item_id, shot["id"]))


def apply_extra_page(con, item_id, parsed, shot):
    """A scrolled-down screenshot of a listing (no title, no price): fill in its details only."""
    item = con.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    fill = {}
    for field, key in (("seller", "seller"), ("location", "location"), ("condition_notes", "condition"),
                       ("listed_ago", "listed_ago")):
        if not item[field] and parsed.get(key):
            fill[field] = parsed[key]
    desc = parsed.get("description", "")
    if desc and desc not in (item["description"] or ""):
        fill["description"] = ((item["description"] or "") + "\n" + desc).strip()
    reasons = [r for r in (item["check_reasons"] or "").split("; ") if r]
    if fill.get("location"):
        reasons = [r for r in reasons if r != "Location not found"]
    fill["check_reasons"] = "; ".join(reasons)
    fill["needs_checking"] = 1 if reasons else 0
    cols = ", ".join(f"{k} = ?" for k in fill)
    con.execute(f"UPDATE items SET {cols} WHERE id = ?", (*fill.values(), item_id))
    touch_last_checked(con, item_id, shot["observed_at"])
    con.execute("UPDATE screenshots SET item_id = ?, state = 'item' WHERE id = ?", (item_id, shot["id"]))


def _letters(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def find_listing_for_extra_page(con, parsed, observed_at, minutes=15):
    """Which item does a scrolled-down screenshot belong to? By the name in the top bar, else by time."""
    head = _letters(parsed.get("header_title"))
    if len(head) >= 8:
        for r in con.execute("SELECT id, title FROM items ORDER BY last_checked DESC"):
            t = _letters(r["title"])
            if t and (t.startswith(head) or head.startswith(t[:max(8, len(head))])):
                return r["id"]
    row = con.execute(
        """SELECT item_id, observed_at FROM screenshots
           WHERE state = 'item' AND item_id IS NOT NULL AND observed_at <= ?
           ORDER BY observed_at DESC LIMIT 1""", (observed_at,)).fetchone()
    if row:
        gap = datetime.strptime(observed_at, "%Y-%m-%d %H:%M:%S") - \
            datetime.strptime(row["observed_at"], "%Y-%m-%d %H:%M:%S")
        if gap.total_seconds() <= minutes * 60:
            return row["item_id"]
    return None


def flag(con, item_id, reason):
    row = con.execute("SELECT check_reasons FROM items WHERE id = ?", (item_id,)).fetchone()
    reasons = [r for r in (row["check_reasons"] or "").split("; ") if r]
    if reason not in reasons:
        reasons.append(reason)
    con.execute("UPDATE items SET needs_checking = 1, check_reasons = ? WHERE id = ?",
                ("; ".join(reasons), item_id))


def update_item(con, item_id, changes: dict):
    """Apply edits from the catalogue page. Raises UserError with a plain message on bad input."""
    item = con.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        raise UserError(f"Item {item_id} was not found. Please reload the page.")
    sets = {}
    for key, value in changes.items():
        if key in EDITABLE_TEXT:
            sets[key] = ("" if value is None else str(value)).strip()
        elif key in EDITABLE_PRICE:
            label = {"target_price": "Target price", "new_price": "New price", "porter_fare": "Porter fare"}[key]
            sets[key] = parse_rupees(value, label)
        elif key == "distance_km":
            text = ("" if value is None else str(value)).strip().lower().replace("km", "").strip()
            if text == "":
                sets[key] = None
            else:
                try:
                    km = float(text)
                except ValueError:
                    raise UserError(f"Distance must be a number of km, for example 12 (you typed '{value}').")
                if not 0 < km < 2000:
                    raise UserError(f"Distance looks wrong: {value} km.")
                sets[key] = round(km, 1)
        elif key == "vehicle":
            if value not in ("", None) and value not in transport.VEHICLES:
                raise UserError(f"Unknown vehicle '{value}'.")
            sets[key] = value or ""
        elif key == "status":
            if value not in STATUSES:
                raise UserError(f"Unknown status '{value}'.")
            sets["status"] = value
        elif key == "category":
            if value in ("", None):
                sets["category_id"] = None
            else:
                cid = category_id_by_name(con, value)
                if cid is None:
                    raise UserError(f"Unknown category '{value}'.")
                sets["category_id"] = cid
        elif key == "needs_checking":
            on = bool(value)
            sets["needs_checking"] = 1 if on else 0
            if not on:
                sets["check_reasons"] = ""
        elif key == "price":
            price = parse_rupees(value, "Current price", allow_blank=False)
            add_price(con, item_id, price, now_str(), "manual edit")
            touch_last_checked(con, item_id, now_str())
        else:
            raise UserError(f"The field '{key}' cannot be edited.")
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        con.execute(f"UPDATE items SET {cols} WHERE id = ?", (*sets.values(), item_id))


# ---------------------------------------------------------------- reading for the page

def _history(con, item_id):
    return [dict(r) for r in con.execute(
        """SELECT h.price, h.observed_at, h.source, h.screenshot_id, s.path AS screenshot_path
           FROM price_history h LEFT JOIN screenshots s ON s.id = h.screenshot_id
           WHERE h.item_id = ? ORDER BY h.observed_at, h.id""",
        (item_id,),
    )]


def fare_formulas(con):
    """Fare formulas learned from settings.ini fares plus every Porter fare typed on a card."""
    user = []
    for r in con.execute("SELECT * FROM items WHERE porter_fare IS NOT NULL"):
        d = dict(r)
        cat = con.execute("SELECT name FROM categories WHERE id = ?", (d["category_id"],)).fetchone() \
            if d["category_id"] else None
        d["category"] = cat["name"] if cat else ""
        est = transport.estimate(dict(d, porter_fare=None), transport.formulas([]))
        if est["km"] is not None:
            user.append((est["vehicle"], est["km"], d["porter_fare"]))
    return transport.formulas(user)


def item_dict(con, row, fx=None):
    item = dict(row)
    cat = con.execute("SELECT name FROM categories WHERE id = ?", (row["category_id"],)).fetchone() \
        if row["category_id"] else None
    item["category"] = cat["name"] if cat else ""
    hist = _history(con, row["id"])
    item["history"] = hist
    item["current_price"] = hist[-1]["price"] if hist else None
    item["first_price"] = hist[0]["price"] if hist else None
    item["previous_price"] = hist[-2]["price"] if len(hist) >= 2 else None
    cur, first, prev = item["current_price"], item["first_price"], item["previous_price"]
    item["drop_amount"] = (first - cur) if (cur is not None and first is not None) else None
    item["drop_pct"] = round(100.0 * (first - cur) / first, 1) if (cur is not None and first) else None
    item["price_dropped"] = bool(prev is not None and cur is not None and cur < prev)
    tr = transport.estimate(item, fx or fare_formulas(con))
    item["transport"] = tr
    item["total_cost"] = (cur + tr["cost"]) if (cur is not None and tr["cost"] is not None) else None
    pay = item["total_cost"] if item["total_cost"] is not None else cur
    item["target_reached"] = bool(item["target_price"] is not None and pay is not None and pay <= item["target_price"])
    item["deal_score"], item["deal_reasons"] = dealscore.score(cur, first, item["target_price"], item["new_price"],
                                                              total=item["total_cost"])
    item["screenshots"] = [dict(r) for r in con.execute(
        "SELECT id, path, observed_at, raw_text, thumb FROM screenshots WHERE item_id = ? ORDER BY observed_at",
        (row["id"],),
    )]
    latest = item["screenshots"][-1]["id"] if item["screenshots"] else None
    item["latest_screenshot_id"] = latest
    return item


def list_items(con):
    fx = fare_formulas(con)
    return [item_dict(con, r, fx) for r in con.execute("SELECT * FROM items ORDER BY id")]


def get_item(con, item_id):
    row = con.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return item_dict(con, row) if row else None


def pending_duplicates(con):
    out = []
    for r in con.execute(
        """SELECT d.id, d.score, d.reasons, d.candidate_item_id, d.screenshot_id,
                  s.thumb, s.observed_at, s.parsed_json, s.path
           FROM possible_duplicates d JOIN screenshots s ON s.id = d.screenshot_id
           WHERE d.resolved IS NULL ORDER BY d.id"""
    ):
        d = dict(r)
        d["parsed"] = json.loads(d.pop("parsed_json") or "{}")
        d["candidate"] = get_item(con, d["candidate_item_id"])
        out.append(d)
    return out


def resolve_duplicate(con, dup_id, decision):
    d = con.execute("SELECT * FROM possible_duplicates WHERE id = ?", (dup_id,)).fetchone()
    if d is None or d["resolved"] is not None:
        raise UserError("That possible duplicate was already dealt with. Please reload the page.")
    shot = get_screenshot(con, d["screenshot_id"])
    parsed = json.loads(shot["parsed_json"] or "{}")
    if decision == "same":
        apply_repeat_screenshot(con, d["candidate_item_id"], parsed, shot)
        item_id = d["candidate_item_id"]
    elif decision == "different":
        item_id = create_item(con, parsed, shot)
    else:
        raise UserError("Unknown choice.")
    con.execute("UPDATE possible_duplicates SET resolved = ? WHERE id = ?", (decision, dup_id))
    return item_id


def match_candidates(con):
    """Light rows used by the matcher."""
    return [dict(r) for r in con.execute("SELECT id, title, seller, photo_hash FROM items")]


def add_possible_duplicate(con, screenshot_id, item_id, score, reasons):
    con.execute(
        """INSERT INTO possible_duplicates (screenshot_id, candidate_item_id, score, reasons, created_at)
           VALUES (?,?,?,?,?)""",
        (screenshot_id, item_id, score, reasons, now_str()),
    )


def counts(con):
    r = con.execute(
        """SELECT COUNT(*) AS items,
                  SUM(CASE WHEN status IN ('Sold-Gone','Rejected') THEN 1 ELSE 0 END) AS hidden,
                  SUM(needs_checking) AS needs_checking
           FROM items"""
    ).fetchone()
    shots = con.execute("SELECT COUNT(*) AS n FROM screenshots").fetchone()["n"]
    errors = [dict(e) for e in con.execute(
        "SELECT path, error, processed_at FROM screenshots WHERE state = 'error' ORDER BY processed_at DESC"
    )]
    return {"items": r["items"] or 0, "hidden": r["hidden"] or 0,
            "needs_checking": r["needs_checking"] or 0, "screenshots": shots, "errors": errors}
