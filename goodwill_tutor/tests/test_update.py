"""The updater: every file listed, and a bad download never replaces a good one."""

import os
import sys
from support import Report, ROOT, sandbox

sandbox()
import update

r = Report("The updater")

# ── nothing in the folder is left off the list ──────────────────────────
on_disk = set()
for folder, names in ((ROOT, os.listdir(ROOT)),
                      (os.path.join(ROOT, "tests"), os.listdir(os.path.join(ROOT, "tests")))):
    prefix = "" if folder == ROOT else "tests/"
    for name in names:
        if name.endswith((".py", ".txt", ".md")) and not name.startswith("."):
            on_disk.add(prefix + name)
listed = set(update.FILES)
r.check("every file in the folder is on the update list", sorted(on_disk - listed), [])
r.check("nothing on the list is missing from the folder", sorted(listed - on_disk), [])

# ── a bad download is refused before it can replace anything ────────────
class Reply:
    def __init__(self, body):
        self.body = body
    def read(self):
        return self.body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

real = update.urllib.request.urlopen


def refused(body, name="x.py"):
    update.urllib.request.urlopen = lambda url, timeout=60: Reply(body)
    try:
        update.fetch(name)
        return False
    except RuntimeError:
        return True
    finally:
        update.urllib.request.urlopen = real

# ── the latest commit, not a copy GitHub kept for five minutes ──────────
update.urllib.request.urlopen = lambda url, timeout=60: Reply(
    b'{"sha": "c6a1c5eb9e60", "commit": {"committer": {"date": "2026-09-23T04:00:57Z"}}}')
r.check("the newest commit is read", update.latest(), ("c6a1c5eb9e60", "2026-09-23T04:00:57Z"))
r.check("files are fetched by that commit",
        update.RAW.format("c6a1c5eb9e60").endswith("/c6a1c5eb9e60/goodwill_tutor/"))
def offline(url, timeout=60):
    raise update.urllib.error.URLError("offline")
update.urllib.request.urlopen = offline
r.check("no answer from GitHub falls back to the branch", update.latest(), (None, None))
update.urllib.request.urlopen = real

r.check("a '404: Not Found' page is refused", refused(b"404: Not Found"))
r.check("an empty file is refused", refused(b""))
r.check("broken Python is refused", refused(b"def broken(:\n"))
r.check("good Python is accepted", refused(b"x = 1\n"), False)
r.check("a text file is not compiled", refused(b"plain words\n", "notes.txt"), False)

# ── a new updater runs in place of the old one ──────────────────────────
folder = sandbox()
update.HERE = folder
open(os.path.join(folder, "update.py"), "wb").write(b"FILES = []  # the old list\n")
ran = []
update.latest = lambda: (None, None)
update.fetch = lambda name: b"FILES = ['new.py']\n"
update.subprocess.run = lambda cmd, cwd=None, env=None: (
    ran.append((cmd[-1], env.get(update.RESTARTED))) or type("Done", (), {"returncode": 0})())
os.environ.pop(update.RESTARTED, None)
code = update.main()
r.check("a changed updater is installed first",
        open(os.path.join(folder, "update.py"), "rb").read(), b"FILES = ['new.py']\n")
r.check("and the new copy is run, with its own list",
        ran, [(os.path.join(folder, "update.py"), "1")])
r.check("the old copy stops there", code, 0)

# ── installing replaces in one step ─────────────────────────────────────
folder = sandbox()
update.HERE = folder
update.install("tests/example.py", b"x = 2\n")
path = os.path.join(folder, "tests", "example.py")
r.check("the file is written", open(path, "rb").read(), b"x = 2\n")
r.check("no half-written file is left behind",
        [n for n in os.listdir(os.path.dirname(path)) if n.endswith(".part")], [])

sys.exit(r.finish())
