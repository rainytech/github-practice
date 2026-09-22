"""Shared scaffolding for the tests.

Every test runs against a private folder, with no network and no window, so
nothing here can touch your real chapters, spend money, or need watching.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sandbox():
    """A throwaway home folder, so the real ~/.goodwill_tutor is never opened."""
    home = tempfile.mkdtemp(prefix="goodwill_test_")
    os.environ["HOME"] = home
    os.environ["USERPROFILE"] = home
    os.environ["GEMINI_API_KEY"] = "test-key-never-sent"
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    return home


def gui(stream=None, verdict="VERIFIED\nChecked.", models=None):
    """Load the app with the network stubbed out and the window not running.

    Returns the module, so a test can call its functions directly.
    """
    sandbox()
    import tkinter
    import gemini_api as api

    api.list_models = lambda timeout=30: models or [("test-model", "Test model")]
    api.generate = lambda *a, **k: (verdict, 10, 5, 0)
    if stream is not None:
        api.stream_generate = stream
    tkinter.Tk.mainloop = lambda self, *a, **k: None

    import goodwill_tutor as app
    app.SETTINGS["auto_pdf"] = False        # tests that want it turn it back on
    return app


def wait_for_models(app, seconds=10):
    """The model list arrives on a thread; sending before it lands is refused."""
    import time
    limit = time.time() + seconds
    while not app.selected_model() and time.time() < limit:
        app.root.update()
        time.sleep(0.05)
    return app.selected_model()


def settle(app, seconds=30):
    """Pump the window until the answer is finished."""
    import time
    limit = time.time() + seconds
    while app.busy and time.time() < limit:
        app.root.update()
        time.sleep(0.02)
    for _ in range(20):
        app.root.update()
        time.sleep(0.01)


class Report:
    """Collects checks and prints them, one per line."""

    def __init__(self, title):
        self.title = title
        self.rows = []

    def check(self, name, got, want=True):
        ok = got == want
        self.rows.append((ok, name, "" if ok else f"got {got!r}, wanted {want!r}"))
        return ok

    def finish(self):
        print(f"\n{self.title}")
        for ok, name, detail in self.rows:
            print(f"  {'PASS' if ok else 'FAIL'}  {name:<44}{detail}")
        failed = [r for r in self.rows if not r[0]]
        print(f"  {len(self.rows) - len(failed)} of {len(self.rows)} passed")
        return 1 if failed else 0
