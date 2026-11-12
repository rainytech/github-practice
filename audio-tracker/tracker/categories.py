"""Suggests a category and a brand / model from the title (you can always change it)."""
import re

RULES = {
    "Amplifier boards": [
        (r"tpa\s?3\d{3}", 5), (r"pam\s?8\d{3}", 5), (r"tda\s?\d{4}", 5), (r"lm\s?(?:1875|3886|386|4766)", 5),
        (r"xh[- ]?[am]\d+", 4), (r"zk[- ]?\w+", 3), (r"amplifier board", 4), (r"amp board", 4),
        (r"amplifier module", 4), (r"class[- ]?d", 3), (r"amplifier", 2), (r"\bamp\b", 2), (r"preamp", 2),
    ],
    "Power supplies and adapters": [
        (r"\bsmps\b", 4), (r"power supply", 4), (r"\bpsu\b", 4), (r"adapter", 3), (r"adaptor", 3),
        (r"transformer", 3), (r"charger", 2), (r"\b(?:12|19|24|32|36|48)\s?v\b", 1), (r"\d+\s?amps?\b", 1),
    ],
    "Speaker cabinets and enclosures": [
        (r"cabinet", 4), (r"enclosure", 4), (r"empty box", 4), (r"speaker box", 3), (r"bass reflex", 3),
        (r"ported box", 3), (r"sealed box", 3), (r"\bmdf\b", 2), (r"\bbox\b", 1),
    ],
    "Electronic components and accessories": [
        (r"capacitor", 3), (r"resistor", 3), (r"potentiometer", 3), (r"\bpot\b", 2), (r"bluetooth module", 3),
        (r"crossover", 3), (r"binding post", 3), (r"terminal", 2), (r"heat ?sink", 3), (r"\bknob", 2),
        (r"\bcable", 2), (r"\bwire", 2), (r"connector", 2), (r"\brca\b", 2), (r"\bdac\b", 2),
        (r"ne5532", 3), (r"op ?amp", 3), (r"\brelay\b", 2), (r"tone control", 2), (r"\bfan\b", 1),
    ],
    "Speakers and full-range drivers": [
        (r"full ?range", 4), (r"\bdrivers?\b", 3), (r"woofer", 3), (r"subwoofer", 3), (r"tweeter", 3),
        (r"mid ?range", 3), (r"coaxial", 3), (r"speakers?", 2), (r"\d+(?:\.\d)?\s?(?:inch|in\b|\")", 1),
        (r"\d+\s?ohm", 1), (r"bookshelf", 2), (r"\d+\s?w\b", 0.5),
    ],
}

BRANDS = [
    "JBL", "Philips", "Sony", "Bose", "Peerless", "Tang Band", "Dayton Audio", "Dayton", "Visaton", "Fostex",
    "Faital", "P Audio", "Celestion", "Yamaha", "Pioneer", "Kenwood", "Kenford", "Ahuja", "Hertz", "Morel",
    "SB Acoustics", "Vifa", "Scan-Speak", "Markaudio", "Mark Audio", "Sansui", "Onkyo", "Denon", "Marantz",
    "Polk", "KEF", "Wharfedale", "Tannoy", "Klipsch", "Infinity", "boAt", "Edifier", "Behringer", "Harman",
    "Samsung", "LG", "Panasonic", "Technics", "Akai", "Aiwa", "Studiomaster", "Wavecor", "Audax", "Sonodyne",
]

CHIP_RE = re.compile(r"\b(tpa\s?3\d{3}\w*|pam\s?8\d{3}\w*|tda\s?\d{4}\w*|lm\s?\d{3,4}\w*|ne\s?5532|xh[- ]?[am]\d+\w*)",
                     re.I)


def suggest_category(text):
    t = (text or "").lower()
    best, best_score = "", 0.0
    for name, rules in RULES.items():
        s = sum(w for pat, w in rules if re.search(pat, t))
        if s > best_score:
            best, best_score = name, s
    return best if best_score >= 1.5 else ""


def suggest_brand_model(text):
    t = text or ""
    parts = []
    for b in BRANDS:
        if re.search(r"\b" + re.escape(b) + r"\b", t, re.I):
            parts.append(b)
            break
    m = CHIP_RE.search(t)
    if m:
        parts.append(m.group(1).upper().replace(" ", ""))
    return " ".join(parts)
