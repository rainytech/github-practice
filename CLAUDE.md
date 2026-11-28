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
- CRITICAL: the voice must say "Tee-Ess Gray-waal". Write it "T. S. Graywaal" in voice scripts (Kokoro phonemes ɡɹˈeɪwɑːl). Plain "Grewal" comes out "Groo-ul" — wrong (Q39 had to be re-rendered and re-uploaded, 25 Nov 2026). On screen and in text always spell it "Grewal".
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

## ▶ START HERE next session (left 28 Nov 2026 — Q35 (Shubho) video MADE, waiting for the user to check and upload)
- Q35 made 28 Nov: `videos/tsg-ch19-q35/` (9:29, 13 scenes, Rainy's voice, #C8C8C8, FILL-THE-FRAME). Page number unknown, so the reference card and description show no page. Upload texts in `upload/` (title 99 chars, tags 427); thumbnail `upload/thumbnail_photo.jpg`. Pinned quiz for Q35 (answer it in the next video's hook): "If Chatterji's loan had been taken on 1st July, 2025, how much interest would be outstanding?" → 25,000 × 18⁄100 × 9⁄12 = ₹3,375. Q35's hook answered the Q36 quiz (₹1,250).
- NEW TEMPLATE for final-accounts videos: copy `videos/tsg-ch19-q35/voice-script/gen35.py` + its `gen_adj.py` / `gen_acc.py` (fill-the-frame versions: account cards full height with auto font from row count and the stamp in the top-right corner; adjustment effect boxes stretch to the bottom; TB = one Debit column + Credit column with Total rows and a legend). Voice: write "Chatterjee's" (not "Chatterji's") in lines.json, else the name blurs; check every scene with faster_whisper (`/root/video-venv`, model base.en) before rendering.
- Fresh container setup that worked 28 Nov (~5 min): ffmpeg the uploaded voice m4a to `tools/voice/rainy_ref.wav` (docstring); `python3.11 -m venv /root/clone-venv && pip install chatterbox-tts`; `/root/video-venv/bin/pip install rembg`. Do NOT run rembg and Chatterbox at the same time (out of memory). Full voice build took ~15 min.
- STANDARD THUMBNAIL (approved 28 Nov 2026): `videos/tsg-ch19-q36/upload/thumbnail_photo.html` — copy it and change only the texts. Left: small text (tag 28px, title 76px with line-height 1.3 so "T.S. GREWAL" and "Q__ SOLVED" have clear space, trap card 32px, answer chip 32px) with breathing space; top-right: small tilted 3D "Goodwill Solved Notes" book; right: his signature photo cut out, NO white outline, soft blended edges + faint navy glow, height 480px; gold bar "RAINY GOODWILL · ACCOUNTANCY". Photo files `tools/thumb/rainy_photo.jpg` → `rainy_cutout.png` → `rainy_soft.png` are NOT in git: in a fresh container ask him to attach "me in pepe blue shirt.jpg" (Drive id 1eABOFBj-ZZRyUBUuGUv3nXo0WiLh2Ots), then `/root/video-venv/bin/pip install rembg`, cut out with rembg model `birefnet-portrait` (post_process_mask, brightness 1.08, contrast 1.06, unsharp), blur alpha 1.2px, fade the left 90px and bottom 40px.
- VIDEO BACKGROUND = #C8C8C8 (user, 27 Nov 2026: deliberate, prevents eyestrain, same as his PDFs). All video scenes: grey page, black text, navy #00008B headings, darker grey cards #B8B8B8, table headers #A6A6A6, red/blue/purple highlights, dark green ✓. Not for thumbnails (keep them bright). `videos/tsg-ch19-q36/voice-script/gen36.py` has a `grey()` pass that converts the navy templates.
- FILL THE FRAME (user, 27 Nov 2026, from the next video on; Q36 stays as uploaded): tables/cards must stretch to the bottom bar — auto-size fonts from the row count (Trial Balance ~46px, was 33px), no empty lower half in question, adjustment, Trading/P&L/Balance Sheet scenes; stamps in a corner not over figures; on the contact sheet content should reach ~85–90% of the frame height. Trial Balance scene: equal-height columns down to the bottom, rows spread evenly; Total as the last row of the Debit and Credit columns (no separate yellow bar); legend (★ adjustment / 🔍 hidden / ✔ already adjusted) fills the shorter Credit column; ~44px rows.
- Q37 ON HOLD (treated as dropped unless the user checks the book): notes give NP ₹27,538 / BS ₹2,62,888 but the book prints ₹29,538 / ₹2,64,888 (₹2,000 gap). Likely the book has Plant & Machinery depreciation 10% (not 20%) or insurance claim ₹8,000 (not ₹6,000) — the user is to check the book.
- VOICE = RAINY'S OWN CLONED VOICE (default from 25 Nov 2026; user: "My voice sounds good, make it default", wants enthusiasm). Build: `HF_HUB_OFFLINE=1 /root/clone-venv/bin/python tools/voice/build_voice_rainy.py videos/<project>` (offline flag: online it hung on the HF Hub check, 26 Nov) (Chatterbox, MIT licence; exaggeration 0.75 / cfg 0.4; ~5× real time on CPU → background, ~45 min for 10 min of speech; same lines.json/timing.json format). The reference clip `tools/voice/rainy_ref.wav` is NOT in git (privacy): in a fresh container ask the user to upload his recording, saved in his Google Drive as "Rainy voice for YouTube.m4a" (2:26, file id 18s3EjLn_16CsmF0pTiDKAgOvtebiHk6n; do NOT fetch it through the Drive connector, its base64 would flood the context — he shares it into the chat from the Drive app; a copy is also on his PC at C:\Users\Admin\Desktop\Rainy voice for YouTube.m4a — attach it from there) and follow the script docstring; also install `/root/clone-venv` per the docstring (~3 min). Kokoro `hm_omega` only as fallback. Still write "T. S. Graywaal" in scripts; send a short sample before a full build.
- Q36 (Karman, 2 hidden adjustments, Pg 19.89) made and uploaded 27 Nov: `videos/tsg-ch19-q36/` (9:18, #C8C8C8). `voice-script/gen36.py` = latest builder (Q39 templates + grey() pass + contrast-safe colours) — copy it for the next final-accounts video.
- Q38 (Ashok, Purchases Adjusted, Pg 19.90–19.91) made and uploaded 26 Nov in Rainy's voice: `videos/tsg-ch19-q38/` (7:48). `voice-script/gen38.py` builds ALL scenes + index from timing.json (reads Q39 templates) — copy it for the next final-accounts video. Thumbnail: 3D book "Goodwill Solved Notes" in the textbook cover's colours (user loves the book look; never the real T.S. Grewal cover/logo).
- Q40 and Q41 (same notes): NOT to be made (user, 25 Nov 2026: not very useful). Next big-question video: the user will choose; reuse `videos/tsg-ch19-q39/` generators.
- Illustration 17 (Samsung India Ltd, Pg 276–278) video MADE 24 Nov: `videos/mgu-cost-ill17/` (16:9, 6:47, 8 scenes hook → question → step1 → step2A → step2B → step3 → tips → recap). Profit shown as exact ₹5,112.80 (20% on cost), rounded ₹5,113; price ₹30,677. Uploaded 24 Nov with `tools/upload_youtube.py` (first real script upload, Public, playlist OK): https://youtu.be/x6KsUmfpVIM. Next: Education fields + pinned comment are manual; then the pending 9:16 Shorts.
- Voice builder for main videos: `videos/mgu-cost-ill17/voice-script/build_voice.py <project>` (kokoro-onnx in /root/video-venv, all lines in one process, ~2 min; writes assets/voice/*.wav + timing.json). Copy the project's `.gitignore` too (else render work dirs get committed).
- YouTube API: Google replied 23 Nov — no audit needed, API uploads can be Public.
- Thumbnails (from 24 Nov): every video gets a custom 1280×720 `upload/thumbnail.jpg` built from `upload/thumbnail.html` (Playwright screenshot). Style: 2–3 huge words (white + gold), red course tag, one tilted cream card with the key trap/number, gold answer chip, gold bottom bar with logo. Template: `videos/mgu-cost-ill17/upload/thumbnail.html`. The user sets it in Studio (API has no Education fields; thumbnail by hand too for now).
- T.S. Grewal Class 11 (2026–27) Q39 Final Accounts (Manoj, 8 adjustments, Pg 19.91–19.92) main 16:9 video made and uploaded 25 Nov (https://youtu.be/xARyjWijgpQ): `videos/tsg-ch19-q39/` (9:45, 13 scenes; GP 21,910 · NP 1,400 · BS 1,23,850, confirmed by the user). Scene generators: `voice-script/gen_adj.py` (adjustment → Trading / P&L / Balance Sheet effect boxes) and `gen_acc.py` (T-format accounts). Playlist "TS Grewal Class 11 · Final Accounts". GCC exam prep: the user wants full videos for big questions.
- Thumbnails must not copy the real T.S. Grewal cover (trade dress); use our own design with "T.S. Grewal Q39" as text.
- Still pending: 9:16 Shorts from Q14/Q13/Ill 17; T.S. Grewal Ch 8 PP1 Apr 16 Short; Rectification series next error.

## MGU B.Com Hons Sem 6 Cost Accounting video (main video made 22 Nov 2026)
- Source: `videos/mgu-cost-q14/source/notes-tender-quotations-q14-q13-ill17.html` (the user's solved notes). Make **Question 14 (National Ltd), Tender or Quotations, Dr. Jayan Pg 292–293** first.
- Do NOT change the document's solution or wording: follow its 3 steps exactly — Step 1 Cost Sheet (Prime Cost 12,40,000 → Works Cost 14,02,000 → Cost of Production 15,14,000); Step 2 rates (Works OH 30% of wages; Establishment OH 8% of works cost, rounded from 7.9886%; Profit 20% on sales = 20⁄(100−20) = 25% on cost); Step 3 quotation (1,000 + 800 = 1,800 → +240 = 2,040 → +163.20 = 2,203.20 → +550.80 = **₹2,754.00**).
- Proposed format (confirm with the user before building): one 16:9 main video of 5–6 min (hook → question → Step 1 → Step 2 → Step 3 → exam traps → recap/CTA) plus 3 Shorts cut from it ("20% on sales = 25% on cost" trick; absorption bases; quotation in 3 steps).
- Illustration 17 (Samsung India, Pg 276–278) is from the same book. Its notes show profit ₹5,112.81 (from 16.6667%); exact is ₹5,112.80 — ask the user before making it. Q13 video made 22 Nov: `videos/mgu-cost-q13/` (4:40, "try it yourself" with Pause & Try card, tips scene instead of traps, 30–40% bigger text — use this size from now on).
- Book: "Cost Accounting Methods" by Dr. Jayan, MGU-UGP B.Com (Honours) Semester VI (DSC A – MG 6 DSC COM 301). Offering the solved-notes PDF on WhatsApp is OK.
- Main video done: `videos/mgu-cost-q14/` (HyperFrames, 1920×1080, 5:28, 7 scenes hook → question → step1 → step2 → step3 → traps → recap; voice `hm_omega`, one wav per scene built from per-line clips in `voice-script/`). Template for later MGU main videos. Shorts from it: later, when the user asks. On a phone held upright the 16:9 video fills only half the screen; the user kept it as is for now (22 Nov). Later: enlarge tables, figures and fractions 30–40% to fill the frame, and cut the 9:16 Shorts.
- Audience is Kerala B.Com (MGU), not CBSE GCC: separate playlist "MGU B.Com Hons Sem 6 · Cost Accounting"; in the description replace the GCC line with "Online Cost Accounting classes for MGU B.Com Honours students across Kerala." (keep website, WhatsApp, paid demo lines). Stacked fractions on screen, never ÷.
- The user's weekly Claude usage was at 74% on 22 Nov (refresh 7:30 PM IST): keep replies short and avoid unnecessary re-renders.

## Main-video method and cost (MGU Q14, 22 Nov 2026 — the user loved it; reuse it)
- Cost: about 10% of a 5-hour session and about 1% of the weekly limit for a 5½-min 16:9 video (8:45–9:38 AM), voice, 7 scenes, render, upload text and upload guidance included.
- Method that kept it cheap: write the voice script first as per-line clips (`voice-script/lines.json`) → TTS each line → join each scene into one wav with 0.5 s gaps and loudnorm −14 LUFS → line start times (`timing.json`) set every on-screen reveal → one scene file per step → `check` → one snapshot contact sheet → fix → render once in the background (~10 min) → commit project, then MP4.
- Keep: no music, house colours (navy #0B1B3F, gold #F5B700, cream cards, purple #6A0DAD, red #CC0000), stacked fractions, step pills 1·2·3, summary chips, "exam traps" scene, recap + WhatsApp PDF offer + Subscribe animation.

## Check before sending the user on long external tasks (lesson, 24 Nov 2026)
- Before asking the user to do any long outside process (Google/YouTube forms, audits, account setups), check the current official docs with a web search first. Rules change after the training cutoff. On 22 Nov the user spent hours on a YouTube API audit that Google had stopped requiring on 2 Nov 2026.

## Every description must include
```
🌐 www.goodwillonlinetuition.com
📞 WhatsApp: +91 95679 02805 → https://wa.me/919567902805
Book a paid demo class on WhatsApp.
Online Accountancy classes for CBSE Class 11 & 12 students in UAE, Saudi Arabia, Qatar, Kuwait, Oman & Bahrain.
```
- Paid demo class only — never write "free class", "free trial" or "free demo".

## Upload settings to give the user
- Category: Education · Type: Problem walkthrough · Level: Class 11/12 · Exam: YouTube offers only "CBSE Class 12" — set it for Class 12 videos, leave it BLANK for Class 11 (checked 26 Nov 2026).
- Title: 100 characters at most (YouTube limit) — count it before giving it, `#shorts` included.
- Audience: No, it's not made for kids.
- Tags include: cbse accountancy, ncert accountancy, class 11 accountancy, class 12 accountancy, accountancy tuition uae, online accountancy tuition dubai, journal entry, golden rules of accounting, debit and credit explained.
- Publish immediately (Visibility → Public), then the user shares the link on Facebook and WhatsApp straight away. Do not schedule.
- Guide uploads one step at a time when asked.
- Upload script (22 Nov 2026): `tools/upload_youtube.py videos/<project>` (setup in `tools/UPLOAD_SETUP.md`; runs on the user's PC; free API). Give every new project an `upload/settings.json` with its playlist. Public uploads work straight away (Google, 23 Nov 2026: API uploads are no longer locked as private; upload cost is now 1 unit per call, so the free quota is plenty). Education fields and pinned comment stay manual. Count tags the YouTube way (quotes around multi-word tags) — the script checks it. Set up on the user's PC 22 Nov 2026 (repo at C:\Users\Admin\github-practice, Google Cloud project goodwill-youtube-upload / 440497871188, OAuth app "Goodwill Video Uploader", Testing mode, test user = channel Gmail; signed in OK). API audit form submitted 22 Nov 2026 and closed by Google 23 Nov as not needed (answers in tools/audit/FORM_ANSWERS.md; privacy page https://www.goodwillonlinetuition.com/privacy-policy). In Testing mode the sign-in expires after about 7 days: run `python tools\upload_youtube.py --login` again if it fails.

## Channel links (YouTube Studio → Customisation → Profile)
- Channel description rewritten 24 Nov 2026 (970/1000): Rainy Goodwill, 30 years, since 1999; GCC first; CBSE 11 & 12, Kerala Plus One/Two, B.Com & M.Com (Financial, Corporate, Cost Accounting, Income Tax), MBA & BBA (Financial Management — his speciality — and Management Accounting). Main video descriptions can name the teacher as Rainy Goodwill.
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
- MGU B.Com Hons Sem 6 Cost Accounting Q13 (Alpha Manufacturing), "Try it yourself" — main 16:9 video, 4:40, bigger text, same playlist — https://youtu.be/K8D6-XDE_pI (published 22 Nov 2026)
- Tender or Quotations Illustration 17: New Model Price | MGU B.Com Hons Sem 6 Cost Accounting — https://youtu.be/x6KsUmfpVIM (published 24 Nov 2026, uploaded by script)
- TS Grewal Class 11 Q39 Final Accounts with 8 Adjustments | Trading, P&L, Balance Sheet 2026-27 — https://youtu.be/xARyjWijgpQ (published 25 Nov 2026, re-uploaded with "Gray-waal" pronunciation; the first upload qp3WQsu1z-o said "Groo-ul" and was deleted; thumbnail, Education fields and pinned quiz (fire claim ₹2,000 → loss ₹6,000) done; playlist "TS Grewal Class 11 · Final Accounts")
- TS Grewal Class 11 Q38 Final Accounts | Purchases Adjusted, 5 Adjustments | Balance Sheet 2026-27 — https://youtu.be/4Scn74ivA3I (published 26 Nov 2026, uploaded by script; FIRST video in Rainy's own cloned voice; thumbnail + Education done; pinned quiz: goods taken ₹2,500 → purchases ₹2,87,500; 3D "Goodwill Solved Notes" book thumbnail; playlist "TS Grewal Class 11 · Final Accounts")
- TS Grewal Class 11 Q36 Final Accounts | 2 Hidden Adjustments, 6 Adjustments | Balance Sheet 2026-27 — https://youtu.be/PQAtokoqZfg (published 27 Nov 2026, uploaded by script; first video on the #C8C8C8 grey background, Rainy's voice; thumbnail + Education done; pinned quiz: new machine bought 1 Jan 2026 → depreciation ₹1,250; playlist "TS Grewal Class 11 · Final Accounts")
- Channel views: 4,253 (10 Nov 2026) → 4,310 (11 Nov 2026). Compare again around 18 Nov.
- Popular tab (19 Nov 2026): photo Shorts of real exam question papers lead — B.Com Corporate Accounting I paper (QP 22100578, Apr 2022) 1,020 views, others 757 / 663 / 425; MGU Income Tax promo 218; Harris "Business Entity Concept" 107 (6 days old). But those question-paper Shorts are 4 years old (≈0.2–0.7 views/day); the Harris Short got ≈18 views/day — the new animated daily Shorts are far ahead per day.
