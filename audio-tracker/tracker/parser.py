"""Picks the listing fields out of OCR rows of a Marketplace-style screenshot.

Rules:
- A price is only accepted with a currency marker (₹, Rs, INR) or the word "Free".
  Nothing is ever guessed - anything unclear is left blank and reported as a problem.
- The title is the line(s) directly above the price.
"""
import re

PRICE_RE = re.compile(r"(?:₹|\bRs\.?|\bINR)\s*([0-9][0-9,]*)(?:\.[0-9]{1,2})?", re.I)
FREE_RE = re.compile(r"^\s*free\s*$", re.I)
# 950 | 1,250 | 12,500 | 1,25,000 (Indian) | 125,000 (western)
GOOD_NUMBER = re.compile(r"^(?:\d+|\d{1,3}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+)$")
# Looks like a price whose ₹ sign was misread, e.g. "?1,250" or "R1,250"
SUSPECT_PRICE = re.compile(r"^\s*[^\w\s]?[A-Za-z]?\s?\d{1,3}(?:,\d{2,3})+\s*$|^\s*[^\w\s]\s?\d{3,7}\s*$")
# "Listed 2 days ago in Kochi, KL", "Listed last Thursday in Kochi, KL", "Listed yesterday", "Listed in Aluva"
LISTED_IN_RE = re.compile(r"\bListed\s+in\s+(.+)", re.I)
LISTED_RE = re.compile(r"\bListed\s+(.+?)\s+in\s+(.+)", re.I)
LISTED_NOLOC_RE = re.compile(r"\bListed\s+(.+)", re.I)

STOP_HEADINGS = (
    "seller information", "seller details", "seller info", "location is approximate",
    "today's picks", "todays picks", "related listings", "similar listings", "sponsored",
    "more from this seller", "send seller a message", "report listing", "location",
)
SELLER_HEADINGS = ("seller information", "seller details", "seller info")
SELLER_SKIP = re.compile(
    r"^(see profile|seller details|seller information|joined facebook|highly rated|very responsive|"
    r"responsive|usually responds|\(\d+\)|[\d.]+\s*★|★|follow|message)", re.I)
NOISE_LINES = re.compile(r"^(see more|see less|see translation|hide translation)$", re.I)
BUTTON_WORDS = {"message", "save", "share", "send", "saved", "more", "hi, is this available?", "is this available?"}


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _strip_words(text, words):
    t = text.lower()
    for w in words:
        t = t.replace(w, " ")
    return _norm(t)


def parse_price(text):
    """Returns (price or None, problem or None, other prices on the same line)."""
    if FREE_RE.match(text):
        return 0, None, []
    matches = list(PRICE_RE.finditer(text))
    if not matches:
        return None, None, []
    values = []
    for m in matches:
        number = m.group(1).rstrip(",")
        if not GOOD_NUMBER.match(number):
            return None, f"Price unclear: OCR read '{m.group(0).strip()}'", []
        values.append(int(number.replace(",", "")))
    return values[0], None, values[1:]


def _is_price_row(text):
    if FREE_RE.match(text):
        return True
    if not PRICE_RE.search(text):
        return False
    rest = PRICE_RE.sub(" ", text)
    rest = re.sub(r"[·•|\-–—:/]", " ", rest)
    rest = _strip_words(rest, ("in stock", "negotiable", "fixed price", "price", "only", "each", "pair", "free"))
    return len(rest) <= 12


def price_candidates(rows, height):
    """Rows that look like a price whose ₹ sign was lost (e.g. '9501,250', '?1,250').

    Used only when no proper price was found, to give the line a second, closer OCR look.
    """
    out = []
    listed_y = next((r["y0"] for r in rows if LISTED_RE.search(r["text"])), 0.85 * height)
    for i, r in enumerate(rows):
        if not (0.12 * height < r["yc"] <= listed_y):
            continue
        t = r["text"]
        digits = sum(c.isdigit() for c in t)
        other = len(re.sub(r"[\d,.\s]", "", t))
        if digits >= 2 and other <= 3:
            out.append(i)
    return out


def has_price(text):
    return _is_price_row(text)


def _starts(text, prefixes):
    t = text.lower().strip()
    return any(t.startswith(p) for p in prefixes)


def parse(rows, width, height):
    out = {"title": "", "price": None, "price_raw": "", "price_note": "", "listed_ago": "",
           "location": "", "seller": "", "description": "", "condition": "", "problems": [],
           "photo_bottom": None}
    problems = out["problems"]
    body = [r for r in rows if r["yc"] > 0.035 * height]          # drop the phone status bar

    # ---- price
    price_idx = None
    for i, r in enumerate(body):
        if r["yc"] < 0.12 * height:
            continue
        if _is_price_row(r["text"]):
            price_idx = i
            break
    if price_idx is not None:
        r = body[price_idx]
        price, problem, others = parse_price(r["text"])
        out["price_raw"] = r["text"]
        if problem:
            problems.append(problem)
        else:
            out["price"] = price
            if others:
                out["price_note"] = "Other price shown on the listing (probably the old price): " + \
                    ", ".join(f"₹{v:,}" for v in others)
            if r["score"] < 0.80:
                problems.append(f"Price read with low confidence ('{r['text']}') - please check it")

    # ---- listed / location
    listed_idx = None
    for i, r in enumerate(body):
        text = r["text"]
        if not re.match(r"\s*Listed\b", text, re.I):
            continue
        listed_idx = i
        m_in, m, m_noloc = LISTED_IN_RE.search(text), LISTED_RE.search(text), LISTED_NOLOC_RE.search(text)
        if m_in:
            loc = m_in.group(1)
        elif m:
            out["listed_ago"] = _norm("Listed " + m.group(1))
            loc = m.group(2)
        else:
            out["listed_ago"] = _norm(text)
            loc = ""
        loc = _norm(loc)
        if loc.endswith(",") and i + 1 < len(body) and len(body[i + 1]["text"]) <= 25:
            loc = _norm(loc + " " + body[i + 1]["text"])
        out["location"] = loc.rstrip(".,")
        break
    if not out["location"]:
        for i, r in enumerate(body):
            if "location is approximate" in r["text"].lower():
                before = re.split(r"location is approximate", r["text"], flags=re.I)[0].strip(" ·•-")
                if before:
                    out["location"] = before
                elif i > 0:
                    out["location"] = body[i - 1]["text"].strip(" ·•-")
                break

    # ---- title: the line(s) right above the price (or above "Listed ..." if no price)
    anchor = price_idx if price_idx is not None else listed_idx
    if price_idx is None and listed_idx is not None and listed_idx > 0:
        # a price row whose ₹ was misread sits between title and "Listed"
        above = body[listed_idx - 1]["text"]
        if SUSPECT_PRICE.match(above):
            problems.append(f"Price may be '{above.strip()}' but the ₹ sign was not read clearly - please type the price")
            anchor = listed_idx - 1
    if anchor is not None:
        title_rows = []
        line_h = body[anchor]["h"]
        j = anchor - 1
        nxt = body[anchor]
        while j >= 0 and len(title_rows) < 3:
            r = body[j]
            gap = nxt["y0"] - r["y1"]
            limit = 2.0 * line_h if not title_rows else 1.2 * r["h"]
            if gap > limit or r["yc"] < 0.10 * height:
                break
            title_rows.insert(0, r)
            nxt = r
            j -= 1
        if title_rows:
            out["title"] = _norm(" ".join(r["text"] for r in title_rows))
            out["photo_bottom"] = title_rows[0]["y0"]
        else:
            out["photo_bottom"] = body[anchor]["y0"]

    # ---- condition
    for r in body:
        if r["text"].lower().startswith("condition"):
            rest = _norm(r["text"][len("condition"):]).strip(" :·-")
            if rest:
                out["condition"] = rest
            break

    # ---- description
    start = None
    for i, r in enumerate(body):
        if r["text"].strip().lower().rstrip(":") == "description":
            start = i + 1
            break
    if start is None:
        for i, r in enumerate(body):
            if r["text"].strip().lower().rstrip(":") == "details":
                start = i + 1
                break
    if start is not None:
        lines = []
        for r in body[start:]:
            t = r["text"].strip()
            low = t.lower()
            if _starts(low, STOP_HEADINGS) and len(t) <= 40:
                break
            if low.startswith("condition") or NOISE_LINES.match(t) or low in BUTTON_WORDS:
                continue
            lines.append(t)
        out["description"] = _norm(" ".join(lines))

    # ---- seller
    for i, r in enumerate(body):
        if _starts(r["text"], SELLER_HEADINGS):
            for r2 in body[i + 1:i + 6]:
                t = r2["text"].strip()
                if SELLER_SKIP.match(t) or not re.search(r"[A-Za-z]", t) or len(t) > 40:
                    continue
                out["seller"] = re.split(r"\s{2,}", t)[0]
                break
            break

    if not out["title"]:
        problems.append("Title not found")
    if out["price"] is None and not any(p.startswith(("Price", "Price may")) for p in problems):
        problems.append("Price not readable")
    if not out["location"]:
        problems.append("Location not found")
    return out
