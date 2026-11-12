"""Small local web server (127.0.0.1 only) for the catalogue page."""
import json
import logging
import mimetypes
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

from . import backup, config, db, pipeline

log = logging.getLogger("tracker")

STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/style.css": "style.css", "/app.js": "app.js"}


def make_handler(settings):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AudioTracker/1.0"

        # ------------------------------------------------ plumbing
        def log_message(self, fmt, *args):
            log.debug("%s - %s", self.address_string(), fmt % args)

        def _send(self, code, body: bytes, ctype, extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _error(self, message, code=400):
            self._json({"error": message}, code)

        def _file(self, path: Path, ctype=None, extra=None):
            if not path.is_file():
                return self._error("That file is no longer there (was it moved or deleted?).", 404)
            ctype = ctype or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self._send(200, path.read_bytes(), ctype, extra)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except ValueError:
                raise db.UserError("The page sent data that could not be understood. Please reload the page.")

        def _guard(self, fn):
            try:
                fn()
            except db.UserError as exc:
                self._error(str(exc), 400)
            except Exception as exc:
                log.error("Request %s %s failed:\n%s", self.command, self.path, traceback.format_exc())
                self._error(f"Something went wrong: {exc}. Details are in data\\tracker.log", 500)

        # ------------------------------------------------ GET
        def do_GET(self):
            self._guard(self._get)

        def _get(self):
            path = unquote(urlparse(self.path).path)
            if path in STATIC_FILES:
                name = STATIC_FILES[path]
                ctype = {"html": "text/html", "css": "text/css", "js": "text/javascript"}[name.rsplit(".", 1)[1]]
                return self._file(config.WEB_DIR / name, ctype + "; charset=utf-8")
            if path == "/api/items":
                with db.connect(settings.db_path) as con:
                    return self._json({"items": db.list_items(con)})
            if path == "/api/meta":
                with db.connect(settings.db_path) as con:
                    return self._json({
                        "categories": [c["name"] for c in db.categories(con)],
                        "statuses": db.STATUSES,
                        "hidden_statuses": db.HIDDEN_STATUSES,
                        "counts": db.counts(con),
                        "screenshot_folder": str(settings.screenshot_folder),
                        "folder_exists": settings.screenshot_folder.exists(),
                        "data_folder": str(settings.data_dir),
                    })
            if path == "/api/duplicates":
                with db.connect(settings.db_path) as con:
                    return self._json({"duplicates": db.pending_duplicates(con)})
            if path == "/api/scan":
                return self._json(pipeline.status)
            m = re.fullmatch(r"/thumbs/([0-9a-f]{16}\.jpg)", path)
            if m:
                return self._file(settings.thumbs_dir / m.group(1), "image/jpeg")
            m = re.fullmatch(r"/shot/(\d+)", path)
            if m:
                with db.connect(settings.db_path) as con:
                    shot = db.get_screenshot(con, int(m.group(1)))
                if shot is None:
                    return self._error("Screenshot not found.", 404)
                return self._file(Path(shot["path"]))     # read-only: the original is never changed
            m = re.fullmatch(r"/exports/(tracker_export_[0-9_-]+\.json)", path)
            if m:
                return self._file(settings.exports_dir / m.group(1), "application/json",
                                  {"Content-Disposition": f'attachment; filename="{m.group(1)}"'})
            return self._error("Page not found.", 404)

        # ------------------------------------------------ POST
        def do_POST(self):
            self._guard(self._post)

        def _post(self):
            path = urlparse(self.path).path
            if path == "/api/scan":
                started = pipeline.start_background_scan(settings)
                return self._json({"started": started, **pipeline.status})
            m = re.fullmatch(r"/api/items/(\d+)", path)
            if m:
                item_id = int(m.group(1))
                changes = self._body()
                if not isinstance(changes, dict) or not changes:
                    raise db.UserError("Nothing to save.")
                with db.connect(settings.db_path) as con:
                    db.update_item(con, item_id, changes)
                with db.connect(settings.db_path) as con:
                    return self._json({"item": db.get_item(con, item_id)})
            m = re.fullmatch(r"/api/duplicates/(\d+)/(same|different)", path)
            if m:
                with db.connect(settings.db_path) as con:
                    item_id = db.resolve_duplicate(con, int(m.group(1)), m.group(2))
                return self._json({"ok": True, "item_id": item_id})
            if path == "/api/backup":
                target = backup.backup_database(settings)
                return self._json({"ok": True, "path": str(target)})
            if path == "/api/export":
                target = backup.export_json(settings)
                return self._json({"ok": True, "path": str(target), "download": f"/exports/{target.name}"})
            return self._error("Unknown action.", 404)

    return Handler


def create_server(settings, tries=10):
    """Bind to 127.0.0.1 on the configured port, or the next free one."""
    last = None
    for port in range(settings.port, settings.port + tries):
        try:
            return ThreadingHTTPServer(("127.0.0.1", port), make_handler(settings)), port
        except OSError as exc:
            last = exc
    raise OSError(f"Could not start the local web page: ports {settings.port}-{settings.port + tries - 1} "
                  f"are all busy ({last}). Change 'port' in settings.ini.")
