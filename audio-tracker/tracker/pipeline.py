"""Processes new screenshots: hash -> date -> OCR -> fields -> match -> database."""
import logging
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from . import categories, db, matcher, ocr_reader, parser, photohash, scanner

log = logging.getLogger("tracker")

_lock = threading.Lock()
status = {"running": False, "total": 0, "done": 0, "current": "", "summary": None}


def _thumb(img, file_hash, thumbs_dir: Path):
    name = f"{file_hash[:16]}.jpg"
    target = thumbs_dir / name
    if not target.exists():
        t = img.copy()
        t.thumbnail((400, 900))
        t.save(target, "JPEG", quality=82)
    return name


def process_file(settings, path: Path, file_hash: str):
    """Process one screenshot. Returns 'new' | 'updated' | 'duplicate'."""
    try:
        with Image.open(path) as im:
            im.load()
            img = ImageOps.exif_transpose(im).convert("RGB")
            observed_at, date_source = scanner.observation_date(path, im)
    except UnidentifiedImageError:
        raise ValueError("this file is not a readable image")
    except OSError as exc:
        raise ValueError(f"the image could not be opened ({exc}). If it is still syncing it will be retried next time")

    rows = ocr_reader.read_rows(img)
    w, h = img.size
    parsed = parser.parse(rows, w, h)
    if parsed["price"] is None:
        # Second, closer look at lines that may be a price with a lost ₹ sign. A price is still
        # only accepted if this second reading clearly shows ₹ / Rs / INR - never guessed.
        for i in parser.price_candidates(rows, h):
            text, score = ocr_reader.reread_line(img, rows[i], parser.has_price)
            if text:
                rows[i] = dict(rows[i], text=text, score=score)
                parsed = parser.parse(rows, w, h)
                break
    parsed["category"] = categories.suggest_category(parsed["title"] + " " + parsed["description"][:200])
    parsed["brand_model"] = categories.suggest_brand_model(parsed["title"])
    if parsed["price_note"]:
        parsed["description"] = (parsed["description"] + "\n[" + parsed["price_note"] + "]").strip()
    if not rows:
        parsed["problems"] = ["No text could be read from this screenshot"]

    p_hash = photohash.listing_photo_hash(img, parsed.get("photo_bottom"))
    thumb = _thumb(img, file_hash, settings.thumbs_dir)
    raw_text = "\n".join(r["text"] for r in rows)

    with db.connect(settings.db_path) as con:
        shot_id = db.save_screenshot(
            con, file_hash=file_hash, path=path, observed_at=observed_at, date_source=date_source,
            state="processing", raw_text=raw_text, parsed=parsed, photo_hash=p_hash, thumb=thumb)
        shot = db.get_screenshot(con, shot_id)
        verdict, item_id, score, reasons = matcher.best_match(parsed, p_hash, db.match_candidates(con))
        if verdict == "same":
            db.apply_repeat_screenshot(con, item_id, parsed, shot)
            return "updated"
        if verdict == "possible":
            con.execute("UPDATE screenshots SET state = 'pending' WHERE id = ?", (shot_id,))
            db.add_possible_duplicate(con, shot_id, item_id, score, reasons)
            return "duplicate"
        db.create_item(con, parsed, shot)
        return "new"


def scan(settings, on_progress=None):
    """Find and process every screenshot not seen before. Never raises for a single bad file."""
    summary = {"new": 0, "updated": 0, "duplicates": 0, "skipped": 0, "errors": [], "message": ""}
    folder = settings.screenshot_folder
    if not folder.exists():
        summary["message"] = (f"The screenshot folder was not found: {folder}. "
                              "Check the path in settings.ini (and that Google Drive has finished syncing).")
        return summary
    try:
        images, unsupported = scanner.list_images(folder)
    except OSError as exc:
        summary["message"] = f"The screenshot folder could not be read: {exc}"
        return summary
    for p in unsupported:
        summary["errors"].append(f"{p.name}: HEIC photos are not supported. Set the phone to save screenshots as JPG.")

    todo = []
    with db.connect(settings.db_path) as con:
        for p in images:
            try:
                h = scanner.file_hash(p)
            except OSError as exc:
                summary["errors"].append(f"{p.name}: could not be opened ({exc.strerror or exc}).")
                continue
            row = db.get_screenshot_by_hash(con, h)
            if row is not None and row["state"] != "error":
                summary["skipped"] += 1
                continue
            if any(h == t[1] for t in todo):        # identical copy in two places
                summary["skipped"] += 1
                continue
            todo.append((p, h))

    if todo:
        try:
            ocr_reader.engine()
        except ocr_reader.OCRUnavailable as exc:
            summary["message"] = str(exc)
            return summary

    for n, (p, h) in enumerate(todo, 1):
        if on_progress:
            on_progress(n - 1, len(todo), p.name)
        try:
            result = process_file(settings, p, h)
            summary[{"new": "new", "updated": "updated", "duplicate": "duplicates"}[result]] += 1
        except Exception as exc:                    # one bad file must never stop the rest
            msg = str(exc) if isinstance(exc, ValueError) else f"unexpected problem ({exc.__class__.__name__}: {exc})"
            log.exception("Failed to process %s", p)
            summary["errors"].append(f"{p.name}: {msg}")
            try:
                with db.connect(settings.db_path) as con:
                    observed = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
                    db.save_screenshot(con, file_hash=h, path=p, observed_at=observed,
                                       date_source="file modified time", state="error", error=msg)
            except Exception:
                log.exception("Could not record the error for %s", p)
    if on_progress:
        on_progress(len(todo), len(todo), "")
    if not todo:
        summary["message"] = "No new screenshots."
    else:
        summary["message"] = (f"Processed {len(todo)} screenshot(s): {summary['new']} new item(s), "
                              f"{summary['updated']} price update(s), {summary['duplicates']} possible duplicate(s), "
                              f"{len(summary['errors'])} problem(s).")
    log.info(summary["message"])
    return summary


def start_background_scan(settings):
    """Start a scan in a background thread unless one is already running."""
    with _lock:
        if status["running"]:
            return False
        status.update(running=True, total=0, done=0, current="", summary=None)

    def progress(done, total, name):
        status.update(done=done, total=total, current=name)

    def run():
        try:
            status["summary"] = scan(settings, progress)
        except Exception as exc:
            log.exception("Scan failed")
            status["summary"] = {"new": 0, "updated": 0, "duplicates": 0, "skipped": 0, "errors": [],
                                 "message": f"The scan stopped because of an unexpected problem: {exc}. "
                                            "Details are in data\\tracker.log"}
        finally:
            status["running"] = False

    threading.Thread(target=run, daemon=True, name="scan").start()
    return True
