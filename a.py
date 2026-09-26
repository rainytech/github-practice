"""PDF name maker.

Builds names like:  26 Sept Renosh fm textbook illustrations author Sony.pdf

Usage:
  python a.py                                   interactive (Enter = default)
  python a.py Renosh fm textbook illustrations Sony   quick mode
  python a.py --rename old.pdf                  interactive, then rename file
  python a.py --rename old.pdf Renosh fm textbook illustrations Sony
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

MEMORY = os.path.join(os.path.expanduser("~"), ".pdf_namer.json")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "June",
          "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
FIELDS = [("name", "Student name"), ("subject", "Subject"),
          ("source", "Source"), ("content", "Content"), ("author", "Author")]


def today():
    d = datetime.date.today()
    return f"{d.day} {MONTHS[d.month - 1]}"


def load_memory():
    try:
        with open(MEMORY, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_memory(data):
    try:
        with open(MEMORY, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def ask(label, default):
    shown = f" [{default}]" if default else ""
    value = input(f"{label}{shown}: ").strip()
    return value or default


def clean(text):
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    return re.sub(r"\s+", " ", text).strip()


def build(date, v):
    author = v["author"]
    if author and not author.lower().startswith("author"):
        author = f"author {author}"
    parts = [date, v["name"], v["subject"], v["source"], v["content"], author]
    return clean(" ".join(p for p in parts if p)) + ".pdf"


def desktop():
    home = os.path.expanduser("~")
    for sub in ("OneDrive/Desktop", "Desktop"):
        path = os.path.join(home, sub)
        if os.path.isdir(path):
            return path
    return home


def copy_to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    if sys.platform.startswith("win"):
        cmds = [["clip"]]
    elif sys.platform == "darwin":
        cmds = [["pbcopy"]]
    else:
        cmds = [["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"], ["wl-copy"]]
    for cmd in cmds:
        try:
            subprocess.run(cmd, input=text.encode("utf-16" if cmd == ["clip"] else "utf-8"),
                           check=True)
            return True
        except (OSError, subprocess.CalledProcessError):
            continue
    return False


def main():
    args = sys.argv[1:]
    rename = None
    if "--rename" in args:
        i = args.index("--rename")
        if i + 1 >= len(args):
            sys.exit("Give a file after --rename")
        rename = args[i + 1]
        del args[i:i + 2]
        if not os.path.isfile(rename):
            sys.exit(f"File not found: {rename}")

    memory = load_memory()
    if args:
        if len(args) != len(FIELDS):
            sys.exit("Quick mode needs 5 words: name subject source content author")
        values = dict(zip((k for k, _ in FIELDS), args))
        date = today()
    else:
        date = ask("Date", today())
        values = {k: ask(label, memory.get(k, "")) for k, label in FIELDS}

    save_memory(values)
    filename = build(date, values)
    print(f"\n{filename}")

    if copy_to_clipboard(filename):
        print("Copied to clipboard.")
    else:
        print("Clipboard not available (pip install pyperclip).")

    if not rename and not args:
        path = input("\nPDF to rename (drag it here, or Enter to skip): ")
        path = path.strip().strip('"').strip("'")
        if path:
            if not os.path.isfile(path):
                sys.exit(f"File not found: {path}")
            rename = path

    if rename:
        folder = os.path.dirname(os.path.abspath(rename))
        if input("Move to Desktop? [Y/n]: ").strip().lower() not in ("n", "no"):
            folder = desktop()
        target = os.path.join(folder, filename)
        if os.path.exists(target):
            sys.exit(f"Already exists, not renamed: {target}")
        shutil.move(rename, target)
        print(f"Saved as: {target}")


if __name__ == "__main__":
    main()
