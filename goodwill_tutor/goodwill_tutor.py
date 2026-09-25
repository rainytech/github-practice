"""
GOODWILL TUITION CENTRE — Gemini Tutor
======================================
Run this file.

    python goodwill_tutor.py

Workflow:
    Attach PDF / image  ->  Gemini solves  ->  HTML in house style
    ->  review and edit  ->  Playwright PDF  ->  teach on Zoom

Requires:  pip install requests playwright matplotlib pillow
           playwright install chromium
Key:       set GEMINI_API_KEY in the environment.
"""

import base64
import html as html_lib
import io
import json
import os
import pathlib
import queue
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk

import gemini_api as api
import house_style as hs
import library
import pdf_export
import prompts
import quick_edits

# ── optional dependencies ────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    PIE_CHARTS = True
except ImportError:
    PIE_CHARTS = False

# Tk can only read TEXT from the clipboard, never image data, so pasting a
# screenshot needs Pillow.
try:
    from PIL import ImageGrab, Image
    CLIPBOARD_IMAGES = True
except ImportError:
    CLIPBOARD_IMAGES = False


# ═══════════════════════════════════════════════════════════════
#  PATHS AND CONSTANTS
# ═══════════════════════════════════════════════════════════════

APP_DIR = os.path.join(os.path.expanduser("~"), ".goodwill_tutor")
CONVERSATIONS_DIR = os.path.join(APP_DIR, "conversations")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
SOLUTIONS_DIR = os.path.join(DESKTOP, "Goodwill_Solutions")
PREVIEW_DIR = os.path.join(APP_DIR, "preview")
PASTED_DIR = os.path.join(APP_DIR, "pasted")
# A4 is 210mm, which is 794px at 96dpi. The Preview tab lays the page out at
# exactly that width, with the print rules, so a line wraps where the PDF
# wraps it. At 880px the institute name fitted on one line in Preview and broke
# onto two in the PDF.
PREVIEW_WIDTH = 794

for _d in (APP_DIR, CONVERSATIONS_DIR, SOLUTIONS_DIR, PREVIEW_DIR, PASTED_DIR):
    os.makedirs(_d, exist_ok=True)

# Interface palette — warm beige throughout. Nothing white or near-white:
# every surface sits in a narrow warm band, separated by tone rather than by
# brightness, so the eye is not fighting glare all day.
# The DOCUMENT keeps its own #C8C8C8 page colour; that is house style and is
# set in house_style.py, not here.
BG = "#F3F0E7"           # main background
SIDEBAR = "#E9E5D8"      # side panels and toolbars
FIELD = "#F6F3EA"        # typing box, editor, lists
TEXT = "#2A2723"         # primary text, warm near-black
MUTED = "#8A8376"        # secondary text
BORDER = "#DDD7C7"
ACCENT = "#D97757"       # Claude orange
BLUE = "#0F5FA6"         # links and headings
GREEN = "#2D6A2D"        # success
RED = "#B81E1E"          # failure
USER_BUBBLE = "#E9E5D8"
AI_BUBBLE = "#F6F3EA"
ARTIFACT_BG = "#F3F0E7"

MAX_HISTORY_TURNS = 20
ATTACH_TYPES = [
    ("Question pages", "*.pdf *.jpg *.jpeg *.png *.webp"),
    ("PDF", "*.pdf"),
    ("Images", "*.jpg *.jpeg *.png *.webp"),
    ("All files", "*.*"),
]


# ═══════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════

# Bumped when the preset structure changes. A file written by an older
# version is migrated on load rather than being trusted as-is.
SETTINGS_SCHEMA = 3

DEFAULT_SETTINGS = {
    "schema": SETTINGS_SCHEMA,
    "active": prompts.DEFAULT_MODE,
    "presets": {k: dict(v) for k, v in prompts.MODES.items()},
    "model": "",
    "verify_model": "",       # blank means: check with the same model that solved
    "max_tokens": api.DEFAULT_MAX_TOKENS,
    "temperature": api.DEFAULT_TEMPERATURE,
    "thinking_budget": None,
    "verify": True,
    "charts": False,
    "auto_pdf": True,         # make the PDF straight after each answer
}


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            merged = json.loads(json.dumps(DEFAULT_SETTINGS))
            merged.update(data)
            merged["presets"] = dict(merged.get("presets") or {})

            old_schema = int(data.get("schema", 1))

            # The built-in modes are always present and always current.
            # An older file may hold a preset of the same name carrying last
            # year's prompt, which would silently produce markdown instead of
            # house-style HTML — so the built-ins overwrite, not merge.
            for key, mode in prompts.MODES.items():
                merged["presets"][key] = dict(mode)

            if old_schema < 2:
                # Last year's model IDs and limits no longer exist.
                merged["active"] = prompts.DEFAULT_MODE
                merged["model"] = ""
                merged["max_tokens"] = api.DEFAULT_MAX_TOKENS
                merged["temperature"] = api.DEFAULT_TEMPERATURE

            if old_schema < 3:
                # Last year's preset writes markdown, not house-style HTML, and
                # picking it by mistake wastes a paid call. Schema 2 kept it as
                # "(v1)"; it is now removed. The model and limits are left
                # alone here — only the dead preset goes.
                merged["presets"].pop("default", None)
                merged["presets"].pop("default_v1", None)

            if old_schema < SETTINGS_SCHEMA:
                merged["schema"] = SETTINGS_SCHEMA

            if merged["active"] not in merged["presets"]:
                merged["active"] = prompts.DEFAULT_MODE
            return merged
    except Exception as exc:
        print(f"[settings load failed] {exc}")
    return json.loads(json.dumps(DEFAULT_SETTINGS))


def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(SETTINGS, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"[settings save failed] {exc}")


SETTINGS = load_settings()


def active_preset():
    return SETTINGS["presets"][SETTINGS["active"]]


def active_mode_key():
    return SETTINGS["active"]


# ═══════════════════════════════════════════════════════════════
#  RUNTIME STATE
# ═══════════════════════════════════════════════════════════════

attachments = []          # file paths queued for the next message
conversation_history = []  # Gemini contents array
doc_blocks = []           # .page-block fragments in the open chapter document
last_full_html = ""
last_body = ""
last_response_text = ""
verify_report = ""
current_chapter = None    # the open chapter's id
current_doc = None        # the open document's id
# Titles this app wrote itself. A document keeps an app-written name only until
# the teacher renames it; after that his name stands.
auto_titles = {}
model_ids = []            # [(id, display)] fetched from the API
preview_image = None      # live PhotoImage; Tk discards it without a reference
version_at = None         # the version number the right side is showing
intent_override = None    # "add" / "edit" when the teacher clicked the label
last_turn = None          # what the last Send was, so Retry can repeat it
retry_btn = None          # the Retry button under the last answer
LIVE_PREVIEW = True       # render the Preview tab through Chromium

stop_event = threading.Event()
ui_queue = queue.Queue()
busy = False


def post(fn):
    """Schedule a callable to run on the Tk main thread."""
    ui_queue.put(fn)


def pump():
    """Drain work posted by background threads."""
    while True:
        try:
            fn = ui_queue.get_nowait()
        except queue.Empty:
            break
        try:
            fn()
        except Exception as exc:
            print(f"[ui task failed] {exc}")
    root.after(40, pump)


# ═══════════════════════════════════════════════════════════════
#  CHARTS  (optional — off unless switched on)
# ═══════════════════════════════════════════════════════════════

CHART_TITLES = {
    "OLD": "Old Profit Sharing Ratio",
    "NEW": "New Profit Sharing Ratio",
    "GAIN": "Gaining Ratio",
    "SACRIFICE": "Sacrificing Ratio",
    "CAPITAL": "Capital Contribution",
}
CHART_COLORS = ["#0057B8", "#6A0DAD", RED, GREEN, "#C2185B", "#e07a3c"]

CHART_INSTRUCTION = """

=== CHARTS (this document only) ===
Where you state a profit-sharing, gaining, sacrificing or capital ratio, add a marker
on its own line immediately after the sentence:
  [CHART:OLD] A:5, B:3, C:2 [/CHART]
Types: OLD, NEW, GAIN, SACRIFICE, CAPITAL. The marker is replaced by a pie chart."""


def pie_chart_b64(chart_type, ratios):
    if not PIE_CHARTS:
        return None
    try:
        labels, values = [], []
        for part in ratios.split(","):
            if ":" not in part:
                continue
            name, val = part.split(":", 1)
            labels.append(name.strip())
            values.append(float(val.strip().replace(",", "").replace("Rs.", "").replace("₹", "")))
        if not values or sum(values) == 0:
            return None
        fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
        _, _, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%",
            colors=CHART_COLORS[:len(values)], startangle=90,
            textprops={"fontsize": 12, "weight": "bold"},
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        for t in autotexts:
            t.set_color("white")
            t.set_weight("bold")
        ax.set_title(CHART_TITLES.get(chart_type, "Ratio"), fontsize=14,
                     fontweight="bold", color="#0057B8", pad=15)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return "data:image/png;base64," + base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        print(f"[chart failed] {exc}")
        return None


CHART_RE = re.compile(r"\[CHART:(\w+)\]\s*(.+?)\s*\[/CHART\]", re.DOTALL)


def render_charts(text):
    """Replace chart markers with embedded images, or strip them if charts are off."""
    if not SETTINGS.get("charts"):
        return CHART_RE.sub("", text)

    def repl(m):
        img = pie_chart_b64(m.group(1).upper(), m.group(2))
        if img:
            return (f'<div style="text-align:center;margin:12px 0;">'
                    f'<img src="{img}" style="max-width:380px;height:auto;"></div>')
        return ""
    return CHART_RE.sub(repl, text)


# ═══════════════════════════════════════════════════════════════
#  TEXT HELPERS
# ═══════════════════════════════════════════════════════════════

LATEX_MAP = {
    r"\\times": "&times;", r"\\div": "&divide;", r"\\pm": "&plusmn;",
    r"\\leq": "<=", r"\\geq": ">=", r"\\neq": "!=",
    r"\\approx": "~", r"\\therefore": "&there4;", r"\\because": "&because;",
    r"\\rightarrow": "&rarr;", r"\\leftarrow": "&larr;",
}


def latex_to_unicode(text):
    """Safety net: convert stray LaTeX the model may emit despite instructions."""
    text = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}",
                  r'<span class="frac"><span class="num">\1</span>'
                  r'<span class="den">\2</span></span>', text)
    for pattern, repl in LATEX_MAP.items():
        text = re.sub(pattern, repl, text)
    text = re.sub(r"\$\$([^$]+)\$\$", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = re.sub(r"\\text\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", text)
    return text


# A tag starts with a letter or a slash. Anything else after "<" is ordinary
# text — "n < 5 years" is a comparison, not markup, and Chromium reads it that
# way too. Matching a bare "<...>" instead would swallow every character up to
# the next ">", losing part of the answer.
TAG_RE = re.compile(r"</?[A-Za-z][^<>]*>|<!--.*?-->", re.DOTALL)


def html_to_chat_text(html):
    """Flatten an HTML fragment into readable lines for the chat pane."""
    text = re.sub(r"<(style|script).*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # A fraction the model already bracketed keeps its own brackets, so the
    # chat reads "(1 over 1.331)", not "((1 over 1.331))".
    text = re.sub(r'\(\s*<span class="frac"><span class="num">(.*?)</span>'
                  r'<span class="den">(.*?)</span></span>\s*\)', r"(\1 over \2)", text)
    text = re.sub(r'<span class="frac"><span class="num">(.*?)</span>'
                  r'<span class="den">(.*?)</span></span>', r"(\1 over \2)", text)
    # Powers and subscripts lose their meaning when the tags are simply dropped:
    # (1.10)<sup>3</sup> would read as "(1.10)3".
    text = re.sub(r"<sup>(.*?)</sup>", r"^\1", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<sub>(.*?)</sub>", r"_\1", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</(div|tr|table|p|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</t[dh]>", "  ", text, flags=re.IGNORECASE)
    text = re.sub(r"</span>", " ", text, flags=re.IGNORECASE)
    text = TAG_RE.sub("", text)
    # A streamed snapshot can stop in the middle of a tag. Drop the dangling
    # opener so "<div class=\"t" does not appear as text in the chat.
    text = re.sub(r"<[^<>]*$", "", text)
    # Every entity, not a chosen few: "&times;" reached the chat as five
    # letters because it was missing from a hand-kept list.
    text = html_lib.unescape(text).replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def for_chat(text):
    """Pick the right flattening for the current mode."""
    if active_mode_key() == "general":
        return text.strip()
    return html_to_chat_text(text)


def indian_format(value):
    """12,34,567 — used by the validator report and any local formatting."""
    s = str(int(value))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
    return f"{head},{tail}"


# ═══════════════════════════════════════════════════════════════
#  THE LIBRARY — chapters and documents
# ═══════════════════════════════════════════════════════════════

LIB = library.Library(APP_DIR)


def strip_binary(history):
    """Drop base64 payloads before saving — they make the file enormous."""
    out = []
    for turn in history:
        parts = []
        for part in turn.get("parts", []):
            if "inline_data" in part:
                parts.append({"text": "[attached page]"})
            else:
                parts.append(part)
        out.append({"role": turn.get("role", "user"), "parts": parts})
    return out


def title_from(text):
    """A short document title taken from the teacher's first instruction."""
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return (line[:60].strip() or "Untitled")


def ensure_target(title_hint=""):
    """The chapter and document to write into, creating them if needed."""
    global current_chapter, current_doc
    if current_chapter is None:
        chapters = LIB.list_chapters()
        current_chapter = chapters[0]["id"] if chapters else LIB.create_chapter("My questions")
    if current_doc is None:
        auto = title_from(title_hint)
        current_doc = LIB.create_document(current_chapter, auto)
        auto_titles[current_doc] = auto
        refresh_tree(select=("d", current_chapter, current_doc))
    return current_chapter, current_doc


def save_current(html=None, blocks=None, conversation=None, title=None, model=None):
    """Persist whatever has changed about the open document."""
    if current_chapter is None or current_doc is None:
        return None
    try:
        LIB.write_document(current_chapter, current_doc, html=html, blocks=blocks,
                           conversation=conversation, title=title, model=model)
    except library.LibraryError as exc:
        set_status(str(exc), RED)
        return None
    refresh_file_cards()
    return LIB.html_path(current_chapter, current_doc)


def open_document(chapter_id, doc_id):
    """Load a stored document into the editor and the chat."""
    global current_chapter, current_doc, conversation_history, doc_blocks
    global last_full_html, verify_report, version_at
    try:
        data = LIB.read_document(chapter_id, doc_id)
    except library.LibraryError as exc:
        set_status(str(exc), RED)
        return
    current_chapter, current_doc = chapter_id, doc_id
    conversation_history = data["conversation"]
    doc_blocks = list(data["meta"].get("blocks", []))
    last_full_html = data["html"]
    verify_report = ""

    chat.config(state=tk.NORMAL)
    chat.delete("1.0", tk.END)
    for turn in conversation_history:
        body = "\n".join(p["text"] for p in turn.get("parts", []) if "text" in p)
        if turn.get("role") == "user":
            chat.insert(tk.END, "\n", "spacer")
            chat.insert(tk.END, "  You  ", "user_label")
            chat.insert(tk.END, "\n", "spacer")
            chat.insert(tk.END, f"  {body}\n\n", "user_msg")
        else:
            chat.insert(tk.END, "  Gemini  ", "ai_label")
            chat.insert(tk.END, "\n", "spacer")
            if hs.looks_like_document(body) and 'class="' in body:
                # A document answer is a card, as it was when it arrived.
                chat.insert(tk.END, f"  \U0001F4C4  {card_title(body)}  \n\n", "card")
            else:
                chat.insert(tk.END, f"  {html_to_chat_text(body)}\n\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)

    versions = LIB.list_versions(chapter_id, doc_id)
    version_at = versions[-1]["n"] if versions else None
    refresh_artifact()
    refresh_title()
    refresh_file_cards()
    refresh_intent()
    # A document opened from an older version is repaired on the spot: the
    # stylesheet belongs to the app, not to the document.
    if hs.needs_restyle(last_full_html):
        last_full_html = hs.restyle(last_full_html)
        refresh_artifact()
        save_current(html=last_full_html)
    set_status(f"Opened: {data['meta'].get('title', doc_id)}", GREEN)
    # A PDF older than its page — the page was just repaired, or changed
    # since — is remade quietly, so Open always shows what the page says.
    if pdf_is_stale():
        auto_pdf(keep_status=True)


def current_title():
    """The open document's title, read from the library.

    Not from the title bar: finish() repaints the cards before the title, so a
    card that read the widget showed "No document yet" on the first answer of
    a session while the title bar above it showed the real name.
    """
    if current_chapter is None or current_doc is None:
        return ""
    for d in LIB.list_documents(current_chapter):
        if d["id"] == current_doc:
            return d.get("title", "Untitled")
    return "Untitled"


def refresh_title():
    if current_chapter is None or current_doc is None:
        artifact_title.config(text="No document yet")
        return
    docs = {d["id"]: d for d in LIB.list_documents(current_chapter)}
    chapters = {c["id"]: c for c in LIB.list_chapters()}
    name = chapters.get(current_chapter, {}).get("name", "")
    title = docs.get(current_doc, {}).get("title", "Untitled")
    artifact_title.config(text=f"{name} — {title}" if name else title)


# ── chapter and document actions ────────────────────────────────────

def new_chapter():
    name = _ask_text("New chapter", "Name this chapter:")
    if not name:
        return
    cid = LIB.create_chapter(name)
    refresh_tree(select=("c", cid, None))
    set_status(f"Chapter created: {name}", GREEN)


def new_document():
    """Start a fresh document in the selected chapter."""
    global current_chapter, current_doc
    kind, cid, _ = selected_node()
    if cid is None:
        chapters = LIB.list_chapters()
        cid = chapters[0]["id"] if chapters else LIB.create_chapter("My questions")
    title = _ask_text("New document", "Title:", "Untitled")
    if title is None:
        return
    current_chapter = cid
    current_doc = LIB.create_document(cid, title or "Untitled")
    reset_workspace()
    refresh_tree(select=("d", current_chapter, current_doc))
    refresh_title()
    set_status("New document started.", GREEN)


def reset_workspace():
    """Clear the chat, the blocks and the editor, keeping the open document."""
    global conversation_history, doc_blocks, last_full_html, verify_report
    global version_at, last_turn
    conversation_history = []
    doc_blocks = []
    last_full_html = ""
    verify_report = ""
    version_at = None
    last_turn = None
    clear_chat()
    refresh_artifact()
    refresh_file_cards()
    refresh_intent()


def rename_selected():
    kind, cid, did = selected_node()
    if kind == "c":
        current = next((c["name"] for c in LIB.list_chapters() if c["id"] == cid), "")
        name = _ask_text("Rename chapter", "New name:", current)
        if name:
            LIB.rename_chapter(cid, name)
            refresh_tree(select=("c", cid, None))
            refresh_title()
    elif kind == "d":
        current = next((d["title"] for d in LIB.list_documents(cid) if d["id"] == did), "")
        title = _ask_text("Rename document", "New title:", current)
        if title:
            LIB.rename_document(cid, did, title)
            auto_titles.pop(did, None)   # his name now, not the app's
            refresh_tree(select=("d", cid, did))
            refresh_title()
    else:
        set_status("Select a chapter or a document first.", RED)


def duplicate_selected():
    kind, cid, did = selected_node()
    if kind != "d":
        set_status("Select a document to duplicate.", RED)
        return
    new_id = LIB.duplicate_document(cid, did)
    refresh_tree(select=("d", cid, new_id))
    set_status("Duplicated.", GREEN)


def pin_selected():
    kind, cid, _ = selected_node()
    if kind is None:
        set_status("Select a chapter to pin.", RED)
        return
    now = next((c["pinned"] for c in LIB.list_chapters() if c["id"] == cid), False)
    LIB.pin_chapter(cid, not now)
    refresh_tree(select=("c", cid, None))
    set_status("Unpinned." if now else "Pinned to the top.", GREEN)


def delete_selected():
    global current_chapter, current_doc
    kind, cid, did = selected_node()
    if kind == "c":
        name = next((c["name"] for c in LIB.list_chapters() if c["id"] == cid), cid)
        count = len(LIB.list_documents(cid))
        if not messagebox.askyesno(
            "Delete chapter",
            f"Delete '{name}' and its {count} document(s)?\n\n"
            "The HTML and PDF files inside go too. This cannot be undone."):
            return
        LIB.delete_chapter(cid)
        if current_chapter == cid:
            current_chapter = current_doc = None
            reset_workspace()
            refresh_title()
    elif kind == "d":
        title = next((d["title"] for d in LIB.list_documents(cid) if d["id"] == did), did)
        if not messagebox.askyesno(
            "Delete document",
            f"Delete '{title}'?\n\nIts HTML and PDF go too. This cannot be undone."):
            return
        LIB.delete_document(cid, did)
        if current_doc == did:
            current_doc = None
            reset_workspace()
            refresh_title()
    else:
        set_status("Select something to delete.", RED)
        return
    refresh_tree()
    set_status("Deleted.", GREEN)


# ═══════════════════════════════════════════════════════════════
#  ATTACHMENTS
# ═══════════════════════════════════════════════════════════════

def attach_files():
    paths = filedialog.askopenfilenames(title="Attach question pages", filetypes=ATTACH_TYPES)
    if not paths:
        return
    for p in paths:
        if p not in attachments:
            attachments.append(p)
    refresh_attachments()


def paste_from_clipboard(event=None):
    """Attach whatever is on the clipboard: a screenshot, or files copied in Explorer.

    Returns "break" when something was attached, so the keystroke does not also
    dump binary junk into the typing box. Returns None for plain text, letting
    Tk paste it normally.
    """
    if not CLIPBOARD_IMAGES:
        set_status("Pasting pages needs Pillow — run:  pip install pillow", RED)
        return None

    try:
        grabbed = ImageGrab.grabclipboard()
    except Exception as exc:
        set_status(f"Could not read the clipboard: {exc}", RED)
        return None

    # Files copied in Explorer arrive as a list of paths.
    if isinstance(grabbed, list):
        added, skipped = 0, []
        for path in grabbed:
            try:
                api.mime_for(path)
            except api.GeminiError:
                skipped.append(os.path.basename(path))
                continue
            if path not in attachments:
                attachments.append(path)
                added += 1
        refresh_attachments()
        if added and skipped:
            set_status(f"Attached {added}; skipped {', '.join(skipped[:3])}.", ACCENT)
        elif added:
            set_status(f"Attached {added} file(s) from the clipboard.", GREEN)
        else:
            set_status("Those file types cannot be sent — PDF or image only.", RED)
        return "break"

    # A bitmap: a screenshot, or an image copied out of a PDF reader.
    if Image is not None and isinstance(grabbed, Image.Image):
        try:
            if grabbed.mode not in ("RGB", "L"):
                grabbed = grabbed.convert("RGB")
            name = datetime.now().strftime("pasted_%Y%m%d_%H%M%S_%f.png")
            path = os.path.join(PASTED_DIR, name)
            grabbed.save(path, "PNG")
        except Exception as exc:
            set_status(f"Could not save the pasted image: {exc}", RED)
            return None
        attachments.append(path)
        refresh_attachments()
        set_status(f"Pasted image attached ({grabbed.width}x{grabbed.height}).", GREEN)
        return "break"

    return None          # plain text or an empty clipboard: let Tk handle it


def clear_attachments():
    attachments.clear()
    refresh_attachments()


def refresh_attachments():
    refresh_intent()
    if not attachments:
        attach_label.config(text="No pages attached", fg=MUTED)
        return
    names = ", ".join(os.path.basename(p) for p in attachments[:3])
    extra = f" +{len(attachments) - 3} more" if len(attachments) > 3 else ""
    attach_label.config(text=f"{len(attachments)} attached: {names}{extra}", fg=ACCENT)


# ═══════════════════════════════════════════════════════════════
#  ARTIFACT PANEL
# ═══════════════════════════════════════════════════════════════

def refresh_artifact():
    """Show the current document: the page in Preview, the HTML in Code."""
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, last_full_html or "")
    refresh_preview()
    refresh_versions()


# ── Preview | Code ──────────────────────────────────────────────────

def show_tab(which):
    """Switch the right side between the finished page and its HTML."""
    global current_tab
    current_tab = which
    for name, frame in (("preview", preview_frame), ("code", code_frame)):
        if name == which:
            frame.pack(fill=tk.BOTH, expand=True)
        else:
            frame.pack_forget()
    for name, button in (("preview", preview_tab), ("code", code_tab)):
        on = name == which
        button.config(fg=ACCENT if on else MUTED,
                      font=("Arial", 10, "bold" if on else "normal"))
    if which == "preview":
        refresh_preview()


# The page is drawn by the Chromium that makes the PDF, so the preview cannot
# disagree with what prints. A render takes a second or two, so it runs on a
# thread, one at a time, and a change made meanwhile renders once more after.
preview_running = False
preview_again = False
preview_shown_for = None      # (html, width) of the picture on screen
preview_lines = []            # where each line of text sits in the picture
current_tab = "preview"


def preview_message(text, colour=MUTED):
    preview_canvas.delete("all")
    preview_canvas.create_text(24, 28, anchor="nw", text=text, fill=colour,
                               font=("Georgia", 11),
                               width=max(200, preview_canvas.winfo_width() - 48))
    preview_canvas.configure(scrollregion=(0, 0, 0, 0))


def refresh_preview():
    """Redraw the Preview tab if the page or the panel width has changed."""
    global preview_running, preview_again
    if current_tab != "preview":
        return
    html = last_full_html or ""
    if not html.strip():
        preview_message("The finished page appears here.\n\n"
                        "Attach or paste a question, then press Send.")
        return
    if not LIVE_PREVIEW:
        return
    if not pdf_export.playwright_available():
        preview_message("The preview needs Playwright:  pip install playwright  "
                        "then  playwright install chromium\n\n"
                        "The HTML is in the Code tab.")
        return
    width = max(300, preview_canvas.winfo_width())
    if preview_shown_for == (html, width):
        return
    if preview_running:
        preview_again = True
        return
    preview_running = True
    scale = max(0.4, min(1.0, (width - 24) / PREVIEW_WIDTH))

    def work():
        try:
            tmp_html = os.path.join(PREVIEW_DIR, "preview.html")
            with open(tmp_html, "w", encoding="utf-8") as fh:
                fh.write(html)
            png = pdf_export.html_to_png(tmp_html, os.path.join(PREVIEW_DIR, "preview.png"),
                                         width=PREVIEW_WIDTH, scale=scale,
                                         media="print", lines=True)
            post(lambda: preview_done(png, (html, width)))
        except Exception as exc:
            post(lambda e=str(exc): preview_failed(e))

    threading.Thread(target=work, daemon=True).start()


def preview_done(png, shown_for):
    global preview_running, preview_again, preview_image, preview_shown_for
    preview_running = False
    try:
        preview_image = tk.PhotoImage(file=png)
    except Exception as exc:
        preview_failed(str(exc))
        return
    top = preview_canvas.yview()[0] if preview_shown_for else 0.0
    preview_canvas.delete("all")
    preview_canvas.create_image(0, 0, anchor="nw", image=preview_image)
    preview_canvas.configure(scrollregion=(0, 0, preview_image.width(),
                                           preview_image.height()))
    preview_canvas.yview_moveto(top)
    preview_shown_for = shown_for
    _sel.update(anchor=None, first=None, last=None)       # a new page, no selection
    try:
        with open(png + ".json", encoding="utf-8") as fh:
            preview_lines[:] = json.load(fh)
    except (OSError, ValueError):
        preview_lines[:] = []
    if preview_again:
        preview_again = False
        refresh_preview()


def preview_failed(message):
    global preview_running, preview_again
    preview_running = False
    preview_again = False
    preview_message(f"The preview could not be drawn.\n\n{message.strip()[:400]}", RED)


# ── versions ────────────────────────────────────────────────────────
# Every answer keeps the page as it stood after it: ◀ v3 of 5 ▶ goes back.

def record_version(label, before=None):
    """Keep the page as it now stands. before: the page as it was, when this
    document has no versions yet, so the first one is not lost."""
    global version_at
    if current_chapter is None or current_doc is None or not last_full_html.strip():
        return
    try:
        if not LIB.list_versions(current_chapter, current_doc) and (before or "").strip():
            LIB.save_version(current_chapter, current_doc, before, "Before versions")
        version_at = LIB.save_version(current_chapter, current_doc, last_full_html, label)
    except library.LibraryError as exc:
        set_status(str(exc), RED)
    refresh_versions()


def refresh_versions():
    """◀ v3 of 5 ▶ — hidden until there is more than one version."""
    versions = (LIB.list_versions(current_chapter, current_doc)
                if current_chapter and current_doc else [])
    numbers = [v["n"] for v in versions]
    if len(numbers) < 2:
        version_row.pack_forget()
        return
    at = numbers.index(version_at) if version_at in numbers else len(numbers) - 1
    version_label.config(text=f"v{at + 1} of {len(numbers)}")
    version_prev.config(state=tk.NORMAL if at > 0 else tk.DISABLED)
    version_next.config(state=tk.NORMAL if at < len(numbers) - 1 else tk.DISABLED)
    if not version_row.winfo_ismapped():
        # Packed before the title, so a long title is cut instead of the arrows.
        version_row.pack(side=tk.RIGHT, padx=(0, 10), before=artifact_title)


def step_version(step):
    """Show the version before (-1) or after (+1) the one on screen."""
    global version_at, last_full_html, doc_blocks
    if busy or current_chapter is None or current_doc is None:
        return
    numbers = [v["n"] for v in LIB.list_versions(current_chapter, current_doc)]
    if not numbers:
        return
    at = numbers.index(version_at) if version_at in numbers else len(numbers) - 1
    at = max(0, min(len(numbers) - 1, at + step))
    try:
        html = LIB.read_version(current_chapter, current_doc, numbers[at])
    except library.LibraryError as exc:
        set_status(str(exc), RED)
        return
    # The version shown IS the document: the next answer builds on it, and the
    # later versions stay where they are, one click away.
    version_at = numbers[at]
    last_full_html = html
    doc_blocks = hs.blocks_of(html)
    refresh_artifact()
    save_current(html=last_full_html, blocks=doc_blocks)
    set_status(f"Showing version {at + 1} of {len(numbers)}.", TEXT)
    auto_pdf(keep_status=True)


def apply_edited_html():
    """Take what is in the editor as the document and re-check it."""
    global last_full_html, doc_blocks
    edited = editor.get("1.0", tk.END).rstrip()
    if not edited.strip():
        set_status("The editor is empty — nothing to apply.", RED)
        return
    before = last_full_html
    last_full_html = edited
    doc_blocks = hs.blocks_of(edited)
    save_html(silent=True)
    if edited != before:
        record_version("Your edit", before)
    refresh_preview()
    errors, warnings = run_validator()
    if not errors and not warnings:
        set_status("Applied. House style clean.", GREEN)
    else:
        set_status(f"Applied. {len(errors)} error(s), {len(warnings)} warning(s) — see the chat.", RED)
    # Your edit is now the document, so the PDF is out of date the moment it is
    # applied. Remake it, keeping the message above.
    auto_pdf(keep_status=True)


def restyle_everything():
    """Bring every stored document up to the current house style, at startup.

    A page is saved whole, so a document written by an older version keeps that
    version's colours in every program that opens it. The stylesheet belongs to
    the app, not to the document, so old ones are simply repaired — no menu, no
    question asked. Only the <style> block changes; questions, tables and any
    edit made by hand are untouched, and a document whose style is already
    current is not rewritten at all.
    """
    fixed = 0
    for chapter in LIB.list_chapters():
        for document in LIB.list_documents(chapter["id"]):
            try:
                stored = LIB.read_document(chapter["id"], document["id"])["html"]
            except library.LibraryError:
                continue
            if not hs.needs_restyle(stored):
                continue
            try:
                LIB.write_document(chapter["id"], document["id"],
                                   html=hs.restyle(stored))
                fixed += 1
            except library.LibraryError:
                continue
    return fixed


def check_house_style():
    """Run the validator on demand and always report the outcome."""
    errors, warnings = run_validator()
    if not errors and not warnings:
        say("House style: clean — no rule violations.", "ok")
        set_status("House style clean.", GREEN)
    else:
        set_status(f"{len(errors)} error(s), {len(warnings)} warning(s) — see the chat.", RED)


def run_validator(announce=True):
    """Check the document against the house rules and report into the chat."""
    errors, warnings = hs.validate_html(last_full_html or "")
    if announce and (errors or warnings):
        say(hs.format_validation(errors, warnings), "bad" if errors else "note")
    return errors, warnings


def save_html(silent=False):
    """Write the open document's HTML into its own folder."""
    if not last_full_html.strip():
        if not silent:
            set_status("Nothing to save yet.", RED)
        return None
    ensure_target()
    path = save_current(html=last_full_html, blocks=doc_blocks,
                        conversation=strip_binary(conversation_history))
    if path and not silent:
        set_status("Saved.", GREEN)
    return path


def generate_pdf():
    """Save the current HTML, then render it through Playwright Chromium."""
    if not last_full_html.strip():
        set_status("Nothing to convert yet.", "#CC0000")
        return
    errors, _ = run_validator()
    if errors:
        if not messagebox.askyesno(
            "House style errors",
            f"The validator found {len(errors)} rule violation(s):\n\n"
            + "\n".join(errors[:6])
            + "\n\nGenerate the PDF anyway?",
        ):
            return

    path = save_html(silent=True)
    if not path:
        return
    target = LIB.pdf_path(current_chapter, current_doc)
    set_status("Rendering PDF with Chromium...", ACCENT)
    pdf_make_btn.config(state=tk.DISABLED)

    def work():
        try:
            out = pdf_export.html_to_pdf(path, target)
            post(lambda: pdf_done(out))
        except pdf_export.PdfExportError as exc:
            post(lambda e=exc: pdf_failed(str(e)))
        except Exception as exc:
            post(lambda e=exc: pdf_failed(str(e)))

    threading.Thread(target=work, daemon=True).start()


def pdf_done(path):
    pdf_make_btn.config(state=tk.NORMAL)
    refresh_file_cards()
    set_status("PDF ready.", GREEN)
    try:
        pdf_export.open_file(path)
    except Exception:
        pass


def pdf_failed(message):
    pdf_make_btn.config(state=tk.NORMAL)
    set_status("PDF failed", "#CC0000")
    messagebox.showerror("PDF export failed", message)


# A render takes a couple of seconds. If a second answer lands while one is
# running, both threads would write the same file, so the second waits its turn.
auto_pdf_running = False
auto_pdf_again = False
closing = False


def auto_pdf(keep_status=False):
    """Make the PDF in the background after an answer, without opening it.

    keep_status : leave the status bar alone, so a verification mismatch is
                  not wiped off the screen by a PDF message.
    """
    global auto_pdf_running, auto_pdf_again
    if closing or not SETTINGS.get("auto_pdf", True):
        return
    if current_chapter is None or current_doc is None:
        return
    if not pdf_export.playwright_available():
        return
    html = LIB.html_path(current_chapter, current_doc)
    if not os.path.exists(html):
        return
    if auto_pdf_running:
        auto_pdf_again = True
        return

    auto_pdf_running = True
    target = LIB.pdf_path(current_chapter, current_doc)

    def work():
        try:
            pdf_export.html_to_pdf(html, target)
            post(lambda: auto_pdf_done(keep_status))
        except Exception as exc:
            post(lambda e=exc: auto_pdf_failed(str(e), keep_status))

    threading.Thread(target=work, daemon=True).start()


def auto_pdf_done(keep_status):
    global auto_pdf_running, auto_pdf_again
    auto_pdf_running = False
    refresh_file_cards()
    if not keep_status:
        set_status("Done — PDF ready.", GREEN)
    if auto_pdf_again:
        auto_pdf_again = False
        auto_pdf(keep_status)


def auto_pdf_failed(message, keep_status):
    """Nobody asked for this PDF, so no dialog box — the status bar is enough.

    The usual cause is the PDF being open in a reader, which Windows locks.
    """
    global auto_pdf_running, auto_pdf_again
    auto_pdf_running = False
    auto_pdf_again = False
    refresh_file_cards()
    set_status(f"PDF not remade — {message.strip().splitlines()[0]}", RED)


def open_folder():
    """Reveal the open document's own folder, or the library root."""
    target = LIB.root
    if current_chapter and current_doc:
        try:
            target = LIB.document_path(current_chapter, current_doc)
        except library.LibraryError:
            pass
    pdf_export.open_file(target)


def copy_answer():
    if last_response_text:
        root.clipboard_clear()
        root.clipboard_append(last_response_text)
        set_status("Copied to clipboard.", GREEN)
    else:
        set_status("Nothing to copy yet.", MUTED)


# ═══════════════════════════════════════════════════════════════
#  SENDING
# ═══════════════════════════════════════════════════════════════

def compact_tokens(n):
    """6520 -> '6.5k tok'; keeps the meter short enough to survive the top bar."""
    if n >= 1000:
        return f"{n / 1000:.1f}k tok"
    return f"{n} tok"


def set_status(text, colour=TEXT):
    status_label.config(text=text, fg=colour)


def say(text, kind="note"):
    """Write a notice into the chat: verification results, validator findings."""
    label = {"ok": "  Verified  ", "bad": "  Check this  ", "note": "  Note  "}[kind]
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "\n", "spacer")
    chat.insert(tk.END, label, f"{kind}_label")
    chat.insert(tk.END, "\n", "spacer")
    chat.insert(tk.END, f"  {text.strip()}\n\n", f"{kind}_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)


def selected_model():
    """The model id behind the current dropdown row, chosen by position.

    Matching on the label text breaks the moment the label format changes, or
    when two models share a display name.
    """
    idx = model_dropdown.current()
    if 0 <= idx < len(model_ids):
        return model_ids[idx][0]
    return SETTINGS.get("model") or (model_ids[0][0] if model_ids else "")


def has_document():
    return bool(hs.block_spans(last_full_html or ""))


def current_intent():
    """"add", "edit", "show" or "chat" — what Send will do with the next message."""
    if active_mode_key() == "general":
        return "chat"
    text = entry.get("1.0", tk.END).strip()
    # undo, help, the PDF and the tabs are never worth sending to the model,
    # whatever the label was switched to.
    quick = quick_edits.parse(text)
    if quick and quick[0] in quick_edits.WINDOW_KINDS and not attachments:
        return "free"
    if intent_override and has_document() and text:
        return intent_override
    if not attachments and is_free(text):
        return "free"
    return prompts.read_request(text, has_document(), bool(attachments))


def is_free(text):
    """True when the app can do this itself, without the model."""
    quick = quick_edits.parse(text)
    if quick:
        return quick[0] in ("help", "tab", "pdf", "open_pdf") or has_document()
    if not has_document():
        return False
    return bool(prompts.removal_target(text) or prompts.top_bar_request(text)
                or prompts.number_request(text) or prompts._DATE_ASK.match(text)
                or (prompts.read_request(text, True) == "edit" and prompts.style_request(text)))


INTENT_TEXT = {
    "add": ("Will add", "a new question at the end of the document", ACCENT),
    "free": ("Free", "done by the app — nothing sent to Gemini", GREEN),
    "edit": ("Will edit", "changes the page in place", BLUE),
    "show": ("Will show", "the full merged HTML, in the Code tab", GREEN),
    "chat": ("Chat only", "General mode writes no document", MUTED),
}


def refresh_intent(_evt=None):
    """The line above Send: what Send is about to do, and a way to change it."""
    global intent_override
    if intent_override and not entry.get("1.0", tk.END).strip():
        intent_override = None           # the box was cleared: the switch goes with it
    word, detail, colour = INTENT_TEXT[current_intent()]
    intent_label.config(text=f"{word}", fg=colour)
    hint = "  ·  click to switch" if active_mode_key() != "general" and has_document() else ""
    intent_detail.config(text=f"— {detail}{hint}")


def toggle_intent(_evt=None):
    """Add becomes Edit and Edit becomes Add, for this message only."""
    global intent_override
    if active_mode_key() == "general" or not has_document():
        return
    if not entry.get("1.0", tk.END).strip():
        # Nothing typed yet: a click here used to switch the NEXT message
        # silently, and "help" was then sent to the model as an edit.
        set_status("Type the message first, then click to switch.", MUTED)
        return
    intent_override = "edit" if current_intent() in ("add", "show", "free") else "add"
    refresh_intent()


def send_message(event=None):
    global intent_override
    if busy:
        return "break"

    text = entry.get("1.0", tk.END).strip()
    if not text and not attachments:
        return "break"
    intent = current_intent()
    if not text:
        text = active_preset().get("default_instruction") or "Solve the attached question."
    files = list(attachments)
    if submit(text, files, intent):
        entry.delete("1.0", tk.END)
        clear_attachments()
        intent_override = None
        refresh_intent()
    return "break"


def _user_bubble(text, files):
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "\n", "spacer")
    chat.insert(tk.END, "  You  ", "user_label")
    chat.insert(tk.END, "\n", "spacer")
    for p in files:
        chat.insert(tk.END, f"  [{os.path.basename(p)}]\n", "user_msg")
    chat.insert(tk.END, f"  {text}\n\n", "user_msg")
    chat.config(state=tk.DISABLED)


def _drop_retry():
    """Take the Retry button away — and its line, so no gap is left behind."""
    global retry_btn
    if retry_btn is not None:
        try:
            chat.config(state=tk.NORMAL)
            chat.delete("retry_start", "retry_end")
            chat.config(state=tk.DISABLED)
            retry_btn.destroy()
        except tk.TclError:
            pass
        retry_btn = None


def submit(text, files, intent, local=True):
    """Send one message. Returns False when it could not be sent.

    local : a bare "remove Illustration 7" is done here, without the model.
    """
    global busy, last_turn

    if intent == "show":
        # Asked on Claude.ai to "display the full merged HTML". Here the whole
        # document is already on the right, so nothing is sent and nothing is paid.
        _drop_retry()
        _user_bubble(text, files)
        show_tab("code")
        say("The full merged HTML is in the Code tab on the right — every "
            "question, in order. Nothing was sent to Gemini.", "note")
        return True

    if intent == "free":
        quick = quick_edits.parse(text)
        if quick:
            return run_quick(text, *quick)
        intent = "edit"                  # one of the edits below
    if intent == "edit" and not has_document():
        intent = "add"
    if intent == "edit" and not files and local:
        target = prompts.removal_target(text)
        if target:
            return remove_question(text, target)
        bar = prompts.top_bar_request(text)
        if bar:
            return edit_top_bar(text, bar)
        number = prompts.number_request(text)
        if number:
            return number_question(text, number)
        if prompts._DATE_ASK.match(text):
            return change_date(text)
        if prompts.style_request(text):
            return explain_style(text)

    model = selected_model()
    if not model:
        set_status("No model selected — press Refresh models.", "#CC0000")
        return False

    ensure_target(text)
    _drop_retry()
    last_turn = {"text": text, "files": list(files), "intent": intent,
                 "history": len(conversation_history), "html": last_full_html,
                 "blocks": list(doc_blocks), "version": version_at}

    _user_bubble(text, files)
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, f"  Gemini — {active_preset()['name']}  ", "ai_label")
    chat.insert(tk.END, "\n", "spacer")
    chat.insert(tk.END, "  ", "ai_msg")
    # "end" in a Text widget is the position AFTER the trailing newline, one
    # line below where inserted text actually lands. A mark set there never
    # precedes the streamed text, so delete(mark, END) removes nothing and each
    # repaint appends instead of replacing. "end-1c" anchors it to a real
    # character.
    chat.mark_set("stream_start", "end-1c")
    chat.mark_gravity("stream_start", tk.LEFT)
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)

    busy = True
    stop_event.clear()
    send_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL, bg=ACCENT)
    set_status("Sending...", ACCENT)

    started = datetime.now()
    acc = [""]
    last_paint = [0.0]

    looped = [False]

    def on_chunk(piece):
        acc[0] += piece
        now = datetime.now().timestamp()
        if now - last_paint[0] < 0.12:
            return
        last_paint[0] = now
        snapshot = acc[0]
        post(lambda s=snapshot: paint_stream(s, intent))

        # A model can argue with the contract for thousands of words and never
        # start the document. Waiting for the token limit wastes minutes, and
        # real money on a paid model, so it is cut off as soon as it repeats.
        if not looped[0] and hs.is_looping(snapshot):
            looped[0] = True
            stop_event.set()

    snapshot_html = last_full_html

    def work():
        try:
            system_prompt = active_preset()["system_prompt"]
            if SETTINGS.get("charts") and active_mode_key() != "general":
                system_prompt += CHART_INSTRUCTION

            post(lambda: set_status("Uploading pages..." if files else "Thinking...", ACCENT))
            parts = api.build_parts(text, files)
            conversation_history.append({"role": "user", "parts": parts})
            if len(conversation_history) > MAX_HISTORY_TURNS * 2:
                del conversation_history[:len(conversation_history) - MAX_HISTORY_TURNS * 2]

            if intent == "edit":
                # An edit is shown the page as it stands, and nothing else: the
                # page is the context, and earlier turns only cost tokens.
                system_prompt += prompts.EDIT_CONTRACT
                request = [{"role": "user", "parts": api.build_parts(
                    prompts.EDIT_REQUEST.format(instruction=text,
                                                body=hs.numbered_body(snapshot_html)),
                    files)}]
            else:
                request = compact_history(conversation_history)

            post(lambda: set_status("Streaming...", ACCENT))
            answer, in_tok, out_tok, cached_tok = api.stream_generate(
                request,
                model,
                system_prompt=system_prompt,
                on_chunk=on_chunk,
                stop_event=stop_event,
                max_tokens=int(SETTINGS.get("max_tokens", api.DEFAULT_MAX_TOKENS)),
                temperature=float(SETTINGS.get("temperature", api.DEFAULT_TEMPERATURE)),
                thinking_budget=SETTINGS.get("thinking_budget"),
            )
            conversation_history.append({"role": "model", "parts": [{"text": answer}]})

            verdict, v_cost = "", None
            check = SETTINGS.get("verify") and active_mode_key() == "solve"
            if check and intent == "edit":
                # An edit that changes no figure has nothing to verify, and the
                # check would cost as much again as the edit itself.
                try:
                    edited, _, _ = hs.apply_edits(snapshot_html, api.strip_code_fence(answer))
                    check = hs.figures(edited) != hs.figures(snapshot_html)
                except hs.EditError:
                    check = False
            if check and not stop_event.is_set():
                checker = verify_model_for(model)
                note = ("Verifying..." if checker == model
                        else f"Verifying with {checker}...")
                post(lambda m=note: set_status(m, ACCENT))
                try:
                    verdict, v_in, v_out, v_cached, used = run_verification(
                        text, files, answer, model)
                    v_cost = (used, v_in, v_out, v_cached)
                except api.GeminiError as exc:
                    verdict = f"Verification could not run: {exc}"

            elapsed = (datetime.now() - started).total_seconds()
            if looped[0]:
                post(lambda n=len(answer.split()): loop_stopped(n, intent))
                return
            post(lambda: finish(answer, in_tok, out_tok, cached_tok,
                                elapsed, model, verdict, v_cost, intent))

        except api.GeminiError as exc:
            if conversation_history and conversation_history[-1].get("role") == "user":
                conversation_history.pop()
            post(lambda e=exc: fail(str(e)))
        except Exception as exc:
            if conversation_history and conversation_history[-1].get("role") == "user":
                conversation_history.pop()
            post(lambda e=exc: fail(f"Unexpected error: {e}"))

    threading.Thread(target=work, daemon=True).start()
    return True


def compact_history(history):
    """The conversation as sent to the model: earlier turns cut to the bone.

    Earlier answers go as a short summary — the document already holds them —
    and earlier pages as a placeholder; the question just asked goes whole.
    Sent in full, the second question of a document cost 10 paise more than
    the first, and each later one more again.
    """
    out = []
    last = len(history) - 1
    for i, turn in enumerate(history):
        if i == last:
            out.append(turn)
            continue
        parts = []
        for part in turn.get("parts", []):
            if "inline_data" in part:
                parts.append({"text": "[page attached earlier]"})
            elif turn.get("role") == "model" and "text" in part and 'class="' in part["text"]:
                parts.append({"text": hs.summarize_answer(part["text"])})
            else:
                parts.append(part)
        out.append({"role": turn.get("role", "user"), "parts": parts})
    return out


def paint_stream(snapshot, intent="add"):
    words = len(snapshot.split())
    set_status(f"Streaming... ({words} words)", ACCENT)
    chat.config(state=tk.NORMAL)
    chat.delete("stream_start", tk.END)
    if active_mode_key() == "general":
        chat.insert(tk.END, for_chat(snapshot), "ai_msg")
    else:
        # The page is built on the right; the chat only says it is being written.
        doing = "Editing the page" if intent == "edit" else "Writing the page"
        chat.insert(tk.END, f"\U0001F4C4  {doing}…  {words} words", "card_sub")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)


def card_title(fragment, action=""):
    """"Illustration 7 added" — what a document answer is called in the chat."""
    label = hs.question_label(fragment)
    if not label:
        topic = hs.title_from_block(fragment, "")
        label = topic.split(" — ")[0] if topic else "The page"
    return f"{label} {action}".strip()


def put_card(title, verdict_kind_="", verdict_note=""):
    """The short card that stands for a whole answer, plus Retry under it."""
    chat.config(state=tk.NORMAL)
    chat.delete("stream_start", tk.END)
    chat.insert(tk.END, f"\U0001F4C4  {title}  ", ("card", "card_link"))
    shown = {"ok": ("  ·  Verified ✓", "card_ok"),
             "bad": ("  ·  Check this ✗", "card_bad"),
             "unclear": ("  ·  Verification unclear", "card_sub")}.get(verdict_kind_)
    if shown:
        chat.insert(tk.END, shown[0], shown[1])
    if verdict_note:
        chat.insert(tk.END, f"  ·  {verdict_note}", "card_sub")
    chat.insert(tk.END, "\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)


def put_retry():
    """A Retry button under the last answer — one at a time, like Claude.ai."""
    global retry_btn
    _drop_retry()
    if not last_turn:
        return
    retry_btn = tk.Button(chat, text="↻  Retry", command=retry_last,
                          font=("Arial", 9), bg=SIDEBAR, fg=TEXT, relief=tk.FLAT,
                          padx=10, pady=2, cursor="hand2", activebackground=BORDER)
    chat.config(state=tk.NORMAL)
    chat.mark_set("retry_start", "end-1c")
    chat.mark_gravity("retry_start", tk.LEFT)
    chat.insert(tk.END, "  ", "spacer")
    chat.window_create(tk.END, window=retry_btn)
    chat.insert(tk.END, "\n", "spacer")
    chat.mark_set("retry_end", "end-1c")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)


def retry_last():
    """Ask again: the page goes back to how it was, and the same message is sent.

    The answer being replaced is kept as a version, so nothing is lost by it.
    """
    global last_full_html, doc_blocks, version_at
    if busy or not last_turn:
        return
    turn = last_turn
    if last_full_html != turn["html"]:
        last_full_html = turn["html"]
        doc_blocks = list(turn["blocks"])
        version_at = turn["version"]
        refresh_artifact()
        save_current(html=last_full_html, blocks=doc_blocks)
    del conversation_history[turn["history"]:]
    say("Retrying — the page is back to how it was before that answer. "
        "That answer is kept as a version.", "note")
    submit(turn["text"], turn["files"], turn["intent"])


def _local_turn(text):
    """Chat bubble, label and Retry bookkeeping for an edit made here."""
    global last_turn
    _drop_retry()
    _user_bubble(text, [])
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "  Goodwill  ", "ai_label")
    chat.insert(tk.END, "\n", "spacer")
    chat.mark_set("stream_start", "end-1c")
    chat.mark_gravity("stream_start", tk.LEFT)
    chat.config(state=tk.DISABLED)
    last_turn = {"text": text, "files": [], "intent": "edit",
                 "history": len(conversation_history), "html": last_full_html,
                 "blocks": list(doc_blocks), "version": version_at}


def run_quick(text, kind, match):
    """A free edit from quick_edits: made here, nothing sent to the model."""
    global last_full_html, doc_blocks
    _local_turn(text)
    if kind == "help":
        put_card("Free edits")
        say(quick_edits.HELP, "note")
        return True
    if kind == "tab":
        show_tab("code" if match.group(1).lower() in ("code", "html") else "preview")
        put_card("Showing the " + ("Code" if current_tab == "code" else "Preview"))
        return True
    if kind == "pdf":
        put_card("Making the PDF")
        generate_pdf()
        return True
    if kind == "open_pdf":
        put_card("Opening the PDF")
        _open_doc_file("pdf")
        return True
    if kind == "rename_doc":
        title = match.group(1).strip()
        try:
            LIB.rename_document(current_chapter, current_doc, title)
        except library.LibraryError as exc:
            put_card("Not renamed", verdict_note=str(exc))
            return True
        auto_titles.pop(current_doc, None)       # his name now
        refresh_tree(select=("d", current_chapter, current_doc))
        refresh_title()
        put_card(f"Document renamed to {title}", verdict_note="free")
        return True
    if kind in ("undo", "redo"):
        numbers = [v["n"] for v in LIB.list_versions(current_chapter, current_doc)]
        at = numbers.index(version_at) if version_at in numbers else len(numbers) - 1
        step = -1 if kind == "undo" else 1
        if not numbers or not 0 <= at + step < len(numbers):
            put_card("Nothing to " + kind, verdict_note="no version " +
                     ("before" if kind == "undo" else "after") + " this one")
            return True
        step_version(step)
        put_card(f"{'Undone' if kind == 'undo' else 'Redone'} — showing v{at + step + 1} "
                 f"of {len(numbers)}", verdict_note="free")
        return True
    before = last_full_html
    try:
        html, title = quick_edits.apply(kind, match, last_full_html)
    except quick_edits.QuickEditError as exc:
        put_card("Nothing changed", verdict_note=str(exc))
        set_status("Nothing changed.", RED)
        return True
    last_full_html = html
    doc_blocks = hs.blocks_of(html)
    save_current(html=last_full_html, blocks=doc_blocks)
    record_version(title, before)
    refresh_artifact()
    put_card(title, verdict_note="done here, free — nothing sent to Gemini")
    set_status(f"{title} — free.", GREEN)
    auto_pdf(keep_status=True)
    return True


def explain_style(text):
    """Colours and fonts belong to the house style; say so instead of asking Gemini."""
    _local_turn(text)
    put_card("Nothing changed", verdict_note="the look comes from the house style")
    say("Colours, fonts, spacing, borders and backgrounds are set by the house style "
        "(house_style.py), not by Gemini — so every page looks the same and the "
        "look cannot drift. Table cells are already #C8C8C8, the page colour; a "
        "table's header row is #BDBDBD.\n\nTo change the look of every page, ask "
        "Claude to change the house style. Nothing was sent to Gemini.", "note")
    set_status("Style question answered — nothing sent.", TEXT)
    return True


def change_date(text):
    """Change the date in the header — the model never sees the header."""
    global last_full_html
    when = prompts.date_request(text, datetime.now().date())
    _local_turn(text)
    if when is None:
        put_card("Date unchanged", verdict_note="could not read that date — try  change the date to 25 September")
        set_status("Date not understood — nothing changed.", RED)
        return True
    before = last_full_html
    last_full_html = hs.set_header_date(last_full_html, when)
    if last_full_html == before:
        put_card("Date unchanged", verdict_note="it already reads that way")
        return True
    stamp = hs.today_stamp(when)
    save_current(html=last_full_html, blocks=doc_blocks)
    record_version(f"Date set to {stamp}", before)
    refresh_artifact()
    put_card(f"Date set to {stamp}", verdict_note="done here, free — nothing sent to Gemini")
    set_status(f"Date set to {stamp} — free.", GREEN)
    auto_pdf(keep_status=True)
    return True


def number_question(text, number):
    """Number or renumber a question, without asking the model.

    An unnumbered question is numbered first; otherwise, the last question.
    """
    global last_full_html, doc_blocks, last_turn
    spans = hs.block_spans(last_full_html)
    bare = [s for s in spans if not hs.question_label(last_full_html[s[0]:s[1]])]
    if not spans:
        return submit(text, [], "edit", local=False)
    a, b = (bare or spans)[-1]
    if number[0] is None:                # keep the word the question already uses
        current = hs.question_label(last_full_html[a:b])
        number = (current.split(" ")[0] if current else "Illustration", number[1])
    before = last_full_html
    block = hs.set_qno(last_full_html[a:b], *number)
    if block == last_full_html[a:b]:
        return submit(text, [], "edit", local=False)
    _drop_retry()
    _user_bubble(text, [])
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "  Goodwill  ", "ai_label")
    chat.insert(tk.END, "\n", "spacer")
    chat.mark_set("stream_start", "end-1c")
    chat.mark_gravity("stream_start", tk.LEFT)
    chat.config(state=tk.DISABLED)
    last_turn = {"text": text, "files": [], "intent": "edit",
                 "history": len(conversation_history), "html": before,
                 "blocks": list(doc_blocks), "version": version_at}
    last_full_html = last_full_html[:a] + block + last_full_html[b:]
    doc_blocks = hs.blocks_of(last_full_html)
    label = f"{number[0]} {number[1]}"
    save_current(html=last_full_html, blocks=doc_blocks)
    record_version(f"{label} numbered", before)
    refresh_artifact()
    put_card(f"{label} numbered", verdict_note="done here, free — nothing sent to Gemini")
    set_status(f"{label} numbered — free.", GREEN)
    auto_pdf(keep_status=True)
    return True


def edit_top_bar(text, request):
    """Change the book or page in the top bar without asking the model."""
    global last_full_html, doc_blocks, last_turn
    spans = hs.block_spans(last_full_html)
    which = request["which"]
    if which:
        want = f"{which[0]} {which[1]}".lower()
        spans = [(a, b) for a, b in spans
                 if hs.question_label(last_full_html[a:b]).lower() == want]
        if not spans:
            return submit(text, [], "edit", local=False)
    before = last_full_html
    html = last_full_html
    for a, b in reversed(spans):
        block = html[a:b]
        book, page = hs.read_pgref(block)
        book = book if request["book"] is None else request["book"]
        page = page if request["page"] is None else request["page"]
        if book and not page:
            page = ""                    # a book with no page is not printed
        html = html[:a] + hs.set_pgref(block, book, page) + html[b:]
    _drop_retry()
    _user_bubble(text, [])
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "  Goodwill  ", "ai_label")
    chat.insert(tk.END, "\n", "spacer")
    chat.mark_set("stream_start", "end-1c")
    chat.mark_gravity("stream_start", tk.LEFT)
    chat.config(state=tk.DISABLED)
    if html == before:
        note = ("a book prints only with its page — give the page too"
                if request["book"] and request["page"] is None else "it already reads that way")
        put_card("Top bar unchanged", verdict_note=note)
        set_status("Nothing to change.", TEXT)
        return True
    last_turn = {"text": text, "files": [], "intent": "edit",
                 "history": len(conversation_history), "html": before,
                 "blocks": list(doc_blocks), "version": version_at}
    last_full_html = html
    doc_blocks = hs.blocks_of(html)
    save_current(html=last_full_html, blocks=doc_blocks)
    record_version("Top bar edited", before)
    refresh_artifact()
    put_card("Top bar edited", verdict_note="done here, free — nothing sent to Gemini")
    set_status("Top bar edited — free.", GREEN)
    auto_pdf(keep_status=True)
    return True


def remove_question(text, target):
    """Take a question out without asking the model — free, and exact."""
    global last_full_html, doc_blocks, last_turn
    spans = hs.block_spans(last_full_html)
    if target == "last":
        pick = [len(spans) - 1] if spans else []
    elif target == "copy":
        # The later of two questions with the same number and wording.
        seen, pick = {}, []
        for i, (a, b) in enumerate(spans):
            key = hs._question_of(last_full_html[a:b])
            key = (hs.question_label(last_full_html[a:b]), tuple(key[1]) if key else ())
            if key in seen and key[0]:
                pick.append(i)
            seen.setdefault(key, i)
        pick = pick[:1]
    elif target[0] == "#":
        pick = [target[1] - 1] if 1 <= target[1] <= len(spans) else []
    else:
        want = f"{target[0]} {target[1]}".lower()
        pick = [i for i, (a, b) in enumerate(spans)
                if hs.question_label(last_full_html[a:b]).lower() == want]
    if len(spans) < 2:
        set_status("That is the only question here — nothing was removed.", RED)
        return False
    if len(pick) != 1:
        return submit(text, [], "edit", local=False)
    _drop_retry()
    _user_bubble(text, [])
    before = last_full_html
    a, b = spans[pick[0]]
    label = card_title(last_full_html[a:b], "removed")
    last_turn = {"text": text, "files": [], "intent": "edit",
                 "history": len(conversation_history), "html": before,
                 "blocks": list(doc_blocks), "version": version_at}
    while b < len(last_full_html) and last_full_html[b] in " \t\r\n":
        b += 1
    last_full_html = last_full_html[:a] + last_full_html[b:]
    doc_blocks = hs.blocks_of(last_full_html)
    save_current(html=last_full_html, blocks=doc_blocks)
    record_version(label, before)
    refresh_artifact()
    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "  Goodwill  ", "ai_label")
    chat.insert(tk.END, "\n", "spacer")
    chat.mark_set("stream_start", "end-1c")
    chat.mark_gravity("stream_start", tk.LEFT)
    chat.config(state=tk.DISABLED)
    put_card(label, verdict_note="done here, nothing sent to Gemini")
    set_status(f"{label} — {len(doc_blocks)} question block(s) left.", GREEN)
    auto_pdf(keep_status=True)
    return True



def verify_model_for(solve_model):
    """The model that checks the work — a different one if chosen, else the solver."""
    chosen = (SETTINGS.get("verify_model") or "").strip()
    if not chosen:
        return solve_model
    if model_ids and chosen not in [mid for mid, _ in model_ids]:
        return solve_model          # it vanished from the account; fall back quietly
    return chosen


def run_verification(question_text, files, answer_html, model):
    """Second pass. Returns (verdict, input, output, cached_input, model)."""
    check_parts = api.build_parts(
        "ORIGINAL INSTRUCTION FROM THE TEACHER:\n"
        f"{question_text}\n\n"
        "SOLUTION TO BE CHECKED:\n"
        f"{answer_html}",
        files,
    )
    checker = verify_model_for(model)
    verdict, v_in, v_out, v_cached = api.generate(
        [{"role": "user", "parts": check_parts}],
        checker,
        system_prompt=prompts.VERIFY_PROMPT,
        max_tokens=8192,
        temperature=0.0,
    )
    return verdict.strip(), v_in, v_out, v_cached, checker


# The word may be glued to whatever came before it — "50,000VERIFIED" — so
# there is no word boundary to open on.
_MISMATCH = re.compile(r"mismatch\b", re.I)
_VERIFIED = re.compile(r"verified\b", re.I)
# A verdict denied within the two words before it is not that verdict:
# "no mismatch", "could not be verified", "unverified".
_DENIED = re.compile(r"\b(no|not|n't|cannot|unable|without|any|fail\w*)\b"
                     r"\s*(?:\w+\s+){0,2}$", re.I)


def _asserted(pattern, text):
    """True if the word is stated, rather than denied or part of another word."""
    for found in pattern.finditer(text):
        before = text[max(0, found.start() - 40):found.start()]
        if before[-2:].lower() == "un" or _DENIED.search(before):
            continue
        return True
    return False


def verdict_kind(verdict):
    """'bad', 'ok' or 'unclear' — read from the whole verdict, not its first word.

    The checker is told to answer with MISMATCH or VERIFIED alone, and a small
    model does not: it writes a paragraph first and puts the word in the middle,
    even glued to a figure — "Present Value: 50,000VERIFIED". Reading only the
    first word called every one of those a pass, so a genuine mismatch would
    have been reported in green as verified. A mismatch anywhere wins.
    """
    text = verdict or ""
    if _asserted(_MISMATCH, text):
        return "bad"
    if _asserted(_VERIFIED, text):
        return "ok"
    return "unclear"


def finish(answer, in_tok, out_tok, cached_tok, elapsed, model, verdict, v_cost=None,
           intent="add"):
    global busy, last_response_text, last_body, last_full_html, verify_report, doc_blocks
    busy = False
    send_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED, bg=BORDER)

    last_response_text = answer

    total = api.cost_inr(model, in_tok, out_tok, cached_tok)
    used = in_tok + out_tok
    cached = cached_tok
    if v_cost:
        v_model, v_in, v_out, v_cached = v_cost
        v_inr = api.cost_inr(v_model, v_in, v_out, v_cached)
        if total is not None and v_inr is not None:
            total += v_inr
        used += v_in + v_out
        cached += v_cached
    # The top bar is narrow, and a long meter is silently clipped from the
    # right — which hides the cost, the part worth reading.
    saved = f" ({compact_tokens(cached).replace(' tok', '')} cached)" if cached else ""
    meter_label.config(
        text=f"{api.format_inr(total)}  ·  {compact_tokens(used)}{saved}  ·  {elapsed:.0f}s")

    verify_report = verdict or ""
    kind = verdict_kind(verdict) if verdict else ""

    if active_mode_key() == "general":
        # A conversation is read in the chat, so it stays in full.
        chat.config(state=tk.NORMAL)
        chat.delete("stream_start", tk.END)
        chat.insert(tk.END, f"{for_chat(answer)}\n\n", "ai_msg")
        chat.config(state=tk.DISABLED)
        chat.see(tk.END)
        save_current(conversation=strip_binary(conversation_history))
        put_retry()
        set_status("Done.", GREEN)
        return

    # Notes about the cleaning go under the card, not above it.
    notes = []
    before = last_full_html

    body = api.strip_code_fence(answer)
    body = latex_to_unicode(body)
    body = render_charts(body)

    if intent == "edit":
        # Slashes and carets are fixed here too; the block markers are comments
        # and pass through untouched.
        body, repairs = hs.repair_markup(body)
        body = hs.strip_backgrounds(body)
        try:
            new_html, changed, removed = hs.apply_edits(last_full_html, body)
        except hs.EditError as exc:
            put_card("Nothing changed")
            say(str(exc), "bad")
            set_status("No edit made — the page is as it was.", RED)
            save_current(conversation=strip_binary(conversation_history))
            put_retry()
            return
        spans = hs.block_spans(new_html)
        old_spans = hs.block_spans(last_full_html)
        if changed:
            first = changed[0] - 1 - sum(1 for r in removed if r < changed[0])
            a, b = spans[first]
            title = card_title(new_html[a:b], "edited")
            if len(changed) > 1:
                title += f" and {len(changed) - 1} more"
        else:
            a, b = old_spans[removed[0] - 1]
            title = card_title(last_full_html[a:b], "removed")
        last_full_html = new_html
        doc_blocks = hs.blocks_of(new_html)
        if repairs:
            notes.append(("Repaired " + " and ".join(repairs)
                          + " — divisions are stacked fractions, powers are superscripts.",
                          "note"))
    else:
        # A weak model narrates before it writes. That planning used to be printed
        # into the PDF as page one. Keep the document, say what was dropped.
        body, dropped = hs.extract_document(body)
        if dropped:
            notes.append((f"Removed {len(dropped)} characters the model wrote before the "
                          f"document — its own notes, not part of the answer.", "note"))

        # Slashes and carets are the house style's own rule, not a matter of
        # opinion, so Python fixes them rather than asking the model again. No
        # figure is altered — only how the division is written.
        body, repairs = hs.repair_markup(body)
        if repairs:
            notes.append(("Repaired " + " and ".join(repairs)
                          + " — divisions are stacked fractions, powers are superscripts.",
                          "note"))
        # A background written into the answer would print as a white table.
        body = hs.strip_backgrounds(body)

        # "Add one more question" often comes back with the earlier question too.
        # The document already holds it, so it is left out rather than printed twice.
        asked = last_turn["text"] if last_turn else ""
        resolve = bool(re.search(r"\b(?:method|another\s+way|other\s+way|again|re-?solve|"
                                 r"alternative|also\s+solve|pvf|table)\b", asked, re.I))
        body, repeated = hs.drop_repeats(last_full_html, body, resolve_wanted=resolve)
        if repeated:
            notes.append((f"Gemini sent {' and '.join(repeated)} again — this document "
                          f"already has it, so it was left out and only the new question "
                          f"was added.", "note"))

        # A small model sometimes recites the contract instead of answering it.
        # Saving that would put a page of quoted instructions into the chapter and
        # overwrite nothing useful, so the document is left exactly as it was.
        if not hs.looks_like_document(body):
            put_card("Nothing added")
            say("The model wrote about the instructions instead of solving the "
                "question, so nothing was added to the document. Press Retry, or "
                "choose a stronger model — Gemini 3.1 Flash-Lite is about "
                "10 paise a question.", "bad")
            set_status("No document produced — nothing was changed.", RED)
            save_current(conversation=strip_binary(conversation_history))
            put_retry()
            return

        if 'class="page-block"' not in body:
            body = f'<div class="page-block">\n{body}\n</div>'
        # The book and page print only when the teacher typed them.
        body = hs.teacher_pgrefs(body, last_turn["text"] if last_turn else "")
        last_body = body
        title = card_title(body, "added")
        if active_mode_key() == "solve" and not hs.question_label(body):
            notes.append(("Gemini left out the question number. Type, for example,  "
                          "number it Illustration 6  and it is put in — free.", "bad"))

        doc_blocks.append(body)
        if last_full_html.strip():
            # Append into the live document so manual edits in the Code tab survive.
            last_full_html = hs.append_block(last_full_html, body)
        else:
            last_full_html = hs.wrap_document(doc_blocks)

    # A pass is the tick on the card; only a doubt is worth reading in full.
    if kind == "bad":
        notes.insert(0, (verdict, "bad"))
    elif kind == "unclear":
        notes.insert(0, (verdict, "note"))
    put_card(title, kind)
    for text, how in notes:
        say(text, how)

    refresh_artifact()
    run_validator()
    save_current(html=last_full_html, blocks=doc_blocks,
                 conversation=strip_binary(conversation_history), model=model)
    record_version(title, before)
    if intent == "add":
        name_document_from(body)
    refresh_tree(select=("d", current_chapter, current_doc))
    refresh_title()
    refresh_intent()
    if prompts.wants_code(last_turn["text"] if last_turn else ""):
        show_tab("code")
    put_retry()
    if kind == "bad":
        set_status("Verification found a mismatch — see the chat.", RED)
    elif kind == "ok":
        set_status("Verified.", GREEN)
    elif kind == "unclear":
        set_status("Verification unclear — read it yourself.", ACCENT)
    else:
        set_status(f"Done — {len(doc_blocks)} block(s) in this document.", GREEN)
    auto_pdf(keep_status=bool(verdict))


def name_document_from(block):
    """Rename a document from its first answer, never over a name he chose.

    A document is created from the instruction typed at the time, so a chapter
    fills with twenty documents all called "solve it in a table format". The
    answer knows better: "Discounting — Illustration 6 (Pg. 43)".
    """
    if current_chapter is None or current_doc is None:
        return
    if len(doc_blocks) > 1:          # only the first answer names it
        return
    current = next((d["title"] for d in LIB.list_documents(current_chapter)
                    if d["id"] == current_doc), "")
    if current != auto_titles.get(current_doc):
        return                       # he renamed it himself; leave it alone
    title = hs.title_from_block(block, "")
    if not title or title == current:
        return
    try:
        LIB.rename_document(current_chapter, current_doc, title)
    except library.LibraryError:
        return
    auto_titles[current_doc] = title


def loop_stopped(words, intent="add"):
    """The model went round in circles and was cut off."""
    global busy
    busy = False
    send_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED, bg=BORDER)
    put_card("Nothing changed" if intent == "edit" else "Nothing added")
    say(f"The model kept repeating itself — {words} words and no document — so "
        "it was stopped. Nothing was added. Press Retry, or choose "
        "a model that follows instructions; Gemini 3.1 Flash-Lite is about 10 "
        "paise a question.", "bad")
    set_status("Stopped — the model was going in circles.", RED)
    save_current(conversation=strip_binary(conversation_history))
    put_retry()


def fail(message):
    global busy
    busy = False
    send_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED, bg=BORDER)
    chat.config(state=tk.NORMAL)
    chat.delete("stream_start", tk.END)
    chat.insert(tk.END, f"[{message}]\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)
    put_retry()
    set_status("Failed — see the chat for details.", "#CC0000")


def stop_generation():
    stop_event.set()
    set_status("Stopping...", RED)


def clear_chat():
    global conversation_history, last_turn
    conversation_history = []
    last_turn = None
    _drop_retry()
    chat.config(state=tk.NORMAL)
    chat.delete("1.0", tk.END)
    chat.insert(tk.END, "\n  Chat cleared.\n\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    meter_label.config(text="")


def remove_last_block():
    """Drop the last question from the open document, keeping any manual edits above it."""
    global last_full_html
    if not doc_blocks:
        set_status("No blocks to remove.", "#CC0000")
        return
    before = last_full_html
    doc_blocks.pop()
    cut = last_full_html.rfind('<div class="page-block"')
    if cut == -1:
        last_full_html = hs.wrap_document(doc_blocks) if doc_blocks else ""
    else:
        last_full_html = last_full_html[:cut].rstrip() + "\n</body>\n</html>\n"
    save_current(html=last_full_html, blocks=doc_blocks)
    record_version("Last question removed", before)
    refresh_artifact()
    set_status(f"Removed the last block — {len(doc_blocks)} remaining.", GREEN)


# ═══════════════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════════════

def refresh_models(initial=False):
    set_status("Fetching model list...", ACCENT)

    def work():
        try:
            found = api.list_models()
            post(lambda: models_loaded(found, initial))
        except api.GeminiError as exc:
            post(lambda e=exc: models_failed(str(e), initial))

    threading.Thread(target=work, daemon=True).start()


def models_loaded(found, initial):
    global model_ids
    model_ids = found
    labels = [display for _, display in found]
    model_dropdown["values"] = labels
    if not labels:
        set_status("The API returned no usable models.", "#CC0000")
        return
    saved = SETTINGS.get("model")
    chosen = 0
    for i, (mid, _) in enumerate(found):
        if mid == saved:
            chosen = i
            break
    else:
        # No saved choice: prefer a Pro model for difficult problems.
        for i, (mid, _) in enumerate(found):
            if "pro" in mid:
                chosen = i
                break
    model_var.set(labels[chosen])
    SETTINGS["model"] = found[chosen][0]
    save_settings()
    set_status(f"{len(found)} models available. Using {found[chosen][0]}.", GREEN)


def models_failed(message, initial):
    set_status("Could not fetch models.", "#CC0000")
    if initial:
        messagebox.showerror("Gemini", message)


def on_model_change(_evt=None):
    SETTINGS["model"] = selected_model()
    save_settings()


# ═══════════════════════════════════════════════════════════════
#  SETTINGS WINDOW
# ═══════════════════════════════════════════════════════════════

def open_settings():
    win = tk.Toplevel(root)
    win.title("Settings")
    win.geometry("900x720")
    win.configure(bg=BG)
    win.transient(root)

    tk.Label(win, text="Mode / preset", font=("Arial", 10, "bold"),
             bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 2))

    row = tk.Frame(win, bg=BG)
    row.pack(fill=tk.X, padx=16)
    keys = list(SETTINGS["presets"].keys())
    names = [SETTINGS["presets"][k]["name"] for k in keys]
    sel = tk.StringVar(value=SETTINGS["presets"][SETTINGS["active"]]["name"])
    dd = ttk.Combobox(row, textvariable=sel, values=names, state="readonly", width=44)
    dd.pack(side=tk.LEFT)

    tk.Label(win, text="System prompt", font=("Arial", 10, "bold"),
             bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 2))
    box = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 9), height=22,
                                    bg=FIELD, fg=TEXT, relief=tk.FLAT)
    box.pack(fill=tk.BOTH, expand=True, padx=16)
    box.frame.config(bg=BG)

    def show(key):
        box.delete("1.0", tk.END)
        box.insert(tk.END, SETTINGS["presets"][key]["system_prompt"])

    current = {"key": SETTINGS["active"]}
    show(current["key"])

    def on_select(_e=None):
        current["key"] = keys[names.index(sel.get())]
        show(current["key"])
    dd.bind("<<ComboboxSelected>>", on_select)

    gen = tk.LabelFrame(win, text=" Generation ", bg=BG, fg=TEXT, font=("Arial", 9, "bold"))
    gen.pack(fill=tk.X, padx=16, pady=12)

    tk.Label(gen, text="Max output tokens", bg=BG, fg=TEXT).grid(row=0, column=0, sticky="w", padx=8, pady=4)
    tok = tk.Entry(gen, width=10)
    tok.insert(0, str(SETTINGS.get("max_tokens", api.DEFAULT_MAX_TOKENS)))
    tok.grid(row=0, column=1, sticky="w", pady=4)

    tk.Label(gen, text="Temperature", bg=BG, fg=TEXT).grid(row=0, column=2, sticky="w", padx=8)
    temp = tk.Entry(gen, width=8)
    temp.insert(0, str(SETTINGS.get("temperature", api.DEFAULT_TEMPERATURE)))
    temp.grid(row=0, column=3, sticky="w")

    tk.Label(gen, text="Thinking budget (blank = model default)",
             bg=BG, fg=TEXT).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=4)
    think = tk.Entry(gen, width=10)
    think.insert(0, "" if SETTINGS.get("thinking_budget") is None else str(SETTINGS["thinking_budget"]))
    think.grid(row=1, column=1, sticky="w", pady=4)

    verify_var = tk.BooleanVar(value=SETTINGS.get("verify", True))
    tk.Checkbutton(gen, text="Run the verification pass after solving", variable=verify_var,
                   bg=BG, fg=TEXT, selectcolor=BG, activebackground=BG
                   ).grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=4)

    # A model checking its own arithmetic can repeat its own slip. Solving on a
    # cheap model and checking on a strong one costs little, because the check
    # is short.
    tk.Label(gen, text="Check the answer with", bg=BG, fg=TEXT
             ).grid(row=3, column=0, sticky="w", padx=8, pady=4)
    SAME = "Same model that solved it"
    verify_choices = [SAME] + [disp for _, disp in model_ids]
    saved_vm = (SETTINGS.get("verify_model") or "").strip()
    current_row = 0
    for i, (mid, _) in enumerate(model_ids):
        if mid == saved_vm:
            current_row = i + 1
            break
    verify_dd = ttk.Combobox(gen, values=verify_choices, state="readonly", width=30)
    verify_dd.current(current_row)
    verify_dd.grid(row=3, column=1, columnspan=3, sticky="w", pady=4)

    charts_var = tk.BooleanVar(value=SETTINGS.get("charts", False))
    tk.Checkbutton(gen, text="Add pie charts for profit-sharing ratios", variable=charts_var,
                   bg=BG, fg=TEXT, selectcolor=BG, activebackground=BG
                   ).grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

    autopdf_var = tk.BooleanVar(value=SETTINGS.get("auto_pdf", True))
    tk.Checkbutton(gen, text="Make the PDF automatically after each answer",
                   variable=autopdf_var, bg=BG, fg=TEXT, selectcolor=BG,
                   activebackground=BG
                   ).grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

    def do_save():
        SETTINGS["presets"][current["key"]]["system_prompt"] = box.get("1.0", tk.END).rstrip()
        try:
            SETTINGS["max_tokens"] = max(1024, int(tok.get().strip()))
        except ValueError:
            pass
        try:
            SETTINGS["temperature"] = max(0.0, min(2.0, float(temp.get().strip())))
        except ValueError:
            pass
        raw = think.get().strip()
        SETTINGS["thinking_budget"] = int(raw) if raw.isdigit() else None
        SETTINGS["verify"] = verify_var.get()
        row = verify_dd.current()
        SETTINGS["verify_model"] = ("" if row <= 0 else model_ids[row - 1][0])
        SETTINGS["charts"] = charts_var.get()
        SETTINGS["auto_pdf"] = autopdf_var.get()
        save_settings()
        set_status("Settings saved.", GREEN)
        win.destroy()

    def do_reset():
        key = current["key"]
        if key in prompts.MODES:
            SETTINGS["presets"][key]["system_prompt"] = prompts.MODES[key]["system_prompt"]
            show(key)
            set_status(f"'{SETTINGS['presets'][key]['name']}' prompt reset to the built-in version.", GREEN)

    bar = tk.Frame(win, bg=BG)
    bar.pack(fill=tk.X, padx=16, pady=(0, 14))
    tk.Button(bar, text="Save", command=do_save, bg=ACCENT, fg="white",
              relief=tk.FLAT, padx=18, pady=5).pack(side=tk.LEFT)
    tk.Button(bar, text="Reset this prompt", command=do_reset, bg=SIDEBAR, fg=TEXT,
              relief=tk.FLAT, padx=14, pady=5).pack(side=tk.LEFT, padx=8)
    tk.Button(bar, text="Cancel", command=win.destroy, bg=BORDER, fg=TEXT,
              relief=tk.FLAT, padx=14, pady=5).pack(side=tk.RIGHT)


def on_mode_change(_evt=None):
    label = mode_var.get()
    for key, preset in SETTINGS["presets"].items():
        if preset["name"] == label:
            SETTINGS["active"] = key
            save_settings()
            refresh_intent()
            set_status(f"Mode: {label}", TEXT)
            return


# ═══════════════════════════════════════════════════════════════
#  WINDOW
# ═══════════════════════════════════════════════════════════════

root = tk.Tk()
def installed_version():
    """The version update.py installed, e.g. "c6a1c5e" — or "" if unknown."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION"),
                  encoding="utf-8") as fh:
            return fh.read().strip()[:12]
    except OSError:
        return ""


root.title("Goodwill Gemini Tutor" + (f"  —  version {installed_version()}"
                                       if installed_version() else ""))
# Size to the screen rather than a fixed guess: leave room for the Windows
# taskbar and the title bar, so the typing box and attach row are never
# pushed out of reach on a smaller laptop display.
_sw, _sh = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry(f"{min(1500, _sw - 80)}x{min(800, _sh - 140)}+30+25")
root.minsize(1000, 560)

# ── theming for the ttk widgets ──────────────────────────────────────
# The native Windows theme ignores colour options, so switch to 'clam',
# which honours them.
style = ttk.Style(root)
try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure("TNotebook", background=ARTIFACT_BG, borderwidth=0)
style.configure("TNotebook.Tab", background=SIDEBAR, foreground=TEXT,
                padding=(16, 7), borderwidth=0)
style.map("TNotebook.Tab",
          background=[("selected", ARTIFACT_BG)],
          foreground=[("selected", ACCENT)])

style.configure("TCombobox", fieldbackground=FIELD, background=SIDEBAR,
                foreground=TEXT, arrowcolor=TEXT, borderwidth=0, padding=4)
style.map("TCombobox",
          fieldbackground=[("readonly", FIELD)],
          background=[("readonly", FIELD)],
          foreground=[("readonly", TEXT)],
          selectbackground=[("readonly", FIELD)],
          selectforeground=[("readonly", TEXT)])

# The combobox drop-down list is a classic Tk listbox, themed separately.
root.option_add("*TCombobox*Listbox.background", FIELD)
root.option_add("*TCombobox*Listbox.foreground", TEXT)
root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
root.option_add("*TCombobox*Listbox.font", ("Arial", 9))

# Scrollbars
for _opt, _val in (("background", SIDEBAR), ("troughColor", BG),
                   ("activeBackground", BORDER), ("borderWidth", 0),
                   ("highlightThickness", 0)):
    root.option_add(f"*Scrollbar.{_opt}", _val)

# Text cursor and selection inside the dark input fields
for _cls in ("Text", "Entry", "Listbox"):
    root.option_add(f"*{_cls}.insertBackground", TEXT)
    root.option_add(f"*{_cls}.selectBackground", ACCENT)
    root.option_add(f"*{_cls}.selectForeground", "#FFFFFF")
    root.option_add(f"*{_cls}.highlightThickness", 0)
root.configure(bg=BG)

# ── top bar ──────────────────────────────────────────────────────────
top = tk.Frame(root, bg=SIDEBAR, height=52)
top.pack(fill=tk.X)
top.pack_propagate(False)

tk.Label(top, text="GOODWILL TUITION CENTRE", font=("Georgia", 12, "bold"),
         bg=SIDEBAR, fg=BLUE).pack(side=tk.LEFT, padx=16)

mode_var = tk.StringVar(value=active_preset()["name"])
mode_dropdown = ttk.Combobox(
    top, textvariable=mode_var,
    values=[p["name"] for p in SETTINGS["presets"].values()],
    state="readonly", width=14,
)
mode_dropdown.pack(side=tk.LEFT, padx=6)
mode_dropdown.bind("<<ComboboxSelected>>", on_mode_change)

model_var = tk.StringVar()
model_dropdown = ttk.Combobox(top, textvariable=model_var, values=[], state="readonly", width=26)
model_dropdown.pack(side=tk.LEFT, padx=6)
model_dropdown.bind("<<ComboboxSelected>>", on_model_change)

tk.Button(top, text="Refresh models", command=lambda: refresh_models(),
          bg=SIDEBAR, fg=TEXT, relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
tk.Button(top, text="Settings", command=open_settings,
          bg=SIDEBAR, fg=TEXT, relief=tk.FLAT, padx=10).pack(side=tk.RIGHT, padx=16)

# Anchored west so that, on a narrow window, Tk trims the seconds from the
# right rather than the cost from the left.
meter_label = tk.Label(top, text="", font=("Arial", 9), bg=SIDEBAR, fg=MUTED,
                       anchor="w")
meter_label.pack(side=tk.RIGHT, padx=10)

# ── body ─────────────────────────────────────────────────────────────
# The status bar runs along the foot of the whole window. Sat beside Send, a
# long message was squeezed over "Clear chat" as soon as the chat got narrow.
status_bar = tk.Frame(root, bg=SIDEBAR)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)
status_label = tk.Label(status_bar, text="Ready", font=("Arial", 9), bg=SIDEBAR, fg=MUTED,
                        anchor="w")
status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=3)

body = tk.Frame(root, bg=BG)
body.pack(fill=tk.BOTH, expand=True)

# ── sidebar: chapters and their documents ────────────────────────────
side = tk.Frame(body, bg=SIDEBAR, width=240)
side.pack(side=tk.LEFT, fill=tk.Y)
side.pack_propagate(False)

side_buttons = tk.Frame(side, bg=SIDEBAR)
side_buttons.pack(fill=tk.X, padx=10, pady=(12, 6))
tk.Button(side_buttons, text="+ Chapter", command=lambda: new_chapter(),
          bg=SIDEBAR, fg=TEXT, relief=tk.FLAT, font=("Arial", 9),
          padx=8, pady=5, cursor="hand2").pack(side=tk.LEFT)
tk.Button(side_buttons, text="+ Document", command=lambda: new_document(),
          bg=ACCENT, fg="white", relief=tk.FLAT, font=("Arial", 9, "bold"),
          padx=10, pady=5, cursor="hand2").pack(side=tk.RIGHT)

tree_wrap = tk.Frame(side, bg=SIDEBAR)
tree_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
tree_scroll = tk.Scrollbar(tree_wrap)
tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
tree = ttk.Treeview(tree_wrap, show="tree", selectmode="browse",
                    yscrollcommand=tree_scroll.set)
tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
tree_scroll.config(command=tree.yview)

style.configure("Treeview", background=SIDEBAR, fieldbackground=SIDEBAR,
                foreground=TEXT, borderwidth=0, rowheight=24)
style.map("Treeview", background=[("selected", ACCENT)],
          foreground=[("selected", "#FFFFFF")])

tk.Button(side, text="Rename", command=lambda: rename_selected(),
          bg=SIDEBAR, fg=MUTED, relief=tk.FLAT, font=("Arial", 9),
          cursor="hand2").pack(fill=tk.X, padx=10)
tk.Button(side, text="Delete", command=lambda: delete_selected(),
          bg=SIDEBAR, fg=MUTED, relief=tk.FLAT, font=("Arial", 9),
          cursor="hand2").pack(fill=tk.X, padx=10, pady=(0, 12))


def selected_node():
    """(kind, chapter_id, document_id) for the highlighted row.

    kind is "c" for a chapter, "d" for a document, None for nothing.

    The id carries its parts separated by "|". Tcl truncates a string at a NUL
    byte, so a NUL separator silently collapses every chapter to the same item;
    slugs are [a-z0-9-] only, so "|" can never appear inside one.
    """
    sel = tree.selection()
    if not sel:
        return (None, None, None)
    parts = sel[0].split("|")
    if parts[0] == "c":
        return ("c", parts[1], None)
    if parts[0] == "d":
        return ("d", parts[1], parts[2])
    return (None, None, None)


def refresh_tree(select=None):
    """Rebuild the tree, keeping what was open expanded.

    select is ("c", chapter_id, None) or ("d", chapter_id, doc_id).
    """
    opened = {iid for iid in tree.get_children("") if tree.item(iid, "open")}
    tree.delete(*tree.get_children(""))
    for chapter in LIB.list_chapters():
        cid = chapter["id"]
        iid = f"c|{cid}"
        label = ("* " if chapter["pinned"] else "") + chapter["name"]
        if chapter["documents"]:
            label += f"   {chapter['documents']}"
        tree.insert("", "end", iid=iid, text=label, open=(iid in opened
                                                          or cid == current_chapter))
        for doc in LIB.list_documents(cid):
            tree.insert(iid, "end", iid=f"d|{cid}|{doc['id']}",
                        text="   " + doc["title"])
    if select:
        kind, cid, did = select
        iid = f"c|{cid}" if kind == "c" else f"d|{cid}|{did}"
        if tree.exists(iid):
            parent = tree.parent(iid)
            if parent:
                tree.item(parent, open=True)
            tree.selection_set(iid)
            tree.see(iid)


def on_tree_open(_evt=None):
    """Open a document on double-click; a single click only selects."""
    kind, cid, did = selected_node()
    if kind == "d":
        open_document(cid, did)


tree.bind("<Double-1>", on_tree_open)
tree.bind("<Return>", on_tree_open)


def open_tree_menu(event):
    """Right-click actions, matched to what was clicked."""
    iid = tree.identify_row(event.y)
    if iid:
        tree.selection_set(iid)
    kind, cid, did = selected_node()
    menu = _menu()
    if kind == "d":
        menu.add_command(label="Open", command=lambda: open_document(cid, did))
        menu.add_separator()
        menu.add_command(label="Rename", command=rename_selected)
        menu.add_command(label="Duplicate", command=duplicate_selected)
        menu.add_command(label="Delete", command=delete_selected)
    elif kind == "c":
        menu.add_command(label="New document here", command=new_document)
        menu.add_separator()
        menu.add_command(label="Rename", command=rename_selected)
        menu.add_command(label="Pin / unpin", command=pin_selected)
        menu.add_command(label="Delete chapter", command=delete_selected)
    else:
        menu.add_command(label="New chapter", command=new_chapter)
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


tree.bind("<Button-3>", open_tree_menu)


def _ask_text(title, label, default=""):
    """A small modal prompt. Returns None when cancelled."""
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.transient(root)
    win.resizable(False, False)
    tk.Label(win, text=label, bg=BG, fg=TEXT, font=("Arial", 10)).pack(
        anchor="w", padx=16, pady=(14, 4))
    entry_box = tk.Entry(win, width=44, bg=FIELD, fg=TEXT, relief=tk.FLAT,
                         font=("Arial", 11))
    entry_box.pack(padx=16)
    entry_box.insert(0, default)
    entry_box.select_range(0, tk.END)
    answer = {"value": None}

    def ok(_e=None):
        answer["value"] = entry_box.get().strip()
        win.destroy()

    row = tk.Frame(win, bg=BG)
    row.pack(fill=tk.X, padx=16, pady=12)
    tk.Button(row, text="OK", command=ok, bg=ACCENT, fg="white", relief=tk.FLAT,
              padx=16, pady=4).pack(side=tk.LEFT)
    tk.Button(row, text="Cancel", command=win.destroy, bg=BORDER, fg=TEXT,
              relief=tk.FLAT, padx=12, pady=4).pack(side=tk.RIGHT)
    entry_box.bind("<Return>", ok)
    entry_box.bind("<Escape>", lambda _e: win.destroy())
    win.update_idletasks()
    win.geometry(f"+{root.winfo_rootx() + 180}+{root.winfo_rooty() + 150}")
    entry_box.focus_set()
    win.grab_set()
    root.wait_window(win)
    return answer["value"]


# split
split = tk.PanedWindow(body, orient=tk.HORIZONTAL, bg=SIDEBAR, sashwidth=6,
                       sashrelief=tk.FLAT, bd=0)
split.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# ── left: chat ───────────────────────────────────────────────────────
left = tk.Frame(split, bg=BG)
split.add(left, minsize=380, width=620)

# The input area is packed FIRST and anchored to the bottom, so it always
# keeps its space. Packing the chat first lets it claim the whole cavity and
# push the attach row off the bottom of the screen.
input_frame = tk.Frame(left, bg=BG)
input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 12))

chat_frame = tk.Frame(left, bg=BG)
chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=14, pady=(12, 4))
chat = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Georgia", 11),
                                 bg=BG, fg=TEXT, relief=tk.FLAT, borderwidth=0,
                                 padx=10, pady=10)
chat.pack(fill=tk.BOTH, expand=True)
chat.frame.config(bg=BG)          # ScrolledText's wrapper keeps Tk's grey otherwise
chat.config(state=tk.DISABLED)
# The chat is read-only, and on Windows a read-only Text never takes the
# keyboard focus from a click — so a selection could be made but Ctrl+C did
# nothing, and the selection was drawn without its highlight. Take focus on
# click, copy on Ctrl+C, and keep the highlight when the focus moves on.
chat.config(inactiveselectbackground=ACCENT, exportselection=True)


def _chat_selection():
    try:
        return chat.get("sel.first", "sel.last")
    except tk.TclError:
        return ""


def copy_chat(_evt=None, everything=False):
    text = chat.get("1.0", "end-1c") if everything else _chat_selection()
    text = text.strip()
    if not text:
        set_status("Select some text in the chat first.", MUTED)
        return "break"
    root.clipboard_clear()
    root.clipboard_append(text)
    set_status("Copied.", GREEN)
    return "break"


def chat_to_message(_evt=None):
    """Put the selected text in the typing box — a command from help, say."""
    text = _chat_selection().strip()
    if not text:
        set_status("Select a line in the chat first.", MUTED)
        return "break"
    entry.delete("1.0", tk.END)
    entry.insert("1.0", text)
    entry.focus_set()
    refresh_intent()
    return "break"


def open_chat_menu(event):
    menu = _menu()
    menu.add_command(label="Copy", command=copy_chat)
    menu.add_command(label="Copy all", command=lambda: copy_chat(everything=True))
    menu.add_separator()
    menu.add_command(label="Put in my message", command=chat_to_message)
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


chat.bind("<Button-1>", lambda _e: chat.focus_set(), add="+")
for _seq in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
    chat.bind(_seq, copy_chat)
chat.bind("<Button-3>", open_chat_menu)
chat.tag_config("user_label", background=ACCENT, foreground="white",
                font=("Arial", 9, "bold"), spacing1=5, spacing3=5)
chat.tag_config("ai_label", background=TEXT, foreground=BG,
                font=("Arial", 9, "bold"), spacing1=5, spacing3=5)
chat.tag_config("user_msg", background=USER_BUBBLE, font=("Georgia", 11),
                lmargin1=10, lmargin2=10, rmargin=10, spacing1=3, spacing3=3)
chat.tag_config("ai_msg", background=AI_BUBBLE, font=("Georgia", 11),
                lmargin1=10, lmargin2=10, rmargin=10, spacing1=3, spacing3=3)
chat.tag_config("spacer", spacing1=2, spacing3=2)
chat.tag_config("ok_label", background=GREEN, foreground="white",
                font=("Arial", 9, "bold"), spacing1=5, spacing3=5)
chat.tag_config("bad_label", background=RED, foreground="white",
                font=("Arial", 9, "bold"), spacing1=5, spacing3=5)
chat.tag_config("note_label", background=BLUE, foreground="white",
                font=("Arial", 9, "bold"), spacing1=5, spacing3=5)
for _k in ("ok", "bad", "note"):
    chat.tag_config(f"{_k}_msg", background=AI_BUBBLE, font=("Consolas", 10),
                    lmargin1=10, lmargin2=10, rmargin=10, spacing1=3, spacing3=3)
# The card that stands for a whole answer: the page is on the right, so the
# chat only names what happened to it. Clicking it shows the page.
chat.tag_config("card", background=SIDEBAR, foreground=TEXT, font=("Arial", 10, "bold"),
                lmargin1=10, spacing1=6, spacing3=6)
chat.tag_config("card_ok", background=SIDEBAR, foreground=GREEN, font=("Arial", 10, "bold"))
chat.tag_config("card_bad", background=SIDEBAR, foreground=RED, font=("Arial", 10, "bold"))
chat.tag_config("card_sub", background=SIDEBAR, foreground=MUTED, font=("Arial", 9),
                lmargin1=10)
# The message shading is drawn over the selection unless the selection is
# raised above it: the text turned white on a pale bubble and looked unselected.
chat.tag_raise("sel")
chat.tag_bind("card_link", "<Button-1>", lambda _e: show_tab("preview"))
chat.tag_bind("card_link", "<Enter>", lambda _e: chat.config(cursor="hand2"))
chat.tag_bind("card_link", "<Leave>", lambda _e: chat.config(cursor=""))

# What Send is about to do — "Will add" or "Will edit" — read from the words
# typed, as Claude.ai does. A click switches it for this one message.
intent_row = tk.Frame(input_frame, bg=BG)
intent_row.pack(fill=tk.X, pady=(0, 2))
intent_label = tk.Label(intent_row, text="Will add", font=("Arial", 9, "bold"),
                        bg=BG, fg=ACCENT, cursor="hand2")
intent_label.pack(side=tk.LEFT)
intent_detail = tk.Label(intent_row, text="", font=("Arial", 9), bg=BG, fg=MUTED,
                         cursor="hand2", anchor="w")
intent_detail.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
for _w in (intent_label, intent_detail):
    _w.bind("<Button-1>", toggle_intent)

btn_row = tk.Frame(input_frame, bg=BG)
btn_row.pack(fill=tk.X, pady=(0, 5))
send_btn = tk.Button(btn_row, text="Send", command=send_message, font=("Arial", 11, "bold"),
                     bg=ACCENT, fg="white", relief=tk.FLAT, padx=22, pady=6, cursor="hand2")
send_btn.pack(side=tk.LEFT)
stop_btn = tk.Button(btn_row, text="Stop", command=lambda: stop_generation(),
                     font=("Arial", 10), bg=BORDER, fg=TEXT, relief=tk.FLAT,
                     padx=14, pady=6, state=tk.DISABLED)
stop_btn.pack(side=tk.LEFT, padx=6)
tk.Button(btn_row, text="Clear chat", command=lambda: clear_chat(), font=("Arial", 9),
          bg=BG, fg=MUTED, relief=tk.FLAT).pack(side=tk.LEFT, padx=6)


attach_row = tk.Frame(input_frame, bg=BG)
attach_row.pack(fill=tk.X, pady=(0, 6))
tk.Button(attach_row, text="Attach PDF / image", command=attach_files, font=("Arial", 9),
          bg=SIDEBAR, fg=TEXT, relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT)
tk.Button(attach_row, text="Paste  (Ctrl+V)", command=paste_from_clipboard,
          font=("Arial", 9), bg=SIDEBAR, fg=TEXT, relief=tk.FLAT,
          padx=10, cursor="hand2").pack(side=tk.LEFT, padx=5)
tk.Button(attach_row, text="Clear", command=clear_attachments, font=("Arial", 9),
          bg=BG, fg=MUTED, relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
attach_label = tk.Label(attach_row, text="No pages attached", font=("Arial", 9), anchor="w",
                        width=1,
                        bg=BG, fg=MUTED)
attach_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)   # cut at the end, not the middle

entry = tk.Text(input_frame, height=4, wrap=tk.WORD, font=("Georgia", 11),
                bg=FIELD, fg=TEXT, relief=tk.FLAT, padx=10, pady=8)
entry.pack(fill=tk.X)
entry.bind("<Return>", send_message)
entry.bind("<Shift-Return>", lambda e: None)
entry.bind("<KeyRelease>", refresh_intent, add="+")
for _seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
    entry.bind(_seq, paste_from_clipboard)
    root.bind(_seq, paste_from_clipboard)

# ── right: artifact ──────────────────────────────────────────────────
# Laid out like Claude.ai's artifact panel: the title and ◀ v3 of 5 ▶ on top,
# then Preview | Code on the left and the PDF buttons on the right.
right = tk.Frame(split, bg=ARTIFACT_BG)
split.add(right, minsize=420, width=800)

art_header = tk.Frame(right, bg=ARTIFACT_BG, height=40)
art_header.pack(fill=tk.X)
art_header.pack_propagate(False)

version_row = tk.Frame(art_header, bg=ARTIFACT_BG)
version_prev = tk.Button(version_row, text="◀", command=lambda: step_version(-1),
                         font=("Arial", 9), bg=ARTIFACT_BG, fg=TEXT, relief=tk.FLAT,
                         padx=6, cursor="hand2", activebackground=SIDEBAR,
                         disabledforeground=BORDER)
version_prev.pack(side=tk.LEFT)
version_label = tk.Label(version_row, text="", font=("Arial", 9, "bold"),
                         bg=ARTIFACT_BG, fg=TEXT)
version_label.pack(side=tk.LEFT, padx=2)
version_next = tk.Button(version_row, text="▶", command=lambda: step_version(1),
                         font=("Arial", 9), bg=ARTIFACT_BG, fg=TEXT, relief=tk.FLAT,
                         padx=6, cursor="hand2", activebackground=SIDEBAR,
                         disabledforeground=BORDER)
version_next.pack(side=tk.LEFT)

artifact_title = tk.Label(art_header, text="No document yet", font=("Arial", 11, "bold"),
                          bg=ARTIFACT_BG, fg=TEXT, anchor="w")
artifact_title.pack(side=tk.LEFT, padx=14, pady=8, fill=tk.X, expand=True)

tab_bar = tk.Frame(right, bg=ARTIFACT_BG)
tab_bar.pack(fill=tk.X, padx=8)

def _popup(menu, anchor):
    """Drop a menu directly under the button that opened it."""
    try:
        menu.tk_popup(anchor.winfo_rootx(),
                      anchor.winfo_rooty() + anchor.winfo_height())
    finally:
        menu.grab_release()


def _menu():
    return tk.Menu(root, tearoff=0, bg=FIELD, fg=TEXT,
                   activebackground=ACCENT, activeforeground="#FFFFFF",
                   borderwidth=1, font=("Arial", 10))


def _select_open_document():
    """Point the tree at the open document, so the shared actions act on it."""
    if current_chapter is None or current_doc is None:
        set_status("No document open.", RED)
        return False
    refresh_tree(select=("d", current_chapter, current_doc))
    return True


def rename_this():
    if _select_open_document():
        rename_selected()


def duplicate_this():
    if _select_open_document():
        duplicate_selected()


def delete_this():
    if _select_open_document():
        delete_selected()


def open_more_menu(event=None):
    """Everything to do with building the document."""
    menu = _menu()
    menu.add_command(label="Save as HTML", command=lambda: save_html())
    menu.add_command(label="Open the HTML file", command=lambda: _open_doc_file("html"))
    menu.add_command(label="Open in browser", command=open_in_browser)
    menu.add_separator()
    menu.add_command(label="Apply my edits", command=apply_edited_html)
    menu.add_command(label="Check house style", command=check_house_style)
    menu.add_separator()
    menu.add_command(label="New document", command=new_document)
    menu.add_command(label="New chapter", command=new_chapter)
    menu.add_command(label="Remove last question", command=remove_last_block)
    menu.add_separator()
    menu.add_command(label="Rename this document", command=rename_this)
    menu.add_command(label="Duplicate this document", command=duplicate_this)
    menu.add_command(label="Delete this document", command=delete_this)
    menu.add_separator()
    menu.add_command(label="Open this document's folder", command=open_folder)
    menu.add_command(label="Copy answer", command=copy_answer)
    _popup(menu, more_btn)


def _tab(text, which):
    button = tk.Button(tab_bar, text=text, command=lambda: show_tab(which),
                       font=("Arial", 10), bg=ARTIFACT_BG, fg=MUTED, relief=tk.FLAT,
                       padx=6, pady=3, cursor="hand2", activebackground=SIDEBAR)
    button.pack(side=tk.LEFT)
    return button


preview_tab = _tab("Preview", "preview")
tk.Label(tab_bar, text="|", bg=ARTIFACT_BG, fg=BORDER).pack(side=tk.LEFT)
code_tab = _tab("Code", "code")

# One menu for everything else. A separate ▾ beside it made the row too wide
# for Windows at 125% text size, and Make PDF was cut in half.
more_btn = tk.Button(tab_bar, text="More ▾", command=open_more_menu,
                     font=("Arial", 10), bg=ARTIFACT_BG, fg=MUTED,
                     relief=tk.FLAT, padx=6, pady=3, cursor="hand2",
                     activebackground=SIDEBAR)
more_btn.pack(side=tk.RIGHT, padx=(2, 4))

# The PDF buttons: Open shows the PDF on disk and says when it is out of date;
# Make PDF renders it now and opens it.
pdf_open_btn = tk.Button(tab_bar, text="Open PDF", command=lambda: _open_doc_file("pdf"),
                         font=("Arial", 9), bg=SIDEBAR, fg=TEXT, relief=tk.FLAT,
                         padx=10, pady=3, cursor="hand2", activebackground=BORDER,
                         disabledforeground=MUTED)
pdf_open_btn.pack(side=tk.RIGHT, padx=2)
pdf_make_btn = tk.Button(tab_bar, text="Make PDF", command=lambda: generate_pdf(),
                         font=("Arial", 9, "bold"), bg=ACCENT, fg="white", relief=tk.FLAT,
                         padx=10, pady=3, cursor="hand2", activebackground=ACCENT,
                         disabledforeground=BORDER)
pdf_make_btn.pack(side=tk.RIGHT, padx=2)

tab_body = tk.Frame(right, bg=ARTIFACT_BG)
tab_body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(4, 12))

# ── Preview: the page as Chromium draws it ───────────────────────────
preview_frame = tk.Frame(tab_body, bg=ARTIFACT_BG)
preview_scroll = tk.Scrollbar(preview_frame, orient=tk.VERTICAL)
preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
preview_canvas = tk.Canvas(preview_frame, bg=ARTIFACT_BG, highlightthickness=0, bd=0,
                           yscrollcommand=preview_scroll.set)
preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
preview_scroll.config(command=preview_canvas.yview)


def _preview_wheel(event):
    step = -1 if (getattr(event, "delta", 0) > 0 or event.num == 4) else 1
    preview_canvas.yview_scroll(step * 3, "units")


for _seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
    preview_canvas.bind(_seq, _preview_wheel)

# Selecting text in the Preview, as in a browser. The picture has no text in
# it, so Chromium also records where every word was drawn; the panel then does
# what a browser does: press and drag to select in reading order, double-click
# a word, triple-click a line, Ctrl+A for the page, Ctrl+C to copy. Letting go
# of the mouse copies too — one step fewer for the teacher.
SELECT_BLUE = "#3390FF"
_sel = {"anchor": None, "first": None, "last": None, "multi": False, "moved": False,
        "x": 0, "y": 0}


def _canvas_xy(event):
    return preview_canvas.canvasx(event.x), preview_canvas.canvasy(event.y)


def _draw_selection():
    """Highlight the selected words, one band per line, as a browser draws it."""
    preview_canvas.delete("picked")
    if _sel["first"] is None:
        return
    first, last = sorted((_sel["first"], _sel["last"]))
    bands = {}
    for w in preview_lines[first:last + 1]:
        key = (w["b"], round(w["y"] / 4))
        x0, y0, x1, y1 = bands.get(key, (w["x"], w["y"], w["x"] + w["w"], w["y"] + w["h"]))
        bands[key] = (min(x0, w["x"]), min(y0, w["y"]),
                      max(x1, w["x"] + w["w"]), max(y1, w["y"] + w["h"]))
    for x0, y0, x1, y1 in bands.values():
        preview_canvas.create_rectangle(x0 - 1, y0, x1 + 1, y1, fill=SELECT_BLUE,
                                        stipple="gray50", outline="", tags="picked")


def _select(first, last):
    _sel["first"], _sel["last"] = first, last
    _draw_selection()


def clear_preview_selection():
    _sel.update(anchor=None, first=None, last=None)
    preview_canvas.delete("picked")


def copy_preview_selection(_evt=None):
    """Copy what is selected in the Preview. Returns the text."""
    if _sel["first"] is None or not preview_lines:
        set_status("Select some text in the Preview first — press and drag." if preview_lines
                   else "The preview is still being drawn — try again in a moment.", MUTED)
        return ""
    text = pdf_export.words_text(preview_lines, _sel["first"], _sel["last"])
    root.clipboard_clear()
    root.clipboard_append(text)
    words = abs(_sel["last"] - _sel["first"]) + 1
    set_status(f"Copied: {text[:50]}" if words <= 8 else f"Copied {words} words.", GREEN)
    return text


def _preview_press(event):
    preview_canvas.focus_set()
    x, y = _canvas_xy(event)
    _sel.update(x=x, y=y, moved=False, multi=False)
    clear_preview_selection()
    _sel["anchor"] = pdf_export.word_at(preview_lines, x, y)


def _preview_motion(event):
    if _sel["anchor"] is None:
        return
    x, y = _canvas_xy(event)
    if not _sel["moved"] and abs(x - _sel["x"]) < 3 and abs(y - _sel["y"]) < 3:
        return
    _sel["moved"] = True
    # Drag past the edge and the page scrolls with you.
    if event.y < 16:
        preview_canvas.yview_scroll(-1, "units")
    elif event.y > preview_canvas.winfo_height() - 16:
        preview_canvas.yview_scroll(1, "units")
    x, y = _canvas_xy(event)
    _select(_sel["anchor"], pdf_export.word_at(preview_lines, x, y))


def _preview_release(_event):
    if _sel["multi"]:
        _sel["multi"] = False
        copy_preview_selection()
    elif _sel["moved"] and _sel["first"] is not None:
        copy_preview_selection()


def _preview_double(event):
    x, y = _canvas_xy(event)
    i = pdf_export.word_at(preview_lines, x, y)
    if i is not None:
        _sel["multi"] = True
        _select(i, i)
    return "break"


def _preview_triple(event):
    x, y = _canvas_xy(event)
    i = pdf_export.word_at(preview_lines, x, y)
    if i is not None:
        block = preview_lines[i]["b"]
        same = [j for j, w in enumerate(preview_lines) if w["b"] == block]
        _sel["multi"] = True
        _select(same[0], same[-1])
    return "break"


def select_all_preview(_evt=None):
    if preview_lines:
        _select(0, len(preview_lines) - 1)
        copy_preview_selection()
    return "break"


def _preview_hover(event):
    x, y = _canvas_xy(event)
    preview_canvas.config(cursor="xterm" if pdf_export.hit_word(preview_lines, x, y) else "")


def open_in_browser():
    """The page in the system browser — Edge and Chrome are Chromium too."""
    path = save_html(silent=True)
    if not path:
        set_status("Nothing to open yet.", RED)
        return
    import webbrowser
    webbrowser.open(pathlib.Path(path).as_uri())


def _preview_menu(event):
    menu = _menu()
    has = _sel["first"] is not None
    menu.add_command(label="Copy", command=copy_preview_selection,
                     state=tk.NORMAL if has else tk.DISABLED)
    menu.add_command(label="Select all and copy", command=select_all_preview)
    menu.add_separator()
    menu.add_command(label="Open in browser", command=open_in_browser)
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


preview_canvas.bind("<ButtonPress-1>", _preview_press)
preview_canvas.bind("<B1-Motion>", _preview_motion)
preview_canvas.bind("<ButtonRelease-1>", _preview_release)
preview_canvas.bind("<Double-Button-1>", _preview_double)
preview_canvas.bind("<Triple-Button-1>", _preview_triple)
preview_canvas.bind("<Motion>", _preview_hover)
preview_canvas.bind("<Button-3>", _preview_menu)
for _seq in ("<Control-a>", "<Control-A>"):
    preview_canvas.bind(_seq, select_all_preview)
for _seq in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
    preview_canvas.bind(_seq, copy_preview_selection)

# A narrower panel draws the page smaller, once the dragging stops.
_resize_job = [None]


def _preview_resized(_evt=None):
    if _resize_job[0]:
        root.after_cancel(_resize_job[0])
    _resize_job[0] = root.after(400, refresh_preview)


preview_canvas.bind("<Configure>", _preview_resized)

# ── Code: the document as editable HTML ──────────────────────────────
code_frame = tk.Frame(tab_body, bg=ARTIFACT_BG)
editor_bar = tk.Frame(code_frame, bg=ARTIFACT_BG)
editor_bar.pack(fill=tk.X)
tk.Button(editor_bar, text="Apply my edits", command=apply_edited_html,
          font=("Arial", 9, "bold"), bg=ACCENT, fg="white", relief=tk.FLAT,
          padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, pady=(0, 6))
# Short enough to survive a narrow panel; the long version was cut mid-word.
tk.Label(editor_bar, text="Edit, then Apply.",
         font=("Arial", 9), bg=ARTIFACT_BG, fg=MUTED).pack(side=tk.LEFT, padx=10)

editor = scrolledtext.ScrolledText(code_frame, wrap=tk.NONE, font=("Consolas", 9),
                                   bg=FIELD, fg=TEXT, relief=tk.FLAT, undo=True)
editor.pack(fill=tk.BOTH, expand=True)
editor.frame.config(bg=ARTIFACT_BG)


def _open_doc_file(which):
    if current_chapter is None or current_doc is None:
        set_status("No document open.", RED)
        return
    path = (LIB.pdf_path(current_chapter, current_doc) if which == "pdf"
            else LIB.html_path(current_chapter, current_doc))
    if not os.path.exists(path):
        set_status("Not made yet — press Make PDF." if which == "pdf"
                   else "Not saved yet — use the ▾ menu.", RED)
        return
    if which == "pdf" and pdf_is_stale():
        if not messagebox.askyesno(
            "PDF is out of date",
            "This PDF was made before the latest change to the document.\n\n"
            "Open the old one anyway?\n\n"
            "Choose No, then press  Make PDF  to remake it."):
            return
    pdf_export.open_file(path)


def pdf_is_stale():
    """True when the HTML has changed since the PDF was made.

    Existence is not freshness: adding a second question rewrites the HTML but
    leaves the old PDF on disk, and a button that only checks existence keeps
    offering it.
    """
    if current_chapter is None or current_doc is None:
        return False
    pdf = LIB.pdf_path(current_chapter, current_doc)
    html = LIB.html_path(current_chapter, current_doc)
    if not (os.path.exists(pdf) and os.path.exists(html)):
        return False
    try:
        return os.path.getmtime(html) > os.path.getmtime(pdf) + 1
    except OSError:
        return False


def refresh_file_cards():
    """Show on the PDF buttons whether there is a PDF, and whether it is current."""
    if current_chapter is None or current_doc is None:
        pdf_open_btn.config(text="Open PDF", state=tk.DISABLED, fg=MUTED)
        pdf_make_btn.config(state=tk.DISABLED)
        return
    has_html = os.path.exists(LIB.html_path(current_chapter, current_doc))
    pdf_make_btn.config(state=tk.NORMAL if has_html else tk.DISABLED)
    if not os.path.exists(LIB.pdf_path(current_chapter, current_doc)):
        pdf_open_btn.config(text="Open PDF", state=tk.DISABLED, fg=MUTED)
    elif pdf_is_stale():
        pdf_open_btn.config(text="Open old PDF", state=tk.NORMAL, fg=RED)
    else:
        pdf_open_btn.config(text="Open PDF", state=tk.NORMAL, fg=TEXT)


show_tab("preview")


# ── start ────────────────────────────────────────────────────────────
chat.config(state=tk.NORMAL)
chat.insert(tk.END, "\n  Goodwill Gemini Tutor\n", "ai_msg")
chat.insert(tk.END, "  Attach or paste (Ctrl+V) a PDF or image of the question, then press Send.\n", "ai_msg")
chat.insert(tk.END, "  Solve mode builds an A4 document in house style.\n", "ai_msg")
chat.insert(tk.END, "  The page appears on the right: Preview shows it, Code holds the HTML.\n", "ai_msg")
chat.insert(tk.END, "  \"Add a question\" adds to the document; \"change / fix / remove\" edits it.\n", "ai_msg")
chat.insert(tk.END, "  Chapters are on the left. Double-click a document to reopen it.\n\n", "ai_msg")
if not pdf_export.playwright_available():
    chat.insert(tk.END, "  For the preview and PDF export:  pip install playwright"
                        "  then  playwright install chromium\n\n", "ai_msg")
chat.config(state=tk.DISABLED)

refresh_artifact()
refresh_title()
refresh_file_cards()
refresh_intent()

# Bring last year's flat files into a chapter. Copies only — the originals in
# Desktop/Goodwill_Solutions and the old conversations folder are left alone.
try:
    _moved = LIB.migrate(CONVERSATIONS_DIR, SOLUTIONS_DIR)
    if _moved["documents"]:
        say(f"Brought {_moved['documents']} earlier item(s) into the chapter "
            f"'Before chapters'. Your original files were copied, not moved.", "note")
except library.LibraryError as _exc:
    print(f"[migration failed] {_exc}")

def on_close():
    """Let a PDF finish before the window goes.

    Chromium is driven through a Node process on the other end of a pipe.
    Closing the window mid-render takes Python away while that process is still
    talking, and Node prints a wall of "EPIPE: broken pipe" to the console.
    Nothing is lost by it, but it reads like a crash.
    """
    global closing
    closing = True
    if auto_pdf_running:
        set_status("Finishing the PDF before closing...", ACCENT)
        deadline = time.time() + 20
        while auto_pdf_running and time.time() < deadline:
            root.update()
            time.sleep(0.05)
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

def _restyle_sweep():
    count = restyle_everything()
    if count:
        post(lambda n=count: set_status(
            f"{n} older document(s) brought up to the current house style.", GREEN))


threading.Thread(target=_restyle_sweep, daemon=True).start()

refresh_tree()
root.after(40, pump)

try:
    api.get_api_key()
    refresh_models(initial=True)
except api.GeminiError as exc:
    set_status("GEMINI_API_KEY is not set.", RED)
    _key_error = str(exc)
    root.after(300, lambda m=_key_error: messagebox.showerror("API key missing", m))

root.mainloop()
