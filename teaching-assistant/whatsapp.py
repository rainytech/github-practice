"""One-line WhatsApp class messages, opened in the WhatsApp app ready to send."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import quote

ASSIST_PHONE = "9567902805"


def ampm(hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    return f"{h % 12 or 12}:{m:02d} {'PM' if h >= 12 else 'AM'}"


def question_label(point: str) -> str:
    """'Question 24' -> 'Question No. 24'; anything else unchanged."""
    m = re.fullmatch(r"\s*([A-Za-z]+)\s*(?:No\.?)?\s*(\d+[A-Za-z]?)\s*", point or "")
    return f"{m.group(1).capitalize()} No. {m.group(2)}" if m else (point or "").strip()


def build_message(day: date | None, start: str | None, book: str, page: str, point: str,
                  today: date | None = None) -> str:
    """Class at 5:30 PM — T.S. Grewal, Page 3.1, Question No. 24. For assistance: 9567902805."""
    today = today or date.today()
    if start and day and day != today:
        when = f"Class on {day:%a} {day.day} {day:%b} at {ampm(start)}"
    elif start:
        when = f"Class at {ampm(start)}"
    else:
        when = "Next class"
    parts = [p for p in (book.strip(), f"Page {page.strip()}" if page.strip() else "", question_label(point)) if p]
    body = f"{when} — {', '.join(parts)}" if parts else when
    return f"{body.rstrip('.')}. For assistance: {ASSIST_PHONE}."


def normalize_phone(phone: str) -> str:
    """Digits with country code; 10-digit Indian numbers get 91 in front."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return "91" + digits if len(digits) == 10 else digits


def whatsapp_url(phone: str, text: str) -> str:
    """Opens the WhatsApp app with the message typed; without a number WhatsApp asks for the chat."""
    num = normalize_phone(phone)
    return f"whatsapp://send?phone={num}&text={quote(text)}" if num else f"whatsapp://send?text={quote(text)}"


def next_class(rows: list[tuple[str, str]], now: datetime) -> tuple[date, str] | None:
    """rows: [(day 'YYYY-MM-DD', start 'HH:MM')] sorted. The class today still to come or
    running (up to an hour after start), else the next day's first class."""
    for day_s, start in rows:
        d = date.fromisoformat(day_s)
        begin = datetime.combine(d, datetime.strptime(start, "%H:%M").time())
        if (begin - now).total_seconds() > -3600:
            return d, start
    return None
