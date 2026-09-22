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

Gemini writes only the `.page-block` body. Every line of CSS comes from
`house_style.py`, so the house style cannot drift between documents.

What the model sends is cleaned before it is kept:

- anything written **before** the first `.page-block` is dropped — a weak model
  narrates its plan first, and that planning used to print as page one
- `66,550 / 1.331` becomes a stacked fraction and `(1 + r)^n` a superscript,
  with the power kept under the line where it belongs
- no figure is ever changed; only how a division is written

Both are reported in the chat, so you can see what was done.

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

The right side is the document as editable HTML, and nothing else. Two menus
sit in its header.

**▾** — what to do with the finished document:

- **Preview** — opens a window showing the page rendered by Chromium, the same
  engine that makes the PDF, so it cannot disagree with what prints
- **Save as HTML**
- **Save as PDF**

**More** — building the document: apply edits, check house style, new document,
remove the last question, open the folder, copy.

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

## Chapters and documents

The sidebar is a two-level tree. A **chapter** holds **documents**; a document
is one HTML page, its PDF, and the conversation that produced it.

- **Double-click** a document to reopen it — chat and all
- **Right-click** for Rename, Duplicate, Pin, Delete
- **+ Chapter** / **+ Document** at the top
- A pinned chapter sorts to the top, marked `*`

Each answer appends to the open document as a new `.page-block`, so one chapter
becomes one HTML file and one PDF. Manual edits in the editor survive later
appends. Under the editor, two cards open the PDF and the HTML.

The PDF is made for you as soon as an answer lands, and again whenever you
apply an edit, so the card is current without your doing anything. It takes a
couple of seconds, runs in the background, and costs nothing — Chromium is on
your own machine. Turn it off in **Settings > Make the PDF automatically after
each answer**, and then **▾ > Save as PDF** makes it on demand.

If the PDF is open in your reader, Windows locks it and the status bar says so
in red — close it and apply again, or use **▾ > Save as PDF**.

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

### The PDF goes out of date

With the automatic render switched off, adding a question rewrites the HTML but
leaves the old PDF on disk. The card then reads **"PDF — out of date"** in red,
and opening it asks first. Use **▾ > Save as PDF** to remake it.

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
