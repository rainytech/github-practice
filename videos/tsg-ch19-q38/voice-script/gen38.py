# Builds every Q38 scene + index.html from voice-script/timing.json (Rainy's voice).
# Run after tools/voice/build_voice_rainy.py:  python3 voice-script/gen38.py
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
COMP = os.path.join(PROJ, "compositions")
sys.path.insert(0, HERE)
import gen_adj, gen_acc
W = gen_acc.W

T = json.load(open(os.path.join(HERE, "timing.json")))
def L(scene, i, extra=0.0):
    """Scene time of voice line i (+0.3 audio offset) plus extra seconds, kept inside that line."""
    s, d = T[scene]["lines"][i]
    return round(0.3 + s + min(extra, max(d - 0.3, 0)), 2)
def E(scene, i, back=0.6):
    s, d = T[scene]["lines"][i]
    return round(0.3 + s + max(d - back, 0), 2)
EXTRA = {"adjust": 4.0, "recap": 3.0, "question": 0.5}
DUR = {k: round(v["dur"] + 1.3 + EXTRA.get(k, 0), 1) for k, v in T.items()}

TPL = os.path.join(PROJ, "..", "tsg-ch19-q39", "compositions")
def rd(name): return open(os.path.join(TPL, name)).read()  # always start from the Q39 templates
def wr(name, s): open(os.path.join(COMP, name), "w").write(s)

# ---------- question ----------
dr = [("Building", "1,50,000", "st"), ("Purchases (Adjusted)", "2,90,000", "ok"), ("Salaries", "5,000", "st"), ("Bad Debts", "2,000", ""),
      ("Wages", "10,000", ""), ("Rent", "5,000", ""), ("Prepaid Rent (At the end)", "3,000", "ok"), ("Insurance", "5,000", "st"),
      ("Furniture (At cost)", "60,000", "st"), ("Drawings", "5,000", "st"), ("Sundry Debtors", "25,000", "st"), ("Closing Stock", "40,000", "ok")]
cr = [("Capital", "30,000", ""), ("Sales", "5,29,500", ""), ("Wages Outstanding (At the end)", "8,000", "ok"),
      ("Provision for Depreciation on Furniture", "12,000", "st"), ("Apprentice Premium", "500", ""), ("Sundry Creditors", "20,000", "")]
def rows(lst):
    out = []
    for n, a, k in lst:
        mark = ' <span class="st">★</span>' if k == "st" else (' <span class="okm">✔ adjusted</span>' if k == "ok" else "")
        cls = "ok" if k == "ok" else ""
        out.append(f'<tr class="{cls}"><td>{n}{mark}</td><td class="r">{a}</td></tr>')
    return "\n".join(out)
d = DUR["question"]
wr("question.html", f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .hdr {{ position: absolute; left: 100px; top: 40px; font-family: "Archivo Black", sans-serif; font-size: 58px; color: #F5B700; }}
    .ref {{ position: absolute; right: 100px; top: 60px; font-size: 32px; font-weight: 700; color: rgba(255,255,255,0.85); }}
    #q-lead {{ position: absolute; left: 100px; top: 130px; width: 1720px; font-family: "EB Garamond", serif; font-size: 40px; }}
    .card {{ position: absolute; top: 200px; background: #FFFDF5; color: #111; border-radius: 16px; padding: 12px 18px 16px; font-family: "EB Garamond", serif; box-shadow: 0 12px 30px rgba(0,0,0,0.3); }}
    .card .t {{ font-family: "Archivo Black", sans-serif; font-size: 32px; margin-bottom: 6px; }}
    #q-d {{ left: 100px; width: 880px; border-top: 10px solid #0057B8; }} #q-d .t {{ color: #0057B8; }}
    #q-c {{ left: 1000px; width: 820px; border-top: 10px solid #CC0000; }} #q-c .t {{ color: #CC0000; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 38px; }}
    td {{ padding: 0 10px; border: 2px solid #000; line-height: 1.2; }}
    td.r {{ text-align: right; width: 170px; white-space: nowrap; }}
    .st {{ color: #CC0000; font-weight: 700; display: inline-block; }}
    .okm {{ color: #1E8E3E; font-weight: 700; font-size: 0.7em; font-family: "Inter", sans-serif; display: inline-block; }}
    tr.ok td {{ background: rgba(30,142,62,0.0); }}
    #q-tot {{ position: absolute; left: 100px; top: 925px; width: 1720px; height: 100px; background: #F5B700; color: #0B1B3F; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-family: "Archivo Black", sans-serif; font-size: 46px; }}
    #q-note {{ position: absolute; left: 1000px; top: 790px; width: 820px; background: #1E8E3E; color: #fff; border-radius: 16px; padding: 16px 24px; font-size: 36px; font-weight: 800; line-height: 1.25; }}
  </style>
  <div id="root" data-composition-id="question" data-width="1920" data-height="1080">
    <div class="hdr clip" id="q-hdr" data-start="0" data-duration="{d}" data-track-index="0">The Question</div>
    <div class="ref clip" id="q-ref" data-start="0" data-duration="{d}" data-track-index="1">T.S. Grewal · Q 38 · Pg 19.90</div>
    <div class="clip" id="q-lead" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">The following is the Trial Balance of Ashok as on 31st March, 2026:</div>
    <div class="card clip" id="q-d" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="3"><div class="t">Debit Balances (₹)</div><table>
{rows(dr)}
    </table></div>
    <div class="card clip" id="q-c" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="4"><div class="t">Credit Balances (₹)</div><table>
{rows(cr)}
    </table></div>
    <div class="clip" id="q-note" data-start="{L('question', 4)}" data-duration="{d - L('question', 4):.1f}" data-track-index="5">✔ = already adjusted in the Trial Balance · ★ = adjustment coming</div>
    <div class="clip" id="q-tot" data-start="{L('question', 3)}" data-duration="{d - L('question', 3):.1f}" data-track-index="6">Total Debit ₹ 6,00,000 &nbsp;=&nbsp; Total Credit ₹ 6,00,000 ✓</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#q-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    tl.fromTo("#q-ref", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.2);
    tl.fromTo("#q-lead", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.3);
    tl.fromTo(["#q-d", "#q-c"], {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.5, stagger: 0.2, ease: "power3.out" }}, 0.8);
    tl.fromTo("#q-d", {{ boxShadow: "0 0 0 0 rgba(245,183,0,0)" }}, {{ boxShadow: "0 0 0 10px rgba(245,183,0,0.9)", duration: 0.4, yoyo: true, repeat: 1, repeatDelay: 6 }}, {L('question', 1)});
    tl.fromTo("#q-c", {{ boxShadow: "0 0 0 0 rgba(245,183,0,0)" }}, {{ boxShadow: "0 0 0 10px rgba(245,183,0,0.9)", duration: 0.4, yoyo: true, repeat: 1, repeatDelay: 5 }}, {L('question', 2)});
    tl.fromTo("#q-tot", {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)" }}, {L('question', 3)});
    tl.fromTo("#q-note", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.4 }}, {L('question', 4)});
    tl.to("tr.ok td", {{ backgroundColor: "rgba(30,142,62,0.25)", duration: 0.4 }}, {L('question', 4, 1.0)});
    tl.to(".okm", {{ scale: 1.25, duration: 0.3, yoyo: true, repeat: 3, ease: "sine.inOut" }}, {L('question', 4, 1.5)});
    window.__timelines["question"] = tl;
  </script>
</template>
''')

# ---------- adjust (list of 5 + pause) ----------
items = [("(i)", "Salaries for the month of March, 2026 of <b>₹ 1,000</b> were unpaid which are to be provided. Balance in the account included <b>₹ 800</b> paid in advance."),
         ("(ii)", "Insurance is prepaid to the extent of <b>₹ 2,000</b>."),
         ("(iii)", "Depreciate Furniture by <b>10%</b> on original cost and Building by <b>5%</b>."),
         ("(iv)", "Stock of <b>₹ 1,500</b> was taken by Ashok for his personal use."),
         ("(v)", "Make a Provision for Doubtful Debts equal to <b>10%</b> of Sundry Debtors.")]
s = rd("adjust.html")
a = s.index('<div class="clip" id="ad-card"'); b = s.index('<div class="clip" id="ad-pause"')
d = DUR["adjust"]; tp = L("adjust", 6)
s = s[:a] + f'<div class="clip" id="ad-card" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">\n' + \
    "\n".join(f'      <div class="it" id="ad-{i}"><span class="n">{n}</span><span class="tx">{t}</span></div>' for i, (n, t) in enumerate(items)) + \
    "\n    </div>\n    " + s[b:]
s = re.sub(r'data-start="[0-9.]+" data-duration="[0-9.]+" data-track-index="3"><span class="ic">', f'data-start="{tp}" data-duration="{d - tp:.1f}" data-track-index="3"><span class="ic">', s)
s = re.sub(r'data-duration="70.4"', f'data-duration="{d}"', s)
s = s.replace("The 8 Adjustments", "The 5 Adjustments").replace("T.S. Grewal · Q 39", "T.S. Grewal · Q 38")
a = s.index('    show("#ad-0"'); b = s.index('    tl.fromTo("#ad-pause"')
s = s[:a] + "".join(f'    show("#ad-{i}", {L("adjust", i + 1)});\n' for i in range(5)) + s[b:]
s = re.sub(r'(tl\.fromTo\("#ad-pause".*?\}, )[0-9.]+\);', lambda m: f"{m.group(1)}{tp + 0.1:.2f});", s)
s = re.sub(r'(tl\.to\("#ad-pause \.ic".*?\}, )[0-9.]+\);', lambda m: f"{m.group(1)}{tp + 0.7:.2f});", s)
s = s.replace(".it { display: flex; gap: 14px; font-size: 40px;", ".it { display: flex; gap: 14px; font-size: 46px;").replace("#ad-pause { position: absolute; left: 560px; top: 905px;", "#ad-pause { position: absolute; left: 560px; top: 860px;")
wr("adjust.html", s)

# ---------- already (the big trap) ----------
d = DUR["already"]
wr("already.html", f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .hdr {{ position: absolute; left: 100px; top: 40px; font-family: "Archivo Black", sans-serif; font-size: 56px; color: #F5B700; }}
    .box {{ position: absolute; left: 100px; width: 1720px; background: #FFFDF5; color: #111; border-radius: 16px; padding: 14px 30px; border-left: 16px solid #1E8E3E; font-family: "EB Garamond", serif; box-shadow: 0 12px 30px rgba(0,0,0,0.3); }}
    .k {{ font-family: "Archivo Black", sans-serif; font-size: 34px; color: #1E8E3E; margin-bottom: 4px; }}
    .ln {{ display: block; font-size: 42px; line-height: 1.3; }}
    .ln b {{ color: #0057B8; }} .no {{ color: #CC0000; font-weight: 700; }}
    #al-1 {{ top: 140px; }} #al-2 {{ top: 560px; }}
    #al-stamp {{ position: absolute; right: 120px; bottom: 50px; background: #CC0000; color: #fff; font-family: "Archivo Black", sans-serif; font-size: 52px; padding: 10px 34px; border-radius: 16px; transform: rotate(-4deg); box-shadow: 0 12px 30px rgba(0,0,0,0.45); }}
  </style>
  <div id="root" data-composition-id="already" data-width="1920" data-height="1080">
    <div class="hdr clip" id="al-hdr" data-start="0" data-duration="{d}" data-track-index="0">The Big Trap · Already Adjusted</div>
    <div class="box clip" id="al-1" data-start="{L('already', 1)}" data-duration="{d - L('already', 1):.1f}" data-track-index="1">
      <div class="k">✔ Purchases (Adjusted) ₹ 2,90,000</div>
      <span class="ln" id="al-1a">= Opening Stock + Purchases − Purchases Return − Closing Stock</span>
      <span class="ln" id="al-1b">Trading A/c: only Adjusted Purchases · <span class="no">no Opening Stock, no Closing Stock</span></span>
      <span class="ln" id="al-1c">Closing Stock ₹ 40,000 → <b>Balance Sheet (Assets) only</b></span>
    </div>
    <div class="box clip" id="al-2" data-start="{L('already', 4)}" data-duration="{d - L('already', 4):.1f}" data-track-index="2">
      <div class="k">✔ Wages Outstanding ₹ 8,000 &nbsp;·&nbsp; ✔ Prepaid Rent ₹ 3,000</div>
      <span class="ln" id="al-2a">Entries already passed · they are inside the Trial Balance</span>
      <span class="ln" id="al-2b">Wages Outstanding → <b>Liabilities only</b> · Prepaid Rent → <b>Assets only</b></span>
    </div>
    <div class="clip" id="al-stamp" data-start="{E('already', 5, 2.5)}" data-duration="{d - E('already', 5, 2.5):.1f}" data-track-index="3">DON'T ADJUST AGAIN!</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const card = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }}, t);
    const line = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4 }}, t);
    tl.fromTo("#al-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    card("#al-1", {L('already', 1)}); line("#al-1a", {L('already', 1, 2.0)}); line("#al-1b", {L('already', 2)}); line("#al-1c", {L('already', 3)});
    card("#al-2", {L('already', 4)}); line("#al-2a", {L('already', 4, 2.5)}); line("#al-2b", {L('already', 5)});
    tl.fromTo("#al-stamp", {{ opacity: 0, scale: 2.2 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.6)" }}, {E('already', 5, 2.5)});
    window.__timelines["already"] = tl;
  </script>
</template>
''')

# ---------- adjustment scenes ----------
FR = lambda n, dd: f"<span class=fr><span>{n}</span><span>{dd}</span></span>"
S = {
 "a1": dict(dur=DUR["a1"], title="Adjustment (i) · Salaries",
   adj="(i) Salaries for March, 2026 of <b>₹ 1,000</b> unpaid; balance included <b>₹ 800</b> paid in advance.",
   tables=[[("Salaries (as per Trial Balance)", "5,000", L("a1", 1), ""), ("Add: Outstanding Salaries (March, 2026)", "1,000", L("a1", 1, 3.0), ""),
            ("", "6,000", E("a1", 1), "tot"), ("Less: Prepaid Salaries (paid in advance)", "800", L("a1", 2), ""),
            ("Salaries charged to P&amp;L A/c", "5,200", L("a1", 2, 3.0), "tot")]],
   eff={"tr": [], "pl": [("To Salaries", "5,200", L("a1", 2, 3.5))],
        "bs": [("Outstanding Salaries (Liab.)", "1,000", L("a1", 3, 1.5)), ("Prepaid Salaries (Assets)", "800", L("a1", 3, 5.0))]}),
 "a2": dict(dur=DUR["a2"], title="Adjustment (ii) · Prepaid Insurance",
   adj="(ii) Insurance is prepaid to the extent of <b>₹ 2,000</b>.",
   tables=[[("Insurance (as per Trial Balance)", "5,000", L("a2", 1), ""), ("Less: Prepaid Insurance", "2,000", L("a2", 1, 2.0), ""),
            ("Insurance charged to P&amp;L A/c", "3,000", L("a2", 1, 4.0), "tot")]],
   eff={"tr": [], "pl": [("To Insurance", "3,000", L("a2", 1, 4.5))], "bs": [("Prepaid Insurance (Assets)", "2,000", L("a2", 2, 0.5))]}),
 "a3": dict(dur=DUR["a3"], title="Adjustment (iii) · Depreciation",
   adj="(iii) Depreciate Furniture by <b>10%</b> on original cost and Building by <b>5%</b>.",
   tables=[[("Building: 1,50,000 × " + FR(5, 100), "7,500", L("a3", 1), ""), ("Furniture: 60,000 × " + FR(10, 100), "6,000", L("a3", 2), ""),
            ("Total Depreciation", "13,500", L("a3", 3), "tot")],
           [("As per Trial Balance", "12,000", L("a3", 4), ""), ("Add: This year (10%)", "6,000", L("a3", 4, 2.5), ""),
            ("Total Provision", "18,000", L("a3", 4, 5.0), "tot")]],
   titles=["Depreciation to P&amp;L A/c", "Provision for Dep. on Furniture"],
   amt_at={"Building": E("a3", 1), "Furniture": E("a3", 2)},
   eff={"tr": [], "pl": [("Depreciation 7,500 + 6,000", "13,500", L("a3", 3, 1.0))],
        "bs": [("Furniture 60,000 − 18,000", "42,000", L("a3", 5, 2.0)), ("Building 1,50,000 − 7,500", "1,42,500", L("a3", 6, 2.0))]}),
 "a4": dict(dur=DUR["a4"], title="Adjustment (iv) · Goods for Personal Use",
   adj="(iv) Stock of <b>₹ 1,500</b> was taken by Ashok for his personal use.",
   tables=[[("Purchases (Adjusted) as per Trial Balance", "2,90,000", L("a4", 1), ""), ("Less: Goods taken by Ashok (Drawings)", "1,500", L("a4", 1, 3.0), ""),
            ("Purchases in Trading A/c", "2,88,500", L("a4", 1, 6.0), "tot"), ("Drawings: 5,000 + 1,500", "6,500", L("a4", 2, 3.0), "")]],
   eff={"tr": [("Purchases (Adjusted) − 1,500", "2,88,500", L("a4", 1, 6.5))], "pl": [],
        "bs": [("Drawings (less from Capital)", "6,500", L("a4", 2, 4.0))]}),
 "a5": dict(dur=DUR["a5"], title="Adjustment (v) · Provision for Doubtful Debts",
   adj="(v) Make a Provision for Doubtful Debts equal to <b>10%</b> of Sundry Debtors.",
   tables=[[("New Provision: 25,000 × " + FR(10, 100), "2,500", L("a5", 1), ""),
            ("Bad Debts (as per Trial Balance)", "2,000", L("a5", 2), ""), ("Add: New Provision", "2,500", L("a5", 2, 3.0), ""),
            ("Charge to P&amp;L A/c", "4,500", E("a5", 2), "tot")]],
   amt_at={"New Provision": E("a5", 1)},
   eff={"tr": [], "pl": [("Bad Debts + Provision", "4,500", E("a5", 2, 0.2))],
        "bs": [("Sundry Debtors 25,000 − 2,500", "22,500", L("a5", 3, 3.0))]}),
}
gen_adj.OUT = COMP
for k, v in S.items():
    gen_adj.build(k, v)

# ---------- accounts ----------
A = {
 "trading": dict(dur=DUR["trading"], fs=44, title="Trading Account", sub="of Ashok for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Purchases (Adjusted)", "2,90,000", "", L("trading", 1), ""),
      ("Less: Goods taken by Ashok", "1,500", "2,88,500", L("trading", 1, 5.0), ""),
      ("To Wages", "", "10,000", L("trading", 2), ""),
      ("To Gross Profit c/d", "", "2,31,000", L("trading", 4), "bal")],
   R=[("By Sales", "", "5,29,500", L("trading", 3), ""),
      (W("(no Closing Stock — already adjusted)"), "", "", L("trading", 3, 3.5), "")],
   totL=("5,29,500", L("trading", 4, 0.3)), totR=("5,29,500", L("trading", 3, 4.5)),
   stamp=("Gross Profit ₹ 2,31,000", L("trading", 4, 0.6))),
 "pl": dict(dur=DUR["pl"], fs=42, title="Profit &amp; Loss Account", sub="of Ashok for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Salaries " + W("(5,000 + 1,000 − 800)"), "", "5,200", L("pl", 2), ""),
      ("To Bad Debts " + W("(2,000 + 2,500)"), "", "4,500", L("pl", 3), ""),
      ("To Rent", "", "5,000", L("pl", 4), ""),
      ("To Insurance " + W("(5,000 − 2,000)"), "", "3,000", L("pl", 4, 2.0), ""),
      ("To Depreciation: Building", "7,500", "", L("pl", 5), ""),
      ("Furniture", "6,000", "13,500", L("pl", 5, 3.5), ""),
      ("To Net Profit " + W("(to Capital A/c)"), "", "2,00,300", L("pl", 6), "bal")],
   R=[("By Gross Profit b/d", "", "2,31,000", L("pl", 1), ""),
      ("By Apprentice Premium", "", "500", L("pl", 1, 3.5), "")],
   totL=("2,31,500", L("pl", 6, 0.4)), totR=("2,31,500", L("pl", 1, 6.0)),
   stamp=("Net Profit ₹ 2,00,300", L("pl", 6, 0.7))),
 "bs": dict(dur=DUR["bs"], fs=40, title="Balance Sheet", sub="of Ashok as at 31st March, 2026",
   heads=("", ""), cols=("Liabilities", "Assets"),
   L=[("Capital", "30,000", "", L("bs", 1), ""),
      ("Add: Net Profit", "2,00,300", "", L("bs", 1, 2.5), ""),
      ("Less: Drawings " + W("(5,000 + 1,500)"), "6,500", "2,23,800", L("bs", 1, 6.0), ""),
      ("Sundry Creditors", "", "20,000", L("bs", 2), ""),
      ("Wages Outstanding", "", "8,000", L("bs", 2, 2.5), ""),
      ("Outstanding Salaries", "", "1,000", L("bs", 2, 5.0), "")],
   R=[("Building " + W("(1,50,000 − 7,500)"), "", "1,42,500", L("bs", 4, 1.0), ""),
      ("Furniture " + W("(60,000 − 18,000)"), "", "42,000", L("bs", 4, 4.0), ""),
      ("Closing Stock", "", "40,000", L("bs", 5), ""),
      ("Sundry Debtors " + W("(25,000 − 2,500)"), "", "22,500", L("bs", 5, 2.5), ""),
      ("Prepaid Rent", "", "3,000", L("bs", 6), ""),
      ("Prepaid Salaries", "", "800", L("bs", 6, 2.0), ""),
      ("Prepaid Insurance", "", "2,000", L("bs", 6, 4.0), "")],
   totL=("2,52,800", L("bs", 3)), totR=("2,52,800", L("bs", 7)),
   stamp=("TALLIED ✓ ₹ 2,52,800", L("bs", 7, 3.0))),
}
gen_acc.OUT = COMP
for k, v in A.items():
    gen_acc.build(k, v)

# ---------- traps ----------
d = DUR["traps"]
s = rd("traps.html")
boxes = [("Trap 1 · Purchases (Adjusted)", 'No Opening / Closing Stock in Trading · Closing Stock <b>₹ 40,000</b> → Balance Sheet only'),
         ("Trap 2 · Already in the Trial Balance", 'Wages O/s <b>₹ 8,000</b> → Liabilities · Prepaid Rent <b>₹ 3,000</b> → Assets · <span class="x">twice</span>'),
         ("Trap 3 · Provision for Depreciation", 'Furniture ₹ 60,000 − total provision ₹ 18,000 = <b>₹ 42,000</b>'),
         ("Trap 4 · Goods for Personal Use", 'Purchases − <b>₹ 1,500</b> · Drawings + <b>₹ 1,500</b>')]
for i, (k, ln) in enumerate(boxes, 1):
    s = re.sub(rf'<div class="box clip" id="tp-{i}" data-start="[0-9.]+" data-duration="[0-9.]+"(.*?)<div class="k">.*?</div><span class="ln">.*?</span></div>',
               lambda m: f'<div class="box clip" id="tp-{i}" data-start="{L("traps", i)}" data-duration="{d - L("traps", i):.1f}"{m.group(1)}<div class="k">{k}</div><span class="ln">{ln}</span></div>', s, flags=re.S)
s = s.replace('data-duration="42.9"', f'data-duration="{d}"').replace(".ln { display: block; font-size: 46px;", ".ln { display: block; font-size: 42px;")
a = s.index('    card("#tp-1"'); b = s.index('    window.__timelines["traps"]')
s = s[:a] + f'    card("#tp-1", {L("traps", 1)}); card("#tp-2", {L("traps", 2)}); card("#tp-3", {L("traps", 3)}); card("#tp-4", {L("traps", 4)});\n    tl.to("#tp-2 .x", {{ scale: 1.15, duration: 0.3, yoyo: true, repeat: 3 }}, {L("traps", 2, 5.0)});\n' + s[b:]
wr("traps.html", s)

# ---------- hook & recap: remap old Q39 times to the new voice lines ----------
def remap(s, old_starts, new_starts, dur_old, dur_new):
    def f(t):
        t = float(t); k = max(i for i, o in enumerate(old_starts) if o <= t + 1e-6)
        return round(t - old_starts[k] + new_starts[k], 2)
    s = re.sub(r'data-start="([0-9.]+)" data-duration="([0-9.]+)"',
               lambda m: f'data-start="{f(m.group(1))}" data-duration="{max(dur_new - f(m.group(1)), 0.5):.1f}"', s)
    s = re.sub(r'(\}, |slide\("[^"]+", |pop\("[^"]+", )([0-9]+\.[0-9]+|[0-9]+)\)', lambda m: f"{m.group(1)}{f(m.group(2))})", s)
    s = s.replace(f"duration: {dur_old}, ease", f"duration: {dur_new}, ease")
    return s
q39T = json.load(open(os.path.join(PROJ, "..", "tsg-ch19-q39", "voice-script", "timing.json")))
# hook: Q39 events -> new lines. Q39 ref card (line 0) -> new line 1; "8 adjustments" (6.2) -> new line 2; "Will it tally?" (14.5) -> new line 3
old = [0.0, 0.301, 6.2, 14.0]
new = [0.0, L("hook", 1), L("hook", 2), L("hook", 3)]
s = rd("hook.html")
s = remap(s, old, new, 18.5, DUR["hook"])
s = s.replace("Question 39 · Manoj · Pg 19.91–19.92", "Question 38 · Ashok · Pg 19.90–19.91")
s = s.replace('<span class="g">8 adjustments</span> · 3 statements', 'Purchases <span class="g">ADJUSTED</span>?')
s = s.replace("WILL IT TALLY?", "CLOSING STOCK?").replace("Let's solve it", "Where does it go?")
quiz_end = L("hook", 1)
s = s.replace('<div id="hook-same"', f'<div id="hook-quiz" class="clip" data-start="0.3" data-duration="{quiz_end - 0.3:.1f}" data-track-index="8">Q39 quiz answer: <span class="g">₹ 6,000 ✓</span></div>\n    <div id="hook-same"')
s = s.replace("#hook-same .g { color: #F5B700; }", "#hook-same .g { color: #F5B700; }\n    #hook-quiz { position: absolute; left: 130px; top: 800px; width: 1140px; font-family: \"Archivo Black\", sans-serif; font-size: 60px; color: #fff; }\n    #hook-quiz .g { color: #7EE2A0; }")
s = s.replace('window.__timelines["hook"] = tl;', 'tl.fromTo("#hook-quiz", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0.35);\n    window.__timelines["hook"] = tl;')
wr("hook.html", s)

s = rd("recap.html")
old = [0.3 + x[0] for x in q39T["recap"]["lines"]]
new = [L("recap", i) for i in range(7)]
s = remap(s, [0.0] + old[1:], [0.0] + new[1:], 33.0, DUR["recap"])
s = s.replace("Recap · T.S. Grewal Q 39", "Recap · T.S. Grewal Q 38").replace("₹ 21,910", "₹ 2,31,000").replace("₹ 1,400<", "₹ 2,00,300<").replace("₹ 1,23,850 ✓", "₹ 2,52,800 ✓")
s = s.replace('Every adjustment has <span style="color:#F5B700">two effects</span>', 'In the Trial Balance? <span style="color:#F5B700">Show it once</span>')
s = s.replace("Check your answer: GP 21,910 · NP 1,400", "Check: GP 2,31,000 · NP 2,00,300")
wr("recap.html", s)

# ---------- index ----------
order = ["hook", "question", "adjust", "already", "a1", "a2", "a3", "a4", "a5", "trading", "pl", "bs", "traps", "recap"]
t0 = 0.0; divs = []; aud = []; chapters = []
for n in order:
    dd = DUR[n]
    divs.append(f'      <div id="{n}" data-composition-id="{n}" data-composition-src="compositions/{n}.html" data-start="{round(t0, 1)}" data-duration="{dd}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>')
    aud.append(f'      <audio id="vo-{n}" class="clip" src="assets/voice/{n}.wav" data-start="{round(t0 + 0.3, 1)}" data-duration="{T[n]["dur"]}" data-track-index="5" data-volume="0.85"></audio>')
    chapters.append(f"{int(t0 // 60)}:{int(t0 % 60):02d} {n}")
    t0 += dd
src = open(os.path.join(PROJ, "..", "tsg-ch19-q39", "index.html")).read()
head = src.split('<div id="root"')[0].replace('"default":"1,23,850"', '"default":"2,52,800"')
tail = src[src.index("    <script>\n      window.__timelines"):]
open(os.path.join(PROJ, "index.html"), "w").write(head + f'<div id="root" data-composition-id="main" data-start="0" data-duration="{round(t0, 1)}" data-width="1920" data-height="1080">\n' + "\n".join(divs + aud) + "\n    </div>\n" + tail)
print("total", round(t0, 1)); print("\n".join(chapters))
