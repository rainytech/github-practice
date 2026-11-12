"""Offline deal score out of 10 - a fixed rule, not AI.

Uses only: asking price vs your target price, asking price vs the new price,
and how far the price has dropped since your first screenshot.
"""


def _indian(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])


def score(current, first, target, new_price, total=None):
    """Return (score 1-10 or None, list of plain-English reasons).

    Target and new-price comparisons use the total cost (price + Porter transport) when known.
    """
    if current is None:
        return None, ["No price yet."]
    if target is None and not new_price:
        return None, ["Set a target price or the new price to get a deal score."]

    asking = current
    points = 5.0
    reasons = []
    if total is not None:
        reasons.append(f"Compared using total cost {_indian(total)} (price + transport)")
        current = total

    if target is not None:
        if current <= target * 0.85:
            points += 4
            reasons.append(f"Well below your target {_indian(target)} (+4)")
        elif current <= target:
            points += 3
            reasons.append(f"At or below your target {_indian(target)} (+3)")
        elif current <= target * 1.10:
            points += 1
            reasons.append(f"Within 10% of your target {_indian(target)} (+1)")
        elif current <= target * 1.30:
            points -= 1
            reasons.append(f"10-30% above your target {_indian(target)} (-1)")
        else:
            points -= 2.5
            reasons.append(f"More than 30% above your target {_indian(target)} (-2.5)")

    if new_price:
        saving = 1 - current / new_price
        pct = round(saving * 100)
        if saving >= 0.60:
            points += 2
            reasons.append(f"{pct}% cheaper than new ({_indian(new_price)}) (+2)")
        elif saving >= 0.40:
            points += 1
            reasons.append(f"{pct}% cheaper than new ({_indian(new_price)}) (+1)")
        elif saving >= 0.20:
            reasons.append(f"{pct}% cheaper than new ({_indian(new_price)}) (0)")
        elif saving >= 0:
            points -= 1.5
            reasons.append(f"Only {pct}% cheaper than new ({_indian(new_price)}) (-1.5)")
        else:
            points -= 3
            reasons.append(f"Costs more than new ({_indian(new_price)}) (-3)")

    if first and asking < first:
        drop = 1 - asking / first
        if drop >= 0.20:
            points += 1
            reasons.append(f"Price dropped {round(drop * 100)}% since first seen (+1)")
        elif drop >= 0.10:
            points += 0.5
            reasons.append(f"Price dropped {round(drop * 100)}% since first seen (+0.5)")

    final = max(1, min(10, int(points + 0.5)))
    return final, reasons
