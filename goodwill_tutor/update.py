"""Bring this folder up to date with the latest version, then check it.

    python update.py

Every file the app and its tests need is fetched, each one checked before it
replaces the old copy, and then the tests run. A download that fails leaves the
file you had untouched — never half a file, never a "404: Not Found" page saved
as code.

Your chapters and documents are not in this folder and are never touched.
"""

import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

BRANCH = "claude/trusting-volta-4blgva"
BASE = ("https://raw.githubusercontent.com/rainytech/github-practice/"
        f"{BRANCH}/goodwill_tutor/")

# Every file, in one place, so nothing can be forgotten the way a hand-typed
# list of curl lines forgot tests/test_restyle.py.
FILES = [
    "goodwill_tutor.py",
    "house_style.py",
    "prompts.py",
    "gemini_api.py",
    "library.py",
    "pdf_export.py",
    "update.py",
    "requirements.txt",
    "README.md",
    "tests/support.py",
    "tests/run_all.py",
    "tests/test_house_style.py",
    "tests/test_library.py",
    "tests/test_answer.py",
    "tests/test_bad_model.py",
    "tests/test_restyle.py",
    "tests/test_window.py",
    "tests/test_pdf.py",
    "tests/test_update.py",
]

HERE = os.path.dirname(os.path.abspath(__file__))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def fetch(name):
    """Download one file; return its bytes, or raise with a plain reason."""
    try:
        with urllib.request.urlopen(BASE + name, timeout=60) as reply:
            data = reply.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"not found on GitHub ({exc.code})")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"no connection ({getattr(exc, 'reason', exc)})")
    if not data.strip() or data.strip().startswith(b"404: Not Found"):
        raise RuntimeError("GitHub sent an empty or missing file")
    if name.endswith(".py"):
        try:
            compile(data, name, "exec")
        except SyntaxError as exc:
            raise RuntimeError(f"arrived damaged (line {exc.lineno})")
    return data


def install(name, data):
    """Replace the file in one step, so a failure never leaves half of it."""
    target = os.path.join(HERE, *name.split("/"))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".part")
    with os.fdopen(handle, "wb") as fh:
        fh.write(data)
    os.replace(temp, target)


def main():
    print("Updating Goodwill Gemini Tutor\n")
    changed, same, failed = [], [], []
    for name in FILES:
        print(f"  {name:<28}", end="", flush=True)
        try:
            data = fetch(name)
        except RuntimeError as exc:
            print(f"FAILED — {exc}; your old copy is kept")
            failed.append(name)
            continue
        path = os.path.join(HERE, *name.split("/"))
        old = open(path, "rb").read() if os.path.exists(path) else None
        if old == data:
            print("up to date")
            same.append(name)
        else:
            install(name, data)
            print("updated" if old is not None else "new")
            changed.append(name)

    print(f"\n  {len(changed)} updated, {len(same)} already current, {len(failed)} failed")
    if failed:
        print("\n  Some files did not download. Check the internet connection and run")
        print("  python update.py  again. Nothing was damaged.")
        return 1

    print("\nChecking everything...\n")
    tests = os.path.join(HERE, "tests", "run_all.py")
    return subprocess.run([sys.executable, tests], cwd=HERE).returncode


if __name__ == "__main__":
    sys.exit(main())
