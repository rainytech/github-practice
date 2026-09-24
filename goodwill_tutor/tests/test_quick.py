"""The free edits: each one made by the app, none sent to the model."""

import sys
from support import Report, gui, settle, wait_for_models


def block(n, amount):
    return ('<div class="page-block"><div class="top-bar"><span class="title">DISCOUNTING</span></div>'
            f'<div class="q"><span class="qno">Illustration <span class="num">{n}</span>.</span>'
            f'<span>Find the present value of Rs. {amount}.</span></div>'
            '<div class="sol-label">Solution:-</div><div class="wn-label">Working Notes:-</div>'
            '<table class="wn"><tr><td>F</td><td class="right">Rs. 66,550</td></tr></table>'
            '<div class="rule-note">&#9658; A rule.</div>'
            f'<div class="final-ans">Present Value = Rs. {amount}</div></div>')


state = {"reply": block(6, "50,000"), "calls": 0}


def stream(conv, model, system_prompt="", on_chunk=None, stop_event=None, **kw):
    state["calls"] += 1
    if on_chunk:
        on_chunk(state["reply"])
    return state["reply"], 4000, 900, 0


r = Report("The free edits")
app = gui(stream=stream)
r.check("a model is available", bool(wait_for_models(app)))


def ask(what):
    app.entry.insert("1.0", what)
    app.refresh_intent()
    label = app.intent_label.cget("text")
    app.send_message()
    settle(app)
    return label


def page():
    return app.last_full_html


def chat():
    return app.chat.get("1.0", "end")


ask("solve this")
state["reply"] = block(7, "1,00,000")
ask("add one more question")
paid = state["calls"]
versions = lambda: len(app.LIB.list_versions(app.current_chapter, app.current_doc))

r.check("1. the label says Free", ask("replace 'Find' with 'Calculate'"), "Free")
r.check("   replace changes every question", page().count("Calculate the present value"), 2)
ask("replace 'Calculate' with 'Find' in Illustration 7")
r.check("   replace in one question only", page().count("Calculate the present value"), 1)
before = versions()
ask("undo")
r.check("2. undo goes back one version", page().count("Calculate the present value"), 2)
ask("redo")
r.check("3. redo comes forward again", page().count("Calculate the present value"), 1)
ask("change Rs. to ₹")
r.check("4. Rs. becomes ₹", "₹ 66,550" in page() and "Rs. 66,550" not in page())
ask("change ₹ to Rs.")
r.check("5. and back to Rs.", "Rs. 66,550" in page() and "₹" not in page().split("<body")[1])
ask("change the title to admission of a partner")
r.check("6. the title changes", page().count(">ADMISSION OF A PARTNER<"), 2)
ask("add (CBSE 2019) to Illustration 6")
r.check("7. a source tag is added", '<span class="source">(CBSE 2019)</span>' in page())
ask("remove the source")
r.check("8. and removed", 'class="source"' in page(), False)
ask("add answer: Rs. 1,00,000")
r.check("9. an answer line goes under the last question", "[Ans.: Rs. 1,00,000]" in page())
ask("add hint to Illustration 6: use 1.10 × 1.10")
r.check("10. a hint goes under Illustration 6", "[Hint: use 1.10 × 1.10]" in page())
ask("remove the answer line")
r.check("11. the answer line goes", 'class="ans"' in page(), False)
r.check("    and the final answer stays", 'class="final-ans"' in page())
ask("remove the hint")
r.check("12. the hint goes", 'class="hint"' in page(), False)
ask("change the final answer to The present value is Rs. 1,00,000.")
r.check("13. the final answer is replaced", "∴ The present value is Rs. 1,00,000." in page())
ask("remove the rule note")
r.check("14. the rule notes go", 'class="rule-note"' in page(), False)
ask("move Illustration 7 above Illustration 6")
first = app.hs.blocks_of(page())[0]
r.check("15. Illustration 7 moves to the top", app.hs.question_label(first), "Illustration 7")
ask("move the last question to the top")
r.check("16. and the last question back up",
        app.hs.question_label(app.hs.blocks_of(page())[0]), "Illustration 6")
ask("renumber the questions from 1")
r.check("17. renumbered 1 and 2",
        [app.hs.question_label(b) for b in app.hs.blocks_of(page())], ["Illustration 1", "Illustration 2"])
ask("remove the top bar from Illustration 2")
r.check("18. one top bar is removed", page().count('class="top-bar"'), 1)
ask("remove the solution from Illustration 2")
two = app.hs.blocks_of(page())[1]
r.check("19. a worksheet: the solution goes", 'class="sol-label"' in two or "<table" in two, False)
r.check("    and the question stays", "Find the present value" in two)
r.check("    the other question keeps its working", 'class="sol-label"' in app.hs.blocks_of(page())[0])
ask("rename the document to Discounting — Set 1")
title = next(d["title"] for d in app.LIB.list_documents(app.current_chapter) if d["id"] == app.current_doc)
r.check("20. the document is renamed", title, "Discounting — Set 1")
ask("show the code")
r.check("21. show the code", app.current_tab, "code")
ask("show the preview")
r.check("22. show the preview", app.current_tab, "preview")
ask("help")
r.check("23. help lists the free edits", "Free — done by the app" in chat())
r.check("a mistyped word is reported, not guessed", "Nothing changed" in (ask("replace 'Zebra' with 'x'") and chat()))

# a click on the label with nothing typed must not switch the next message
app.entry.delete("1.0", "end")
app.toggle_intent()
r.check("a click on an empty box switches nothing", app.intent_override, None)
r.check("help is free after that click", ask("help"), "Free")
app.entry.insert("1.0", "undo")
app.toggle_intent()
r.check("undo stays free even when switched", app.current_intent(), "free")
app.entry.delete("1.0", "end")
app.refresh_intent()

# ── copying from the chat ───────────────────────────────────────────────
at = app.chat.search("make the pdf", "1.0", "end")
app.chat.tag_add("sel", at, f"{at}+12c")
app.copy_chat()
r.check("the selection is drawn above the message shading",
        app.chat.tag_names()[-1] == "sel" or app.chat.tag_names().index("sel") > app.chat.tag_names().index("note_msg"))
r.check("Ctrl+C copies the selection", app.root.clipboard_get(), "make the pdf")
app.chat_to_message()
r.check("'Put in my message' fills the typing box", app.entry.get("1.0", "end").strip(), "make the pdf")
r.check("and it reads as Free", app.intent_label.cget("text"), "Free")
app.entry.delete("1.0", "end")
app.refresh_intent()

r.check("none of it was sent to Gemini", state["calls"], paid)
r.check("each change kept a version", versions() > before)
r.check("a real edit still goes to Gemini", ask("fix the working in Illustration 1"), "Will edit")

sys.exit(r.finish())
