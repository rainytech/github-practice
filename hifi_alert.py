#!/usr/bin/env python3
"""
hifi_alert.py — Mini HiFi deal watcher for Android (Termux).

Reads YOUR OWN phone notifications from the Facebook / OLX apps
(saved-search alerts), keeps only real matches, and raises a loud alert.
No scraping, no login, no website access.

Setup (once):
  1. Install Termux + Termux:API from F-Droid.
  2. In Termux:  pkg install python termux-api
  3. Phone Settings > Notification access > enable Termux:API
  4. Phone Settings > Battery > Termux > Unrestricted
  5. FB Marketplace + OLX: saved searches with alerts ON
     (Tripunithura, 25 km, max Rs 5000)
Run:
  python hifi_alert.py
Test the filter without a phone:
  python hifi_alert.py --test "Sony music system for sale Rs 4,500 Vyttila"
"""

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

# ─────────────── SETTINGS — edit freely ───────────────
MAX_PRICE = 5000
CHECK_EVERY = 120          # seconds

APPS = {
    "com.facebook.katana": ("Facebook", "https://www.facebook.com/marketplace/"),
    "com.facebook.lite":   ("FB Lite",  "https://www.facebook.com/marketplace/"),
    "com.olx.southasia":   ("OLX",      "https://www.olx.in/"),
}

KEYWORDS = [
    "hifi", "hi-fi", "hi fi", "mini system", "micro system", "music system",
    "home theatre", "home theater", "stereo system", "audio system",
    "mini component", "hi-fi system",
]
BRANDS = ["sony", "philips", "panasonic", "lg", "onkyo", "denon", "yamaha",
          "samsung", "jbl", "marantz", "kenwood", "aiwa", "pioneer", "bose"]

EXCLUDE = ["wanted", "looking for", "need", "repair", "spares", "spare",
           "service", "car", "bike", "buying"]

PLACES = ["tripunithura", "thrippunithura", "ernakulam", "kochi", "cochin",
          "vyttila", "maradu", "kadavanthra", "kakkanad", "edappally",
          "palarivattom", "kaloor", "thevara", "fort kochi", "mattancherry",
          "kalamassery", "chottanikkara", "mulanthuruthy", "udayamperoor",
          "irumpanam", "eroor", "kumbalam", "aroor", "piravom", "aluva",
          "panangad", "vaduthala", "elamakkara", "kolenchery"]

FAR_PLACES = ["thrissur", "kottayam", "alappuzha", "alleppey", "angamaly",
              "muvattupuzha", "perumbavoor", "kothamangalam", "chalakudy",
              "idukki", "palakkad", "kozhikode", "calicut", "malappuram",
              "kannur", "trivandrum", "thiruvananthapuram", "kollam",
              "pathanamthitta", "cherthala", "bangalore", "chennai"]
# ──────────────────────────────────────────────────────

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(HERE, "seen.json")
LOG_FILE = os.path.join(HERE, "matches.csv")

BRAND_RE = re.compile(
    r"\b(" + "|".join(BRANDS) + r")\b.*\b(system|hifi|hi-fi|stereo|audio)\b")
PRICE_RES = [
    re.compile(r"(?:₹|\brs\.?|\binr)\s*([\d,]+(?:\.\d+)?)\s*(k\b)?"),
    re.compile(r"\b([\d,]+(?:\.\d+)?)\s*(k)\b"),
    re.compile(r"\b([\d,]+)\s*/-"),
]


def has_word(text, words):
    return next((w for w in words if re.search(r"\b" + re.escape(w) + r"\b", text)), None)


def find_price(text):
    for rx in PRICE_RES:
        m = rx.search(text)
        if m:
            try:
                value = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            if len(m.groups()) > 1 and m.group(2):
                value *= 1000
            return int(value)
    return None


def check(text):
    """Return (is_match, price_label, place_label)."""
    t = text.lower()
    if not (has_word(t, KEYWORDS) or BRAND_RE.search(t)):
        return False, "", ""
    if has_word(t, EXCLUDE) or has_word(t, FAR_PLACES):
        return False, "", ""

    price = find_price(t)
    if price is None or price < 100:            # ₹0 / ₹1 placeholder prices
        price_label = "price not stated"
    elif price > MAX_PRICE:
        return False, "", ""
    else:
        price_label = f"₹{price:,}"

    place = has_word(t, PLACES)
    place_label = place.title() if place else "location not stated"
    return True, price_label, place_label


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen[-2000:], f)


def log_match(app, price, place, text):
    new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "app", "price", "place", "text"])
        w.writerow([datetime.now().strftime("%d-%m-%Y %H:%M"), app, price, place, text])


def alert(app, url, price, place, text, n):
    subprocess.run([
        "termux-notification",
        "--id", f"hifi{n}",
        "--title", f"🎵 {price} · {place} · {app}",
        "--content", text[:300],
        "--priority", "high",
        "--sound",
        "--vibrate", "500,300,500",
        "--action", f"termux-open-url {url}",
    ], check=False)


def read_notifications():
    out = subprocess.run(["termux-notification-list"],
                         capture_output=True, text=True, timeout=30).stdout
    return json.loads(out or "[]")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--test":
        print(check(" ".join(sys.argv[2:])))
        return

    subprocess.run(["termux-wake-lock"], check=False)
    seen = load_seen()
    count = 0
    print(f"Watching {', '.join(a for a, _ in APPS.values())} "
          f"every {CHECK_EVERY}s. Ctrl+C to stop.")

    while True:
        try:
            for n in read_notifications():
                pkg = n.get("packageName", "")
                if pkg not in APPS:
                    continue
                text = f"{n.get('title', '')} {n.get('content', '')}".strip()
                key = hashlib.md5(f"{pkg}|{text}".encode()).hexdigest()
                if key in seen:
                    continue
                seen.append(key)

                ok, price, place = check(text)
                if ok:
                    app, url = APPS[pkg]
                    count += 1
                    alert(app, url, price, place, text, count)
                    log_match(app, price, place, text)
                    print(f"[{datetime.now():%H:%M}] MATCH {price} | {place} | {text}")
            save_seen(seen)
        except Exception as e:
            print(f"[{datetime.now():%H:%M}] error: {e}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
