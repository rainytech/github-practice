# TeachMark — Where I Stopped Teaching

Remembers, for each student, the **folder, PDF file, page (e.g. 8 / 26) and point
(e.g. Illustration 9)** where you stopped — read automatically from a screenshot.

- Fully offline. Uses the OCR built into Windows. No internet, no accounts.
- Never opens or controls Icecream PDF Editor (or any PDF viewer).
- Keeps the last 5 stops per student, with the screenshot.

## Setup (one time, Windows 10/11)

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>.
   On the first installer screen, tick **"Add python.exe to PATH"**.
2. Copy this `teaching-assistant` folder anywhere (e.g. `Documents\TeachMark`).
3. Double-click **`run.bat`**. The first start installs everything (2–3 minutes);
   later starts are instant.

Optional — a single `TeachMark.exe`: double-click **`build_exe.bat`**, then use
`dist\TeachMark.exe` (you can pin it to the taskbar).

## Daily use

**After a class**
1. Press **Win + Shift + S** and select the whole Icecream window
   (the bottom bar with the file path and `8 / 26` must be visible).
2. Click TeachMark and press **Ctrl + V**.
3. Check the details (student is suggested automatically), add a note if you
   like, press **Save**.

**Before a class** — click the student. You see:

| Folder | File | Page | Stopped at |
|---|---|---|---|
| 23 sept akhil sir | combined_akhil_sir_document Compressed.pdf | **8 / 26** | **Illustration 9** |

Or click **Latest Screenshot** to load the newest picture from
`Pictures\Screenshots` (e.g. after **Win + PrtScn**).

Buttons: **Show in Folder** (Explorer with the file highlighted), **Copy File Path**,
**View Screenshot**.

You can also drag an image file onto the window, or use **Open Image…**.

## Weekly timetable

1. Take a screenshot of this week's timetable (a grid: times like `4.3` = 4:30 PM
   across the top, `25 Fri` down the side, student names in the cells).
2. Click **📅 Timetable**. It reads the newest screenshot and lists the classes.
3. Check the names, press **Save**.

The **Today** list at the top then shows each class with where to continue:
🟢 Ready · 🟠 Prepare next PDF (80% done) · 🔴 PDF finished · ⚪ No stop saved yet.
The current or next class is highlighted. After class, the screenshot is matched
to the class that just ended, so the student is filled in for you.

## How the student is suggested

1. The timetable class that just ended (if a timetable is saved), else
2. the student who last used the same PDF, else
3. a student whose name appears in the folder/file name (e.g. "Akhil sir" in
   `23 sept akhil sir`).

Otherwise choose or type the name — new names are added automatically.

## Data

Stored in `%APPDATA%\TeachMark` (`teachmark.db` + `shots\`).
Back up that folder to keep your history.

## Troubleshooting

- **"Windows OCR has no English language pack"** — Settings → Time & language →
  Language & region → Add a language → *English (United States)*.
- **"✘ Not found"** under the PDF file — the file was moved/renamed or the path
  was misread; fix it or press **Browse…**.
- The app looks for PDFs under your Desktop (including OneDrive Desktop).

## For developers

```
pip install -r requirements.txt pytest
python -m pytest tests
python reader.py screenshot.png      # prints what was read
```
Off Windows, Tesseract (`pip install pytesseract`) is used as the OCR engine.
