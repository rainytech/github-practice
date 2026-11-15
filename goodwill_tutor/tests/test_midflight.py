"""While an answer is on its way: Stop, and moving to another document."""

import sys
import threading
import time
from support import Report, gui, settle, wait_for_models


def block(n, amount):
    return ('<div class="page-block"><div class="top-bar"><span class="title">DISCOUNTING</span></div>'
            f'<div class="q"><span class="qno">Illustration <span class="num">{n}</span>.</span>'
            f'<span>Find the present value of Rs. {amount}.</span></div>'
            f'<div class="final-ans">Present Value = Rs. {amount}</div></div>')


state = {"mode": "whole", "reply": block(6, "50,000")}
entered = threading.Event()
release = threading.Event()


def stream(conv, model, system_prompt="", on_chunk=None, stop_event=None, **kw):
    reply = state["reply"]
    if state["mode"] == "hold":
        # The answer is still on its way until the test lets it go.
        entered.set()
        release.wait(10)
    if state["mode"] == "stopped":
        # Stop pressed half-way: the stream ends early with what had arrived.
        reply = reply[:len(reply) // 2]
        if on_chunk:
            on_chunk(reply)
        stop_event.set()
        return reply, 4000, 300, 0
    if on_chunk:
        on_chunk(reply)
    return reply, 4000, 900, 0


r = Report("While an answer is on its way")
app = gui(stream=stream)
r.check("a model is available", bool(wait_for_models(app)))


def ask(what, wait=True):
    app.entry.insert("1.0", what)
    app.refresh_intent()
    app.send_message()
    if wait:
        settle(app)


def chat_text():
    return app.chat.get("1.0", "end")


ask("solve this question")
first = (app.current_chapter, app.current_doc)
r.check("the first answer is in the document", "Rs. 50,000" in app.last_full_html)

# ── moving to another document while Gemini is still writing ───────────
other = app.LIB.create_document(app.current_chapter, "Another document")
state.update(mode="hold", reply=block(7, "1,00,000"))
ask("add one more question", wait=False)
entered.wait(10)
app.open_document(first[0], other)
r.check("opening another document is refused while busy",
        (app.current_chapter, app.current_doc), first)
held_history = len(app.conversation_history)
app.clear_chat()
r.check("Clear chat is refused while busy", len(app.conversation_history), held_history)
release.set()
settle(app)
r.check("the answer lands in the document it was asked in",
        "Rs. 1,00,000" in app.LIB.read_document(*first)["html"])
r.check("the other document is untouched",
        app.LIB.read_document(first[0], other)["html"], "")
r.check("once finished, the other document opens",
        (app.open_document(first[0], other), app.current_doc)[1], other)
app.open_document(*first)

# ── Stop pressed half-way through an answer ─────────────────────────────
before = app.last_full_html
blocks = len(app.doc_blocks)
state.update(mode="stopped", reply=block(8, "70,000"))
ask("add one more question")
r.check("a stopped answer adds nothing to the page", app.last_full_html, before)
r.check("no half block is kept", len(app.doc_blocks), blocks)
r.check("nothing half-written is saved",
        "70,000" in app.LIB.read_document(*first)["html"], False)
r.check("the chat says it was stopped", "Stopped" in chat_text())
r.check("Send works again", app.busy, False)
r.check("Retry is offered", app.retry_btn is not None)

sys.exit(r.finish())
