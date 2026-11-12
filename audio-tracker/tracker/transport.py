"""Porter transport estimate: distance from home -> vehicle -> fare, learned from your real fares.

Fare formula per vehicle = base + rate per km, fitted (least squares) to real fares:
- the fares listed in settings.ini (two_wheeler_fares), and
- every "Porter fare" you type on an item card.
A vehicle with no real fares yet uses the two-wheeler formula x a rough multiplier,
and is labelled as a rough estimate.
"""
import math
import re

from . import places

VEHICLES = {"two_wheeler": "Two-wheeler", "three_wheeler": "Three-wheeler", "mini_truck": "Mini truck (Tata Ace)"}

# Used only if settings.ini has no [transport] section (same values as the shipped settings).
DEFAULTS = {
    "home": "Puthiyakavu, Tripunithura",
    "road_factor": 1.3,
    "two_wheeler_fares": "Tripunithura 60; Thevara 126; Aluva 300",
    "three_wheeler_multiplier": 2.5,
    "mini_truck_multiplier": 3.5,
    "loading_charge": 0,
}
FALLBACK_TWO_WHEELER = (49.0, 10.0)      # base, per km - fitted from the fares above


class Config:
    def __init__(self):
        self.home_name = DEFAULTS["home"]
        self.home = places.PLACES["puthiyakavu"]
        self.road_factor = DEFAULTS["road_factor"]
        self.multipliers = {"two_wheeler": 1.0, "three_wheeler": DEFAULTS["three_wheeler_multiplier"],
                            "mini_truck": DEFAULTS["mini_truck_multiplier"]}
        self.loading_charge = DEFAULTS["loading_charge"]
        self.settings_fares = []         # (km, fare) for two-wheeler
        self.warnings = []


CONFIG = Config()


def _num(value, default, label, warnings):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        warnings.append(f"settings.ini [transport]: '{label}' should be a number (found '{value}'); using {default}.")
        return default


def configure(section):
    """section: the [transport] part of settings.ini (a mapping), or None."""
    cfg = Config()
    sec = dict(section) if section else {}
    w = cfg.warnings
    cfg.home_name = (sec.get("home") or DEFAULTS["home"]).strip()
    if sec.get("home_lat") and sec.get("home_lon"):
        cfg.home = (_num(sec["home_lat"], cfg.home[0], "home_lat", w), _num(sec["home_lon"], cfg.home[1], "home_lon", w))
    else:
        key, pos = places.find(cfg.home_name)
        if pos:
            cfg.home = pos
        else:
            w.append(f"Home '{cfg.home_name}' is not in the place list; using Puthiyakavu. "
                     "Add home_lat and home_lon in settings.ini.")
    cfg.road_factor = _num(sec.get("road_factor", DEFAULTS["road_factor"]), DEFAULTS["road_factor"], "road_factor", w)
    for v in ("three_wheeler", "mini_truck"):
        k = f"{v}_multiplier"
        cfg.multipliers[v] = _num(sec.get(k, DEFAULTS[k]), DEFAULTS[k], k, w)
    cfg.loading_charge = _num(sec.get("loading_charge", 0), 0, "loading_charge", w)
    for chunk in (sec.get("two_wheeler_fares", DEFAULTS["two_wheeler_fares"]) or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"(.+?)\s+₹?\s*(\d+)$", chunk)
        if not m:
            w.append(f"settings.ini: could not read the fare '{chunk}' (write it like 'Aluva 300').")
            continue
        km = distance_km(m.group(1))
        if km is None:
            w.append(f"settings.ini: the place '{m.group(1)}' in two_wheeler_fares is not in the place list.")
            continue
        cfg.settings_fares.append((km, float(m.group(2))))
    global CONFIG
    CONFIG = cfg
    return cfg


def _haversine(a, b):
    r = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def distance_km(location_text):
    """Estimated road km from home, or None if the place is unknown."""
    _, pos = places.find(location_text)
    if pos is None:
        return None
    return max(1.0, round(_haversine(CONFIG.home, pos) * CONFIG.road_factor, 1))


def _fit(points):
    """Least-squares base + rate*km. Returns (base, rate) or None."""
    if len(points) < 2 or len({round(k, 1) for k, _ in points}) < 2:
        return None
    n = len(points)
    mk = sum(k for k, _ in points) / n
    mf = sum(f for _, f in points) / n
    sxx = sum((k - mk) ** 2 for k, _ in points)
    rate = sum((k - mk) * (f - mf) for k, f in points) / sxx
    base = mf - rate * mk
    if rate <= 0:
        return None
    if base < 0:                       # force through zero instead
        rate = sum(k * f for k, f in points) / sum(k * k for k, _ in points)
        base = 0.0
    return base, rate


def formulas(user_fares):
    """user_fares: list of (vehicle, km, fare) from item cards. Returns {vehicle: info}."""
    pts = {v: [] for v in VEHICLES}
    pts["two_wheeler"].extend(CONFIG.settings_fares)
    for vehicle, km, fare in user_fares:
        if vehicle in pts and km and fare:
            pts[vehicle].append((float(km), float(fare)))

    two = _fit(pts["two_wheeler"])
    two_src = f"from {len(pts['two_wheeler'])} real fares" if two else "default"
    two = two or FALLBACK_TWO_WHEELER
    out = {"two_wheeler": {"base": two[0], "rate": two[1], "source": two_src, "rough": False}}
    for v in ("three_wheeler", "mini_truck"):
        fit = _fit(pts[v])
        if fit:
            out[v] = {"base": fit[0], "rate": fit[1], "source": f"from {len(pts[v])} real fares", "rough": False}
        elif len(pts[v]) == 1:
            km, fare = pts[v][0]
            mult = fare / (two[0] + two[1] * km)
            out[v] = {"base": two[0] * mult, "rate": two[1] * mult, "source": "from 1 real fare", "rough": False}
        else:
            mult = CONFIG.multipliers[v]
            out[v] = {"base": two[0] * mult, "rate": two[1] * mult,
                      "source": f"rough: two-wheeler x {mult:g}", "rough": True}
    for info in out.values():
        info["text"] = f"₹{round(info['base'])} + ₹{info['rate']:.1f}/km ({info['source']})"
    return out


BIG_WORDS = re.compile(r"tower|floor ?stand|\bpa\b|\bdj\b|1[258] ?(?:inch|in\b|\")|home theat|cabinet pair|\bamplifier\b.*\brack", re.I)
SMALL_SPEAKER_WORDS = re.compile(r"\bdrivers?\b|woofer|tweeter|full ?range|mid ?range|\bunit\b|\bcone\b", re.I)


def suggest_vehicle(category, title):
    t = title or ""
    if BIG_WORDS.search(t):
        return "mini_truck"
    if category == "Speaker cabinets and enclosures":
        return "three_wheeler"
    if category == "Speakers and full-range drivers":
        if SMALL_SPEAKER_WORDS.search(t) and not re.search(r"speaker (?:set|system|box)|hi-?fi|bookshelf", t, re.I):
            return "two_wheeler"
        return "three_wheeler"
    return "two_wheeler"


def estimate(item, fx):
    """item: dict with location, distance_km, vehicle, porter_fare, category, title. fx: formulas()."""
    res = {"km": None, "km_source": "", "place": "", "vehicle": "", "vehicle_source": "",
           "cost": None, "cost_source": "", "rough": False}
    if item.get("distance_km") is not None:
        res["km"], res["km_source"] = float(item["distance_km"]), "typed by you"
    else:
        key, _ = places.find(item.get("location"))
        if key:
            res["km"] = distance_km(item["location"])
            res["km_source"] = f"estimated from {key.title()} centre"
            res["place"] = key
    if item.get("vehicle") in VEHICLES:
        res["vehicle"], res["vehicle_source"] = item["vehicle"], "chosen by you"
    else:
        res["vehicle"], res["vehicle_source"] = suggest_vehicle(item.get("category"), item.get("title")), "suggested"

    if item.get("porter_fare") is not None:
        res["cost"], res["cost_source"] = int(item["porter_fare"]), "your Porter fare"
    elif res["km"] is not None:
        f = fx[res["vehicle"]]
        raw = f["base"] + f["rate"] * res["km"] + CONFIG.loading_charge
        res["cost"] = int(round(raw / 10.0) * 10)
        res["cost_source"] = "estimate " + f["text"]
        res["rough"] = f["rough"]
    return res
