# Generates compositions/trading.html, pl.html, bs.html (T-format accounts).
# Row: (particulars, inner, outer, time, kind)  kind: "" | "sub" (working shown pink) | "bal" (balancing figure)
import os
OUT = os.path.join(os.path.dirname(__file__), "..", "compositions")
W = lambda s: f'<span class="w">{s}</span>'

S = {
 "trading": dict(dur=55.9, title="Trading Account", sub="of Manoj for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Opening Stock", "", "40,200", 6.8, ""),
      ("To Purchases", "1,32,700", "", 10.2, ""),
      ("Less: Purchases Return", "970", "", 14.0, ""),
      ("", "1,31,730", "", 16.0, ""),
      ("Less: Stock destroyed by Fire", "8,000", "1,23,730", 17.6, ""),
      ("To Wages " + W("(31,250 − 500 + 700)"), "", "31,450", 24.1, ""),
      ("To Carriage Inwards", "", "3,400", 28.0, ""),
      ("To Gross Profit c/d", "", "21,910", 50.3, "bal")],
   R=[("By Sales", "1,91,940", "", 31.4, ""),
      ("Less: Sales Return", "1,250", "1,90,690", 36.0, ""),
      ("By Closing Stock " + W("(Cost or NRV, lower)"), "", "30,000", 43.3, "")],
   totL=("2,20,690", 50.6), totR=("2,20,690", 46.1),
   stamp=("Gross Profit ₹ 21,910", 51.0)),
 "pl": dict(dur=49.3, title="Profit &amp; Loss Account", sub="of Manoj for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Salaries " + W("(5,610 + 500)"), "", "6,110", 12.6, ""),
      ("To Discount Allowed", "", "2,640", 16.3, ""),
      ("To Bank Charges", "", "90", 19.6, ""),
      ("To Bad Debts &amp; Provision", "", "1,900", 22.0, ""),
      ("To Insurance " + W("(1,250 − 250)"), "", "1,000", 25.7, ""),
      ("To Rent", "", "2,450", 28.3, ""),
      ("To Advertisement " + W("(3,500 − 500)"), "", "3,000", 30.4, ""),
      ("To Loss of Stock by Fire", "", "3,000", 32.6, ""),
      ("To Depreciation: Machinery", "1,810", "", 36.9, ""),
      ("Furniture", "510", "2,320", 39.6, ""),
      ("To Net Profit " + W("(to Capital A/c)"), "", "1,400", 45.3, "bal")],
   R=[("By Gross Profit b/d", "", "21,910", 3.1, ""),
      ("By Discount Received", "", "2,000", 7.2, "")],
   totL=("23,910", 45.8), totR=("23,910", 10.2),
   stamp=("Net Profit ₹ 1,400", 46.0)),
 "bs": dict(dur=71.3, title="Balance Sheet", sub="of Manoj as at 31st March, 2026",
   heads=("", ""), cols=("Liabilities", "Assets"),
   L=[("Capital", "1,00,000", "", 6.1, ""),
      ("Add: Net Profit", "1,400", "", 8.6, ""),
      ("Less: Drawings", "4,200", "97,200", 11.2, ""),
      ("Bank Loan", "", "10,000", 15.4, ""),
      ("Sundry Creditors", "", "12,450", 17.8, ""),
      ("Creditor for Machinery", "", "3,000", 21.2, ""),
      ("Outstanding Wages", "", "700", 24.3, ""),
      ("Outstanding Salaries", "", "500", 26.3, "")],
   R=[("Building", "", "21,700", 34.0, ""),
      ("Machinery " + W("(18,100 − 1,810)"), "", "16,290", 37.0, ""),
      ("Furniture " + W("(3,400 − 510)"), "", "2,890", 40.6, ""),
      ("Closing Stock", "", "30,000", 43.9, ""),
      ("Sundry Debtors " + W("(43,800 − 300 − 1,400)"), "", "42,100", 46.5, ""),
      ("Insurance Claim Receivable", "", "5,000", 49.4, ""),
      ("Prepaid Insurance", "", "250", 52.4, ""),
      ("Prepaid Advertisement", "", "500", 54.6, ""),
      ("Cash at Bank", "", "2,470", 57.8, ""),
      ("Cash in Hand", "", "2,650", 60.6, "")],
   totL=("1,23,850", 28.9), totR=("1,23,850", 64.7),
   stamp=("TALLIED ✓ ₹ 1,23,850", 67.0)),
}

def side(key, sd, rows, n, tot):
    trs = []
    js = []
    for i in range(n):
        if i < len(rows):
            p, a, b, t, k = rows[i]
            rid = f"{key}-{sd}{i}"
            trs.append(f'<tr id="{rid}" class="{k}"><td>{p}</td><td class="r">{a}</td><td class="r">{b}</td></tr>')
            js.append(f'row("#{rid}", {t});')
            if k == "bal":
                js.append(f'tl.fromTo("#{rid}", {{ backgroundColor: "rgba(245,183,0,0.7)" }}, {{ backgroundColor: "rgba(245,183,0,0.25)", duration: 2.5 }}, {t + 0.3});')
        else:
            trs.append('<tr class="pad"><td>&nbsp;</td><td></td><td></td></tr>')
    tid = f"{key}-{sd}tot"
    trs.append(f'<tr class="tot"><td></td><td></td><td class="r"><span id="{tid}">{tot[0]}</span></td></tr>')
    js.append(f'tl.fromTo("#{tid}", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)" }}, {tot[1]});')
    return trs, js

def build(key, sp):
    d = sp["dur"]
    n = max(len(sp["L"]), len(sp["R"]))
    rowh = 852 / (n + 2)
    fs = sp.get("fs") or min(sp.get("cap", 48), int(rowh / 1.32))
    tl_, jl = side(key, "L", sp["L"], n, sp["totL"])
    tr_, jr = side(key, "R", sp["R"], n, sp["totR"])
    hd = lambda c: f'<tr><th>{c}</th><th>₹</th><th>₹</th></tr>'
    st_text, st_t = sp["stamp"]
    html = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .card {{ position: absolute; left: 60px; top: 28px; width: 1800px; height: 1024px; display: flex; flex-direction: column; background: #FFFDF5; color: #111; border-radius: 16px; padding: 10px 24px 16px; border-left: 16px solid #6A0DAD; font-family: "EB Garamond", serif; box-shadow: 0 14px 34px rgba(0,0,0,0.3); }}
    .tt {{ text-align: center; font-weight: 700; font-size: 42px; color: #6A0DAD; text-decoration: underline; line-height: 1.1; }}
    .ts {{ text-align: center; font-style: italic; font-size: 30px; color: #6A0DAD; }}
    .drcr {{ display: flex; justify-content: space-between; font-weight: 700; font-size: 30px; color: #6A0DAD; padding: 0 6px; }}
    .two {{ display: flex; flex: 1; min-height: 0; }}
    .two table {{ width: 50%; height: 100%; border-collapse: collapse; font-size: {fs}px; }}
    .fr {{ display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; font-size: 0.8em; line-height: 1.02; margin: 0 0.1em; }}
    .fr > span:last-child {{ border-top: 2px solid currentColor; padding: 0 0.1em; }}
    th {{ background: #BDBDBD; font-style: italic; padding: 0 10px; border: 2px solid #000; }}
    td {{ padding: 0 10px; border-left: 2px solid #000; border-right: 2px solid #000; line-height: 1.26; }}
    td.r {{ text-align: right; white-space: nowrap; width: {int(fs * 3.9)}px; }}
    tr.tot td {{ font-weight: 700; border-top: 3px solid #000; border-bottom: 5px double #000; }}
    tr.bal td {{ font-weight: 700; }}
    .w {{ color: #C2185B; font-style: italic; font-size: 0.86em; }}
    .stamp {{ position: absolute; right: 90px; top: 34px; background: #CC0000; color: #fff; font-family: "Archivo Black", sans-serif; font-size: 40px; padding: 8px 28px; border-radius: 16px; transform: rotate(-4deg); box-shadow: 0 12px 30px rgba(0,0,0,0.45); }}
  </style>
  <div id="root" data-composition-id="{key}" data-width="1920" data-height="1080">
    <div class="card clip" id="{key}-card" data-start="0.2" data-duration="{d - 0.2:.1f}" data-track-index="0">
      <div class="tt">{sp["title"]}</div>
      <div class="ts">{sp["sub"]}</div>
      <div class="drcr"><span>{sp["heads"][0]}</span><span>{sp["heads"][1]}</span></div>
      <div class="two">
        <table>{hd(sp["cols"][0])}{"".join(tl_)}</table>
        <table>{hd(sp["cols"][1])}{"".join(tr_)}</table>
      </div>
    </div>
    <div class="stamp clip" id="{key}-stamp" data-start="{st_t}" data-duration="{d - st_t:.1f}" data-track-index="1">{st_text}</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const row = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -24 }}, {{ opacity: 1, x: 0, duration: 0.35 }}, t);
    tl.fromTo("#{key}-card", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }}, 0.2);
    {chr(10).join("    " + j for j in jl + jr).strip()}
    tl.fromTo("#{key}-stamp", {{ opacity: 0, scale: 2.2 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.6)" }}, {st_t});
    window.__timelines["{key}"] = tl;
  </script>
</template>
"""
    open(os.path.join(OUT, f"{key}.html"), "w").write(html)

if __name__ == "__main__":
  for k, v in S.items():
      build(k, v)
print("ok")
