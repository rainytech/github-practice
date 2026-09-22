"""Chapters and documents on disk: created, renamed, copied, removed."""

import os
import sys
from support import Report, sandbox

home = sandbox()
import library

r = Report("Library — chapters and documents")
LIB = library.Library(os.path.join(home, ".goodwill_tutor"))

cid = LIB.create_chapter("Discounting")
did = LIB.create_document(cid, "Illustration 6")
r.check("the chapter is listed", [c["name"] for c in LIB.list_chapters()], ["Discounting"])
r.check("the document is listed", [d["title"] for d in LIB.list_documents(cid)],
        ["Illustration 6"])

LIB.write_document(cid, did, html="<html>one</html>", blocks=["a"],
                   conversation=[{"role": "user", "parts": [{"text": "hi"}]}])
data = LIB.read_document(cid, did)
r.check("the page is saved", data["html"], "<html>one</html>")
r.check("the blocks are saved", data["meta"]["blocks"], ["a"])
r.check("the conversation is saved", len(data["conversation"]), 1)
r.check("the file is really on disk", os.path.exists(LIB.html_path(cid, did)))

LIB.rename_document(cid, did, "Discounting — Illustration 6 (Pg. 43)")
r.check("renaming keeps the contents", LIB.read_document(cid, did)["html"], "<html>one</html>")
r.check("and shows the new name", [d["title"] for d in LIB.list_documents(cid)],
        ["Discounting — Illustration 6 (Pg. 43)"])

copy = LIB.duplicate_document(cid, did)
r.check("a copy is made", len(LIB.list_documents(cid)), 2)
r.check("the copy has the page too", LIB.read_document(cid, copy)["html"], "<html>one</html>")
LIB.delete_document(cid, copy)
r.check("and can be deleted", len(LIB.list_documents(cid)), 1)

second = LIB.create_chapter("Partnership")
LIB.pin_chapter(second, True)
r.check("a pinned chapter sorts first", LIB.list_chapters()[0]["name"], "Partnership")

LIB.move_document(cid, did, second)
r.check("a document can move chapter", len(LIB.list_documents(second)), 1)
r.check("and leaves the old one empty", len(LIB.list_documents(cid)), 0)

# A name that Windows will not accept as a folder, and one that repeats.
odd = LIB.create_document(second, 'CON: "Ratio / Analysis" *2024*')
r.check("an impossible name still makes a folder", os.path.isdir(
    LIB.document_path(second, odd)))
again = LIB.create_document(second, "Illustration 6")
more = LIB.create_document(second, "Illustration 6")
r.check("two documents may share a title", len({again, more}), 2)

# A folder deleted behind the app's back must not break the list.
import shutil
shutil.rmtree(LIB.document_path(second, more))
r.check("a folder removed by hand is forgotten",
        more in [d["id"] for d in LIB.list_documents(second)], False)

r.check("nothing was written outside the test folder",
        LIB.root.startswith(home))

sys.exit(r.finish())
