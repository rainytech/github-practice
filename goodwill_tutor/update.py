"""Bring this folder up to date with the latest version, then check it.

    python update.py

Every file the app and its tests need is fetched, each one checked before it
replaces the old copy, and then the tests run. A download that fails leaves the
file you had untouched — never half a file, never a "404: Not Found" page saved
as code.

Your chapters and documents are not in this folder and are never touched.
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

BRANCH = "claude/trusting-volta-4blgva"
RAW = "https://raw.githubusercontent.com/rainytech/github-practice/{}/goodwill_tutor/"
API = f"https://api.github.com/repos/rainytech/github-practice/commits/{BRANCH}"
# Asked for by branch name, GitHub may hand out a copy up to five minutes old:
# an update run just after a fix was pushed could install yesterday's files
# and report "up to date". Asked for by commit, a file can only be that
# commit's. The branch name is the fallback when the commit cannot be looked up.
BASE = RAW.format(BRANCH)
VERSION_FILE = "VERSION"
# Set when this script has replaced itself and started the new copy, so the new
# copy does not do it again.
RESTARTED = "GOODWILL_UPDATE_RESTARTED"

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
    "tests/test_claude.py",
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


def latest():
    """The newest commit on the branch, as (sha, date) — or (None, None)."""
    request = urllib.request.Request(API, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "goodwill-update"})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            info = json.loads(reply.read())
        return info["sha"], info["commit"]["committer"]["date"]
    except Exception:
        return None, None


def install(name, data):
    """Replace the file in one step, so a failure never leaves half of it."""
    target = os.path.join(HERE, *name.split("/"))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".part")
    with os.fdopen(handle, "wb") as fh:
        fh.write(data)
    os.replace(temp, target)


def main():
    global BASE
    print("Updating Goodwill Gemini Tutor\n")
    sha, date = latest()
    if sha:
        BASE = RAW.format(sha)
        print(f"  Latest version: {sha[:7]}, {date.replace('T', ' ').rstrip('Z')} UTC\n")
    else:
        print("  Could not ask GitHub for the latest version; using the branch.\n")
    # update.py goes first. The list below is the OLD copy's list: run on as
    # it is, a file added since — tests/test_claude.py — is never fetched, and
    # the tests then report it missing. A new updater is installed and run in
    # this one's place, so the new list is the one used.
    if not os.environ.get(RESTARTED):
        try:
            data = fetch("update.py")
        except RuntimeError:
            data = None
        path = os.path.join(HERE, "update.py")
        if data is not None and open(path, "rb").read() != data:
            install("update.py", data)
            print("  update.py                   updated — starting the new copy\n")
            env = dict(os.environ, **{RESTARTED: "1"})
            return subprocess.run([sys.executable, path], cwd=HERE, env=env).returncode

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
    if sha:
        # The app shows this in its title bar, so a screenshot says which
        # version produced it.
        install(VERSION_FILE, sha[:7].encode())

    print("\nChecking everything...\n")
    tests = os.path.join(HERE, "tests", "run_all.py")
    return subprocess.run([sys.executable, tests], cwd=HERE).returncode


if __name__ == "__main__":
    sys.exit(main())
