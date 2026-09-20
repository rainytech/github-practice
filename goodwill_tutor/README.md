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

Switch with the dropdown in the top bar.

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

## Chapter documents

Each answer is appended to the open document as a new `.page-block`, so one
chapter becomes one HTML file and one PDF. *New document* starts a fresh one.
*Remove last block* drops the most recent question.

Manual edits made in the HTML tab survive later appends.

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
