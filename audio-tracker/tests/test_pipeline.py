"""End-to-end check using made-up sample screenshots.

Run from the tracker folder:   py tests\\test_pipeline.py
Uses its own temporary data folder - your real database is never touched.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def check(cond, text):
    print(("  OK   " if cond else "  FAIL ") + text)
    if not cond:
        check.failed += 1


check.failed = 0


def main():
    import make_samples
    from tracker import db, parser

    print("Price reading rules:")
    for text, want in [("₹1,250", 1250), ("₹ 12,500", 12500), ("Rs. 950", 950), ("INR 2,000", 2000),
                       ("₹1,25,000", 125000), ("Free", 0), ("1,250", None), ("₹1,2,50", None)]:
        got = parser.parse_price(text)[0]
        check(got == want, f"{text!r} -> {got} (expected {want})")

    tmp = Path(tempfile.mkdtemp(prefix="tracker_test_"))
    try:
        samples = tmp / "screens"
        make_samples.OUT = samples
        make_samples.main()
        (tmp / "settings.ini").write_text(
            f"[tracker]\nscreenshot_folder = {samples}\ndata_folder = data\nport = 8798\nopen_browser = no\n",
            encoding="utf-8")
        os.environ["TRACKER_SETTINGS"] = str(tmp / "settings.ini")
        from tracker import config, pipeline
        settings = config.load()
        settings.make_dirs()
        db.init(settings.db_path)

        print("\nFirst scan (4 sample screenshots):")
        s = pipeline.scan(settings)
        print("  " + s["message"])
        check(s["new"] == 2 and s["updated"] == 1 and s["duplicates"] == 1 and not s["errors"],
              "2 new items, 1 price update, 1 possible duplicate, no errors")

        with db.connect(settings.db_path) as con:
            items = {i["title"]: i for i in db.list_items(con)}
            spk = items.get("Tang Band 4 inch full range speaker pair")
            check(spk is not None, "speaker listing read with the right title")
            if spk:
                prices = [h["price"] for h in spk["history"]]
                check(prices == [1250, 950], f"price history {prices} == [1250, 950]")
                check(spk["price_dropped"], "'Price dropped' badge is on")
                check(spk["drop_amount"] == 300 and spk["drop_pct"] == 24.0, "drop ₹300 (24%)")
                check(spk["last_checked"] == "2026-11-12 08:30:00", "last checked = date of the newest screenshot")
                check(spk["location"] == "Kochi, KL" and spk["seller"] == "Arun Mathew", "location and seller read")
                check(spk["category"] == "Speakers and full-range drivers", "category suggested")
                check(len(spk["screenshots"]) == 2, "one item, two screenshots (no duplicate item)")

                added = db.add_price(con, spk["id"], 950, "2026-11-13 09:00:00", "manual edit")
                check(not added, "same price again does not add a history line")
                tr = spk["transport"]
                check(tr["km"] is not None and 8 <= tr["km"] <= 12, f"Kochi is about {tr['km']} km from home")
                check(tr["vehicle"] == "two_wheeler" and tr["cost"] is not None,
                      f"Porter two-wheeler estimate {tr['cost']} ({tr['cost_source']})")
                check(spk["total_cost"] == 950 + tr["cost"], f"total cost = ₹950 + transport = {spk['total_cost']}")
                db.update_item(con, spk["id"], {"target_price": "₹1,000"})
                check(not db.get_item(con, spk["id"])["target_reached"],
                      "target ₹1,000 is NOT reached once transport is added")
                db.update_item(con, spk["id"], {"target_price": "₹1,200"})
                check(db.get_item(con, spk["id"])["target_reached"], "target ₹1,200 -> 'At or below target'")
                db.update_item(con, spk["id"], {"porter_fare": "140"})
                it = db.get_item(con, spk["id"])
                check(it["transport"]["cost"] == 140 and it["total_cost"] == 1090, "typed Porter fare ₹140 is used")
                check("4 real fares" in db.fare_formulas(con)["two_wheeler"]["text"],
                      "typed fare is learned: formula now uses 4 real fares")
                db.update_item(con, spk["id"], {"distance_km": "15", "vehicle": "three_wheeler", "porter_fare": ""})
                it = db.get_item(con, spk["id"])
                check(it["transport"]["km"] == 15 and it["transport"]["vehicle"] == "three_wheeler"
                      and it["transport"]["rough"], "typed km and vehicle are used (three-wheeler marked rough)")
            dups = db.pending_duplicates(con)
            check(len(dups) == 1, "similar amplifier listing waits in 'Possible duplicate'")
            if dups:
                db.resolve_duplicate(con, dups[0]["id"], "different")
                check(len(db.list_items(con)) == 3, "'Different item' adds it as a new item")

        print("\nSecond scan (nothing new):")
        s = pipeline.scan(settings)
        check(s["new"] == 0 and s["updated"] == 0 and s["skipped"] == 4, "already-processed files are skipped")
        check(len(list(samples.iterdir())) == 4, "original screenshots untouched (still 4 files)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nRESULT:", "ALL PASSED" if not check.failed else f"{check.failed} CHECK(S) FAILED")
    return 1 if check.failed else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
