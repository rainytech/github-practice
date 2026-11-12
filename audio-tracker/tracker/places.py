"""Approximate map positions (latitude, longitude) of places in Kerala, for distance estimates.

Positions are town/area centres, so distances are estimates. A place that is not
in this list gives "distance unknown" - type the km on the card instead.
Add your own places at the bottom of PLACES if you like.
"""
import re

PLACES = {
    # ---- Kochi / Ernakulam area
    "puthiyakavu": (9.9345, 76.3470),
    "tripunithura": (9.9496, 76.3436),
    "kochi": (9.9680, 76.2860),
    "ernakulam": (9.9816, 76.2999),
    "thevara": (9.9370, 76.2990),
    "aluva": (10.1076, 76.3516),
    "edappally": (10.0261, 76.3083),
    "kalamassery": (10.0527, 76.3165),
    "kakkanad": (10.0159, 76.3419),
    "thrikkakara": (10.0330, 76.3330),
    "vyttila": (9.9667, 76.3185),
    "kaloor": (9.9973, 76.2930),
    "palarivattom": (10.0048, 76.3070),
    "kadavanthra": (9.9667, 76.2990),
    "elamakkara": (10.0150, 76.2900),
    "pachalam": (10.0000, 76.2820),
    "vaduthala": (10.0050, 76.2800),
    "fort kochi": (9.9658, 76.2421),
    "mattancherry": (9.9580, 76.2590),
    "palluruthy": (9.9180, 76.2700),
    "kumbalam": (9.9020, 76.3110),
    "maradu": (9.9330, 76.3200),
    "kundannoor": (9.9420, 76.3170),
    "poonithura": (9.9570, 76.3260),
    "eroor": (9.9670, 76.3330),
    "irumpanam": (9.9640, 76.3550),
    "thiruvankulam": (9.9460, 76.3700),
    "chottanikkara": (9.9330, 76.3910),
    "panangad": (9.8930, 76.3240),
    "udayamperoor": (9.9030, 76.3610),
    "mulanthuruthy": (9.9000, 76.3900),
    "kumbalangi": (9.8640, 76.2850),
    "chellanam": (9.8200, 76.2700),
    "vypin": (10.0000, 76.2300),
    "njarakkal": (10.0420, 76.2140),
    "cherai": (10.1400, 76.1800),
    "eloor": (10.0750, 76.3000),
    "cheranalloor": (10.0600, 76.2900),
    "varapuzha": (10.0720, 76.2770),
    "kizhakkambalam": (10.0420, 76.4100),
    "pukkattupady": (10.0570, 76.3700),
    "nedumbassery": (10.1520, 76.3910),
    "angamaly": (10.1960, 76.3860),
    "kalady": (10.1670, 76.4380),
    "perumbavoor": (10.1150, 76.4770),
    "kolenchery": (9.9800, 76.4700),
    "piravom": (9.8730, 76.4900),
    "muvattupuzha": (9.9894, 76.5790),
    "kothamangalam": (10.0602, 76.6351),
    "north paravur": (10.1430, 76.2310),
    "paravur": (10.1430, 76.2310),
    # ---- rest of Kerala
    "kodungallur": (10.2300, 76.1950),
    "thrissur": (10.5276, 76.2144),
    "chalakudy": (10.3000, 76.3330),
    "irinjalakuda": (10.3430, 76.2110),
    "guruvayur": (10.5940, 76.0410),
    "kunnamkulam": (10.6500, 76.0700),
    "alappuzha": (9.4981, 76.3388),
    "cherthala": (9.6840, 76.3360),
    "haripad": (9.2830, 76.4600),
    "kayamkulam": (9.1740, 76.5010),
    "mavelikkara": (9.2510, 76.5480),
    "chengannur": (9.3180, 76.6110),
    "kottayam": (9.5916, 76.5222),
    "vaikom": (9.7490, 76.3950),
    "ettumanoor": (9.6700, 76.5600),
    "changanassery": (9.4440, 76.5410),
    "pala": (9.7110, 76.6830),
    "kanjirappally": (9.5570, 76.7900),
    "thodupuzha": (9.8950, 76.7180),
    "idukki": (9.8500, 76.9700),
    "kattappana": (9.7500, 77.1200),
    "munnar": (10.0889, 77.0595),
    "kumily": (9.6070, 77.1660),
    "thiruvalla": (9.3835, 76.5741),
    "pathanamthitta": (9.2648, 76.7870),
    "adoor": (9.1530, 76.7350),
    "kollam": (8.8932, 76.6141),
    "varkala": (8.7330, 76.7160),
    "attingal": (8.6960, 76.8150),
    "thiruvananthapuram": (8.5241, 76.9366),
    "neyyattinkara": (8.4000, 77.0870),
    "palakkad": (10.7867, 76.6548),
    "ottapalam": (10.7700, 76.3770),
    "shoranur": (10.7600, 76.2700),
    "pattambi": (10.8090, 76.1950),
    "alathur": (10.6480, 76.5380),
    "chittur": (10.7000, 76.7470),
    "malappuram": (11.0510, 76.0711),
    "manjeri": (11.1200, 76.1200),
    "perinthalmanna": (10.9760, 76.2270),
    "kottakkal": (11.0000, 75.9950),
    "tirur": (10.9150, 75.9220),
    "ponnani": (10.7680, 75.9250),
    "nilambur": (11.2760, 76.2250),
    "kozhikode": (11.2588, 75.7804),
    "koyilandy": (11.4400, 75.6950),
    "vadakara": (11.6080, 75.5910),
    "kalpetta": (11.6085, 76.0830),
    "sulthan bathery": (11.6650, 76.2600),
    "mananthavady": (11.8000, 76.0000),
    "thalassery": (11.7480, 75.4920),
    "kannur": (11.8745, 75.3704),
    "payyanur": (12.1000, 75.2000),
    "kasaragod": (12.4996, 74.9869),
}

ALIASES = {
    "cochin": "kochi", "ernakulam city": "ernakulam", "thrippunithura": "tripunithura",
    "tripunithura": "tripunithura", "thripunithura": "tripunithura", "tripunithara": "tripunithura",
    "vytilla": "vyttila", "edapally": "edappally", "kalamasseri": "kalamassery", "angamali": "angamaly",
    "perumbavur": "perumbavoor", "moovattupuzha": "muvattupuzha", "trichur": "thrissur", "alleppey": "alappuzha",
    "trivandrum": "thiruvananthapuram", "quilon": "kollam", "palghat": "palakkad", "calicut": "kozhikode",
    "cannanore": "kannur", "tellicherry": "thalassery", "kasargod": "kasaragod", "wayanad": "kalpetta",
    "fortkochi": "fort kochi", "vypeen": "vypin", "chalakudi": "chalakudy", "guruvayoor": "guruvayur",
    "kottayam town": "kottayam", "thiruvalla town": "thiruvalla", "nedumbassery airport": "nedumbassery",
    "mattanchery": "mattancherry", "palluruthi": "palluruthy", "maradu municipality": "maradu",
}


def _clean(text):
    return re.sub(r"[^a-z ]+", " ", (text or "").lower()).split()


def find(location_text):
    """'Kochi, KL' -> ('kochi', (lat, lon)); unknown -> (None, None).

    The first comma-separated part is tried first ('Tripunithura, Kerala'), then any
    known place name inside the text.
    """
    if not location_text:
        return None, None
    parts = [p.strip() for p in location_text.split(",") if p.strip()]
    for part in parts[:2]:
        key = " ".join(_clean(part))
        key = ALIASES.get(key, key)
        if key in PLACES:
            return key, PLACES[key]
    words = " ".join(_clean(location_text))
    for name in sorted(list(PLACES) + list(ALIASES), key=len, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", words):
            key = ALIASES.get(name, name)
            return key, PLACES[key]
    return None, None
