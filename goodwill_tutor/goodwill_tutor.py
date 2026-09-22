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
import io
import json
import os
import queue
import re
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk

import gemini_api as api
import house_style as hs
import library
import pdf_export
import prompts

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
PREVIEW_WIDTH = 880       # A4 at 96dpi is 794px; a little wider reads better

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
preview_window = None     # the open preview Toplevel, if any
preview_image = None      # live PhotoImage; Tk discards it without a reference

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
    text = (text.replace("&amp;", "&").replace("&nbsp;", " ")
                .replace("&there4;", "therefore").replace("&#9658;", ">")
                .replace("&lt;", "<").replace("&gt;", ">"))
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
    global last_full_html, verify_report
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
            chat.insert(tk.END, f"  {html_to_chat_text(body)}\n\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)

    refresh_artifact()
    refresh_title()
    refresh_file_cards()
    set_status(f"Opened: {data['meta'].get('title', doc_id)}", GREEN)


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
    conversation_history = []
    doc_blocks = []
    last_full_html = ""
    verify_report = ""
    clear_chat()
    refresh_artifact()
    refresh_file_cards()


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
    """Load the current document into the HTML editor."""
    editor.delete("1.0", tk.END)
    editor.insert(tk.END, last_full_html or "")


def apply_edited_html():
    """Take what is in the editor as the document and re-check it."""
    global last_full_html
    edited = editor.get("1.0", tk.END).rstrip()
    if not edited.strip():
        set_status("The editor is empty — nothing to apply.", RED)
        return
    last_full_html = edited
    save_html(silent=True)
    errors, warnings = run_validator()
    if not errors and not warnings:
        set_status("Applied. House style clean.", GREEN)
    else:
        set_status(f"Applied. {len(errors)} error(s), {len(warnings)} warning(s) — see the chat.", RED)
    # Your edit is now the document, so the PDF is out of date the moment it is
    # applied. Remake it, keeping the message above.
    auto_pdf(keep_status=True)


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
    output_btn.config(state=tk.DISABLED)

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
    output_btn.config(state=tk.NORMAL)
    refresh_file_cards()
    set_status("PDF ready.", GREEN)
    try:
        pdf_export.open_file(path)
    except Exception:
        pass


def pdf_failed(message):
    output_btn.config(state=tk.NORMAL)
    set_status("PDF failed", "#CC0000")
    messagebox.showerror("PDF export failed", message)


# A render takes a couple of seconds. If a second answer lands while one is
# running, both threads would write the same file, so the second waits its turn.
auto_pdf_running = False
auto_pdf_again = False


def auto_pdf(keep_status=False):
    """Make the PDF in the background after an answer, without opening it.

    keep_status : leave the status bar alone, so a verification mismatch is
                  not wiped off the screen by a PDF message.
    """
    global auto_pdf_running, auto_pdf_again
    if not SETTINGS.get("auto_pdf", True):
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


def open_preview():
    """Open the document in a window, rendered by the Chromium that makes the PDF."""
    global preview_window
    if not (last_full_html or "").strip():
        set_status("Nothing to preview yet.", RED)
        return

    if preview_window is not None and preview_window.winfo_exists():
        preview_window.destroy()

    win = tk.Toplevel(root)
    preview_window = win
    win.title("Preview")
    win.configure(bg=ARTIFACT_BG)
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    win.geometry(f"{min(PREVIEW_WIDTH + 40, sw - 80)}x{min(920, sh - 140)}+{sw // 3}+20")

    wrap = tk.Frame(win, bg=ARTIFACT_BG)
    wrap.pack(fill=tk.BOTH, expand=True)
    bar = tk.Scrollbar(wrap, orient=tk.VERTICAL)
    bar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas = tk.Canvas(wrap, bg=ARTIFACT_BG, highlightthickness=0, bd=0,
                       yscrollcommand=bar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    bar.config(command=canvas.yview)

    def wheel(event):
        step = -1 if (getattr(event, "delta", 0) > 0 or event.num == 4) else 1
        canvas.yview_scroll(step * 3, "units")

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        canvas.bind(seq, wheel)
    canvas.focus_set()
    canvas.create_text(24, 28, anchor="nw", text="Rendering...", fill=MUTED,
                       font=("Georgia", 11))

    html_snapshot = last_full_html

    def place(png):
        global preview_image
        if not win.winfo_exists():
            return
        try:
            preview_image = tk.PhotoImage(file=png)
        except Exception as exc:
            fail_preview(str(exc))
            return
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=preview_image)
        canvas.configure(scrollregion=(0, 0, preview_image.width(), preview_image.height()))

    def fail_preview(message):
        if not win.winfo_exists():
            return
        canvas.delete("all")
        canvas.create_text(24, 28, anchor="nw", fill=RED, font=("Georgia", 11),
                           width=PREVIEW_WIDTH - 60,
                           text=f"Preview could not be rendered.\n\n{message}")

    def work():
        try:
            tmp_html = os.path.join(PREVIEW_DIR, "preview.html")
            with open(tmp_html, "w", encoding="utf-8") as fh:
                fh.write(html_snapshot)
            png = pdf_export.html_to_png(
                tmp_html, os.path.join(PREVIEW_DIR, "preview.png"), width=PREVIEW_WIDTH)
            post(lambda: place(png))
        except Exception as exc:
            post(lambda e=str(exc): fail_preview(e))

    threading.Thread(target=work, daemon=True).start()


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


def send_message(event=None):
    global busy
    if busy:
        return "break"

    text = entry.get("1.0", tk.END).strip()
    if not text and not attachments:
        return "break"
    if not text:
        text = active_preset().get("default_instruction") or "Solve the attached question."

    model = selected_model()
    if not model:
        set_status("No model selected — press Refresh models.", "#CC0000")
        return "break"

    files = list(attachments)
    ensure_target(text)

    chat.config(state=tk.NORMAL)
    chat.insert(tk.END, "\n", "spacer")
    chat.insert(tk.END, "  You  ", "user_label")
    chat.insert(tk.END, "\n", "spacer")
    for p in files:
        chat.insert(tk.END, f"  [{os.path.basename(p)}]\n", "user_msg")
    chat.insert(tk.END, f"  {text}\n\n", "user_msg")
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

    entry.delete("1.0", tk.END)
    clear_attachments()
    busy = True
    stop_event.clear()
    send_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL, bg=ACCENT)
    set_status("Sending...", ACCENT)

    started = datetime.now()
    acc = [""]
    last_paint = [0.0]

    def on_chunk(piece):
        acc[0] += piece
        now = datetime.now().timestamp()
        if now - last_paint[0] < 0.12:
            return
        last_paint[0] = now
        snapshot = acc[0]
        post(lambda s=snapshot: paint_stream(s))

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

            post(lambda: set_status("Streaming...", ACCENT))
            answer, in_tok, out_tok, cached_tok = api.stream_generate(
                conversation_history,
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
            if SETTINGS.get("verify") and active_mode_key() == "solve" and not stop_event.is_set():
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
            post(lambda: finish(answer, in_tok, out_tok, cached_tok,
                                elapsed, model, verdict, v_cost))

        except api.GeminiError as exc:
            if conversation_history and conversation_history[-1].get("role") == "user":
                conversation_history.pop()
            post(lambda e=exc: fail(str(e)))
        except Exception as exc:
            if conversation_history and conversation_history[-1].get("role") == "user":
                conversation_history.pop()
            post(lambda e=exc: fail(f"Unexpected error: {e}"))

    threading.Thread(target=work, daemon=True).start()
    return "break"


def paint_stream(snapshot):
    words = len(snapshot.split())
    set_status(f"Streaming... ({words} words)", ACCENT)
    chat.config(state=tk.NORMAL)
    chat.delete("stream_start", tk.END)
    chat.insert(tk.END, for_chat(snapshot), "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)


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


def finish(answer, in_tok, out_tok, cached_tok, elapsed, model, verdict, v_cost=None):
    global busy, last_response_text, last_body, last_full_html, verify_report
    busy = False
    send_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED, bg=BORDER)

    last_response_text = answer
    chat.config(state=tk.NORMAL)
    chat.delete("stream_start", tk.END)
    chat.insert(tk.END, f"{for_chat(answer)}\n\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)

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
    if verdict:
        kind = verdict_kind(verdict)
        if kind == "bad":
            say(verdict, "bad")
            set_status("Verification found a mismatch — see the chat.", RED)
        elif kind == "ok":
            say(verdict, "ok")
            set_status("Verified.", GREEN)
        else:
            say(verdict, "note")
            set_status("Verification unclear — read it yourself.", ACCENT)

    if active_mode_key() == "general":
        save_current(conversation=strip_binary(conversation_history))
        if not verdict:
            set_status("Done.", GREEN)
        return

    body = api.strip_code_fence(answer)
    body = latex_to_unicode(body)
    body = render_charts(body)

    # A weak model narrates before it writes. That planning used to be printed
    # into the PDF as page one. Keep the document, say what was dropped.
    body, dropped = hs.extract_document(body)
    if dropped:
        say(f"Removed {len(dropped)} characters the model wrote before the "
            f"document — its own notes, not part of the answer.", "note")

    # Slashes and carets are the house style's own rule, not a matter of
    # opinion, so Python fixes them rather than asking the model again. No
    # figure is altered — only how the division is written.
    body, repairs = hs.repair_markup(body)
    if repairs:
        say("Repaired " + " and ".join(repairs)
            + " — divisions are stacked fractions, powers are superscripts.", "note")

    # A small model sometimes recites the contract instead of answering it.
    # Saving that would put a page of quoted instructions into the chapter and
    # overwrite nothing useful, so the document is left exactly as it was.
    if not hs.looks_like_document(body):
        say("The model wrote about the instructions instead of solving the "
            "question, so nothing was added to the document. Press Send to try "
            "again, or choose a stronger model — Gemini 3.1 Flash-Lite is about "
            "10 paise a question.", "bad")
        set_status("No document produced — nothing was changed.", RED)
        save_current(conversation=strip_binary(conversation_history))
        return

    if 'class="page-block"' not in body:
        body = f'<div class="page-block">\n{body}\n</div>'
    last_body = body

    doc_blocks.append(body)
    if last_full_html.strip():
        # Append into the live document so manual edits in the HTML tab survive.
        last_full_html = hs.append_block(last_full_html, body)
    else:
        last_full_html = hs.wrap_document(doc_blocks)

    refresh_artifact()
    run_validator()
    save_current(html=last_full_html, blocks=doc_blocks,
                 conversation=strip_binary(conversation_history), model=model)
    name_document_from(body)
    refresh_tree(select=("d", current_chapter, current_doc))
    refresh_title()
    if not verdict:
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


def fail(message):
    global busy
    busy = False
    send_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED, bg=BORDER)
    chat.config(state=tk.NORMAL)
    chat.delete("stream_start", tk.END)
    chat.insert(tk.END, f"[{message}]\n\n", "ai_msg")
    chat.config(state=tk.DISABLED)
    chat.see(tk.END)
    set_status("Failed — see the chat for details.", "#CC0000")


def stop_generation():
    stop_event.set()
    set_status("Stopping...", RED)


def clear_chat():
    global conversation_history
    conversation_history = []
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
    doc_blocks.pop()
    cut = last_full_html.rfind('<div class="page-block"')
    if cut == -1:
        last_full_html = hs.wrap_document(doc_blocks) if doc_blocks else ""
    else:
        last_full_html = last_full_html[:cut].rstrip() + "\n</body>\n</html>\n"
    refresh_artifact()
    save_current(html=last_full_html, blocks=doc_blocks)
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
            set_status(f"Mode: {label}", TEXT)
            return


# ═══════════════════════════════════════════════════════════════
#  WINDOW
# ═══════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("Goodwill Gemini Tutor")
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

status_label = tk.Label(btn_row, text="Ready", font=("Arial", 9), bg=BG, fg=MUTED)
status_label.pack(side=tk.RIGHT)

attach_row = tk.Frame(input_frame, bg=BG)
attach_row.pack(fill=tk.X, pady=(0, 6))
tk.Button(attach_row, text="Attach PDF / image", command=attach_files, font=("Arial", 9),
          bg=SIDEBAR, fg=TEXT, relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT)
tk.Button(attach_row, text="Paste  (Ctrl+V)", command=paste_from_clipboard,
          font=("Arial", 9), bg=SIDEBAR, fg=TEXT, relief=tk.FLAT,
          padx=10, cursor="hand2").pack(side=tk.LEFT, padx=5)
tk.Button(attach_row, text="Clear", command=clear_attachments, font=("Arial", 9),
          bg=BG, fg=MUTED, relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
attach_label = tk.Label(attach_row, text="No pages attached", font=("Arial", 9),
                        bg=BG, fg=MUTED)
attach_label.pack(side=tk.LEFT, padx=10)

entry = tk.Text(input_frame, height=4, wrap=tk.WORD, font=("Georgia", 11),
                bg=FIELD, fg=TEXT, relief=tk.FLAT, padx=10, pady=8)
entry.pack(fill=tk.X)
entry.bind("<Return>", send_message)
entry.bind("<Shift-Return>", lambda e: None)
for _seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
    entry.bind(_seq, paste_from_clipboard)
    root.bind(_seq, paste_from_clipboard)

# ── right: artifact ──────────────────────────────────────────────────
right = tk.Frame(split, bg=ARTIFACT_BG)
split.add(right, minsize=420, width=800)

art_header = tk.Frame(right, bg=ARTIFACT_BG, height=46)
art_header.pack(fill=tk.X)
art_header.pack_propagate(False)

artifact_title = tk.Label(art_header, text="No document yet", font=("Arial", 11, "bold"),
                          bg=ARTIFACT_BG, fg=TEXT)
artifact_title.pack(side=tk.LEFT, padx=14, pady=12)

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


def open_output_menu(event=None):
    """What to do with the finished document."""
    menu = _menu()
    menu.add_command(label="Preview", command=open_preview)
    menu.add_separator()
    menu.add_command(label="Save as HTML", command=lambda: save_html())
    menu.add_command(label="Save as PDF", command=generate_pdf)
    _popup(menu, output_btn)


def open_more_menu(event=None):
    """Everything to do with building the document."""
    menu = _menu()
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


output_btn = tk.Button(art_header, text="\u25be", command=open_output_menu,
                       font=("Arial", 13), bg=ARTIFACT_BG, fg=TEXT,
                       relief=tk.FLAT, padx=12, pady=2, cursor="hand2",
                       activebackground=SIDEBAR)
output_btn.pack(side=tk.RIGHT, padx=(4, 14), pady=8)

more_btn = tk.Button(art_header, text="More", command=open_more_menu,
                     font=("Arial", 10), bg=ARTIFACT_BG, fg=MUTED,
                     relief=tk.FLAT, padx=10, pady=5, cursor="hand2",
                     activebackground=SIDEBAR)
more_btn.pack(side=tk.RIGHT, padx=2, pady=8)

# ── the document, as editable HTML ───────────────────────────────────
editor_bar = tk.Frame(right, bg=ARTIFACT_BG)
editor_bar.pack(fill=tk.X, padx=14)
tk.Button(editor_bar, text="Apply my edits", command=apply_edited_html,
          font=("Arial", 9, "bold"), bg=ACCENT, fg="white", relief=tk.FLAT,
          padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, pady=(0, 6))
tk.Label(editor_bar, text="Edit freely, then Apply. The PDF uses what is here.",
         font=("Arial", 9), bg=ARTIFACT_BG, fg=MUTED).pack(side=tk.LEFT, padx=10)

editor = scrolledtext.ScrolledText(right, wrap=tk.NONE, font=("Consolas", 9),
                                   bg=FIELD, fg=TEXT, relief=tk.FLAT, undo=True)
editor.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))
editor.frame.config(bg=ARTIFACT_BG)

# ── the document's files, as a pair you can open ─────────────────────
files_row = tk.Frame(right, bg=ARTIFACT_BG)
files_row.pack(fill=tk.X, padx=14, pady=(0, 12))


def _open_doc_file(which):
    if current_chapter is None or current_doc is None:
        set_status("No document open.", RED)
        return
    path = (LIB.pdf_path(current_chapter, current_doc) if which == "pdf"
            else LIB.html_path(current_chapter, current_doc))
    if not os.path.exists(path):
        set_status("Not made yet — use the \u25be menu to save it.", RED)
        return
    if which == "pdf" and pdf_is_stale():
        if not messagebox.askyesno(
            "PDF is out of date",
            "This PDF was made before the latest change to the document.\n\n"
            "Open the old one anyway?\n\n"
            "Choose No, then use  \u25be  >  Save as PDF  to remake it."):
            return
    pdf_export.open_file(path)


def _card(parent, glyph, kind):
    card = tk.Frame(parent, bg=SIDEBAR, highlightbackground=BORDER,
                    highlightthickness=1)
    card.pack(side=tk.LEFT, padx=(0, 10))
    tk.Label(card, text=glyph, bg=SIDEBAR, fg=MUTED,
             font=("Arial", 14)).pack(side=tk.LEFT, padx=(10, 6), pady=6)
    label = tk.Label(card, text="—", bg=SIDEBAR, fg=TEXT, font=("Arial", 9),
                     anchor="w", width=22, justify="left")
    label.pack(side=tk.LEFT, pady=6)
    button = tk.Button(card, text="Open", command=lambda: _open_doc_file(kind),
                       bg=SIDEBAR, fg=TEXT, relief=tk.FLAT, font=("Arial", 9),
                       padx=10, cursor="hand2")
    button.pack(side=tk.LEFT, padx=(6, 8), pady=5)
    return label, button


pdf_label, pdf_open_btn = _card(files_row, "\U0001F4C4", "pdf")
html_label, html_open_btn = _card(files_row, "\U0001F310", "html")


def pdf_is_stale():
    """True when the HTML has changed since the PDF was made.

    Existence is not freshness: adding a second question rewrites the HTML but
    leaves the old PDF on disk, and a card that only checks existence keeps
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
    """Show whether this document has been saved, printed, and is up to date."""
    if current_chapter is None or current_doc is None:
        for lbl, btn in ((pdf_label, pdf_open_btn), (html_label, html_open_btn)):
            lbl.config(text="No document", fg=MUTED)
            btn.config(state=tk.DISABLED, fg=MUTED)
        return

    title = current_title()[:20]
    stale = pdf_is_stale()

    pdf = LIB.pdf_path(current_chapter, current_doc)
    if not os.path.exists(pdf):
        # Answering a question writes the HTML but never runs Chromium, so
        # this is the normal state until  \u25be  >  Save as PDF  is used.
        pdf_label.config(text=f"{title}\nPDF — not made yet", fg=MUTED)
        pdf_open_btn.config(state=tk.DISABLED, fg=MUTED)
    elif stale:
        pdf_label.config(text=f"{title}\nPDF — out of date", fg=RED)
        pdf_open_btn.config(state=tk.NORMAL, fg=TEXT)
    else:
        pdf_label.config(text=f"{title}\nPDF", fg=TEXT)
        pdf_open_btn.config(state=tk.NORMAL, fg=TEXT)

    html = LIB.html_path(current_chapter, current_doc)
    if os.path.exists(html):
        html_label.config(text=f"{title}\nHTML", fg=TEXT)
        html_open_btn.config(state=tk.NORMAL, fg=TEXT)
    else:
        html_label.config(text=f"{title}\nHTML — not saved yet", fg=MUTED)
        html_open_btn.config(state=tk.DISABLED, fg=MUTED)


# ── start ────────────────────────────────────────────────────────────
chat.config(state=tk.NORMAL)
chat.insert(tk.END, "\n  Goodwill Gemini Tutor\n", "ai_msg")
chat.insert(tk.END, "  Attach or paste (Ctrl+V) a PDF or image of the question, then press Send.\n", "ai_msg")
chat.insert(tk.END, "  Solve mode builds an A4 document in house style.\n", "ai_msg")
chat.insert(tk.END, "  The HTML appears on the right. Edit it, then Save as PDF.\n", "ai_msg")
chat.insert(tk.END, "  Chapters are on the left. Double-click a document to reopen it.\n\n", "ai_msg")
if not pdf_export.playwright_available():
    chat.insert(tk.END, "  For the preview and PDF export:  pip install playwright"
                        "  then  playwright install chromium\n\n", "ai_msg")
chat.config(state=tk.DISABLED)

refresh_artifact()
refresh_title()
refresh_file_cards()

# Bring last year's flat files into a chapter. Copies only — the originals in
# Desktop/Goodwill_Solutions and the old conversations folder are left alone.
try:
    _moved = LIB.migrate(CONVERSATIONS_DIR, SOLUTIONS_DIR)
    if _moved["documents"]:
        say(f"Brought {_moved['documents']} earlier item(s) into the chapter "
            f"'Before chapters'. Your original files were copied, not moved.", "note")
except library.LibraryError as _exc:
    print(f"[migration failed] {_exc}")

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
