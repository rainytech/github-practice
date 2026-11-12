"""Decides whether a new screenshot is a listing already in the catalogue."""
import re
from difflib import SequenceMatcher

from .photohash import distance


def _clean(text):
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).split()


def similarity(a, b):
    """0..1, or None when either side is blank. Word order is ignored as well."""
    wa, wb = _clean(a), _clean(b)
    if not wa or not wb:
        return None
    plain = SequenceMatcher(None, " ".join(wa), " ".join(wb)).ratio()
    ordered = SequenceMatcher(None, " ".join(sorted(wa)), " ".join(sorted(wb))).ratio()
    return max(plain, ordered)


def compare(parsed, photo_hash, item):
    pd = distance(photo_hash, item["photo_hash"])
    ts = similarity(parsed.get("title"), item["title"])
    ss = similarity(parsed.get("seller"), item["seller"])
    seller_conflict = ss is not None and ss < 0.5

    photo_part = 0.0 if pd is None else max(0.0, 1 - pd / 32)
    score = 0.5 * photo_part + 0.35 * (ts or 0) + 0.15 * (ss if ss is not None else 0.5)

    strong = not seller_conflict and (
        (pd is not None and pd <= 6 and (ts or 0) >= 0.80)
        or (pd is not None and pd <= 2 and (ts or 0) >= 0.60)
        or (ts is not None and ts >= 0.95 and ss is not None and ss >= 0.90 and (pd is None or pd <= 12))
    )
    possible = not strong and ((pd is not None and pd <= 12) or (ts or 0) >= 0.75)

    reasons = []
    if pd is not None:
        reasons.append(f"photo difference {pd}/64")
    if ts is not None:
        reasons.append(f"title {round(ts * 100)}% alike")
    if ss is not None:
        reasons.append(f"seller {round(ss * 100)}% alike")
    verdict = "same" if strong else ("possible" if possible else "different")
    return {"verdict": verdict, "score": round(score, 3), "reasons": ", ".join(reasons)}


def best_match(parsed, photo_hash, items):
    """Returns (verdict, item_id, score, reasons). verdict: same | possible | new."""
    best = {"same": None, "possible": None}
    for item in items:
        c = compare(parsed, photo_hash, item)
        if c["verdict"] in best and (best[c["verdict"]] is None or c["score"] > best[c["verdict"]][1]["score"]):
            best[c["verdict"]] = (item["id"], c)
    for verdict in ("same", "possible"):
        if best[verdict]:
            item_id, c = best[verdict]
            return verdict, item_id, c["score"], c["reasons"]
    return "new", None, 0.0, ""
