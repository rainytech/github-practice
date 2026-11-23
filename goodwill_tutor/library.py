"""
GOODWILL TUITION CENTRE — Document Library
==========================================
Where chapters and documents live on disk.

One folder is one document: its HTML, its PDF, the conversation that produced
it, and its title. Before this, a chat and the document it produced were two
unrelated files with timestamps for names, so nothing could be renamed, paired
or found again.

    library.json                    chapters, their order, which are pinned
    chapters/<chapter>/
        chapter.json                name, created, pinned
        <document>/
            document.json           title, blocks, the model that wrote it
            document.html
            document.pdf            once generated
            conversation.json
            versions/               v1.html, v2.html ... and versions.json

Pure storage: no Tkinter, no network.
"""

import json
import os
import re
import shutil
import unicodedata
from datetime import datetime

SCHEMA = 1

LIBRARY_FILE = "library.json"
CHAPTERS_DIR = "chapters"
CHAPTER_META = "chapter.json"
DOC_META = "document.json"
DOC_HTML = "document.html"
DOC_PDF = "document.pdf"
DOC_CHAT = "conversation.json"
VERSIONS_DIR = "versions"
VERSIONS_INDEX = "versions.json"

MIGRATION_CHAPTER = "Before chapters"


class LibraryError(RuntimeError):
    """Something could not be stored or read, with a message fit for the status bar."""


# ═══════════════════════════════════════════════════════════════
#  NAMES
# ═══════════════════════════════════════════════════════════════

def slugify(name, fallback="untitled"):
    """A folder name that is safe on Windows and still recognisable.

    Windows forbids <>:"/\\|?* and reserves names like CON and NUL, so a
    title is stripped to letters, digits and hyphens rather than escaped.
    """
    text = unicodedata.normalize("NFKD", str(name))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)[:60].strip("-")
    if not text or text.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        return fallback
    return text


def _unique(parent, slug):
    """Append -2, -3 ... until the folder name is free."""
    candidate, n = slug, 1
    while os.path.exists(os.path.join(parent, candidate)):
        n += 1
        candidate = f"{slug}-{n}"
    return candidate


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ═══════════════════════════════════════════════════════════════
#  SAFE JSON
# ═══════════════════════════════════════════════════════════════

def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    """Write through a temporary file, so a crash cannot leave a half-written index."""
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError as exc:
        raise LibraryError(f"Could not save to {path}: {exc}")
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════
#  LIBRARY
# ═══════════════════════════════════════════════════════════════

class Library:
    """Chapters of documents, stored under one root folder."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.chapters_dir = os.path.join(self.root, CHAPTERS_DIR)
        os.makedirs(self.chapters_dir, exist_ok=True)
        self.index_path = os.path.join(self.root, LIBRARY_FILE)
        self.index = _read_json(self.index_path) or {"schema": SCHEMA, "chapters": []}
        self.index.setdefault("schema", SCHEMA)
        self.index.setdefault("chapters", [])
        self._prune()

    # ── index ────────────────────────────────────────────────────────

    def _save_index(self):
        _write_json(self.index_path, self.index)

    def _prune(self):
        """Drop index entries whose folder has been deleted behind our back."""
        alive = [c for c in self.index["chapters"]
                 if os.path.isdir(os.path.join(self.chapters_dir, c["id"]))]
        if len(alive) != len(self.index["chapters"]):
            self.index["chapters"] = alive
            self._save_index()

    def _entry(self, chapter_id):
        for c in self.index["chapters"]:
            if c["id"] == chapter_id:
                return c
        raise LibraryError(f"No such chapter: {chapter_id}")

    def chapter_path(self, chapter_id):
        path = os.path.join(self.chapters_dir, chapter_id)
        if not os.path.isdir(path):
            raise LibraryError(f"No such chapter: {chapter_id}")
        return path

    def document_path(self, chapter_id, doc_id):
        path = os.path.join(self.chapter_path(chapter_id), doc_id)
        if not os.path.isdir(path):
            raise LibraryError(f"No such document: {doc_id}")
        return path

    # ── chapters ─────────────────────────────────────────────────────

    def create_chapter(self, name):
        name = (name or "").strip() or "Untitled chapter"
        cid = _unique(self.chapters_dir, slugify(name, "chapter"))
        path = os.path.join(self.chapters_dir, cid)
        os.makedirs(path)
        _write_json(os.path.join(path, CHAPTER_META),
                    {"id": cid, "name": name, "created": _now(), "pinned": False})
        self.index["chapters"].append(
            {"id": cid, "name": name, "pinned": False, "created": _now()})
        self._save_index()
        return cid

    def list_chapters(self):
        """Pinned first, then newest first. Each carries its document count."""
        out = []
        for c in self.index["chapters"]:
            out.append({
                "id": c["id"],
                "name": c.get("name", c["id"]),
                "pinned": bool(c.get("pinned")),
                "created": c.get("created", ""),
                "documents": len(self.list_documents(c["id"])),
            })
        out.sort(key=lambda c: (not c["pinned"], c["created"]), reverse=False)
        out.sort(key=lambda c: not c["pinned"])
        return out

    def rename_chapter(self, chapter_id, name):
        name = (name or "").strip()
        if not name:
            raise LibraryError("A chapter needs a name.")
        entry = self._entry(chapter_id)
        entry["name"] = name
        meta_path = os.path.join(self.chapter_path(chapter_id), CHAPTER_META)
        meta = _read_json(meta_path, {})
        meta["name"] = name
        _write_json(meta_path, meta)
        self._save_index()

    def pin_chapter(self, chapter_id, pinned=True):
        entry = self._entry(chapter_id)
        entry["pinned"] = bool(pinned)
        self._save_index()

    def delete_chapter(self, chapter_id):
        """Remove a chapter and everything in it. Not recoverable."""
        path = self.chapter_path(chapter_id)
        shutil.rmtree(path, ignore_errors=True)
        self.index["chapters"] = [c for c in self.index["chapters"] if c["id"] != chapter_id]
        self._save_index()

    # ── documents ────────────────────────────────────────────────────

    def create_document(self, chapter_id, title="Untitled"):
        parent = self.chapter_path(chapter_id)
        title = (title or "").strip() or "Untitled"
        did = _unique(parent, slugify(title, "document"))
        path = os.path.join(parent, did)
        os.makedirs(path)
        _write_json(os.path.join(path, DOC_META), {
            "id": did, "title": title, "created": _now(), "updated": _now(),
            "blocks": [], "model": "",
        })
        return did

    def list_documents(self, chapter_id):
        """Newest first."""
        try:
            parent = self.chapter_path(chapter_id)
        except LibraryError:
            return []
        out = []
        for name in sorted(os.listdir(parent)):
            folder = os.path.join(parent, name)
            if not os.path.isdir(folder):
                continue
            meta = _read_json(os.path.join(folder, DOC_META))
            if not meta:
                continue
            out.append({
                "id": meta.get("id", name),
                "title": meta.get("title", name),
                "created": meta.get("created", ""),
                "updated": meta.get("updated", ""),
                "blocks": len(meta.get("blocks", [])),
                "has_pdf": os.path.exists(os.path.join(folder, DOC_PDF)),
                "has_html": os.path.exists(os.path.join(folder, DOC_HTML)),
            })
        out.sort(key=lambda d: d.get("updated") or d.get("created") or "", reverse=True)
        return out

    def read_document(self, chapter_id, doc_id):
        """Everything needed to reopen a document: metadata, HTML, conversation."""
        folder = self.document_path(chapter_id, doc_id)
        meta = _read_json(os.path.join(folder, DOC_META), {}) or {}
        html_path = os.path.join(folder, DOC_HTML)
        html = ""
        if os.path.exists(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as fh:
                    html = fh.read()
            except OSError as exc:
                raise LibraryError(f"Could not read the document: {exc}")
        return {
            "meta": meta,
            "html": html,
            "conversation": _read_json(os.path.join(folder, DOC_CHAT), []) or [],
            "folder": folder,
            "html_path": html_path if html else None,
            "pdf_path": (os.path.join(folder, DOC_PDF)
                         if os.path.exists(os.path.join(folder, DOC_PDF)) else None),
        }

    def write_document(self, chapter_id, doc_id, html=None, blocks=None,
                       conversation=None, title=None, model=None):
        """Save any part of a document. Anything left as None is untouched."""
        folder = self.document_path(chapter_id, doc_id)
        meta_path = os.path.join(folder, DOC_META)
        meta = _read_json(meta_path, {}) or {}
        if title is not None:
            meta["title"] = title.strip() or meta.get("title", "Untitled")
        if blocks is not None:
            meta["blocks"] = list(blocks)
        if model:
            meta["model"] = model
        meta.setdefault("id", doc_id)
        meta.setdefault("created", _now())
        meta["updated"] = _now()
        _write_json(meta_path, meta)

        if html is not None:
            try:
                with open(os.path.join(folder, DOC_HTML), "w", encoding="utf-8") as fh:
                    fh.write(html)
            except OSError as exc:
                raise LibraryError(f"Could not save the document: {exc}")
        if conversation is not None:
            _write_json(os.path.join(folder, DOC_CHAT), conversation)
        return meta

    def rename_document(self, chapter_id, doc_id, title):
        title = (title or "").strip()
        if not title:
            raise LibraryError("A document needs a title.")
        # The folder name stays put: renaming it would break any PDF the
        # teacher has already opened or linked from elsewhere.
        return self.write_document(chapter_id, doc_id, title=title)

    def duplicate_document(self, chapter_id, doc_id):
        source = self.document_path(chapter_id, doc_id)
        meta = _read_json(os.path.join(source, DOC_META), {}) or {}
        title = f"{meta.get('title', 'Untitled')} (copy)"
        parent = self.chapter_path(chapter_id)
        new_id = _unique(parent, slugify(title, "document"))
        target = os.path.join(parent, new_id)
        shutil.copytree(source, target)
        meta.update({"id": new_id, "title": title, "created": _now(), "updated": _now()})
        _write_json(os.path.join(target, DOC_META), meta)
        # A copy has not been printed yet.
        stale_pdf = os.path.join(target, DOC_PDF)
        if os.path.exists(stale_pdf):
            try:
                os.remove(stale_pdf)
            except OSError:
                pass
        return new_id

    def delete_document(self, chapter_id, doc_id):
        shutil.rmtree(self.document_path(chapter_id, doc_id), ignore_errors=True)

    def move_document(self, chapter_id, doc_id, to_chapter_id):
        source = self.document_path(chapter_id, doc_id)
        parent = self.chapter_path(to_chapter_id)
        new_id = _unique(parent, doc_id)
        shutil.move(source, os.path.join(parent, new_id))
        meta_path = os.path.join(parent, new_id, DOC_META)
        meta = _read_json(meta_path, {}) or {}
        meta["id"] = new_id
        _write_json(meta_path, meta)
        return new_id

    def pdf_path(self, chapter_id, doc_id):
        """Where a PDF for this document belongs, whether or not it exists yet."""
        return os.path.join(self.document_path(chapter_id, doc_id), DOC_PDF)

    def html_path(self, chapter_id, doc_id):
        return os.path.join(self.document_path(chapter_id, doc_id), DOC_HTML)

    # ── versions ─────────────────────────────────────────────────────
    # Every answer keeps the page as it stood after it, so an answer that
    # spoils the page is one click from undone. Nothing is ever overwritten.

    def _versions_dir(self, chapter_id, doc_id):
        return os.path.join(self.document_path(chapter_id, doc_id), VERSIONS_DIR)

    def list_versions(self, chapter_id, doc_id):
        """[{"n", "label", "when"}], oldest first."""
        index = os.path.join(self._versions_dir(chapter_id, doc_id), VERSIONS_INDEX)
        return list(_read_json(index, []) or [])

    def save_version(self, chapter_id, doc_id, html, label=""):
        """Keep this page as the next version. Returns its number."""
        folder = self._versions_dir(chapter_id, doc_id)
        versions = self.list_versions(chapter_id, doc_id)
        n = (versions[-1]["n"] if versions else 0) + 1
        try:
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, f"v{n}.html"), "w", encoding="utf-8") as fh:
                fh.write(html or "")
        except OSError as exc:
            raise LibraryError(f"Could not keep this version: {exc}")
        versions.append({"n": n, "label": (label or "").strip(), "when": _now()})
        _write_json(os.path.join(folder, VERSIONS_INDEX), versions)
        return n

    def read_version(self, chapter_id, doc_id, n):
        path = os.path.join(self._versions_dir(chapter_id, doc_id), f"v{int(n)}.html")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            raise LibraryError(f"Version {n} could not be read: {exc}")

    # ── migration ────────────────────────────────────────────────────

    def migrate(self, conversations_dir, solutions_dir):
        """Bring flat, timestamped work into a chapter. Originals are left alone.

        Old layout paired nothing: a chat was <stamp>.json in one folder and the
        document it produced was goodwill_<stamp>.html in another. They are
        matched back together on the YYYYMMDD_HHMMSS in their names.

        Returns a short report. Running it twice imports nothing the second time.
        """
        report = {"documents": 0, "paired": 0, "skipped": 0, "chapter": None}

        already = any(c.get("name") == MIGRATION_CHAPTER for c in self.index["chapters"])
        if already:
            return report

        stamp_re = re.compile(r"(\d{8}_\d{6})")

        chats = {}
        if os.path.isdir(conversations_dir):
            for name in os.listdir(conversations_dir):
                if not name.endswith(".json"):
                    continue
                m = stamp_re.search(name)
                if m:
                    chats[m.group(1)] = os.path.join(conversations_dir, name)

        pages = {}
        if os.path.isdir(solutions_dir):
            for name in os.listdir(solutions_dir):
                if not name.lower().endswith((".html", ".htm")):
                    continue
                m = stamp_re.search(name)
                if m:
                    pages.setdefault(m.group(1), os.path.join(solutions_dir, name))

        if not chats and not pages:
            return report

        cid = self.create_chapter(MIGRATION_CHAPTER)
        report["chapter"] = cid

        for stamp in sorted(set(chats) | set(pages), reverse=True):
            chat_path, page_path = chats.get(stamp), pages.get(stamp)
            data = _read_json(chat_path, {}) if chat_path else {}
            title = (data.get("title") or "").strip()
            if not title:
                title = f"Saved {stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
            html = ""
            if page_path:
                try:
                    with open(page_path, "r", encoding="utf-8", errors="replace") as fh:
                        html = fh.read()
                except OSError:
                    report["skipped"] += 1
                    continue
            if not html and not data:
                report["skipped"] += 1
                continue

            did = self.create_document(cid, title[:60])
            self.write_document(
                cid, did,
                html=html or None,
                blocks=data.get("blocks") or None,
                conversation=data.get("history") or None,
                title=title[:60],
            )
            report["documents"] += 1
            if chat_path and page_path:
                report["paired"] += 1

        if report["documents"] == 0:
            self.delete_chapter(cid)
            report["chapter"] = None
        return report
