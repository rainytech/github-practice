"""TeachMark — remembers where you stopped teaching each student.

Paste a screenshot of your PDF viewer after class; TeachMark reads the file
path, page and heading from it and shows them before the next class.
Fully offline. Never opens or controls the PDF viewer.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path, PureWindowsPath

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QEventLoop, QIODevice, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication, QImage, QKeySequence, QPalette, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import reader
from ocr_engine import OcrError
from storage import Store, data_dir

APP = "TeachMark"
VERSION = "1.3"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
SCREENSHOTS = [Path.home() / "Pictures" / "Screenshots"]
if os.environ.get("OneDrive"):
    SCREENSHOTS.append(Path(os.environ["OneDrive"]) / "Pictures" / "Screenshots")


def screenshot_dirs() -> list[Path]:
    return [d for d in SCREENSHOTS if d.is_dir()]

STYLE = """
QWidget { font-size: 11pt; }
QPushButton { padding: 6px 14px; }
QPushButton#big { font-size: 13pt; font-weight: bold; padding: 10px 18px;
                  background: #0057B8; color: white; border-radius: 6px; }
QPushButton#big:hover { background: #00469a; }
QLabel#name { font-size: 18pt; font-weight: bold; color: #00008B; }
QLabel#page { font-size: 24pt; font-weight: bold; color: #CC0000; }
QLabel#point { font-size: 14pt; font-weight: bold; color: #6A0DAD; }
QLabel#key { color: #555; }
QFrame#card { background: #FAF9F5; border: 1px solid #DDD8C8; border-radius: 8px; }
QMainWindow, QDialog, QStatusBar { background: #F0EEE6; }
QListWidget, QTableWidget { background: #FAF9F5; border: 1px solid #DDD8C8; }
QListWidget::item:selected { background: #E3DACB; color: #000; }
QHeaderView::section { background: #EAE6DA; border: none; border-right: 1px solid #DDD8C8; padding: 4px; }
"""

# Claude-style warm beige
BEIGE, PAPER = "#F0EEE6", "#FAF9F5"


def log_error(e: BaseException) -> None:
    try:
        with open(data_dir() / "error.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("".join(traceback.format_exception(type(e), e, e.__traceback__)))
    except OSError:
        pass


def pretty_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    return f"{dt.day} {dt:%b %Y}, {dt.hour % 12 or 12}:{dt:%M} {dt:%p}"


def qimage_to_pil(qimg: QImage) -> Image.Image:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    qimg.save(buf, "PNG")
    return Image.open(io.BytesIO(buf.data().data())).convert("RGB")


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    b = io.BytesIO()
    img.save(b, "PNG")
    pm = QPixmap()
    pm.loadFromData(QByteArray(b.getvalue()))
    return pm


def show_in_explorer(path: str) -> None:
    """Opens Explorer with the PDF highlighted. Does not open the PDF itself."""
    if os.name == "nt" and os.path.isfile(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        folder = os.path.dirname(path)
        if os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))


# ====================================================================== dialogs

class ImageDialog(QDialog):
    def __init__(self, pixmap: QPixmap, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        lbl = QLabel()
        lbl.setPixmap(pixmap)
        area = QScrollArea()
        area.setWidget(lbl)
        lay = QVBoxLayout(self)
        lay.addWidget(area)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(pixmap.width() + 40, screen.width() - 80), min(pixmap.height() + 40, screen.height() - 80))


class ReviewDialog(QDialog):
    """Shows what was read from the screenshot; lets the teacher fix anything, then save."""

    def __init__(self, image: Image.Image, r: reader.Reading, names: list[str], suggested: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save where you stopped")
        self.image = image

        preview = QLabel()
        preview.setPixmap(pil_to_pixmap(image).scaledToWidth(560, Qt.TransformationMode.SmoothTransformation))
        preview.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.student = QComboBox()
        self.student.setEditable(True)
        self.student.addItems(names)
        self.student.setCurrentText(suggested)
        self.student.lineEdit().setPlaceholderText("Choose or type student name")

        self.path = QLineEdit(r.path)
        self.path.setMinimumWidth(420)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path)
        path_row.addWidget(browse)
        self.path_status = QLabel()
        self.path.textChanged.connect(self._check_path)

        self.page = QSpinBox()
        self.page.setRange(0, 99999)
        self.page.setSpecialValueText("?")
        self.page.setValue(r.page or 0)
        self.page.valueChanged.connect(self._check_page)
        self.total = QSpinBox()
        self.total.setRange(0, 99999)
        self.total.setSpecialValueText("?")
        self.total.setValue(r.total or 0)
        page_row = QHBoxLayout()
        page_row.addWidget(self.page)
        page_row.addWidget(QLabel("/"))
        page_row.addWidget(self.total)
        self.page_hint = QLabel("← please type the page")
        self.page_hint.setStyleSheet("color: #CC0000; font-weight: bold;")
        page_row.addWidget(self.page_hint)
        page_row.addStretch()

        self.point = QComboBox()
        self.point.setEditable(True)
        self.point.addItems(r.headings)
        self.point.lineEdit().setPlaceholderText("e.g. Illustration 9")
        self.chapter = QLineEdit(r.chapter)
        self.note = QLineEdit()
        self.note.setPlaceholderText("Optional — e.g. continue from Working Note 2")

        form = QFormLayout()
        form.addRow("Student", self.student)
        form.addRow("PDF file", path_row)
        form.addRow("", self.path_status)
        form.addRow("Page", page_row)
        form.addRow("Stopped at", self.point)
        form.addRow("Chapter", self.chapter)
        form.addRow("Note", self.note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        right = QVBoxLayout()
        right.addLayout(form)
        right.addStretch()
        right.addWidget(buttons)
        lay = QHBoxLayout(self)
        lay.addWidget(preview)
        lay.addLayout(right)
        self._check_path()
        self._check_page()

    def _check_page(self):
        self.page_hint.setVisible(self.page.value() == 0)

    def _check_path(self):
        ok = os.path.isfile(self.path.text().strip())
        self.path_status.setText("✔ Found on this computer" if ok else "✘ Not found — correct it or use Browse…")
        self.path_status.setStyleSheet(f"color: {'#1B7F3B' if ok else '#CC0000'};")

    def _browse(self):
        start = os.path.dirname(self.path.text()) or (reader.default_roots() or [""])[0]
        f, _ = QFileDialog.getOpenFileName(self, "Choose the PDF", start, "PDF files (*.pdf)")
        if f:
            self.path.setText(os.path.normpath(f))
            n = reader.pdf_page_count(f)
            if n:
                self.total.setValue(n)

    def _save(self):
        if not self.student.currentText().strip():
            QMessageBox.warning(self, APP, "Please choose or type the student's name.")
            return
        if not self.path.text().strip():
            QMessageBox.warning(self, APP, "Please enter the PDF file.")
            return
        self.accept()

    def values(self) -> dict:
        return dict(
            student=self.student.currentText().strip(),
            pdf_path=self.path.text().strip(),
            page=self.page.value() or None,
            total=self.total.value() or None,
            point=self.point.currentText().strip(),
            chapter=self.chapter.text().strip(),
            note=self.note.text().strip(),
        )


# ====================================================================== main window

class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.setWindowTitle(f"{APP} {VERSION} — Where I Stopped Teaching")
        self.setAcceptDrops(True)
        self.resize(1100, 680)

        # --- top bar
        paste = QPushButton("📋  Paste Screenshot   (Ctrl+V)")
        paste.setObjectName("big")
        paste.clicked.connect(self.paste)
        latest = QPushButton("🖼  Latest Screenshot")
        latest.setObjectName("big")
        latest.setToolTip("Loads the newest picture from your Screenshots folder")
        latest.clicked.connect(self.latest_screenshot)
        open_img = QPushButton("Open Image…")
        open_img.clicked.connect(self.open_image)
        hint = QLabel("After class: Win+Shift+S → Ctrl+V here,\nor Win+PrtScn → Latest Screenshot")
        hint.setObjectName("key")
        top = QHBoxLayout()
        top.addWidget(paste)
        top.addWidget(latest)
        top.addWidget(open_img)
        top.addSpacing(12)
        top.addWidget(hint)
        top.addStretch()
        QShortcut(QKeySequence.StandardKey.Paste, self, activated=self.paste)

        # --- student list
        self.list = QListWidget()
        self.list.setMinimumWidth(300)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(lambda *_: self.show_student())
        rename = QPushButton("Rename")
        rename.clicked.connect(self.rename)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete)
        left_btns = QHBoxLayout()
        left_btns.addWidget(rename)
        left_btns.addWidget(delete)
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Students</b>"))
        left.addWidget(self.list)
        left.addLayout(left_btns)

        # --- detail card
        self.name = QLabel()
        self.name.setObjectName("name")
        self.folder = QLabel()
        self.file = QLabel()
        for w in (self.folder, self.file):
            w.setWordWrap(True)
            w.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.page = QLabel()
        self.page.setObjectName("page")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(260)
        self.progress.setFormat("%p% done")
        self.point = QLabel()
        self.point.setObjectName("point")
        self.point.setWordWrap(True)
        self.chapter = QLabel()
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.saved = QLabel()

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        rows = [("Folder", self.folder), ("File", self.file), ("Page", None), ("Stopped at", self.point),
                ("Chapter", self.chapter), ("Note", self.note), ("Saved", self.saved)]
        for i, (key, widget) in enumerate(rows):
            k = QLabel(key)
            k.setObjectName("key")
            grid.addWidget(k, i, 0, Qt.AlignmentFlag.AlignTop)
            if widget is None:
                pr = QHBoxLayout()
                pr.addWidget(self.page)
                pr.addSpacing(16)
                pr.addWidget(self.progress)
                pr.addStretch()
                grid.addLayout(pr, i, 1)
            else:
                grid.addWidget(widget, i, 1)

        self.btn_folder = QPushButton("Show in Folder")
        self.btn_folder.clicked.connect(lambda: show_in_explorer(self.current_stop["pdf_path"]))
        self.btn_copy = QPushButton("Copy File Path")
        self.btn_copy.clicked.connect(self.copy_path)
        self.btn_shot = QPushButton("View Screenshot")
        self.btn_shot.clicked.connect(lambda: self.view_shot(self.current_stop))
        card_btns = QHBoxLayout()
        for b in (self.btn_folder, self.btn_copy, self.btn_shot):
            card_btns.addWidget(b)
        card_btns.addStretch()

        card = QFrame()
        card.setObjectName("card")
        card_lay = QVBoxLayout(card)
        card_lay.addWidget(self.name)
        card_lay.addLayout(grid)
        card_lay.addLayout(card_btns)

        self.history = QTableWidget(0, 4)
        self.history.setHorizontalHeaderLabels(["Saved", "File", "Page", "Stopped at"])
        self.history.verticalHeader().hide()
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.history.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history.cellDoubleClicked.connect(lambda row, _c: self.view_shot(self.history_rows[row]))

        self.empty = QLabel("No students yet.\n\nAfter your next class, take a screenshot of the PDF window,\n"
                            "then press Ctrl+V here or click Latest Screenshot.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setObjectName("key")

        self.detail = QWidget()
        right = QVBoxLayout(self.detail)
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(card)
        right.addWidget(QLabel("<b>Last 5 stops</b>  <span style='color:#777'>(double-click to see screenshot)</span>"))
        right.addWidget(self.history)

        body = QHBoxLayout()
        body.addLayout(left)
        body.addWidget(self.detail, 1)
        body.addWidget(self.empty, 1)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addLayout(top)
        lay.addLayout(body)
        self.setCentralWidget(root)

        self.current_stop = None
        self.history_rows = []
        self.refresh()

    # ---------------------------------------------------------------- list / detail
    def refresh(self, select: str | None = None):
        keep = select or (self.list.currentItem().data(Qt.ItemDataRole.UserRole + 1) if self.list.currentItem() else None)
        self.list.blockSignals(True)
        self.list.clear()
        for s in self.store.students():
            sub = f"p. {s['page'] or '?'} / {s['total'] or '?'}  ·  {pretty_date(s['saved'])}" if s["saved"] else "no stops yet"
            item = QListWidgetItem(f"{s['name']}\n    {sub}")
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, s["name"])
            self.list.addItem(item)
            if keep and s["name"].lower() == keep.lower():
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        self.list.blockSignals(False)
        self.show_student()

    def show_student(self):
        item = self.list.currentItem()
        has = item is not None
        self.detail.setVisible(has)
        self.empty.setVisible(not has)
        if not has:
            return
        self.name.setText(item.data(Qt.ItemDataRole.UserRole + 1))
        stops = self.store.stops(item.data(Qt.ItemDataRole.UserRole))
        self.current_stop = stops[0] if stops else None
        self.history_rows = stops
        s = self.current_stop
        for b in (self.btn_folder, self.btn_copy):
            b.setEnabled(s is not None)
        self.btn_shot.setEnabled(bool(s and self.store.shot_path(s["shot"])))
        if s:
            p = PureWindowsPath(s["pdf_path"])
            exists = os.path.isfile(s["pdf_path"])
            self.folder.setText(p.parent.name)
            self.folder.setToolTip(str(p.parent))
            self.file.setText(p.name + ("" if exists else "   ⚠ file moved or renamed"))
            self.page.setText(f"{s['page'] or '?'} / {s['total'] or '?'}")
            self.progress.setVisible(bool(s["page"] and s["total"]))
            if s["page"] and s["total"]:
                self.progress.setMaximum(s["total"])
                self.progress.setValue(min(s["page"], s["total"]))
            self.point.setText(s["point"] or "—")
            self.chapter.setText(s["chapter"] or "—")
            self.note.setText(s["note"] or "—")
            self.saved.setText(pretty_date(s["saved"]))
        else:
            for w in (self.folder, self.file, self.page, self.point, self.chapter, self.note, self.saved):
                w.setText("—")
            self.progress.hide()

        self.history.setRowCount(len(stops))
        for r, st in enumerate(stops):
            vals = [pretty_date(st["saved"]), PureWindowsPath(st["pdf_path"]).name,
                    f"{st['page'] or '?'} / {st['total'] or '?'}", st["point"] or ""]
            for c, v in enumerate(vals):
                self.history.setItem(r, c, QTableWidgetItem(v))

    def selected(self):
        item = self.list.currentItem()
        return (item.data(Qt.ItemDataRole.UserRole), item.data(Qt.ItemDataRole.UserRole + 1)) if item else (None, None)

    def rename(self):
        sid, name = self.selected()
        if sid is None:
            return
        new, ok = QInputDialog.getText(self, APP, "New name:", text=name)
        if ok and new.strip() and new.strip() != name:
            try:
                self.store.rename_student(sid, new)
            except Exception:
                QMessageBox.warning(self, APP, f"A student called '{new}' already exists.")
                return
            self.refresh(select=new.strip())

    def delete(self):
        sid, name = self.selected()
        if sid is None:
            return
        if QMessageBox.question(self, APP, f"Delete {name} and all saved stops?") == QMessageBox.StandardButton.Yes:
            self.store.delete_student(sid)
            self.refresh()

    def copy_path(self):
        if self.current_stop:
            QGuiApplication.clipboard().setText(self.current_stop["pdf_path"])
            self.statusBar().showMessage("File path copied.", 3000)

    def view_shot(self, stop):
        p = self.store.shot_path(stop["shot"]) if stop else None
        if p:
            ImageDialog(QPixmap(str(p)), f"Screenshot — {pretty_date(stop['saved'])}", self).exec()

    # ---------------------------------------------------------------- screenshot input
    def paste(self):
        md = QGuiApplication.clipboard().mimeData()
        if md.hasImage():
            self.process(qimage_to_pil(QGuiApplication.clipboard().image()))
            return
        for url in md.urls():
            if url.toLocalFile().lower().endswith(IMAGE_EXT):
                self.process(Image.open(url.toLocalFile()).convert("RGB"))
                return
        QMessageBox.information(self, APP, "No screenshot on the clipboard.\n\n"
                                "Press Win+Shift+S, select the PDF window, then press Ctrl+V here.")

    def latest_screenshot(self):
        files = [p for d in screenshot_dirs() for p in d.iterdir()
                 if p.is_file() and p.suffix.lower() in IMAGE_EXT]
        if not files:
            QMessageBox.information(self, APP, f"No screenshots found in:\n{SCREENSHOTS[0]}")
            return
        newest = max(files, key=lambda p: p.stat().st_mtime)
        self.process(Image.open(newest).convert("RGB"))

    def open_image(self):
        start = str(screenshot_dirs()[0]) if screenshot_dirs() else ""
        f, _ = QFileDialog.getOpenFileName(self, "Open screenshot", start, "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if f:
            self.process(Image.open(f).convert("RGB"))

    def dragEnterEvent(self, e):
        if e.mimeData().hasImage() or any(u.toLocalFile().lower().endswith(IMAGE_EXT) for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        for url in md.urls():
            if url.toLocalFile().lower().endswith(IMAGE_EXT):
                self.process(Image.open(url.toLocalFile()).convert("RGB"))
                return
        if md.hasImage():
            self.process(qimage_to_pil(QImage(md.imageData())))

    def process(self, image: Image.Image):
        # OCR runs on a worker thread: Windows OCR deadlocks on Qt's UI (STA) thread,
        # and the window stays responsive while reading.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.statusBar().showMessage("Reading screenshot…")
        known = self.store.known_paths()
        future = self.pool.submit(reader.read_image, image, known, log_dir=str(self.store.dir))
        deadline = time.monotonic() + 60
        while not future.done() and time.monotonic() < deadline:
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents, 50)
            time.sleep(0.02)
        QApplication.restoreOverrideCursor()
        self.statusBar().clearMessage()

        r, error = reader.Reading(), ""
        if not future.done():
            self.pool = ThreadPoolExecutor(max_workers=1)  # leave the stuck worker behind
            error = "Reading the screenshot took too long. Please fill in the details yourself."
        elif future.exception():
            e = future.exception()
            log_error(e)
            error = str(e) if isinstance(e, OcrError) else f"Could not read the screenshot ({e}).\nPlease fill in the details yourself."
        else:
            r = future.result()
        if error:
            QMessageBox.warning(self, APP, error)

        names = [s["name"] for s in self.store.students()]
        suggested = reader.suggest_student(r, names, self.store.last_path_owner())
        dlg = ReviewDialog(image, r, names, suggested or "", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.values()
            self.store.add_stop(image=image, **v)
            self.refresh(select=v["student"])
            self.statusBar().showMessage(f"Saved: {v['student']} — page {v['page'] or '?'}", 4000)


def main():
    sys.excepthook = lambda t, e, tb: log_error(e)
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setFont(QFont("Segoe UI", 10))
    pal = app.palette()
    for role, color in ((QPalette.ColorRole.Window, BEIGE), (QPalette.ColorRole.Base, PAPER),
                        (QPalette.ColorRole.AlternateBase, BEIGE), (QPalette.ColorRole.Button, PAPER)):
        pal.setColor(role, QColor(color))
    app.setPalette(pal)
    app.setStyleSheet(STYLE)
    win = MainWindow(Store())
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
