# Goodwill Gemini Tutor

Solve Accountancy and Income Tax problems from a scanned page, produce an A4
teaching document in the Goodwill house style, review it, and convert it to PDF
for Zoom teaching.

```
Attach PDF / image  ->  Gemini solves  ->  HTML in house style
->  review and edit  ->  Playwright PDF  ->  teach
```

## Getting a question in

Three ways, all equivalent:

- **Ctrl+V** — paste a screenshot (Snipping Tool), an image copied from a PDF
  reader or browser, or files copied in File Explorer
- **Attach PDF / image** — the file dialog, several pages at once
- Mix both in one message

Pasting needs Pillow. Without it, Ctrl+V still pastes text and says so.

## Setup (once per machine)

```
pip install -r requirements.txt
playwright install chromium
```

Set the API key in the environment — never in the code:

```
Windows      setx GEMINI_API_KEY "your-key-here"        then reopen the terminal
Linux / Mac  export GEMINI_API_KEY="your-key-here"
```

## Run

```
python goodwill_tutor.py
```

## The files

| File | What it holds | Edit it when |
|---|---|---|
| `goodwill_tutor.py` | The window: chat, artifact pane, buttons | Changing the interface |
| `house_style.py` | The A4 stylesheet, header, validator | Changing colours, fonts, spacing |
| `prompts.py` | What Gemini is told in each mode | Changing how it solves or writes |
| `gemini_api.py` | All network calls | Changing models, tokens, uploads |
| `pdf_export.py` | Playwright PDF and preview rendering | Changing the PDF geometry |
| `quick_edits.py` | The free edits: what they read and what they change | Adding a free edit |

Gemini writes only the `.page-block` body. Every line of CSS comes from
`house_style.py`, so the house style cannot drift between documents.

What the model sends is cleaned before it is kept:

- anything written **before** the first `.page-block` is dropped — a weak model
  narrates its plan first, and that planning used to print as page one
- `66,550 / 1.331` becomes a stacked fraction and `(1 + r)^n` a superscript,
  with the power kept under the line where it belongs
- no figure is ever changed; only how a division is written

Both are reported in the chat, so you can see what was done.

A small model sometimes argues with the contract for thousands of words
without ever starting the document — "Wait, the prompt says no \\times, I'll
use multiplied by", over and over. That is cut off as soon as the same kind of
line appears four times, or after 9,000 characters with no document in sight:
the chat says the model kept repeating itself, and nothing is added. Waiting
for the token limit instead would cost minutes, and real money on a paid model.

A small model sometimes recites the contract instead of following it — "the
HTML must start with `<div class="page-block">` and end with `</div>`". That
quoted tag is an example, not a document, so it is ignored, and an answer with
no house-style markup in it is refused outright: the chat says so and the open
document is left exactly as it was.

The interface is warm beige throughout, with no white surfaces. The document
does not follow it — it keeps the `#C8C8C8` house page colour, set in
`house_style.py`.

## Choosing models

Two settings, both in **Settings**:

- the **model** in the top bar solves the problem
- **Check the answer with** picks the model that verifies it

A model checking its own arithmetic can repeat its own slip, so solving on a
cheap model and checking on a strong one is worth the few extra paise — the
check is short, so it costs little.

### What the meter costs mean

The rupee figure is **list price**, computed from the rates in `PRICING`
(`gemini_api.py`, checked September 2026) at Rs. 88 to the dollar. It is shown
with a `~` because it does not know about:

- batch rates, which are half price
- your actual exchange rate

Cached input **is** accounted for. Gemini reports how much of a prompt it served
from cache, that part bills at a tenth, and the meter says so:
`~10 paise · 4.4k tok (2.2k cached)`. If no "cached" appears, nothing was
cached and you are paying full rate for the house-style contract on every
question — about 5 paise of the roughly 11 paise floor.

Gemma models cost nothing — Google serves them on the Gemini API free, with
rate limits instead of a bill — so the meter reads **free**. They do not follow
the house-style contract closely: expect slash fractions instead of stacked
ones and repeated top-bars, both of which the validator flags.

The Flash line runs at an introductory rate until 31 December 2026 and doubles
on 1 January 2027. The table carries both, and switches itself on the date.
A prompt over 200,000 tokens re-rates the whole request on the Pro line, which
the table also handles.

Rates differ per Flash generation — 3.5 Flash costs twice what 3.6, 3.7 and 3.8
Flash do — so `PRICING` is an ordered list, matched first-hit. `flash-lite` is
listed before `flash` deliberately: match on the longest substring instead and
`gemini-3.5-flash-lite` gets priced as a 3.5 Flash, six times too much.

## Modes

- **Solve** — accounting and income tax problems, full working notes, verification pass
- **Notes** — teaching notes from source material, same house style
- **General** — plain conversation, no document

Switch with the dropdown in the top bar. Last year's preset is removed on first
run — it wrote markdown, not house-style HTML. Your own presets, model and
limits are untouched.

## The right side

The right side is the finished page, laid out like Claude.ai's artifact panel.

- **Preview | Code** — Preview shows the page drawn by Chromium, the same
  engine that makes the PDF, so it cannot disagree with what prints. It
  redraws itself after every answer and every applied edit. Code is the HTML,
  editable: change it, then **Apply my edits**.
- **Selecting text in the Preview** works as in a browser, though the Preview
  is a picture: Chromium records where every word was drawn, and the panel
  does the rest. Press and drag to select in reading order (drag past the
  edge and the page scrolls), double-click a word, triple-click a line or
  cell, Ctrl+A for the whole page. Letting go copies; Ctrl+C and right-click
  > Copy work too. Lines paste as lines, table cells tab-apart (so a table
  pastes into Excel), a fraction as 66,550/1.331, a power as 1.10^3.
  Right-click > Open in browser shows the page in Edge or Chrome.
- **Make PDF** renders the PDF now and opens it. **Open PDF** opens the one on
  disk, and reads **Open old PDF** in red when the page has changed
  since.
- **◀ v3 of 5 ▶** — every answer keeps a version of the page. The arrows step
  back and forward; the version shown is the document, and the next answer
  builds on it. Later versions are never deleted, so going back loses nothing.
  An applied edit and a removed question keep a version too.
- **More ▾** — Save as HTML, open the HTML file, apply edits, check house
  style, new document, remove the last question, open the folder, copy.

Gemini's verification pass and the house-style validator report into the chat
on the left, so there is only one place to read.

The verdict is read from the whole of what the checker wrote, not its first
word. A small model writes a paragraph before it answers, and sometimes glues
the word to a figure — "Present Value: 50,000VERIFIED" — so a mismatch buried
under a preamble would otherwise have been reported in green as a pass. A
mismatch anywhere wins; "no mismatch" and "could not be verified" are not
verdicts; anything else is reported as unclear rather than as a pass.

The verifier is told to ignore rounding: a four-decimal table factor cannot give
an exact round figure, so a difference of a rupee or less that comes only from
rounding is not reported. It reports what a student would write down wrongly —
a wrong factor, period, rate or treatment.

## Add or edit — like Claude.ai

The line above **Send** says what Send will do, read from the words typed:

- **Will add** — "add a question", "one more", "solve Illustration 8",
  "append to the same artifact": a new question goes at the end.
- **Will edit** — "change", "fix", "remove", "correct", "use str_replace to…",
  "add a hint to Illustration 6": the page is changed in place. Gemini is
  shown the page with each block numbered and sends back only the blocks it
  changed; the rest stay exactly as they are, hand edits included. An answer
  that does not say which block it changed is refused, and the page is left
  alone. The block's own outer tag is always kept, so an edit cannot box or
  restyle the whole page.
- **Will show** — "display the full merged HTML" on its own opens the Code
  tab. Nothing is sent to Gemini: the app always keeps the merged document.

Click the line to switch Add and Edit for that one message.

"Remove Illustration 7", "remove the last question", "remove the book name
and page from the top bar", "change the book name to P.K. Lazar, Pg. 43" and
"set the page to 43", "number it Illustration 6", "rename it illus 8" and "change the date to 25th sept" are done by the app itself — free, instant, and they
cannot touch anything else. Sent to Gemini, the top-bar one cost 23 paise.

A colour, font, border or background request ("change the background of the
table to c8c8c8") is answered by the app, not sent: the look comes from
`house_style.py`, and Gemini may not write CSS. Asked to, a small model argues
with that rule until it is stopped.

An edit is verified again only when it changes a figure. Rewording a sentence
or fixing a title costs the edit alone, not the edit and a second check.

### The book and page in the top bar

They print only when you type them. "solve it — P.K. Lazar, Pg. 43" prints
**P.K. Lazar | Pg. 43**; "solve it, page 43" prints **Pg. 43**; with neither,
the top bar shows the topic alone. Whatever Gemini writes there is checked
against your message, so a book it guesses — or reads off the scan — is never
printed.

A small model sometimes leaves out the question number. The chat says so under
the card; "number it Illustration 6" puts it in, free.

### Free edits

When the line above Send reads **Free**, the app makes the change itself —
instant, exact, nothing sent to Gemini. Type **help** for the list:

| Type | Does |
|---|---|
| `undo` · `redo` | step back or forward one version |
| `replace 'Find' with 'Calculate'` | every question; add `in Illustration 6` for one. Quotes needed |
| `change Rs. to ₹` · `change ₹ to Rs.` | the currency sign, everywhere |
| `change the title to ADMISSION OF A PARTNER` | the top bar's topic |
| `add (CBSE 2019) to Illustration 6` · `remove the source` | the exam source tag |
| `add answer: Rs. 50,000` · `remove the answer line` | the [Ans.: ...] line |
| `add hint: use 1.10 × 1.10` · `remove the hint` | the [Hint: ...] line |
| `change the final answer to ...` | the ∴ line |
| `remove the rule note` | the ► notes |
| `remove the solutions` · `remove the solution from Illustration 6` | a worksheet: questions only |
| `renumber the questions from 1` | 1, 2, 3 ... in page order |
| `move Illustration 7 above Illustration 6` · `move the last question to the top` | reorder |
| `remove the top bar` | the topic and page line |
| `make the pdf` · `open the pdf` · `show the code` · `show the preview` | the buttons, by typing |
| `rename the document to Discounting — Set 1` | the sidebar name |
| `remove Illustration 7` · `number it Illustration 6` · `rename illustration no. 10` | as above |
| `remove the second question` · `remove the duplicate question` | by position; the later of two copies |
| `change the book name to P.K. Lazar, Pg. 43` · `change the date to 25th sept` | as above |

An answer or hint with no question named goes under the last question. A
word that is not on the page is reported, not guessed. Every free edit keeps a
version, so `undo` takes it back.

### Cards and Retry

The chat shows a short card for each answer — **Illustration 7 added ·
Verified ✓** — instead of the whole answer: the answer is the page on the
right. Clicking the card shows the Preview. A mismatch or an unclear
verification is still written out in full under the card.

**↻ Retry** under the last answer puts the page back as it was before that
answer and sends the same message again. The answer it replaces stays in the
versions.

## Chapters and documents

The sidebar is a two-level tree. A **chapter** holds **documents**; a document
is one HTML page, its PDF, and the conversation that produced it.

- **Double-click** a document to reopen it — chat and all
- **Right-click** for Rename, Duplicate, Pin, Delete
- **+ Chapter** / **+ Document** at the top
- A pinned chapter sorts to the top, marked `*`

Each answer appends to the open document as a new `.page-block`, so one chapter
becomes one HTML file and one PDF. Manual edits in the editor survive later
appends. **Open PDF** in the header opens the PDF; **More ▾** opens the HTML.

The PDF is made for you as soon as an answer lands, and again whenever you
apply an edit, so Open PDF is current without your doing anything. It takes a
couple of seconds, runs in the background, and costs nothing — Chromium is on
your own machine. Turn it off in **Settings > Make the PDF automatically after
each answer**, and then **Make PDF** makes it on demand.

If the PDF is open in your reader, Windows locks it and the status bar says so
in red — close it and apply again, or press **Make PDF**.

Closing the window while a PDF is still rendering waits for it — the status bar
says "Finishing the PDF before closing...". Without that wait, Chromium's Node
process loses the pipe to Python and prints a page of `EPIPE: broken pipe` to
the console, which looks alarming and means nothing.

Send a question with nothing open and a document is created for you, titled
from what you typed. When the first answer arrives the document is renamed from
the answer itself — **"Discounting — Illustration 6 (Pg. 43)"** — taken from the
top bar and the question number, so a chapter does not fill with twenty
documents all called "solve it in a table format". Rename one yourself and your
name stands; the app never overwrites it.

### An older document keeps its old colours

A document is saved whole — stylesheet and all — and a new question is spliced
into it so your own edits survive. The cost is that a document written last
year, or this morning before a fix, keeps the stylesheet it was born with, and
looks wrong in **every** program that opens it: Chrome, a PDF reader, anything.
That is not the viewer's fault and no setting will change it.

There is nothing to do about it. The stylesheet belongs to the app, not to the
document, so every stored document is brought up to date when the app starts —
no menu, no question asked. Only the `<style>` block changes; questions, tables
and anything you typed by hand stay exactly where they are, and a document that
is already current is not rewritten at all. A question or page number printed
at body size is set at 20pt at the same time. Opening such a document remakes
its PDF by itself.

### "Add one more question" and the earlier one

Asked for one more question "with the full merged HTML", a model sends the
earlier question back along with the new one. The app already keeps the
document, so an earlier question that comes back word for word, with the same
amounts, is left out and the chat says so. A question solved again by another
method reads differently and is kept. You never need to ask for the merged
document: every answer is added after the ones before it.

An earlier question sent back re-worded — the same wording and amounts in the
question, new words in the working — is a copy too, and is left out, unless
you asked for another method or to solve it again.

### Why a second question used to cost more

Each Send used to carry the whole conversation: the first page's screenshot
and its full HTML answer went to Gemini again with the second question — about
4,000 tokens, roughly 8 paise more, and more with every question added. The
document already holds those answers, so earlier answers now go as a short
summary (the question, its wording, its final answer) and earlier pages as a
placeholder. Gemini still sees what came before, enough to match its
difficulty and phrasing, without paying to read it all again.

### The PDF goes out of date

With the automatic render switched off, adding a question rewrites the HTML but
leaves the old PDF on disk. The button then reads **"Open old PDF"** in red,
and opening it asks first. Press **Make PDF** to remake it.

If the PDF is open in your reader, Windows will not let it be overwritten. The
app checks before rendering and tells you to close it, rather than failing
several seconds later with a Chromium error.

### Where it lives

```
~/.goodwill_tutor/
    library.json                 chapters, order, pins
    chapters/<chapter>/
        chapter.json
        <document>/
            document.json        title, blocks, model
            document.html
            document.pdf
            conversation.json
            versions/            v1.html, v2.html ... versions.json
```

Work from the previous version is copied into a chapter called
**"Before chapters"** the first time you run this. Chats are matched back to
their pages by the timestamp in the filenames. **Originals are copied, never
moved** — `Desktop/Goodwill_Solutions` is left exactly as it was.

### Table widths

A table fits its own contents — a three-row statement no longer spreads across
the page with blank space beside every amount, and a wide journal still stays on
the paper and wraps instead of cropping.

The exception is a two-sided ledger account, where both halves must match:
`<table class="wn full">` with a `<colgroup>` spans the page. Gemini is told
which to use.

## Updating

```
python update.py
```

Fetches every file the app and its tests need, checks each one before it
replaces your copy, then runs the tests. A download that fails keeps the file
you had, so an update can never leave the app half-installed. Your chapters
and documents live elsewhere and are never touched.

## Checking that it still works

```
python tests\run_all.py
```

Ten groups, about half a minute, and it prints `ALL PASS` or names what broke.
It runs against a throwaway folder, sends nothing to Gemini and costs nothing,
so it can be run as often as you like — after any change, before any class.

| Group | What it holds to |
|---|---|
| the document rules | preamble stripped, fractions stacked, loops caught, titles read |
| chapters and documents | saving, renaming, copying, deleting, odd names |
| a whole answer | clean answer in, house-style page out, named, saved |
| a weak model | reciting, looping and chatty verdicts all handled |
| an older document | old stylesheet spotted, swapped, questions kept |
| the window | every control reachable, PDF buttons honest, no white |
| like Claude.ai | add or edit, versions, cards, Retry, the Claude phrases |
| the free edits | every free edit made here, none sent to Gemini |
| the printed page | A4, selectable text, `#C8C8C8` throughout, answer never stranded |
| the updater | every file listed; a bad download never replaces a good one |

The last group runs Chromium and takes a few seconds; it says SKIP instead of
failing if Playwright is not installed. `pip install pypdfium2` adds the page
size and colour checks.

Break something on purpose to see it work — change the page colour in
`house_style.py` and three of the six groups will name it.

### The final answer stays with its working

`.final-ans` is kept on the same page as the line above it (RULE 4 extended
with the teacher's approval, 23 Sept 2026). When the two will not both fit,
they move to the next page together. On paper the last block carries no bottom
margin: nothing follows it, and that gap was enough to push the answer over
alone with room still left on the page.

### The question number stays with its question

`Illustration 7.` is kept on the same page as the first sentence of its
question (approved by the teacher, 24 Sept 2026). Without it, a question that
began near the foot of a page printed its number alone as the page's last line.
The rule is `break-before: avoid` on that first sentence — no forced break,
and nothing held together but those two lines.

Each sentence line in a question, its notes, adjustments and working-note text
has a quarter line (3pt) under it, so lines read apart on Zoom (approved by
the teacher, 24 Sept 2026). Tables and formula boxes are unchanged.

Lines holding a stacked fraction get extra space above and below, since a
fraction is two lines tall inside one. The body stays at line-height 1.5.

## Page geometry

Fixed, and enforced by the validator:

```
@page margin 0   +   body padding 0.5cm   +   Playwright margin 0cm
```

The body padding is the only page margin.

## What the validator checks

Forced page breaks, break-avoidance scope, `.q > span` versus `.q span`,
`@page` margin, body padding, the `#C8C8C8` background, division signs and
slash fractions, `table-layout: fixed`, repeated headers, and social links.

Errors are listed before the PDF is generated, with the option to continue anyway.

Table cells are painted `#C8C8C8` with `!important`, so a model that writes
`style="background:#fff"` into a row cannot whiten the page — the validator
warns about it as well. White seen in **Icecream PDF Editor** is that program's
Edit mode outlining each text object; switch to **Annotate** and it goes.
