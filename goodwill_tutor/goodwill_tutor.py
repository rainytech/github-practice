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
SETTINGS_SCHEMA = 2

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

            if old_schema < SETTINGS_SCHEMA:
                # Keep the teacher's own presets, but rename any legacy one out
                # of the way and start them on the new Solve mode.
                legacy = merged["presets"].pop("default", None)
                if legacy and legacy.get("system_prompt"):
                    legacy["name"] = f"{legacy.get('name', 'Old preset')} (v1)"
                    merged["presets"]["default_v1"] = legacy
                merged["active"] = prompts.DEFAULT_MODE
                merged["schema"] = SETTINGS_SCHEMA
                merged["model"] = ""          # old model IDs are long gone
                merged["max_tokens"] = api.DEFAULT_MAX_TOKENS
                merged["temperature"] = api.DEFAULT_TEMPERATURE

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
current_html_path = None
current_conversation_id = None
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
#  CONVERSATIONS
# ═══════════════════════════════════════════════════════════════

def list_conversations():
    items = []
    for name in os.listdir(CONVERSATIONS_DIR):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(CONVERSATIONS_DIR, name), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            items.append((data.get("id", name[:-5]),
                          data.get("title", "Untitled"),
                          data.get("created", "")))
        except Exception:
            continue
    items.sort(key=lambda t: t[2], reverse=True)
    return items


def save_conversation():
    global current_conversation_id
    if not conversation_history:
        return
    if not current_conversation_id:
        current_conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    title = "New chat"
    for turn in conversation_history:
        if turn.get("role") == "user":
            for part in turn.get("parts", []):
                if part.get("text", "").strip():
                    title = part["text"].strip()[:60]
                    break
            break
    payload = {
        "id": current_conversation_id,
        "title": title,
        "created": datetime.now().isoformat(),
        "history": strip_binary(conversation_history),
        "blocks": doc_blocks,
        "last_html": last_full_html,
    }
    try:
        path = os.path.join(CONVERSATIONS_DIR, f"{current_conversation_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except Exception as exc:
        print(f"[conversation save failed] {exc}")


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


def new_conversation():
    global current_conversation_id, conversation_history, doc_blocks
    global last_full_html, last_body, current_html_path, verify_report
    current_conversation_id = None
    conversation_history = []
    doc_blocks = []
    last_full_html = ""
    last_body = ""
    current_html_path = None
    verify_report = ""
    clear_chat()
    artifact_title.config(text="No document yet")
    refresh_artifact()
    refresh_history_list()


def load_conversation(conv_id):
    global current_conversation_id, conversation_history, doc_blocks
    global last_full_html, current_html_path
    try:
        with open(os.path.join(CONVERSATIONS_DIR, f"{conv_id}.json"), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        set_status(f"Could not load chat: {exc}", "#CC0000")
        return
    current_conversation_id = conv_id
    conversation_history = data.get("history", [])
    doc_blocks = data.get("blocks", [])
    last_full_html = data.get("last_html", "")
    current_html_path = None

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
    artifact_title.config(text=data.get("title", "Artifact"))
    refresh_artifact()
    set_status(f"Loaded: {data.get('title', conv_id)}", GREEN)


def delete_conversation(conv_id):
    try:
        os.remove(os.path.join(CONVERSATIONS_DIR, f"{conv_id}.json"))
    except Exception:
        pass
    if current_conversation_id == conv_id:
        new_conversation()
    else:
        refresh_history_list()


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
    global current_html_path
    if not last_full_html.strip():
        if not silent:
            set_status("Nothing to save yet.", "#CC0000")
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SOLUTIONS_DIR, f"goodwill_{stamp}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(last_full_html)
    current_html_path = path
    artifact_title.config(text=os.path.basename(path))
    if not silent:
        set_status(f"Saved: {os.path.basename(path)}", GREEN)
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
    set_status("Rendering PDF with Chromium...", ACCENT)
    output_btn.config(state=tk.DISABLED)

    def work():
        try:
            out = pdf_export.html_to_pdf(path)
            post(lambda: pdf_done(out))
        except pdf_export.PdfExportError as exc:
            post(lambda e=exc: pdf_failed(str(e)))
        except Exception as exc:
            post(lambda e=exc: pdf_failed(str(e)))

    threading.Thread(target=work, daemon=True).start()


def pdf_done(path):
    output_btn.config(state=tk.NORMAL)
    set_status(f"PDF ready: {os.path.basename(path)}", GREEN)
    try:
        pdf_export.open_file(path)
    except Exception:
        pass


def pdf_failed(message):
    output_btn.config(state=tk.NORMAL)
    set_status("PDF failed", "#CC0000")
    messagebox.showerror("PDF export failed", message)


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
    pdf_export.open_file(SOLUTIONS_DIR)


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
            answer, in_tok, out_tok = api.stream_generate(
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
                    verdict, v_in, v_out, used = run_verification(text, files, answer, model)
                    v_cost = (used, v_in, v_out)
                except api.GeminiError as exc:
                    verdict = f"Verification could not run: {exc}"

            elapsed = (datetime.now() - started).total_seconds()
            post(lambda: finish(answer, in_tok, out_tok, elapsed, model, verdict, v_cost))

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
    """Second independent pass. Returns (verdict, input_tokens, output_tokens, model)."""
    check_parts = api.build_parts(
        "ORIGINAL INSTRUCTION FROM THE TEACHER:\n"
        f"{question_text}\n\n"
        "SOLUTION TO BE CHECKED:\n"
        f"{answer_html}",
        files,
    )
    checker = verify_model_for(model)
    verdict, v_in, v_out = api.generate(
        [{"role": "user", "parts": check_parts}],
        checker,
        system_prompt=prompts.VERIFY_PROMPT,
        max_tokens=8192,
        temperature=0.0,
    )
    return verdict.strip(), v_in, v_out, checker


def finish(answer, in_tok, out_tok, elapsed, model, verdict, v_cost=None):
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

    total = api.cost_inr(model, in_tok, out_tok)
    used = in_tok + out_tok
    if v_cost:
        v_model, v_in, v_out = v_cost
        v_inr = api.cost_inr(v_model, v_in, v_out)
        if total is not None and v_inr is not None:
            total += v_inr
        used += v_in + v_out
    # The top bar is narrow, and a long meter is silently clipped from the
    # right — which hides the cost, the part worth reading.
    meter_label.config(
        text=f"{api.format_inr(total)}  ·  {compact_tokens(used)}  ·  {elapsed:.0f}s")

    verify_report = verdict or ""
    if verdict:
        if verdict.upper().startswith("MISMATCH"):
            say(verdict, "bad")
            set_status("Verification found a mismatch — see the chat.", RED)
        else:
            say(verdict, "ok")
            set_status("Verified.", GREEN)

    if active_mode_key() == "general":
        save_conversation()
        refresh_history_list()
        if not verdict:
            set_status("Done.", GREEN)
        return

    body = api.strip_code_fence(answer)
    body = latex_to_unicode(body)
    body = render_charts(body)
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
    save_html(silent=True)
    save_conversation()
    refresh_history_list()
    if not verdict:
        set_status(f"Done — {len(doc_blocks)} block(s) in this document.", GREEN)


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


def start_new_document():
    """Keep the chat, start a fresh chapter document."""
    global doc_blocks, last_full_html, current_html_path
    doc_blocks = []
    last_full_html = ""
    current_html_path = None
    artifact_title.config(text="Artifact — empty")
    refresh_artifact()
    set_status("New document started. The next answer begins a fresh chapter.", GREEN)


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

# history sidebar
history_panel = tk.Frame(body, bg=SIDEBAR, width=210)
history_panel.pack(side=tk.LEFT, fill=tk.Y)
history_panel.pack_propagate(False)

tk.Button(history_panel, text="+ New chat", command=lambda: new_conversation(),
          bg=ACCENT, fg="white", relief=tk.FLAT, pady=6).pack(fill=tk.X, padx=10, pady=(12, 8))
tk.Label(history_panel, text="History", font=("Arial", 9, "bold"),
         bg=SIDEBAR, fg=MUTED).pack(anchor="w", padx=12)

hist_wrap = tk.Frame(history_panel, bg=SIDEBAR)
hist_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
hist_scroll = tk.Scrollbar(hist_wrap)
hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
history_listbox = tk.Listbox(hist_wrap, font=("Arial", 9), bg=SIDEBAR, fg=TEXT,
                             relief=tk.FLAT, yscrollcommand=hist_scroll.set,
                             highlightthickness=0, bd=0, activestyle="none")
history_listbox.pack(fill=tk.BOTH, expand=True)
hist_scroll.config(command=history_listbox.yview)

history_ids = []


def refresh_history_list():
    history_listbox.delete(0, tk.END)
    history_ids.clear()
    for cid, title, _ in list_conversations():
        history_ids.append(cid)
        history_listbox.insert(tk.END, f" {title[:30]}")


def on_history_select(_evt=None):
    if history_listbox.curselection():
        load_conversation(history_ids[history_listbox.curselection()[0]])


history_listbox.bind("<<ListboxSelect>>", on_history_select)

tk.Button(history_panel, text="Delete chat",
          command=lambda: delete_conversation(history_ids[history_listbox.curselection()[0]])
          if history_listbox.curselection() else None,
          bg=SIDEBAR, fg=MUTED, relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=(0, 12))

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
    menu.add_command(label="New document", command=start_new_document)
    menu.add_command(label="Remove last question", command=remove_last_block)
    menu.add_separator()
    menu.add_command(label="Open solutions folder", command=open_folder)
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
editor.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))
editor.frame.config(bg=ARTIFACT_BG)

# ── start ────────────────────────────────────────────────────────────
chat.config(state=tk.NORMAL)
chat.insert(tk.END, "\n  Goodwill Gemini Tutor\n", "ai_msg")
chat.insert(tk.END, "  Attach or paste (Ctrl+V) a PDF or image of the question, then press Send.\n", "ai_msg")
chat.insert(tk.END, "  Solve mode builds an A4 document in house style.\n", "ai_msg")
chat.insert(tk.END, "  The HTML appears on the right. Edit it, then Generate PDF.\n\n", "ai_msg")
if not pdf_export.playwright_available():
    chat.insert(tk.END, "  For the preview and PDF export:  pip install playwright"
                        "  then  playwright install chromium\n\n", "ai_msg")
chat.config(state=tk.DISABLED)

refresh_artifact()
refresh_history_list()
root.after(40, pump)

try:
    api.get_api_key()
    refresh_models(initial=True)
except api.GeminiError as exc:
    set_status("GEMINI_API_KEY is not set.", "#CC0000")
    _key_error = str(exc)
    root.after(300, lambda m=_key_error: messagebox.showerror("API key missing", m))

root.mainloop()
