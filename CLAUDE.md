# Goodwill Tuition — YouTube Shorts standing instructions

Apply these to every new YouTube video / Short without being asked.

## Audience
- CBSE Class 11 & 12 Accountancy students, mostly in the GCC (UAE, Saudi Arabia, Qatar, Kuwait, Oman, Bahrain), plus India.
- Keep ₹ (matches NCERT and T.S. Grewal). Do not mention D.K. Goel.
- Channel handle: @GoodwillOnlineTuition (changed from @rainytp on 12 Nov 2026). New video every day.
- Viewers watch (76% average) but don't subscribe: end every Short with the voice line "Follow for a new accounting Short every day!" and a Subscribe button animation.

## Video template
- Copy `videos/drawings-short/` (HyperFrames, 1080×1920, 4 scenes: hook → concept → apply → journal entry, ending with the Follow line and Subscribe button). This "Harris" format got about double the views of the earlier ones (13 Nov 2026).
- Replace the concept scene (`compositions/entity.html`) with the idea behind each entry; use the 3 golden rules there only when no specific concept fits.
- Keep the "Harris" storyline (same business) for continuity, and end each Short with a pinned quiz comment that the next Short answers.
- Logo: `assets/img/logo.png` — on the hook frame beside "GOODWILL TUITION CENTRE" and beside the closing call to action.
- Voice: Kokoro `hm_omega`, Indian male (`npx hyperframes tts "..." -v hm_omega -l en-us`, needs `HYPERFRAMES_PYTHON=/root/video-venv/bin/python`); normalise to about −14 LUFS. Chosen 14 Nov 2026; Shorts before that used `af_heart`.
- Verify the accounting entry before rendering; commit and push the project and MP4.

## T.S. Grewal series (from 18 Nov 2026)
- Daily Shorts now solve T.S. Grewal Class 11 (CBSE, 2025–26 edition) back exercises, one transaction per Short. The user sends the question (chapter, problem, page); start with the transactions students get wrong.
- Use the textbook's exact names, amounts and dates. The answer must match the book; if it doesn't, stop and tell the user.
- Hook shows a reference card ("T.S. Grewal · Class 11 · Ch 8 / Practical Problem 1 · Pg 8.57 · 2025–26"); title starts "TS Grewal Class 11 Ch N …".
- Quote only the transaction being solved; never copy whole pages. Description ends with a one-line note that T.S. Grewal is referred to only so students can find the question.
- Voice says "T. S. Grayvaal" (spelled that way for TTS) so it sounds like "Grewal".
- Write title, description and tags to `videos/<project>/upload/` and check lengths (title ≤100, description ≤5,000, tags ≤500).
- Always paste the full description in the chat reply too, ready to copy — never just point to the file.
- Template for T.S. Grewal Shorts: copy `videos/tsg-ch8-pp1-apr9/` (reference card hook, recall chip in the concept scene, dated entry box, "Remember"/"Coming next" box).
- Ch 8 Practical Problem 1 (Pg 8.57), done: Apr 3 purchase from Pankaj (Purchases A/c Dr. To Pankaj A/c 18,000) · Apr 7 goods returned to Pankaj (Pankaj A/c Dr. To Purchases Return A/c 12,000) · Apr 9 goods returned by Naresh (Sales Return A/c Dr. To Naresh A/c 1,400).
- Ch 8 PP1, still to make, in this order:
  1. NEXT — Apr 16 Rent paid to Amit ₹5,000: Rent A/c Dr. 5,000 To Cash A/c 5,000. Trap: not "Amit A/c" — Amit is only the landlord; the expense is rent.
  2. Apr 19 Sold goods to Sumit for cash ₹6,000: Cash A/c Dr. 6,000 To Sales A/c 6,000. Trap: cash sale, so no "Sumit A/c". Pairs with Apr 16: "when NOT to write the person's name".
  3. Apr 30 Cash received from Naresh on account ₹5,000: Cash A/c Dr. 5,000 To Naresh A/c 5,000. Explain "on account"; Naresh then owes ₹9,000 − 1,400 − 5,000 = ₹2,600.
  4. Apr 10 Cash paid to Ajay ₹6,000 (the book really says Ajay; he appears nowhere else): likely Ajay A/c Dr. 6,000 To Cash A/c 6,000 — confirm the book's answer with the user first.
  Skip as Shorts (too simple / already covered): Apr 12 Commission received ₹2,700, Apr 15 Furniture purchased ₹7,000, Apr 24 Cash Sales ₹7,000, Apr 30 Salaries paid ₹10,000.
- Ask the user for the book's narration when unsure; so far we used "(Being goods … )" wording and the user did not object.

## Rectification of Errors series (from 21 Nov 2026)
- T.S. Grewal Class 11 (2025–26) Chapter 17 Rectification of Errors back exercises, one error per Short. Q 5 is on page 17.44. Reference card: "T.S. Grewal · Class 11 · Ch 17 / Rectification of Errors · Q 5 (ii) · Pg 17.44 · 2025–26"; title starts "TS Grewal Class 11 Ch 17 Rectification of Errors …".
- The user's 4-step method, shown in every Short: Step 1 Wrong entry (red) → Step 2 Reverse of the wrong entry (orange) → Step 3 Correct entry (green) → Step 4 Rectifying entry = Step 2 + Step 3, with the common account cancelling (purple).
- Template: copy `videos/tsg-rect-q5-ii/` (hook "THE ERROR" + "RECTIFY IT?", scene 2 = steps 1–2, scene 3 = step 3 + cancel stamp, scene 4 = step 4 + "Remember the 4 steps").
- Narration style: "(Being … wrongly debited/credited to …, now rectified)". Say whether Suspense A/c is needed.
- Keep the ending clean: after the rectifying entry, the voice goes straight to the Follow line. No extra recap lines on screen or in the voice (no "Cash was correct, only Ajay's account was wrong") — the user found it confusing. Put explanations like that in the description instead.
- Order: two-sided errors first (principle, omission, commission, wrong amount), then one-sided errors with Suspense A/c, then before vs after the Trial Balance.
- Done: Q 5 (ii) Salary paid to Ajay debited to his Personal Account ₹8,000 → Salary A/c Dr. To Ajay's A/c.

## MGU B.Com Hons Sem 6 Cost Accounting video (main video made 22 Nov 2026)
- Source: `videos/mgu-cost-q14/source/notes-tender-quotations-q14-q13-ill17.html` (the user's solved notes). Make **Question 14 (National Ltd), Tender or Quotations, Dr. Jayan Pg 292–293** first.
- Do NOT change the document's solution or wording: follow its 3 steps exactly — Step 1 Cost Sheet (Prime Cost 12,40,000 → Works Cost 14,02,000 → Cost of Production 15,14,000); Step 2 rates (Works OH 30% of wages; Establishment OH 8% of works cost, rounded from 7.9886%; Profit 20% on sales = 20⁄(100−20) = 25% on cost); Step 3 quotation (1,000 + 800 = 1,800 → +240 = 2,040 → +163.20 = 2,203.20 → +550.80 = **₹2,754.00**).
- Proposed format (confirm with the user before building): one 16:9 main video of 5–6 min (hook → question → Step 1 → Step 2 → Step 3 → exam traps → recap/CTA) plus 3 Shorts cut from it ("20% on sales = 25% on cost" trick; absorption bases; quotation in 3 steps).
- Book: "Cost Accounting Methods" by Dr. Jayan, MGU-UGP B.Com (Honours) Semester VI (DSC A – MG 6 DSC COM 301). Offering the solved-notes PDF on WhatsApp is OK.
- Main video done: `videos/mgu-cost-q14/` (HyperFrames, 1920×1080, 5:28, 7 scenes hook → question → step1 → step2 → step3 → traps → recap; voice `hm_omega`, one wav per scene built from per-line clips in `voice-script/`). Template for later MGU main videos. Shorts from it: later, when the user asks. On a phone held upright the 16:9 video fills only half the screen; the user kept it as is for now (22 Nov). Later: enlarge tables, figures and fractions 30–40% to fill the frame, and cut the 9:16 Shorts.
- Audience is Kerala B.Com (MGU), not CBSE GCC: separate playlist "MGU B.Com Hons Sem 6 · Cost Accounting"; in the description replace the GCC line with "Online Cost Accounting classes for MGU B.Com Honours students across Kerala." (keep website, WhatsApp, paid demo lines). Stacked fractions on screen, never ÷.
- The user's weekly Claude usage was at 74% on 22 Nov (refresh 7:30 PM IST): keep replies short and avoid unnecessary re-renders.

## Main-video method and cost (MGU Q14, 22 Nov 2026 — the user loved it; reuse it)
- Cost: about 10% of a 5-hour session and about 1% of the weekly limit for a 5½-min 16:9 video (8:45–9:38 AM), voice, 7 scenes, render, upload text and upload guidance included.
- Method that kept it cheap: write the voice script first as per-line clips (`voice-script/lines.json`) → TTS each line → join each scene into one wav with 0.5 s gaps and loudnorm −14 LUFS → line start times (`timing.json`) set every on-screen reveal → one scene file per step → `check` → one snapshot contact sheet → fix → render once in the background (~10 min) → commit project, then MP4.
- Keep: no music, house colours (navy #0B1B3F, gold #F5B700, cream cards, purple #6A0DAD, red #CC0000), stacked fractions, step pills 1·2·3, summary chips, "exam traps" scene, recap + WhatsApp PDF offer + Subscribe animation.

## Every description must include
```
🌐 www.goodwillonlinetuition.com
📞 WhatsApp: +91 95679 02805 → https://wa.me/919567902805
Book a paid demo class on WhatsApp.
Online Accountancy classes for CBSE Class 11 & 12 students in UAE, Saudi Arabia, Qatar, Kuwait, Oman & Bahrain.
```
- Paid demo class only — never write "free class", "free trial" or "free demo".

## Upload settings to give the user
- Category: Education · Type: Problem walkthrough · Class 11/12 · Exam: CBSE Class 11/12, NCERT (Kerala DHSE as extra).
- Title: 100 characters at most (YouTube limit) — count it before giving it, `#shorts` included.
- Audience: No, it's not made for kids.
- Tags include: cbse accountancy, ncert accountancy, class 11 accountancy, class 12 accountancy, accountancy tuition uae, online accountancy tuition dubai, journal entry, golden rules of accounting, debit and credit explained.
- Publish immediately (Visibility → Public), then the user shares the link on Facebook and WhatsApp straight away. Do not schedule.
- Guide uploads one step at a time when asked.

## Channel links (YouTube Studio → Customisation → Profile)
- Website: https://goodwillonlinetuition.com
- WhatsApp: https://wa.me/919567902805

## Published Shorts
- Golden Rules (Rent paid) — https://youtube.com/shorts/eY_sLSSbkfI
- Rent Received — https://youtube.com/shorts/qpoDm5QZLDI
- Salary Paid (₹15,000 cash) — https://youtube.com/shorts/dPcozM6OufE (published 12 Nov 2026, 7:56 AM IST)
- Started business with cash (Business Entity Concept) — https://youtube.com/shorts/B121TZv2bXE (published 13 Nov 2026)
- Drawings (₹5,000 cash for personal use) — https://youtube.com/shorts/SsZHTMTbUYc (published 13 Nov 2026)
- Purchases: To Cash or To Ravi (cash vs credit, first in Indian male voice) — https://youtube.com/shorts/4BKv5oYPLZo (published 14 Nov 2026)
- Sales: Anu is the debtor (cash vs credit sale) — https://youtube.com/shorts/vn51CmqVDjM (published 15 Nov 2026)
- Furniture: Purchases A/c or Furniture A/c? (fixed asset) — https://youtube.com/shorts/p4JwsQXaMiI (published 16 Nov 2026)
- TS Grewal Ch 8 PP1, Apr 3: Goods purchased from Pankaj for credit (first T.S. Grewal Short) — https://youtube.com/shorts/_2O6tqrgyyM (published 18 Nov 2026)
- TS Grewal Ch 8 PP1, Apr 7: Goods returned to Pankaj (Purchases Return) — https://youtube.com/shorts/1f0-mvuEwmk (published 19 Nov 2026)
- TS Grewal Ch 8 PP1, Apr 9: Goods returned by Naresh (Sales Return) — https://youtube.com/shorts/fzdeHb3QRrw (published 20 Nov 2026)
- TS Grewal Ch 17 Rectification Q5 (ii): Salary debited to Ajay's A/c (first rectification Short, 4-step method) — https://youtube.com/shorts/hEt3ASDIvCA (published 21 Nov 2026)
- MGU B.Com Hons Sem 6 Cost Accounting Q14 (National Ltd), Tender or Quotations — main 16:9 video, 5:28, first in playlist "MGU B.Com Hons Sem 6 · Cost Accounting" — https://youtu.be/sV7NjIN_g04 (published 22 Nov 2026)
- Channel views: 4,253 (10 Nov 2026) → 4,310 (11 Nov 2026). Compare again around 18 Nov.
- Popular tab (19 Nov 2026): photo Shorts of real exam question papers lead — B.Com Corporate Accounting I paper (QP 22100578, Apr 2022) 1,020 views, others 757 / 663 / 425; MGU Income Tax promo 218; Harris "Business Entity Concept" 107 (6 days old). But those question-paper Shorts are 4 years old (≈0.2–0.7 views/day); the Harris Short got ≈18 views/day — the new animated daily Shorts are far ahead per day.
