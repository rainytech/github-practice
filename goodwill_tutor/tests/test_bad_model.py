"""The three ways a weak model fails, and what the app does about each."""

import sys
import time
from support import Report, gui, settle, wait_for_models

GOOD = ('<div class="page-block"><div class="q">'
        '<span class="qno">Illustration 6.</span>'
        '<span>Find the present value of Rs. 66,550.</span></div></div>')

RECITED = ('Okay. The HTML must start with `<div class="page-block">` and end '
           'with `</div>`. No `<head>`, no `<style>`. I will now solve it.')

LOOP_LINE = '* *Wait, the prompt says "No LaTeX: no \\%s".* I will use plain text.\n\n'

state = {"reply": GOOD, "chunks": 0}


def stream(conv, model, system_prompt="", on_chunk=None, stop_event=None, **kw):
    """Answer with whatever the test has lined up; loop for ever if asked."""
    if state["reply"] == "LOOP":
        text = ""
        for i in range(400):
            if stop_event is not None and stop_event.is_set():
                break
            piece = LOOP_LINE % f"cmd{i % 6}"
            text += piece
            state["chunks"] += 1
            if on_chunk:
                on_chunk(piece)
            time.sleep(0.02)
        return text, 4000, len(text) // 4, 0
    if on_chunk:
        on_chunk(state["reply"])
    return state["reply"], 4000, 900, 0


r = Report("A weak model")
app = gui(stream=stream)
r.check("a model is available", bool(wait_for_models(app)))


def ask(what):
    app.entry.insert("1.0", what)
    app.send_message()
    settle(app)


# ── a good answer first, so there is something to protect ───────────────
ask("solve this question")
kept = app.last_full_html
r.check("the good answer is saved", 'Illustration <span class="num">6</span>' in kept)

# ── 1. the model recites the contract instead of answering ──────────────
state["reply"] = RECITED
ask("solve it again")
r.check("the document is untouched", app.last_full_html, kept)
r.check("no block was added", len(app.doc_blocks), 1)
r.check("the chat explains", "wrote about the instructions" in app.chat.get("1.0", "end"))
r.check("the status says nothing changed", app.status_label.cget("text"),
        "No document produced — nothing was changed.")
r.check("nothing quoted reached the file", "end with" in open(
    app.LIB.html_path(app.current_chapter, app.current_doc), encoding="utf-8").read(), False)

# ── 2. the model argues with the contract for ever ──────────────────────
state["reply"] = "LOOP"
started = time.time()
ask("solve it once more")
took = time.time() - started
r.check("it was stopped for you", app.busy, False)
r.check("stopped early, not after 400 chunks", state["chunks"] < 80)
r.check("stopped quickly", took < 15)
r.check("the chat says it was repeating", "kept repeating itself" in app.chat.get("1.0", "end"))
r.check("the status explains", app.status_label.cget("text"),
        "Stopped — the model was going in circles.")
r.check("the document is still untouched", app.last_full_html, kept)
r.check("Send works again", str(app.send_btn.cget("state")), "normal")

# ── 3. the checker writes a paragraph instead of a verdict ──────────────
r.check("a plain pass", app.verdict_kind("VERIFIED\nPresent Value = 50,000"), "ok")
r.check("a plain failure", app.verdict_kind("MISMATCH\n[WN 2] — wrong factor"), "bad")
r.check("a pass glued to a figure",
        app.verdict_kind("Key figures.\nPresent Value: 50,000VERIFIED\nDone"), "ok")
r.check("a failure hidden under a paragraph",
        app.verdict_kind("I checked every figure.\n\nMISMATCH\n[WN 1] — rate"), "bad")
r.check("'no mismatch' is a pass", app.verdict_kind("VERIFIED\nI found no mismatch."), "ok")
r.check("a checker that could not run is not a pass",
        app.verdict_kind("Verification could not run: quota exhausted"), "unclear")

sys.exit(r.finish())
