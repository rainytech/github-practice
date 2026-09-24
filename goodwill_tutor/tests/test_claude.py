"""Behaving like Claude.ai: add or edit, versions, cards, Retry, the phrases."""

import sys
from support import Report, gui, settle, wait_for_models


def block(n, amount, extra=""):
    return ('<div class="page-block"><div class="top-bar"><span class="title">DISCOUNTING</span>'
            f'<span class="pgref">Central Concepts | Pg. <span class="num">4{n}</span></span></div>'
            f'<div class="q"><span class="qno">Illustration <span class="num">{n}</span>.</span>'
            f'<span>Find the present value of Rs. {amount}.</span></div>'
            f'<div class="final-ans">Present Value = Rs. {amount}{extra}</div></div>')


state = {"reply": block(6, "50,000"), "calls": 0, "seen": None, "system": ""}


def stream(conv, model, system_prompt="", on_chunk=None, stop_event=None, **kw):
    state["calls"] += 1
    state["seen"] = conv
    state["system"] = system_prompt
    if on_chunk:
        on_chunk(state["reply"])
    return state["reply"], 4000, 900, 0


r = Report("Behaving like Claude.ai")
app = gui(stream=stream)
r.check("a model is available", bool(wait_for_models(app)))


def ask(what):
    app.entry.insert("1.0", what)
    app.refresh_intent()
    app.send_message()
    settle(app)


def chat_text():
    return app.chat.get("1.0", "end")


def versions():
    return app.LIB.list_versions(app.current_chapter, app.current_doc)


# ── the teacher's Claude.ai phrases ─────────────────────────────────────
read = app.prompts.read_request
r.check("'append to the same artifact' adds",
        read("Solve Illustration 8 and append to the same artifact", True), "add")
r.check("'str_replace' to fix a figure edits",
        read("use str_replace to fix the total in WN 2", True), "edit")
r.check("'str_replace' with a new question adds",
        read("add one more question using str_replace", True), "add")
r.check("'display the full merged HTML' alone only shows",
        read("display the full merged HTML", True), "show")
r.check("a new question with the merged HTML adds",
        read("add 1 new question and display the full merged HTML", True), "add")
r.check("'add a hint to Illustration 6' edits",
        read("add a hint to Illustration 6", True), "edit")
r.check("'change the title' edits", read("change the title", True), "edit")
r.check("anything with no document yet adds", read("fix the total", False), "add")
r.check("a bare 'solve it again' adds", read("solve it again", True), "add")

# ── 1. the first answer: added, shown as a card ─────────────────────────
r.check("before a document, Send will add", app.intent_label.cget("text"), "Will add")
ask("solve this question")
r.check("the page holds the question", "Find the present value of Rs. 50,000" in app.last_full_html)
r.check("the chat shows a card", "Illustration 6 added" in chat_text())
r.check("the card says it was verified", "Verified ✓" in chat_text())
r.check("the chat does not repeat the answer",
        "Find the present value of Rs. 50,000" in chat_text(), False)
r.check("a version is kept", len(versions()), 1)
r.check("a Retry button sits under it", app.retry_btn is not None)

# ── 2. a second question is added, a second version kept ───────────────
state["reply"] = block(7, "1,00,000")
ask("add one more question")
r.check("two questions", len(app.hs.blocks_of(app.last_full_html)), 2)
r.check("card: Illustration 7 added", "Illustration 7 added" in chat_text())
r.check("two versions", len(versions()), 2)
r.check("versions read v2 of 2", app.version_label.cget("text"), "v2 of 2")
r.check("only one Retry button", sum(1 for w in app.chat.window_names()), 1)

# ── 3. Will edit, and the edit changes the page in place ────────────────
app.entry.insert("1.0", "change the amount in Illustration 6 to Rs. 60,000")
app.refresh_intent()
r.check("the label says Will edit", app.intent_label.cget("text"), "Will edit")
app.entry.delete("1.0", "end")

state["reply"] = "Here it is.\n<!-- block 1 -->\n" + block(6, "60,000")
ask("change the amount in Illustration 6 to Rs. 60,000")
page = app.last_full_html
r.check("the edit is in the page", "Rs. 60,000" in page)
r.check("the old figure is gone", "Rs. 50,000" in page, False)
r.check("Illustration 7 is untouched", "1,00,000" in page)
r.check("still two questions — nothing appended", len(app.hs.blocks_of(page)), 2)
r.check("the model was shown the numbered page",
        "<!-- block 2 -->" in state["seen"][0]["parts"][0]["text"])
r.check("and told to edit in place", "EDIT THE PAGE IN PLACE" in state["system"])
r.check("card: Illustration 6 edited", "Illustration 6 edited" in chat_text())
r.check("three versions", len(versions()), 3)

# ── 4. ◀ goes back a version, ▶ comes forward ───────────────────────────
app.step_version(-1)
r.check("◀ shows v2 of 3", app.version_label.cget("text"), "v2 of 3")
r.check("v2 has the old figure", "Rs. 50,000" in app.last_full_html)
r.check("and the editor shows it too", "Rs. 50,000" in app.editor.get("1.0", "end"))
app.step_version(1)
r.check("▶ returns to v3", "Rs. 60,000" in app.last_full_html)

# ── 5. Retry puts the page back and asks again ──────────────────────────
calls = state["calls"]
state["reply"] = "<!-- block 1 -->\n" + block(6, "65,000")
app.retry_last()
settle(app)
r.check("Retry asked the model again", state["calls"], calls + 1)
r.check("the retried edit replaced the first try", "Rs. 65,000" in app.last_full_html)
r.check("not on top of it", len(app.hs.blocks_of(app.last_full_html)), 2)
r.check("the first try is kept as a version", len(versions()), 4)

# ── 6. an edit Gemini cannot place changes nothing ──────────────────────
kept = app.last_full_html
state["reply"] = block(6, "70,000")        # no block number, and the page has two
ask("fix the final answer")
r.check("the page is untouched", app.last_full_html, kept)
r.check("the chat says why", "did not say which question" in chat_text())

# ── 7. a bare removal is done here, free ────────────────────────────────
calls = state["calls"]
ask("remove Illustration 7")
r.check("Illustration 7 is gone", "1,00,000" in app.last_full_html, False)
r.check("Illustration 6 stays", "Rs. 65,000" in app.last_full_html)
r.check("no call to Gemini", state["calls"], calls)
r.check("card: Illustration 7 removed", "Illustration 7 removed" in chat_text())

# ── 8. "display the full merged HTML" shows the Code tab, costs nothing ─
calls = state["calls"]
ask("display the full merged HTML")
r.check("nothing sent", state["calls"], calls)
r.check("the Code tab is showing", app.current_tab, "code")
app.show_tab("preview")

# ── 9. a click switches Add and Edit for one message ────────────────────
app.entry.insert("1.0", "one more please")
app.refresh_intent()
r.check("reads as add", app.intent_label.cget("text"), "Will add")
app.toggle_intent()
r.check("a click makes it edit", app.intent_label.cget("text"), "Will edit")
app.entry.delete("1.0", "end")
app.intent_override = None

# ── 9b. Gemini may not restyle the block itself ─────────────────────────
state["reply"] = ("<!-- block 1 -->\n"
                  + block(6, "60,000").replace('class="page-block"',
                                               'class="page-block" style="border:1px solid #000"', 1))
ask("fix the final answer in Illustration 6")
r.check("the edit is made", "Rs. 60,000" in app.last_full_html)
r.check("but a border Gemini put on the block is not kept",
        'style="border' in app.last_full_html, False)

# ── 9c. the top bar's book and page are changed here, free ──────────────
calls = state["calls"]
checks = []
real_generate = app.api.generate
app.api.generate = lambda *a, **k: (checks.append(1), real_generate(*a, **k))[1]
ask("change the book name to P.K. Lazar, Pg. 43")
r.check("book and page set", 'P.K. Lazar | Pg. <span class="num">43</span>' in app.last_full_html)
ask("remove the book name and page from the top bar")
r.check("book and page removed", 'class="pgref"' in app.last_full_html, False)
r.check("card: Top bar edited", "Top bar edited" in chat_text())
r.check("neither sent anything to Gemini", state["calls"], calls)

# ── 9d. an edit that changes no figure is not verified again ────────────
kept = app.last_full_html
state["reply"] = "<!-- block 1 -->\n" + app.hs.blocks_of(kept)[0].replace(
    "Find the present value", "Calculate the present value")
ask("change 'Find' to 'Calculate' in Illustration 6")
r.check("the wording edit is made", "Calculate the present value" in app.last_full_html)
r.check("no verification call for it", len(checks), 0)
state["reply"] = "<!-- block 1 -->\n" + app.hs.blocks_of(app.last_full_html)[0].replace(
    "60,000", "61,000")
ask("fix the amount in Illustration 6")
r.check("an edit that changes a figure is verified", len(checks), 1)
app.api.generate = real_generate

# ── 9e. a question Gemini left unnumbered is numbered here, free ────────
calls = state["calls"]
state["reply"] = block(8, "2,00,000").replace(
    '<span class="qno">Illustration <span class="num">8</span>.</span>', "")
ask("solve the next question")
r.check("the missing number is pointed out", "left out the question number" in chat_text())
ask("number it Illustration 8")
r.check("the number is put in", 'Illustration <span class="num">8</span>.' in app.last_full_html)
r.check("only one call — the solve, not the numbering", state["calls"], calls + 1)

# ── 10. reopening the document shows cards, not the whole answers ───────
app.open_document(app.current_chapter, app.current_doc)
text = chat_text()
r.check("reopened chat shows a card", "Illustration" in text and "\U0001F4C4" in text)
r.check("and not the question text", "Find the present value" in text, False)
r.check("the versions come back", app.version_label.cget("text").endswith(f"of {len(versions())}"))

sys.exit(r.finish())
