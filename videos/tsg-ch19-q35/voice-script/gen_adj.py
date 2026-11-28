# Generates compositions/a1..a5.html (adjustment scenes) from the specs below.
# Row: (text, amount, time, kind) kind: "" normal, "tot" total, "note" rule note
# Effect line: (text, amount, time)
import os
OUT = os.path.join(os.path.dirname(__file__), "..", "compositions")

S = {
 "a1": dict(dur=29.1, title="Adjustment (i) · Closing Stock",
   adj="(i) Closing Stock at cost was <b>₹ 35,000</b> whereas its net realisable value (market value) was <b>₹ 30,000</b>.",
   tables=[[("Closing Stock at Cost", "35,000", 2.95, ""), ("Net Realisable Value (Market Value)", "30,000", 5.2, ""),
            ("Closing Stock valued at (Cost or NRV, whichever is lower)", "30,000", 10.6, "tot"),
            ("► AS-2 &amp; Prudence: value stock at Cost or NRV, whichever is lower.", "", 8.05, "note")]],
   eff={"tr": [("By Closing Stock (Cr. side)", "30,000", 20.9)], "pl": [],
        "bs": [("Closing Stock (Assets)", "30,000", 24.7)]}),
 "a2": dict(dur=58.3, title="Adjustments (ii), (iii) &amp; (viii) · Machinery",
   adj="(ii) New machine <b>₹ 3,000</b> bought on 1st April, 2025, not paid, not recorded. (iii) Wages include <b>₹ 500</b> for installation. (viii) Depreciation: Machinery <b>10%</b>, Furniture <b>15%</b>.",
   tables=[[("Machinery (as per Trial Balance)", "14,600", 3.6, ""), ("Add: New Machine (unrecorded credit purchase)", "3,000", 7.95, ""),
            ("Add: Installation Wages (capital expenditure)", "500", 16.8, ""), ("Total Cost of Machinery", "18,100", 25.05, "tot"),
            ("Depreciation on Machinery: ₹ 18,100 × <span class=fr><span>10</span><span>100</span></span>", "1,810", 29.0, ""),
            ("Depreciation on Furniture: ₹ 3,400 × <span class=fr><span>15</span><span>100</span></span>", "510", 37.2, ""),
            ("Total Depreciation", "2,320", 43.3, "tot")]],
   amt_at={"Depreciation on Machinery": 33.6, "Depreciation on Furniture": 41.0},
   eff={"tr": [("Wages: Less installation", "(500)", 19.5)],
        "pl": [("Depreciation: Machinery 1,810 + Furniture 510", "2,320", 45.0)],
        "bs": [("Creditor for Machinery (Liab.)", "3,000", 12.0), ("Machinery 18,100 − 1,810", "16,290", 50.3), ("Furniture 3,400 − 510", "2,890", 54.5)]}),
 "a3": dict(dur=38.6, title="Adjustment (iv) · Bad Debts &amp; Provision",
   adj="(iv) Provision for Doubtful Debts was raised to <b>₹ 1,400</b> and further bad debts of <b>₹ 300</b> were written off.",
   tables=[[("Sundry Debtors (T.B.)", "43,800", 3.6, ""), ("Less: Further Bad Debts", "300", 5.5, ""), ("Good Debtors", "43,500", 9.8, "tot"),
            ("Less: New Provision", "1,400", 12.5, ""), ("Net Debtors (Balance Sheet)", "42,100", 16.2, "tot")],
           [("Bad Debts (T.B.)", "1,000", 22.4, ""), ("Add: Further Bad Debts", "300", 25.0, ""), ("Add: New Provision", "1,400", 27.4, ""),
            ("", "2,700", 30.5, "tot"), ("Less: Old Provision", "800", 32.1, ""), ("Charge to P&amp;L", "1,900", 35.5, "tot")]],
   titles=["Debtors in the Balance Sheet", "Charge to Profit &amp; Loss A/c"],
   eff={"tr": [], "pl": [("Bad Debts &amp; Provision", "1,900", 36.0)],
        "bs": [("Sundry Debtors 43,800 − 300 − 1,400", "42,100", 16.5)]}),
 "a4": dict(dur=31.8, title="Adjustment (v) · Loss of Stock by Fire",
   adj="(v) Fire on 20th March, 2026 destroyed stock of <b>₹ 8,000</b>. Insurance company admitted claim of <b>₹ 5,000</b>, paid on 15th April, 2026.",
   tables=[[("Cost of Stock destroyed by Fire", "8,000", 3.65, ""), ("Less: Insurance Claim admitted (received 15th April)", "5,000", 12.1, ""),
            ("Net Loss of Stock by Fire", "3,000", 23.6, "tot")]],
   eff={"tr": [("Purchases: Less stock destroyed", "(8,000)", 8.0)], "pl": [("Loss of Stock by Fire", "3,000", 25.5)],
        "bs": [("Insurance Claim Receivable (Assets)", "5,000", 19.0)]}),
 "a5": dict(dur=49.3, title="Adjustments (vi) &amp; (vii) · Outstanding &amp; Prepaid",
   adj="(vi) Outstanding wages <b>₹ 700</b>, outstanding salaries <b>₹ 500</b>. (vii) Prepaid insurance <b>₹ 250</b>, prepaid advertisement <b>₹ 500</b>.",
   tables=[[("Wages 31,250 − 500 (installation) + 700 (outstanding)", "31,450", 4.95, ""),
            ("Salaries 5,610 + 500 (outstanding)", "6,110", 16.65, ""),
            ("Insurance 1,250 − 250 (prepaid)", "1,000", 30.55, ""),
            ("Advertisement 3,500 − 500 (prepaid)", "3,000", 37.35, "")]],
   amt_at={"Wages": 13.5, "Salaries": 22.0, "Insurance": 34.5, "Advertisement": 41.0},
   eff={"tr": [("To Wages", "31,450", 14.0)], "pl": [("To Salaries", "6,110", 22.5), ("To Insurance", "1,000", 35.0), ("To Advertisement", "3,000", 41.5)],
        "bs": [("Outstanding Wages (Liab.)", "700", 25.7), ("Outstanding Salaries (Liab.)", "500", 27.5), ("Prepaid Insurance (Assets)", "250", 43.4), ("Prepaid Advertisement (Assets)", "500", 45.2)]}),
}

CSS = """
    #root { position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }
    .hdr { position: absolute; left: 100px; top: 36px; font-family: "Archivo Black", sans-serif; font-size: 50px; color: #F5B700; }
    .adj { position: absolute; left: 100px; top: 120px; width: 1720px; background: #FFFDF5; color: #111; border-radius: 14px; padding: 10px 26px; border-left: 16px solid #CC0000; font-family: "EB Garamond", serif; font-size: 40px; line-height: 1.22; }
    .adj b { color: #CC0000; }
    .wk { position: absolute; left: 100px; top: 0; width: 1720px; display: flex; gap: 24px; }
    .tb { flex: 1; background: #FFFDF5; color: #111; border-radius: 14px; padding: 10px 22px 14px; border-left: 16px solid #6A0DAD; font-family: "EB Garamond", serif; }
    .tb .t { font-family: "Archivo Black", sans-serif; font-size: 32px; color: #6A0DAD; margin-bottom: 4px; }
    table { width: 100%; border-collapse: collapse; font-size: FSpx; }
    td { padding: 0 12px; border: 2px solid #000; line-height: 1.24; }
    td.r { text-align: right; width: 230px; white-space: nowrap; }
    tr.tot td { font-weight: 700; border-top: 4px solid #000; }
    tr.note td { border: none; font-style: italic; color: #6A0DAD; font-size: 32px; padding-top: 6px; }
    .fr { display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; font-size: 0.8em; line-height: 1.02; margin: 0 0.1em; }
    .fr > span:last-child { border-top: 2px solid currentColor; padding: 0 0.1em; }
    .effs { position: absolute; left: 100px; width: 1720px; top: 0; display: flex; gap: 22px; }
    .ef { flex: 1; border-radius: 14px; padding: 14px 20px; height: EFHpx; background: rgba(255,255,255,0.08); border: 3px solid rgba(255,255,255,0.25); }
    .ef .h { font-family: "Archivo Black", sans-serif; font-size: 40px; margin-bottom: 12px; }
    .ef .ln { display: flex; justify-content: space-between; gap: 12px; background: #FFFDF5; color: #111; border-radius: 8px; padding: 8px 14px; margin-bottom: 12px; font-size: EFFpx; font-weight: 700; line-height: 1.2; }
    .ef .ln .a { white-space: nowrap; color: #CC0000; }
    .ef .none { font-size: 36px; color: rgba(255,255,255,0.45); font-weight: 700; }
    #EF-tr .h { color: #7FB2FF; } #EF-pl .h { color: #D59CFF; } #EF-bs .h { color: #7EE2A0; }
"""

def build(key, sp):
    d = sp["dur"]
    import math, re as _re
    plain = _re.sub(r"<[^>]+>", "", sp["adj"])
    fs = sp.get("fs", 46)
    adj_h = 22 + 49 * math.ceil(len(plain) / 86)
    wk_top = 120 + adj_h + 24
    rows_max = max(len(t) for t in sp["tables"])
    nfr = max(sum(1 for r in t if "fr>" in r[0]) for t in sp["tables"])
    wk_h = 30 + (46 if sp.get("titles") else 0) + int((fs * 1.24 + 2) * rows_max) + int(fs * 0.55 * nfr)
    eff_top = wk_top + wk_h + 28
    efh = 1045 - eff_top
    nlines = max(len(v) for v in sp["eff"].values())
    eff_fs = sp.get("eff_fs", 44 if nlines <= 1 else 38 if nlines <= 2 else 34)
    tabs = []
    js = []
    amt_at = sp.get("amt_at", {})
    for ti, rows in enumerate(sp["tables"]):
        trs = []
        for ri, (txt, amt, t, kind) in enumerate(rows):
            rid = f"{key}-t{ti}r{ri}"
            if kind == "note":
                trs.append(f'<tr class="note" id="{rid}"><td colspan="2">{txt}</td></tr>')
            else:
                trs.append(f'<tr class="{kind}" id="{rid}"><td>{txt}</td><td class="r"><span id="{rid}a">{amt}</span></td></tr>')
            js.append(f'row("#{rid}", {t});')
            for k, at in amt_at.items():
                if txt.startswith(k):
                    js.append(f'pop("#{rid}a", {at});')
            if kind == "tot":
                js.append(f'flash("#{rid}", {t});')
        title = f'<div class="t">{sp["titles"][ti]}</div>' if sp.get("titles") else ""
        tabs.append(f'<div class="tb">{title}<table>{"".join(trs)}</table></div>')
    effs = []
    for k, name in (("tr", "Trading A/c"), ("pl", "Profit &amp; Loss A/c"), ("bs", "Balance Sheet")):
        lns = []
        for i, (txt, amt, t) in enumerate(sp["eff"][k]):
            lid = f"{key}-{k}{i}"
            lns.append(f'<div class="ln" id="{lid}"><span>{txt}</span><span class="a">{amt}</span></div>')
            js.append(f'eff("#{lid}", "#EF-{k}", {t});')
        if not lns:
            lns.append('<div class="none">— no effect</div>')
        effs.append(f'<div class="ef" id="EF-{k}"><div class="h">{name}</div>{"".join(lns)}</div>')
    eff_start = min([t for v in sp["eff"].values() for (_, _, t) in v])
    html = f"""<template>
  <style>{CSS.replace("EF-", key + "-EF-").replace("FSpx", f"{fs}px").replace("EFHpx", f"{efh}px").replace("EFFpx", f"{eff_fs}px")}
    #{key}-wk {{ top: {wk_top}px; }} #{key}-effs {{ top: {eff_top}px; }} #{key}-EF-bs {{ flex: {sp.get("bs_flex", 1)}; }}
  </style>
  <div id="root" data-composition-id="{key}" data-width="1920" data-height="1080">
    <div class="hdr clip" id="{key}-hdr" data-start="0" data-duration="{d}" data-track-index="0">{sp["title"]}</div>
    <div class="adj clip" id="{key}-adj" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="1">{sp["adj"]}</div>
    <div class="wk clip" id="{key}-wk" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">{"".join(tabs)}</div>
    <div class="effs clip" id="{key}-effs" data-start="{max(eff_start - 1.5, 0.5):.1f}" data-duration="{d - max(eff_start - 1.5, 0.5):.1f}" data-track-index="3">{"".join(effs).replace('id="EF-', 'id="' + key + '-EF-')}</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const row = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.35 }}, t);
    const pop = (s, t) => tl.fromTo(s, {{ opacity: 0, scale: 0.5 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)" }}, t);
    const flash = (s, t) => tl.fromTo(s, {{ backgroundColor: "rgba(106,13,173,0.3)" }}, {{ backgroundColor: "rgba(106,13,173,0)", duration: 1.6 }}, t + 0.35);
    const eff = (s, box, t) => {{ tl.fromTo(s, {{ opacity: 0, y: 20, scale: 0.9 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(2)" }}, t);
      tl.fromTo(box, {{ borderColor: "rgba(245,183,0,1)" }}, {{ borderColor: "rgba(255,255,255,0.25)", duration: 2.0 }}, t); }};
    tl.fromTo("#{key}-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    tl.fromTo("#{key}-adj", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.45 }}, 0.3);
    tl.fromTo("#{key}-effs", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {max(eff_start - 1.5, 0.5):.1f});
    {chr(10).join("    " + j for j in js).strip()}
    window.__timelines["{key}"] = tl;
  </script>
</template>
"""
    html = html.replace('"#EF-', f'"#{key}-EF-')
    open(os.path.join(OUT, f"{key}.html"), "w").write(html)

if __name__ == "__main__":
  for k, v in S.items():
      build(k, v)
print("ok")
