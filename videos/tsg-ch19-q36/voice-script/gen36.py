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
dr = [("Drawings", "60,000", ""), ("Opening Stock", "75,000", ""), ("Purchases", "15,95,000", "st"), ("Freight on Purchases", "25,000", "st"),
      ("Wages (11 months up to February, 2026)", "66,000", "hid"), ("Salaries", "1,40,000", ""), ("Postages and Courier", "12,000", ""),
      ("Printing and Stationery", "18,000", ""), ("Miscellaneous Expenses", "30,000", ""), ("Investments", "1,00,000", "st"),
      ("Sundry Debtors", "2,50,000", "st"), ("Bad Debts", "15,000", "st"), ("Building", "3,00,000", "st"), ("Machinery", "5,00,000", "st"),
      ("Furniture", "40,000", "st"), ("Commission on Sales", "45,000", "st"), ("Insurance (up to 31st July, 2026)", "24,000", "hid"), ("Bank Balance", "1,50,000", "")]
cr = [("Capital", "8,00,000", ""), ("Sales", "23,10,000", "st"), ("Sundry Creditors", "3,00,000", ""), ("Discount Received", "15,000", ""),
      ("Provision for Doubtful Debts", "8,000", "st"), ("Interest on Investments", "12,000", "")]
def rows(lst):
    out = []
    for n, a, k in lst:
        mark = ' <span class="st">★</span>' if k == "st" else (' <span class="hidm">🔍 hidden</span>' if k == "hid" else "")
        out.append(f'<tr class="{"hid" if k == "hid" else ""}"><td>{n}{mark}</td><td class="r">{a}</td></tr>')
    return "\n".join(out)
d = DUR["question"]
wr("question.html", f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .hdr {{ position: absolute; left: 100px; top: 40px; font-family: "Archivo Black", sans-serif; font-size: 58px; color: #F5B700; }}
    .ref {{ position: absolute; right: 100px; top: 60px; font-size: 32px; font-weight: 700; color: rgba(255,255,255,0.85); }}
    #q-lead {{ position: absolute; left: 100px; top: 128px; width: 1720px; font-family: "EB Garamond", serif; font-size: 38px; }}
    .card {{ position: absolute; top: 190px; background: #FFFDF5; color: #111; border-radius: 16px; padding: 10px 16px 14px; font-family: "EB Garamond", serif; box-shadow: 0 12px 30px rgba(0,0,0,0.3); }}
    .card .t {{ font-family: "Archivo Black", sans-serif; font-size: 28px; margin-bottom: 4px; }}
    #q-d1, #q-d2 {{ border-top: 10px solid #0057B8; }} #q-d1 .t, #q-d2 .t {{ color: #0057B8; }}
    #q-c {{ border-top: 10px solid #CC0000; }} #q-c .t {{ color: #CC0000; }}
    #q-d1 {{ left: 100px; width: 560px; }} #q-d2 {{ left: 680px; width: 560px; }} #q-c {{ left: 1260px; width: 560px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 33px; }}
    td {{ padding: 0 8px; border: 2px solid #000; line-height: 1.18; }}
    td.r {{ text-align: right; width: 150px; white-space: nowrap; }}
    .st {{ color: #CC0000; font-weight: 700; display: inline-block; }}
    .hidm {{ color: #CC0000; font-weight: 800; font-size: 0.68em; font-family: "Inter", sans-serif; display: inline-block; }}
    #q-tot {{ position: absolute; left: 100px; top: 935px; width: 1720px; height: 96px; background: #F5B700; color: #0B1B3F; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-family: "Archivo Black", sans-serif; font-size: 44px; }}
    #q-note {{ position: absolute; left: 1260px; top: 620px; width: 560px; background: #CC0000; color: #fff; border-radius: 16px; padding: 14px 22px; font-size: 34px; font-weight: 800; line-height: 1.25; }}
  </style>
  <div id="root" data-composition-id="question" data-width="1920" data-height="1080">
    <div class="hdr clip" id="q-hdr" data-start="0" data-duration="{d}" data-track-index="0">The Question</div>
    <div class="ref clip" id="q-ref" data-start="0" data-duration="{d}" data-track-index="1">T.S. Grewal · Q 36 · Pg 19.89</div>
    <div class="clip" id="q-lead" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">Following is the Trial Balance of Karman on 31st March, 2026:</div>
    <div class="card clip" id="q-d1" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="3"><div class="t">Debit (₹)</div><table>
{rows(dr[:9])}
    </table></div>
    <div class="card clip" id="q-d2" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="4"><div class="t">Debit (₹) contd.</div><table>
{rows(dr[9:])}
    </table></div>
    <div class="card clip" id="q-c" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="5"><div class="t">Credit (₹)</div><table>
{rows(cr)}
    </table></div>
    <div class="clip" id="q-note" data-start="{L('question', 4)}" data-duration="{d - L('question', 4):.1f}" data-track-index="6">🔍 Read the headings: 2 hidden adjustments!</div>
    <div class="clip" id="q-tot" data-start="{L('question', 3)}" data-duration="{d - L('question', 3):.1f}" data-track-index="7">Total Debit ₹ 34,45,000 &nbsp;=&nbsp; Total Credit ₹ 34,45,000 ✓</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#q-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    tl.fromTo("#q-ref", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.2);
    tl.fromTo("#q-lead", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.3);
    tl.fromTo(["#q-d1", "#q-d2", "#q-c"], {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.5, stagger: 0.2, ease: "power3.out" }}, 0.8);
    tl.fromTo(["#q-d1", "#q-d2"], {{ boxShadow: "0 0 0 0 rgba(0,0,139,0)" }}, {{ boxShadow: "0 0 0 8px rgba(0,0,139,0.8)", duration: 0.4, yoyo: true, repeat: 1, repeatDelay: 8 }}, {L('question', 1)});
    tl.fromTo("#q-c", {{ boxShadow: "0 0 0 0 rgba(0,0,139,0)" }}, {{ boxShadow: "0 0 0 8px rgba(0,0,139,0.8)", duration: 0.4, yoyo: true, repeat: 1, repeatDelay: 5 }}, {L('question', 2)});
    tl.fromTo("#q-tot", {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)" }}, {L('question', 3)});
    tl.fromTo("#q-note", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.4 }}, {L('question', 4)});
    tl.to("tr.hid td", {{ backgroundColor: "rgba(204,0,0,0.25)", duration: 0.4 }}, {L('question', 4, 1.5)});
    tl.to(".hidm", {{ scale: 1.3, duration: 0.3, yoyo: true, repeat: 5, ease: "sine.inOut" }}, {L('question', 4, 2.0)});
    window.__timelines["question"] = tl;
  </script>
</template>
''')

# ---------- adjust (list of 5 + pause) ----------
items = [("(i)", "Closing Stock <b>₹ 2,25,000</b>."),
         ("(ii)", "Machinery of <b>₹ 45,000</b> purchased on 1st October, 2025 was shown as Purchases. Freight paid on the Machinery was <b>₹ 5,000</b>, which is included in Freight on Purchases."),
         ("(iii)", "Commission is payable at <b>2.5%</b> on sales."),
         ("(iv)", "Investments were sold at <b>10%</b> profit, but the proceeds were credited to Sales Account."),
         ("(v)", "Write off further Bad Debts <b>₹ 10,000</b> and maintain Provision for Doubtful Debts at <b>5%</b> of Debtors."),
         ("(vi)", "Depreciate Building by <b>2.5% p.a.</b> and Machinery and Furniture at <b>10% p.a.</b>")]
s = rd("adjust.html")
a = s.index('<div class="clip" id="ad-card"'); b = s.index('<div class="clip" id="ad-pause"')
d = DUR["adjust"]; tp = L("adjust", 7)
s = s[:a] + f'<div class="clip" id="ad-card" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">\n' + \
    "\n".join(f'      <div class="it" id="ad-{i}"><span class="n">{n}</span><span class="tx">{t}</span></div>' for i, (n, t) in enumerate(items)) + \
    "\n    </div>\n    " + s[b:]
s = re.sub(r'data-start="[0-9.]+" data-duration="[0-9.]+" data-track-index="3"><span class="ic">', f'data-start="{tp}" data-duration="{d - tp:.1f}" data-track-index="3"><span class="ic">', s)
s = re.sub(r'data-duration="70.4"', f'data-duration="{d}"', s)
s = s.replace("The 8 Adjustments", "The 6 Adjustments").replace("T.S. Grewal · Q 39", "T.S. Grewal · Q 36")
a = s.index('    show("#ad-0"'); b = s.index('    tl.fromTo("#ad-pause"')
s = s[:a] + "".join(f'    show("#ad-{i}", {L("adjust", i + 1)});\n' for i in range(6)) + s[b:]
s = re.sub(r'(tl\.fromTo\("#ad-pause".*?\}, )[0-9.]+\);', lambda m: f"{m.group(1)}{tp + 0.1:.2f});", s)
s = re.sub(r'(tl\.to\("#ad-pause \.ic".*?\}, )[0-9.]+\);', lambda m: f"{m.group(1)}{tp + 0.7:.2f});", s)
s = s.replace(".it { display: flex; gap: 14px; font-size: 40px;", ".it { display: flex; gap: 14px; font-size: 42px;").replace("#ad-pause { position: absolute; left: 560px; top: 905px;", "#ad-pause { position: absolute; left: 560px; top: 860px;")
wr("adjust.html", s)

# ---------- hidden adjustments ----------
d = DUR["hidden"]
FRh = lambda n, dd: f'<span class="fr"><span>{n}</span><span>{dd}</span></span>'
wr("hidden.html", f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .hdr {{ position: absolute; left: 100px; top: 40px; font-family: "Archivo Black", sans-serif; font-size: 56px; color: #F5B700; }}
    .box {{ position: absolute; left: 100px; width: 1720px; background: #FFFDF5; color: #111; border-radius: 16px; padding: 14px 30px; border-left: 16px solid #CC0000; font-family: "EB Garamond", serif; box-shadow: 0 12px 30px rgba(0,0,0,0.3); }}
    .k {{ font-family: "Archivo Black", sans-serif; font-size: 34px; color: #CC0000; margin-bottom: 4px; }}
    .ln {{ display: block; font-size: 44px; line-height: 1.35; }}
    .ln b {{ color: #0057B8; }}
    .fr {{ display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; font-size: 0.8em; line-height: 1.05; margin: 0 0.15em; }}
    .fr > span:last-child {{ border-top: 2px solid currentColor; padding: 0 0.15em; }}
    #hd-1 {{ top: 140px; }} #hd-2 {{ top: 520px; }}
    #hd-bs {{ position: absolute; left: 100px; top: 900px; width: 1720px; background: #1E6B34; color: #fff; border-radius: 16px; padding: 16px 30px; font-size: 38px; font-weight: 800; text-align: center; }}
  </style>
  <div id="root" data-composition-id="hidden" data-width="1920" data-height="1080">
    <div class="hdr clip" id="hd-hdr" data-start="0" data-duration="{d}" data-track-index="0">🔍 The 2 Hidden Adjustments</div>
    <div class="box clip" id="hd-1" data-start="{L('hidden', 1)}" data-duration="{d - L('hidden', 1):.1f}" data-track-index="1">
      <div class="k">Wages (11 months up to February, 2026) ₹ 66,000</div>
      <span class="ln" id="hd-1a">March wages are still unpaid → <b>Outstanding Wages</b></span>
      <span class="ln" id="hd-1b">66,000 × {FRh(1, 11)} = <b>₹ 6,000</b> &nbsp;·&nbsp; Wages for the year = 66,000 + 6,000 = <b>₹ 72,000</b></span>
    </div>
    <div class="box clip" id="hd-2" data-start="{L('hidden', 3)}" data-duration="{d - L('hidden', 3):.1f}" data-track-index="2">
      <div class="k">Insurance (up to 31st July, 2026) ₹ 24,000</div>
      <span class="ln" id="hd-2a">April to July 2026 = 4 months of next year → <b>Prepaid Insurance</b></span>
      <span class="ln" id="hd-2b">24,000 × {FRh(4, 12)} = <b>₹ 8,000</b> &nbsp;·&nbsp; Insurance expense = 24,000 − 8,000 = <b>₹ 16,000</b></span>
    </div>
    <div class="clip" id="hd-bs" data-start="{L('hidden', 5)}" data-duration="{d - L('hidden', 5):.1f}" data-track-index="3">Balance Sheet: Outstanding Wages ₹ 6,000 (Liability) · Prepaid Insurance ₹ 8,000 (Asset)</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const card = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }}, t);
    const line = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4 }}, t);
    tl.fromTo("#hd-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    card("#hd-1", {L('hidden', 1)}); line("#hd-1a", {L('hidden', 1, 3.0)}); line("#hd-1b", {L('hidden', 2)});
    card("#hd-2", {L('hidden', 3)}); line("#hd-2a", {L('hidden', 3, 3.5)}); line("#hd-2b", {L('hidden', 4)});
    tl.fromTo("#hd-bs", {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)" }}, {L('hidden', 5)});
    window.__timelines["hidden"] = tl;
  </script>
</template>
''')

# ---------- adjustment scenes ----------
FR = lambda n, dd: f"<span class=fr><span>{n}</span><span>{dd}</span></span>"
S = {
 "a1": dict(dur=DUR["a1"], title="Adjustment (ii) · Machinery shown as Purchases",
   adj="(ii) Machinery <b>₹ 45,000</b> bought on 1st October, 2025 shown as Purchases; its freight <b>₹ 5,000</b> is in Freight on Purchases.",
   tables=[[("Purchases (as per T.B.)", "15,95,000", L("a1", 2), ""), ("Less: Machinery", "45,000", L("a1", 2, 3.0), ""),
            ("Purchases in Trading A/c", "15,50,000", E("a1", 2), "tot")],
           [("Freight on Purchases (T.B.)", "25,000", L("a1", 3), ""), ("Less: Freight on Machinery", "5,000", L("a1", 3, 3.0), ""),
            ("Freight in Trading A/c", "20,000", E("a1", 3), "tot")]],
   titles=["Purchases (capital, not goods!)", "Freight on Purchases"],
   eff={"tr": [("Purchases − 45,000", "15,50,000", E("a1", 2, 0.2)), ("Freight − 5,000", "20,000", E("a1", 3, 0.2))], "pl": [],
        "bs": [("Machinery 5,00,000 + 45,000 + 5,000", "5,50,000", L("a1", 4, 4.0))]}),
 "a2": dict(dur=DUR["a2"], title="Adjustment (iv) · Investments Sold",
   adj="(iv) Investments were sold at <b>10%</b> profit, but the proceeds were credited to Sales Account.",
   tables=[[("Cost of Investments (T.B.)", "1,00,000", L("a2", 1), ""), ("Add: Profit @ 10%", "10,000", L("a2", 1, 3.0), ""),
            ("Sale proceeds", "1,10,000", E("a2", 1), "tot")],
           [("Sales (T.B.)", "23,10,000", L("a2", 2), ""), ("Less: Sale proceeds", "1,10,000", L("a2", 2, 3.0), ""),
            ("Corrected Sales", "22,00,000", E("a2", 2), "tot")]],
   titles=["Sale of Investments", "Sales Account"],
   eff={"tr": [("Sales − 1,10,000", "22,00,000", E("a2", 2, 0.2))], "pl": [("By Profit on Sale of Investments", "10,000", L("a2", 3, 1.0))],
        "bs": [("Investments (all sold)", "Nil", L("a2", 4, 1.0))]}),
 "a3": dict(dur=DUR["a3"], title="Adjustment (iii) · Commission on Sales",
   adj="(iii) Commission is payable at <b>2.5%</b> on sales.",
   tables=[[("Commission: 22,00,000 × " + FR("2.5", 100), "55,000", L("a3", 1), ""), ("Less: Already paid (T.B.)", "45,000", L("a3", 2), ""),
            ("Outstanding Commission", "10,000", E("a3", 2), "tot")]],
   amt_at={"Commission": E("a3", 1)},
   eff={"tr": [], "pl": [("To Commission 45,000 + 10,000", "55,000", L("a3", 3, 1.0))],
        "bs": [("Outstanding Commission (Liab.)", "10,000", L("a3", 3, 4.0))]}),
 "a4": dict(dur=DUR["a4"], title="Adjustment (v) · Bad Debts &amp; Provision",
   adj="(v) Write off further Bad Debts <b>₹ 10,000</b> and maintain Provision for Doubtful Debts at <b>5%</b> of Debtors.",
   tables=[[("Sundry Debtors (T.B.)", "2,50,000", L("a4", 1), ""), ("Less: Further Bad Debts", "10,000", L("a4", 1, 3.0), ""),
            ("Good Debtors", "2,40,000", E("a4", 1), "tot"), ("Less: New Provision " + FR(5, 100), "12,000", L("a4", 2), ""),
            ("Net Debtors", "2,28,000", L("a4", 5, 3.0), "tot")],
           [("Bad Debts (T.B.)", "15,000", L("a4", 3), ""), ("Add: Further Bad Debts", "10,000", L("a4", 3, 2.0), ""),
            ("Add: New Provision", "12,000", L("a4", 3, 4.0), ""), ("", "37,000", E("a4", 3), "tot"),
            ("Less: Old Provision", "8,000", L("a4", 4), ""), ("Charge to P&amp;L", "29,000", E("a4", 4), "tot")]],
   titles=["Debtors in the Balance Sheet", "Charge to P&amp;L A/c"],
   amt_at={"Less: New Provision": E("a4", 2)},
   eff={"tr": [], "pl": [("Bad Debts &amp; Provision", "29,000", E("a4", 4, 0.2))],
        "bs": [("Debtors 2,40,000 − 12,000", "2,28,000", L("a4", 5, 4.0))]}),
 "a5": dict(dur=DUR["a5"], title="Adjustment (vi) · Depreciation",
   adj="(vi) Depreciate Building by <b>2.5% p.a.</b> and Machinery and Furniture at <b>10% p.a.</b>",
   tables=[[("Building: 3,00,000 × " + FR("2.5", 100), "7,500", L("a5", 1), ""),
            ("Machinery (old): 5,00,000 × " + FR(10, 100), "50,000", L("a5", 2), ""),
            ("Machinery (new): 50,000 × " + FR(10, 100) + " × " + FR(6, 12), "2,500", L("a5", 3), ""),
            ("Furniture: 40,000 × " + FR(10, 100), "4,000", L("a5", 4), ""),
            ("Total Depreciation", "64,000", L("a5", 5), "tot")]],
   amt_at={"Building": E("a5", 1), "Machinery (old)": E("a5", 2), "Machinery (new)": E("a5", 3), "Furniture": E("a5", 4, 0.3)},
   eff={"tr": [], "pl": [("Depreciation", "64,000", L("a5", 5, 1.0))],
        "bs": [("Building 3,00,000 − 7,500", "2,92,500", L("a5", 5, 1.5)), ("Machinery 5,50,000 − 52,500", "4,97,500", L("a5", 5, 2.2)),
               ("Furniture 40,000 − 4,000", "36,000", L("a5", 5, 2.9))]}),
}

gen_adj.OUT = COMP
for k, v in S.items():
    gen_adj.build(k, v)

# ---------- accounts ----------
A = {
 "trading": dict(dur=DUR["trading"], fs=40, title="Trading Account", sub="of Karman for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Opening Stock", "", "75,000", L("trading", 1), ""),
      ("To Purchases", "15,95,000", "", L("trading", 2), ""),
      ("Less: Machinery", "45,000", "15,50,000", L("trading", 2, 4.0), ""),
      ("To Freight on Purchases", "25,000", "", L("trading", 3), ""),
      ("Less: Freight on Machinery", "5,000", "20,000", L("trading", 3, 2.5), ""),
      ("To Wages", "66,000", "", L("trading", 4), ""),
      ("Add: Outstanding Wages", "6,000", "72,000", L("trading", 4, 2.5), ""),
      ("To Gross Profit c/d", "", "7,08,000", L("trading", 7), "bal")],
   R=[("By Sales", "23,10,000", "", L("trading", 5), ""),
      ("Less: Sale of Investments", "1,10,000", "22,00,000", L("trading", 5, 4.0), ""),
      ("By Closing Stock", "", "2,25,000", L("trading", 6), "")],
   totL=("24,25,000", L("trading", 7, 0.3)), totR=("24,25,000", L("trading", 6, 3.0)),
   stamp=("Gross Profit ₹ 7,08,000", L("trading", 7, 0.6))),
 "pl": dict(dur=DUR["pl"], fs=36, title="Profit &amp; Loss Account", sub="of Karman for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Salaries", "", "1,40,000", L("pl", 3), ""),
      ("To Postages and Courier", "", "12,000", L("pl", 3, 2.5), ""),
      ("To Printing and Stationery", "", "18,000", L("pl", 4), ""),
      ("To Miscellaneous Expenses", "", "30,000", L("pl", 4, 2.5), ""),
      ("To Bad Debts &amp; Provision", "", "29,000", L("pl", 5), ""),
      ("To Commission " + W("(45,000 + 10,000)"), "", "55,000", L("pl", 6), ""),
      ("To Insurance " + W("(24,000 − 8,000)"), "", "16,000", L("pl", 7), ""),
      ("To Depreciation: Building", "7,500", "", L("pl", 8), ""),
      ("Machinery", "52,500", "", L("pl", 8, 2.0), ""),
      ("Furniture", "4,000", "64,000", L("pl", 8, 4.0), ""),
      ("To Net Profit " + W("(to Capital A/c)"), "", "3,81,000", L("pl", 9), "bal")],
   R=[("By Gross Profit b/d", "", "7,08,000", L("pl", 1), ""),
      ("By Discount Received", "", "15,000", L("pl", 1, 3.0), ""),
      ("By Interest on Investments", "", "12,000", L("pl", 2), ""),
      ("By Profit on Sale of Investments", "", "10,000", L("pl", 2, 2.5), "")],
   totL=("7,45,000", L("pl", 9, 0.4)), totR=("7,45,000", E("pl", 2)),
   stamp=("Net Profit ₹ 3,81,000", L("pl", 9, 0.7))),
 "bs": dict(dur=DUR["bs"], fs=36, title="Balance Sheet", sub="of Karman as at 31st March, 2026",
   heads=("", ""), cols=("Liabilities", "Assets"),
   L=[("Capital", "8,00,000", "", L("bs", 1), ""),
      ("Add: Net Profit", "3,81,000", "", L("bs", 1, 2.5), ""),
      ("Less: Drawings", "60,000", "11,21,000", L("bs", 1, 6.0), ""),
      ("Sundry Creditors", "", "3,00,000", L("bs", 2), ""),
      ("Outstanding Wages", "", "6,000", L("bs", 2, 2.5), ""),
      ("Outstanding Commission", "", "10,000", L("bs", 2, 4.5), "")],
   R=[("Building " + W("(3,00,000 − 7,500)"), "", "2,92,500", L("bs", 4, 1.0), ""),
      ("Machinery " + W("(5,50,000 − 52,500)"), "", "4,97,500", L("bs", 4, 5.0), ""),
      ("Furniture " + W("(40,000 − 4,000)"), "", "36,000", L("bs", 5), ""),
      ("Closing Stock", "", "2,25,000", L("bs", 5, 2.5), ""),
      ("Sundry Debtors " + W("(2,40,000 − 12,000)"), "", "2,28,000", L("bs", 6), ""),
      ("Prepaid Insurance", "", "8,000", L("bs", 6, 3.0), ""),
      ("Bank Balance", "", "1,50,000", L("bs", 6, 5.0), "")],
   totL=("14,37,000", L("bs", 3)), totR=("14,37,000", L("bs", 7)),
   stamp=("TALLIED ✓ ₹ 14,37,000", L("bs", 7, 3.0))),
}

gen_acc.OUT = COMP
for k, v in A.items():
    gen_acc.build(k, v)

# ---------- traps ----------
d = DUR["traps"]
s = rd("traps.html")
boxes = [("Trap 1 · Hidden Adjustments", 'Wages (11 months) → O/s <b>₹ 6,000</b> · Insurance up to July → Prepaid <b>₹ 8,000</b>'),
         ("Trap 2 · Machinery in Purchases", 'Purchases − <b>₹ 45,000</b> · Freight − <b>₹ 5,000</b> · Machinery + <b>₹ 50,000</b>'),
         ("Trap 3 · Commission on Corrected Sales", '2.5% of <b>₹ 22,00,000</b> = ₹ 55,000 · <span class="x">₹ 23,10,000</span>'),
         ("Trap 4 · New Machine for 6 Months", '₹ 50,000 × 10% for 6 months only = <b>₹ 2,500</b>')]
for i, (k, ln) in enumerate(boxes, 1):
    s = re.sub(rf'<div class="box clip" id="tp-{i}" data-start="[0-9.]+" data-duration="[0-9.]+"(.*?)<div class="k">.*?</div><span class="ln">.*?</span></div>',
               lambda m: f'<div class="box clip" id="tp-{i}" data-start="{L("traps", i)}" data-duration="{d - L("traps", i):.1f}"{m.group(1)}<div class="k">{k}</div><span class="ln">{ln}</span></div>', s, flags=re.S)
s = s.replace('data-duration="42.9"', f'data-duration="{d}"').replace(".ln { display: block; font-size: 46px;", ".ln { display: block; font-size: 42px;")
a = s.index('    card("#tp-1"'); b = s.index('    window.__timelines["traps"]')
s = s[:a] + f'    card("#tp-1", {L("traps", 1)}); card("#tp-2", {L("traps", 2)}); card("#tp-3", {L("traps", 3)}); card("#tp-4", {L("traps", 4)});\n    tl.to("#tp-3 .x", {{ scale: 1.15, duration: 0.3, yoyo: true, repeat: 3 }}, {L("traps", 3, 5.0)});\n' + s[b:]
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
s = s.replace("Question 39 · Manoj · Pg 19.91–19.92", "Question 36 · Karman · Pg 19.89")
s = s.replace('<span class="g">8 adjustments</span> · 3 statements', 'TWO <span class="g">hidden</span> adjustments')
s = s.replace("WILL IT TALLY?", "SPOT THEM?")
quiz_end = L("hook", 1)
s = s.replace('<div id="hook-same"', f'<div id="hook-quiz" class="clip" data-start="0.3" data-duration="{quiz_end - 0.3:.1f}" data-track-index="8">Q38 quiz answer: <span class="g">₹ 2,87,500 ✓</span></div>\n    <div id="hook-same"')
s = s.replace("#hook-same .g { color: #F5B700; }", "#hook-same .g { color: #F5B700; }\n    #hook-quiz { position: absolute; left: 130px; top: 800px; width: 1140px; font-family: \"Archivo Black\", sans-serif; font-size: 60px; color: #fff; }\n    #hook-quiz .g { color: #7EE2A0; }")
s = s.replace('window.__timelines["hook"] = tl;', 'tl.fromTo("#hook-quiz", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0.35);\n    window.__timelines["hook"] = tl;')
wr("hook.html", s)

s = rd("recap.html")
old = [0.3 + x[0] for x in q39T["recap"]["lines"]]
new = [L("recap", i) for i in range(7)]
s = remap(s, [0.0] + old[1:], [0.0] + new[1:], 33.0, DUR["recap"])
s = s.replace("Recap · T.S. Grewal Q 39", "Recap · T.S. Grewal Q 36").replace("₹ 21,910", "₹ 7,08,000").replace("₹ 1,400<", "₹ 3,81,000<").replace("₹ 1,23,850 ✓", "₹ 14,37,000 ✓")
s = s.replace('Every adjustment has <span style="color:#F5B700">two effects</span>', 'Read the headings: <span style="color:#F5B700">hidden adjustments</span>')
s = s.replace("Check your answer: GP 21,910 · NP 1,400", "Check: GP 7,08,000 · NP 3,81,000")
wr("recap.html", s)

# ---------- index ----------
order = ["hook", "question", "adjust", "hidden", "a1", "a2", "a3", "a4", "a5", "trading", "pl", "bs", "traps", "recap"]
t0 = 0.0; divs = []; aud = []; chapters = []
for n in order:
    dd = DUR[n]
    divs.append(f'      <div id="{n}" data-composition-id="{n}" data-composition-src="compositions/{n}.html" data-start="{round(t0, 1)}" data-duration="{dd}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>')
    aud.append(f'      <audio id="vo-{n}" class="clip" src="assets/voice/{n}.wav" data-start="{round(t0 + 0.3, 1)}" data-duration="{T[n]["dur"]}" data-track-index="5" data-volume="0.85"></audio>')
    chapters.append(f"{int(t0 // 60)}:{int(t0 % 60):02d} {n}")
    t0 += dd
src = open(os.path.join(PROJ, "..", "tsg-ch19-q39", "index.html")).read()
head = src.split('<div id="root"')[0].replace('"default":"1,23,850"', '"default":"14,37,000"')
tail = src[src.index("    <script>\n      window.__timelines"):]
open(os.path.join(PROJ, "index.html"), "w").write(head + f'<div id="root" data-composition-id="main" data-start="0" data-duration="{round(t0, 1)}" data-width="1920" data-height="1080">\n' + "\n".join(divs + aud) + "\n    </div>\n" + tail)

GREY = [
    ('color: #fff; }', 'color: #111; }', '#root'),
]
def grey(txt):
    txt = txt.replace('#root { position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }', '#root { position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #111; }')
    txt = txt.replace("#root {{ position: absolute; inset: 0; font-family: \"Inter\", sans-serif; color: #fff; }}", "")
    txt = re.sub(r"color:\s*#F5B700", "color: #00008B", txt)
    txt = txt.replace("#FFFDF5", "#B8B8B8").replace("background: #BDBDBD", "background: #A6A6A6")
    txt = re.sub(r"rgba\(255,\s*255,\s*255,\s*(0?\.\d+)\)", r"rgba(0,0,0,\1)", txt)
    txt = txt.replace("#7FB2FF", "#0057B8").replace("#D59CFF", "#6A0DAD").replace("#7EE2A0", "#1E6B34")
    txt = txt.replace("background: rgba(0,0,0,0.08); border: 3px solid rgba(0,0,0,0.25);", "background: rgba(0,0,0,0.06); border: 3px solid #808080;")
    txt = txt.replace('{ borderColor: "rgba(0,0,0,0.25)", duration: 2.0 }', '{ borderColor: "#808080", duration: 2.0 }')
    txt = txt.replace("#hook-quiz { position: absolute; left: 130px; top: 800px; width: 1140px; font-family: \"Archivo Black\", sans-serif; font-size: 60px; color: #fff; }",
                      "#hook-quiz { position: absolute; left: 130px; top: 800px; width: 1140px; font-family: \"Archivo Black\", sans-serif; font-size: 60px; color: #111; }")
    txt = txt.replace("#hook-title { position: absolute;", "#hook-title { color: #00008B; position: absolute;")
    txt = txt.replace(".ef .ln { display: flex; justify-content: space-between; gap: 12px; background: #B8B8B8;", ".ef .ln { display: flex; justify-content: space-between; gap: 12px; background: #A9A9A9;")
    txt = txt.replace("background-color: #0B1B3F;", "background-color: #C8C8C8;")
    txt = re.sub(r"(?<![-\w])color:\s*#CC0000", "color: #A80000", txt)
    txt = re.sub(r"(?<![-\w])color:\s*#C2185B", "color: #8E0E42", txt)
    txt = re.sub(r"(?<![-\w])color:\s*#1E8E3E", "color: #146C2E", txt)
    txt = re.sub(r"(?<![-\w])color:\s*#0057B8", "color: #004A9E", txt)
    return txt
for fn in os.listdir(COMP):
    fp = os.path.join(COMP, fn); txt = grey(open(fp).read()); open(fp, "w").write(txt)
ip = os.path.join(PROJ, "index.html"); txt = grey(open(ip).read()); open(ip, "w").write(txt)
print("total", round(t0, 1)); print("\n".join(chapters))
