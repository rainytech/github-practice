# Builds every Q35 (Shubho) scene + index.html from voice-script/timing.json (Rainy's voice).
# Run after tools/voice/build_voice_rainy.py:  python3 voice-script/gen35.py
# Fill-the-frame layout (user, 27 Nov 2026): tables and cards reach the bottom of the frame.
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
FR = lambda n, dd: f"<span class=fr><span>{n}</span><span>{dd}</span></span>"
FRCSS = ".fr { display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; font-size: 0.8em; line-height: 1.05; margin: 0 0.15em; }\n    .fr > span:last-child { border-top: 2px solid currentColor; padding: 0 0.15em; }"

# ---------- question: Debit column + Credit column, equal height down to the bottom ----------
dr = [("Land and Building", "50,000", "st"), ("Purchases (Adjusted)", "2,07,500", "ok"), ("Stock (31st March, 2026)", "45,000", "ok"),
      ("Wages", "45,300", ""), ("Salaries", "39,000", "st"), ("Office Expenses", "15,400", ""), ("Carriage Inwards", "1,200", ""),
      ("Carriage Outwards", "2,000", ""), ("Discount Allowed", "750", ""), ("Bad Debts", "1,200", "st"), ("Insurance", "1,500", "st"),
      ("Plant and Machinery", "50,000", "st"), ("Furniture and Fixtures", "20,000", "st"), ("Drawings", "20,000", ""),
      ("Sundry Debtors", "40,000", "st"), ("Cash at Bank", "16,000", ""), ("Office Equipments", "12,000", "st")]
cr = [("Discount Received", "1,200", ""), ("Sales", "3,83,500", ""), ("Capital Account", "1,15,000", "st"),
      ("Chatterji's Loan A/c <span class=sm>(Taken on 1st Oct., 2025 @ 18% p.a.)</span>", "25,000", "hid"),
      ("Commission", "1,500", ""), ("Sundry Creditors", "37,350", ""), ("Expenses Payable", "3,300", "ok")]
MK = {"st": ' <span class="st">★</span>', "hid": ' <span class="hidm">🔍</span>', "ok": ' <span class="okm">✔</span>', "": ""}
def rows(lst, tot):
    out = [f'<tr class="r{k}"><td>{n}{MK[k]}</td><td class="r">{a}</td></tr>' for n, a, k in lst]
    out.append(f'<tr class="tot"><td>Total</td><td class="r"><span class="tv">{tot}</span></td></tr>')
    return "\n".join(out)
d = DUR["question"]
wr("question.html", f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .hdr {{ position: absolute; left: 100px; top: 26px; font-family: "Archivo Black", sans-serif; font-size: 54px; color: #F5B700; }}
    .ref {{ position: absolute; right: 100px; top: 44px; font-size: 32px; font-weight: 700; color: rgba(255,255,255,0.85); }}
    #q-lead {{ position: absolute; left: 100px; top: 104px; width: 1720px; font-family: "EB Garamond", serif; font-size: 33px; line-height: 1.2; }}
    .card {{ position: absolute; top: 196px; height: 856px; display: flex; flex-direction: column; background: #FFFDF5; color: #111; border-radius: 16px; padding: 8px 16px 12px; font-family: "EB Garamond", serif; box-shadow: 0 12px 30px rgba(0,0,0,0.3); }}
    .card .t {{ font-family: "Archivo Black", sans-serif; font-size: 30px; margin-bottom: 4px; }}
    #q-d {{ left: 100px; width: 960px; border-top: 10px solid #0057B8; }} #q-d .t {{ color: #0057B8; }}
    #q-c {{ left: 1080px; width: 740px; border-top: 10px solid #CC0000; }} #q-c .t {{ color: #CC0000; }}
    #q-d table {{ flex: 1; height: 100%; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 37px; }}
    td {{ padding: 0 10px; border: 2px solid #000; line-height: 1.06; }}
    td.r {{ text-align: right; width: 170px; white-space: nowrap; }}
    #q-c td {{ padding: 2px 10px; line-height: 1.12; }}
    tr.tot td {{ font-weight: 700; border-top: 4px solid #000; }}
    .sm {{ color: #C2185B; font-style: italic; font-size: 0.78em; }}
    .st {{ color: #CC0000; font-weight: 700; display: inline-block; }}
    .hidm, .okm {{ display: inline-block; font-weight: 800; }} .okm {{ color: #1E8E3E; }}
    #q-leg {{ flex: 1; margin-top: 14px; border: 3px dashed #6A0DAD; border-radius: 12px; padding: 12px 18px; display: flex; flex-direction: column; justify-content: space-evenly; font-family: "Inter", sans-serif; font-size: 36px; font-weight: 700; color: #111; }}
    #q-leg .lt {{ font-family: "Archivo Black", sans-serif; color: #6A0DAD; font-size: 38px; }}
    #q-leg .g {{ display: inline-block; width: 52px; text-align: center; }}
  </style>
  <div id="root" data-composition-id="question" data-width="1920" data-height="1080">
    <div class="hdr clip" id="q-hdr" data-start="0" data-duration="{d}" data-track-index="0">The Question</div>
    <div class="ref clip" id="q-ref" data-start="0" data-duration="{d}" data-track-index="1">T.S. Grewal · Q 35</div>
    <div class="clip" id="q-lead" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">From the following Trial Balance of Shubho, prepare Trading and Profit &amp; Loss Accounts for the year ended 31st March, 2026 and Balance Sheet as at that date:</div>
    <div class="card clip" id="q-d" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="3"><div class="t">Debit Balances (₹)</div><table>
{rows(dr, "5,66,850")}
    </table></div>
    <div class="card clip" id="q-c" data-start="0.8" data-duration="{d - 0.8:.1f}" data-track-index="4"><div class="t">Credit Balances (₹)</div><table>
{rows(cr, "5,66,850")}
    </table>
      <div id="q-leg"><div class="lt">Read the headings!</div><div><span class="g st">★</span> in the adjustments</div><div><span class="g">🔍</span> hidden adjustment</div><div><span class="g okm">✔</span> already adjusted</div></div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#q-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    tl.fromTo("#q-ref", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.2);
    tl.fromTo("#q-lead", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.3);
    tl.fromTo(["#q-d", "#q-c"], {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.5, stagger: 0.2, ease: "power3.out" }}, 0.8);
    tl.fromTo("#q-leg", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 1.4);
    tl.fromTo("#q-d", {{ boxShadow: "0 0 0 0 rgba(0,0,139,0)" }}, {{ boxShadow: "0 0 0 8px rgba(0,0,139,0.8)", duration: 0.4, yoyo: true, repeat: 1, repeatDelay: 8 }}, {L('question', 1)});
    tl.fromTo("#q-c", {{ boxShadow: "0 0 0 0 rgba(0,0,139,0)" }}, {{ boxShadow: "0 0 0 8px rgba(0,0,139,0.8)", duration: 0.4, yoyo: true, repeat: 1, repeatDelay: 5 }}, {L('question', 2)});
    tl.fromTo("tr.tot td", {{ backgroundColor: "rgba(245,183,0,0.9)" }}, {{ backgroundColor: "rgba(245,183,0,0.35)", duration: 2.0 }}, {L('question', 3)});
    tl.fromTo(".tv", {{ scale: 0.6 }}, {{ scale: 1, duration: 0.45, ease: "back.out(2)" }}, {L('question', 3)});
    tl.to("tr.rok td", {{ backgroundColor: "rgba(30,142,62,0.28)", duration: 0.4 }}, {L('question', 4, 0.8)});
    tl.to("tr.rhid td", {{ backgroundColor: "rgba(204,0,0,0.25)", duration: 0.4 }}, {L('question', 4, 3.0)});
    tl.to(".hidm", {{ scale: 1.4, duration: 0.3, yoyo: true, repeat: 5, ease: "sine.inOut" }}, {L('question', 4, 3.4)});
    tl.fromTo("#q-leg", {{ borderColor: "#F5B700" }}, {{ borderColor: "#6A0DAD", duration: 2.0 }}, {L('question', 4, 3.4)});
    window.__timelines["question"] = tl;
  </script>
</template>
''')

# ---------- adjust (list of 6 + pause), bigger text to fill the frame ----------
items = [("(i)", "Depreciate Land and Building @ <b>6%</b>, Plant and Machinery @ <b>10%</b>, Office equipments @ <b>20%</b> and Furniture and Fixtures @ <b>15%</b>."),
         ("(ii)", "Create Provision for Doubtful Debts at <b>2%</b> on Sundry Debtors."),
         ("(iii)", "Insurance includes <b>₹ 250</b> Insurance Premium paid in advance."),
         ("(iv)", "Provide salary to Shubho <b>₹ 15,000 p.a.</b>"),
         ("(v)", "Outstanding Salaries <b>₹ 11,500</b>."),
         ("(vi)", "<b>10%</b> of the net profit is to be transferred to General Reserve.")]
s = rd("adjust.html")
a = s.index('<div class="clip" id="ad-card"'); b = s.index('<div class="clip" id="ad-pause"')
d = DUR["adjust"]; tp = L("adjust", 7)
s = s[:a] + f'<div class="clip" id="ad-card" data-start="0.3" data-duration="{d - 0.3:.1f}" data-track-index="2">\n' + \
    "\n".join(f'      <div class="it" id="ad-{i}"><span class="n">{n}</span><span class="tx">{t}</span></div>' for i, (n, t) in enumerate(items)) + \
    "\n    </div>\n    " + s[b:]
s = re.sub(r'data-start="[0-9.]+" data-duration="[0-9.]+" data-track-index="3"><span class="ic">', f'data-start="{tp}" data-duration="{d - tp:.1f}" data-track-index="3"><span class="ic">', s)
s = re.sub(r'data-duration="70.4"', f'data-duration="{d}"', s)
s = s.replace("The 8 Adjustments", "The 6 Adjustments").replace("T.S. Grewal · Q 39", "T.S. Grewal · Q 35")
a = s.index('    show("#ad-0"'); b = s.index('    tl.fromTo("#ad-pause"')
s = s[:a] + "".join(f'    show("#ad-{i}", {L("adjust", i + 1)});\n' for i in range(6)) + s[b:]
s = re.sub(r'(tl\.fromTo\("#ad-pause".*?\}, )[0-9.]+\);', lambda m: f"{m.group(1)}{tp + 0.1:.2f});", s)
s = re.sub(r'(tl\.to\("#ad-pause \.ic".*?\}, )[0-9.]+\);', lambda m: f"{m.group(1)}{tp + 0.7:.2f});", s)
s = s.replace(".it { display: flex; gap: 14px; font-size: 40px; line-height: 1.24; padding: 3px 8px;", ".it { display: flex; gap: 14px; font-size: 52px; line-height: 1.3; padding: 12px 8px;")
s = s.replace(".it .n { flex: none; width: 82px;", ".it .n { flex: none; width: 100px;")
s = s.replace("#ad-pause { position: absolute; left: 560px; top: 905px;", "#ad-pause { position: absolute; left: 560px; top: 905px;")
wr("adjust.html", s)

# ---------- read the trial balance: 2 already adjusted + 1 hidden ----------
d = DUR["hidden"]
wr("hidden.html", f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Inter", sans-serif; color: #fff; }}
    .hdr {{ position: absolute; left: 100px; top: 30px; font-family: "Archivo Black", sans-serif; font-size: 56px; color: #F5B700; }}
    .box {{ position: absolute; left: 100px; width: 1720px; background: #FFFDF5; color: #111; border-radius: 16px; padding: 14px 30px; font-family: "EB Garamond", serif; box-shadow: 0 12px 30px rgba(0,0,0,0.3); display: flex; flex-direction: column; justify-content: space-evenly; }}
    .k {{ font-family: "Archivo Black", sans-serif; font-size: 36px; }}
    .ok {{ border-left: 16px solid #1E8E3E; }} .ok .k {{ color: #1E8E3E; }}
    .hd {{ border-left: 16px solid #CC0000; }} .hd .k {{ color: #CC0000; }}
    .ln {{ display: block; font-size: 46px; line-height: 1.3; }}
    .ln b {{ color: #0057B8; }}
    {FRCSS}
    #hd-1 {{ top: 120px; height: 300px; }} #hd-2 {{ top: 440px; height: 175px; }} #hd-3 {{ top: 635px; height: 410px; }}
  </style>
  <div id="root" data-composition-id="hidden" data-width="1920" data-height="1080">
    <div class="hdr clip" id="hd-hdr" data-start="0" data-duration="{d}" data-track-index="0">🔍 Read the Trial Balance First</div>
    <div class="box ok clip" id="hd-1" data-start="{L('hidden', 1)}" data-duration="{d - L('hidden', 1):.1f}" data-track-index="1">
      <div class="k">✔ Purchases (Adjusted) ₹ 2,07,500 · Stock (31st March, 2026) ₹ 45,000</div>
      <span class="ln" id="hd-1a">Closing Stock is already deducted from Purchases → <b>no Stock in the Trading A/c</b></span>
      <span class="ln" id="hd-1b">Closing Stock <b>₹ 45,000</b> → shown only in the Balance Sheet (Assets)</span>
    </div>
    <div class="box ok clip" id="hd-2" data-start="{L('hidden', 3)}" data-duration="{d - L('hidden', 3):.1f}" data-track-index="2">
      <div class="k">✔ Expenses Payable ₹ 3,300</div>
      <span class="ln">Already a liability → Balance Sheet only, <b>no adjustment</b></span>
    </div>
    <div class="box hd clip" id="hd-3" data-start="{L('hidden', 4)}" data-duration="{d - L('hidden', 4):.1f}" data-track-index="3">
      <div class="k">🔍 HIDDEN · Chatterji's Loan ₹ 25,000 (taken on 1st Oct., 2025 @ 18% p.a.)</div>
      <span class="ln" id="hd-3a">1st October to 31st March = <b>6 months</b> · no interest in the Trial Balance</span>
      <span class="ln" id="hd-3b">Interest = 25,000 × {FR(18, 100)} × {FR(6, 12)} = <b>₹ 2,250</b> (outstanding)</span>
      <span class="ln" id="hd-3c">P&amp;L: To Interest <b>₹ 2,250</b> · Balance Sheet: Loan 25,000 + 2,250 = <b>₹ 27,250</b></span>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const card = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }}, t);
    const line = (s, t) => tl.fromTo(s, {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4 }}, t);
    tl.fromTo("#hd-hdr", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, 0);
    card("#hd-1", {L('hidden', 1)}); line("#hd-1a", {L('hidden', 2)}); line("#hd-1b", {L('hidden', 2, 5.0)});
    card("#hd-2", {L('hidden', 3)});
    card("#hd-3", {L('hidden', 4)}); line("#hd-3a", {L('hidden', 4, 4.0)}); line("#hd-3b", {L('hidden', 5)}); line("#hd-3c", {L('hidden', 6)});
    tl.fromTo("#hd-3", {{ boxShadow: "0 0 0 0 rgba(204,0,0,0)" }}, {{ boxShadow: "0 0 0 8px rgba(204,0,0,0.8)", duration: 0.4, yoyo: true, repeat: 3 }}, {L('hidden', 4, 0.5)});
    window.__timelines["hidden"] = tl;
  </script>
</template>
''')

# ---------- adjustment scenes ----------
S = {
 "a1": dict(dur=DUR["a1"], fs=52, title="Adjustment (iv) · Salary to Proprietor",
   adj="(iv) Provide salary to Shubho <b>₹ 15,000 p.a.</b>",
   tables=[[("Salary to Shubho — provided, not paid", "15,000", L("a1", 1), ""),
            ("Debit: Profit &amp; Loss A/c (like Interest on Capital)", "15,000", L("a1", 2), ""),
            ("Credit: Shubho's Capital A/c", "15,000", L("a1", 3), ""),
            ("► It is NOT Drawings — no cash has left the business.", "", L("a1", 1, 3.0), "note")]],
   eff={"tr": [], "pl": [("To Salaries: Add Salary to Shubho", "15,000", L("a1", 2, 3.5))],
        "bs": [("Capital: Add Salary to Shubho", "15,000", L("a1", 3, 2.5))]}),
 "a2": dict(dur=DUR["a2"], title="Adjustments (iii) &amp; (v) · Prepaid &amp; Outstanding",
   adj="(iii) Insurance includes <b>₹ 250</b> Insurance Premium paid in advance. (v) Outstanding Salaries <b>₹ 11,500</b>.",
   tables=[[("Salaries (T.B.)", "39,000", L("a2", 1), ""), ("Add: Outstanding", "11,500", L("a2", 1, 3.0), ""),
            ("", "50,500", E("a2", 1), "tot"), ("Add: Salary to Shubho", "15,000", L("a2", 2), ""),
            ("Salaries in P&amp;L", "65,500", E("a2", 2), "tot")],
           [("Insurance (T.B.)", "1,500", L("a2", 3), ""), ("Less: Prepaid", "250", L("a2", 3, 2.0), ""),
            ("Insurance in P&amp;L", "1,250", E("a2", 3), "tot")]],
   titles=["Salaries", "Insurance"],
   eff={"tr": [], "pl": [("To Salaries", "65,500", E("a2", 2, 0.2)), ("To Insurance", "1,250", E("a2", 3, 0.2))],
        "bs": [("Outstanding Salaries (Liab.)", "11,500", L("a2", 4)), ("Prepaid Insurance (Asset)", "250", L("a2", 4, 2.0))]}),
 "a3": dict(dur=DUR["a3"], fs=48, title="Adjustment (ii) · Provision for Doubtful Debts",
   adj="(ii) Create Provision for Doubtful Debts at <b>2%</b> on Sundry Debtors.",
   tables=[[("Sundry Debtors (T.B.)", "40,000", L("a3", 1), ""), ("Less: Provision @ " + FR(2, 100), "800", L("a3", 1, 2.5), ""),
            ("Net Debtors", "39,200", L("a3", 3, 3.0), "tot")],
           [("Bad Debts (T.B.)", "1,200", L("a3", 2, 3.0), ""), ("Add: New Provision", "800", L("a3", 2, 6.0), ""),
            ("Charge to P&amp;L", "2,000", E("a3", 2), "tot")]],
   titles=["Debtors in the Balance Sheet", "Charge to P&amp;L A/c"],
   amt_at={"Less: Provision": E("a3", 1)},
   eff={"tr": [], "pl": [("Bad Debts 1,200 + Provision 800", "2,000", E("a3", 2, 0.2))],
        "bs": [("Debtors 40,000 − 800", "39,200", L("a3", 3, 3.5))]}),
 "a4": dict(dur=DUR["a4"], title="Adjustment (i) · Depreciation", fs=44, eff_fs=32, bs_flex=1.7,
   adj="(i) Depreciate Land and Building @ <b>6%</b>, Plant and Machinery @ <b>10%</b>, Office equipments @ <b>20%</b> and Furniture and Fixtures @ <b>15%</b>.",
   tables=[[("Land and Building: 50,000 × " + FR(6, 100), "3,000", L("a4", 1), ""),
            ("Plant and Machinery: 50,000 × " + FR(10, 100), "5,000", L("a4", 2), ""),
            ("Office Equipments: 12,000 × " + FR(20, 100), "2,400", L("a4", 3), ""),
            ("Furniture and Fixtures: 20,000 × " + FR(15, 100), "3,000", L("a4", 4), ""),
            ("Total Depreciation", "13,400", L("a4", 5), "tot")]],
   amt_at={"Land": E("a4", 1), "Plant": E("a4", 2), "Office": E("a4", 3), "Furniture": E("a4", 4, 0.3)},
   eff={"tr": [], "pl": [("Depreciation", "13,400", L("a4", 5, 1.0))],
        "bs": [("L &amp; B 50,000 − 3,000", "47,000", L("a4", 5, 1.5)), ("P &amp; M 50,000 − 5,000", "45,000", L("a4", 5, 2.2)),
               ("Furniture 20,000 − 3,000", "17,000", L("a4", 5, 2.9)), ("Office Equip. 12,000 − 2,400", "9,600", L("a4", 5, 3.6))]}),
}
gen_adj.OUT = COMP
for k, v in S.items():
    gen_adj.build(k, v)

# ---------- accounts ----------
A = {
 "trading": dict(dur=DUR["trading"], cap=50, title="Trading Account", sub="of Shubho for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Purchases (Adjusted)", "", "2,07,500", L("trading", 1), ""),
      (W("= Opening Stock + Purchases − Closing Stock"), "", "", L("trading", 1, 4.0), ""),
      ("To Wages", "", "45,300", L("trading", 2), ""),
      ("To Carriage Inwards", "", "1,200", L("trading", 2, 2.5), ""),
      ("To Gross Profit c/d " + W("(to P&amp;L A/c)"), "", "1,29,500", L("trading", 4, 2.5), "bal")],
   R=[("By Sales", "", "3,83,500", L("trading", 3), ""),
      (W("No Closing Stock here — Purchases are adjusted"), "", "", L("trading", 3, 3.0), "")],
   totL=("3,83,500", L("trading", 4)), totR=("3,83,500", L("trading", 4, 0.3)),
   stamp=("Gross Profit ₹ 1,29,500", L("trading", 4, 3.5))),
 "pl": dict(dur=DUR["pl"], cap=40, title="Profit &amp; Loss Account", sub="of Shubho for the year ended 31st March, 2026",
   heads=("Dr.", "Cr."), cols=("Particulars", "Particulars"),
   L=[("To Salaries", "39,000", "", L("pl", 2), ""),
      ("Add: Outstanding", "11,500", "", L("pl", 2, 3.0), ""),
      ("Add: Salary to Shubho", "15,000", "65,500", L("pl", 2, 6.0), ""),
      ("To Office Expenses", "", "15,400", L("pl", 3), ""),
      ("To Carriage Outwards", "", "2,000", L("pl", 3, 3.0), ""),
      ("To Discount Allowed", "", "750", L("pl", 3, 5.5), ""),
      ("To Bad Debts " + W("(1,200 + 800)"), "", "2,000", L("pl", 4), ""),
      ("To Insurance " + W("(1,500 − 250)"), "", "1,250", L("pl", 4, 3.0), ""),
      ("To Interest on Chatterji's Loan", "", "2,250", L("pl", 4, 6.0), ""),
      ("To Depreciation", "", "13,400", L("pl", 5), ""),
      ("To General Reserve " + W("(29,650 × " + FR(10, 100) + ")"), "", "2,965", L("pl", 6, 4.0), ""),
      ("To Net Profit " + W("(to Capital A/c)"), "", "26,685", L("pl", 7), "bal")],
   R=[("By Gross Profit b/d", "", "1,29,500", L("pl", 1), ""),
      ("By Discount Received", "", "1,200", L("pl", 1, 4.0), ""),
      ("By Commission", "", "1,500", L("pl", 1, 6.0), "")],
   totL=("1,32,200", L("pl", 7, 0.4)), totR=("1,32,200", E("pl", 1)),
   stamp=("Net Profit ₹ 26,685", L("pl", 7, 0.8))),
 "bs": dict(dur=DUR["bs"], cap=38, title="Balance Sheet", sub="of Shubho as at 31st March, 2026",
   heads=("", ""), cols=("Liabilities", "Assets"),
   L=[("Capital", "1,15,000", "", L("bs", 1), ""),
      ("Add: Salary to Shubho", "15,000", "", L("bs", 1, 3.0), ""),
      ("Add: Net Profit", "26,685", "", L("bs", 1, 6.0), ""),
      ("", "1,56,685", "", L("bs", 2), ""),
      ("Less: Drawings", "20,000", "1,36,685", L("bs", 2, 1.5), ""),
      ("General Reserve", "", "2,965", L("bs", 3), ""),
      ("Chatterji's Loan", "25,000", "", L("bs", 3, 3.0), ""),
      ("Add: Interest Outstanding", "2,250", "27,250", L("bs", 3, 5.5), ""),
      ("Sundry Creditors", "", "37,350", L("bs", 4), ""),
      ("Expenses Payable", "", "3,300", L("bs", 4, 3.0), ""),
      ("Outstanding Salaries", "", "11,500", L("bs", 4, 5.5), "")],
   R=[("Land and Building", "50,000", "", L("bs", 5), ""),
      ("Less: Depreciation", "3,000", "47,000", L("bs", 5, 1.5), ""),
      ("Plant and Machinery", "50,000", "", L("bs", 5, 3.0), ""),
      ("Less: Depreciation", "5,000", "45,000", L("bs", 5, 4.2), ""),
      ("Furniture and Fixtures", "20,000", "", L("bs", 5, 5.5), ""),
      ("Less: Depreciation", "3,000", "17,000", L("bs", 5, 6.5), ""),
      ("Office Equipments", "12,000", "", L("bs", 5, 7.5), ""),
      ("Less: Depreciation", "2,400", "9,600", L("bs", 5, 8.5), ""),
      ("Closing Stock", "", "45,000", L("bs", 6), ""),
      ("Sundry Debtors", "40,000", "", L("bs", 6, 2.5), ""),
      ("Less: Provision for Doubtful Debts", "800", "39,200", L("bs", 6, 3.5), ""),
      ("Prepaid Insurance", "", "250", L("bs", 6, 5.0), ""),
      ("Cash at Bank", "", "16,000", L("bs", 6, 7.0), "")],
   totL=("2,19,050", E("bs", 4)), totR=("2,19,050", L("bs", 7)),
   stamp=("TALLIED ✓ ₹ 2,19,050", L("bs", 7, 3.0))),
}
gen_acc.OUT = COMP
for k, v in A.items():
    gen_acc.build(k, v)

# ---------- traps (taller boxes to fill the frame) ----------
d = DUR["traps"]
s = rd("traps.html")
boxes = [("Trap 1 · Purchases (Adjusted)", 'Closing Stock <b>₹ 45,000</b> → Balance Sheet only · <span class="x">Trading A/c</span>'),
         ("Trap 2 · Hidden Interest on Loan", '25,000 × ' + FR(18, 100) + ' × ' + FR(6, 12) + ' = <b>₹ 2,250</b> outstanding'),
         ("Trap 3 · Salary to Proprietor", 'Debit P&amp;L <b>₹ 15,000</b> · Add to Capital · <span class="x">Drawings</span>'),
         ("Trap 4 · General Reserve", '10% of profit before transfer <b>₹ 29,650</b> = <b>₹ 2,965</b>')]
for i, (k, ln) in enumerate(boxes, 1):
    s = re.sub(rf'<div class="box clip" id="tp-{i}" data-start="[0-9.]+" data-duration="[0-9.]+"(.*?)<div class="k">.*?</div><span class="ln">.*?</span></div>',
               lambda m: f'<div class="box clip" id="tp-{i}" data-start="{L("traps", i)}" data-duration="{d - L("traps", i):.1f}"{m.group(1)}<div class="k">{k}</div><span class="ln">{ln}</span></div>', s, flags=re.S)
s = s.replace('data-duration="42.9"', f'data-duration="{d}"')
s = s.replace("#tp-1 { top: 140px; } #tp-2 { top: 370px; } #tp-3 { top: 600px; } #tp-4 { top: 830px; }",
              "#tp-1 { top: 130px; } #tp-2 { top: 360px; } #tp-3 { top: 590px; } #tp-4 { top: 820px; }\n    .box { height: 215px; display: flex; flex-direction: column; justify-content: space-evenly; }\n    .k { font-size: 40px !important; }\n    .ln { font-size: 52px !important; }\n    " + FRCSS)
a = s.index('    card("#tp-1"'); b = s.index('    window.__timelines["traps"]')
s = s[:a] + f'    card("#tp-1", {L("traps", 1)}); card("#tp-2", {L("traps", 2)}); card("#tp-3", {L("traps", 3)}); card("#tp-4", {L("traps", 4)});\n    tl.to("#tp-1 .x", {{ scale: 1.15, duration: 0.3, yoyo: true, repeat: 3 }}, {L("traps", 1, 4.0)});\n    tl.to("#tp-3 .x", {{ scale: 1.15, duration: 0.3, yoyo: true, repeat: 3 }}, {L("traps", 3, 3.0)});\n' + s[b:]
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
s = s.replace("Question 39 · Manoj · Pg 19.91–19.92", "Question 35 · Shubho")
s = s.replace('<span class="g">8 adjustments</span> · 3 statements', 'ONE <span class="g">hidden</span> adjustment')
s = s.replace("WILL IT TALLY?", "SPOT IT?")
quiz_end = L("hook", 1)
s = s.replace('<div id="hook-same"', f'<div id="hook-quiz" class="clip" data-start="0.3" data-duration="{quiz_end - 0.3:.1f}" data-track-index="8">Q36 quiz answer: <span class="g">₹ 1,250 ✓</span></div>\n    <div id="hook-same"')
s = s.replace("#hook-same .g { color: #F5B700; }", "#hook-same .g { color: #F5B700; }\n    #hook-quiz { position: absolute; left: 130px; top: 800px; width: 1140px; font-family: \"Archivo Black\", sans-serif; font-size: 60px; color: #fff; }\n    #hook-quiz .g { color: #7EE2A0; }")
s = s.replace('window.__timelines["hook"] = tl;', 'tl.fromTo("#hook-quiz", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0.35);\n    window.__timelines["hook"] = tl;')
wr("hook.html", s)

s = rd("recap.html")
old = [0.3 + x[0] for x in q39T["recap"]["lines"]]
new = [L("recap", i) for i in range(7)]
s = remap(s, [0.0] + old[1:], [0.0] + new[1:], 33.0, DUR["recap"])
s = s.replace("Recap · T.S. Grewal Q 39", "Recap · T.S. Grewal Q 35").replace("₹ 21,910", "₹ 1,29,500").replace("₹ 1,400<", "₹ 26,685<").replace("₹ 1,23,850 ✓", "₹ 2,19,050 ✓")
s = s.replace('Every adjustment has <span style="color:#F5B700">two effects</span>', 'Purchases adjusted: <span style="color:#F5B700">Closing Stock → BS only</span>')
s = s.replace("Check your answer: GP 21,910 · NP 1,400", "Check: GP 1,29,500 · NP 26,685")
wr("recap.html", s)

# ---------- index ----------
order = ["hook", "question", "adjust", "hidden", "a1", "a2", "a3", "a4", "trading", "pl", "bs", "traps", "recap"]
t0 = 0.0; divs = []; aud = []; chapters = []
for n in order:
    dd = DUR[n]
    divs.append(f'      <div id="{n}" data-composition-id="{n}" data-composition-src="compositions/{n}.html" data-start="{round(t0, 1)}" data-duration="{dd}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>')
    aud.append(f'      <audio id="vo-{n}" class="clip" src="assets/voice/{n}.wav" data-start="{round(t0 + 0.3, 1)}" data-duration="{T[n]["dur"]}" data-track-index="5" data-volume="0.85"></audio>')
    chapters.append(f"{int(t0 // 60)}:{int(t0 % 60):02d} {n}")
    t0 += dd
src = open(os.path.join(PROJ, "..", "tsg-ch19-q39", "index.html")).read()
head = src.split('<div id="root"')[0].replace('"default":"1,23,850"', '"default":"2,19,050"')
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
