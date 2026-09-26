"""PDF name maker.

Builds names like:  26 Sept Renosh fm textbook illustrations author Sony.pdf

Usage:
  double-click a.py / python a.py               window with subject and author dropdowns
  (rename to a.pyw so no black window opens behind it)
  python a.py --text                            questions in the black window
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
DROPDOWNS = {"subject": ["accounts", "costing", "income tax", "FM"],
             "author": ["Grewal", "Sony", "Jayan", "Lazar"]}
TAG = "Goodwill tuition centre 9567902805"


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
    parts = [date, v["name"], v["subject"], v["source"], v["content"], author, TAG]
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
                           check=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
        except (OSError, subprocess.CalledProcessError):
            continue
    return False


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    import tkinter.font as tkfont

    root = tk.Tk()
    root.title("PDF Name Maker")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        tkfont.nametofont(name).configure(size=14)
    big = ("Segoe UI", 14)
    root.option_add("*TCombobox*Listbox.font", big)

    memory = load_memory()
    for key, options in DROPDOWNS.items():
        old = memory.get(key, "").lower()
        match = [o for o in options if o.lower() == old]
        memory[key] = match[0] if match else options[0]

    date_var = tk.StringVar(value=today())
    vars_ = {k: tk.StringVar(value=memory.get(k, "")) for k, _ in FIELDS}
    desk_var = tk.BooleanVar(value=memory.get("to_desktop", True))

    rows = [("Date", date_var)] + [(label, vars_[k]) for k, label in FIELDS]
    for r, (label, var) in enumerate(rows):
        tk.Label(root, text=label, font=big).grid(row=r, column=0, sticky="w",
                                                  padx=12, pady=6)
        key = next((k for k, v in vars_.items() if v is var), None)
        if key in DROPDOWNS:
            box = ttk.Combobox(root, textvariable=var, values=DROPDOWNS[key],
                               state="readonly", font=big, width=30)
        else:
            box = tk.Entry(root, textvariable=var, font=big, width=32)
        box.grid(row=r, column=1, sticky="we", padx=12, pady=6)

    preview = tk.Label(root, font=("Segoe UI", 14, "bold"), fg="#0057B8",
                       wraplength=520, justify="left")
    preview.grid(row=len(rows), column=0, columnspan=2, padx=12, pady=10,
                 sticky="w")
    status = tk.Label(root, font=big, fg="#008000", wraplength=520,
                      justify="left")

    def values():
        return {k: v.get().strip() for k, v in vars_.items()}

    def filename():
        return build(clean(date_var.get()), values())

    def remember():
        data = values()
        data["to_desktop"] = desk_var.get()
        save_memory(data)

    def refresh(*_):
        preview.config(text=filename())

    for var in [date_var] + list(vars_.values()):
        var.trace_add("write", refresh)
    refresh()

    def copy_name(*_):
        remember()
        name = filename()
        if not copy_to_clipboard(name):
            root.clipboard_clear()
            root.clipboard_append(name)
        status.config(text="Copied. Paste with Ctrl + V.")

    def pick_pdf():
        remember()
        start = os.path.join(os.path.expanduser("~"), "Downloads")
        path = filedialog.askopenfilename(
            title="Choose the PDF to rename", initialdir=start,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        folder = desktop() if desk_var.get() else os.path.dirname(path)
        target = os.path.join(folder, filename())
        if os.path.exists(target):
            messagebox.showerror("Already exists",
                                 f"A file with this name already exists:\n{target}")
            return
        shutil.move(path, target)
        status.config(text=f"Saved as:\n{target}")

    buttons = tk.Frame(root)
    buttons.grid(row=len(rows) + 1, column=0, columnspan=2, pady=6)
    tk.Button(buttons, text="Copy Name", font=big, width=14,
              command=copy_name).pack(side="left", padx=8)
    tk.Button(buttons, text="Pick PDF and Rename", font=big, width=20,
              command=pick_pdf).pack(side="left", padx=8)
    tk.Checkbutton(root, text="Move renamed PDF to Desktop", font=big,
                   variable=desk_var).grid(row=len(rows) + 2, column=0,
                                           columnspan=2, pady=4)
    status.grid(row=len(rows) + 3, column=0, columnspan=2, padx=12, pady=8)
    root.bind("<Return>", copy_name)
    root.mainloop()


def main():
    args = sys.argv[1:]
    if not args:
        try:
            gui()
            return
        except Exception:
            pass  # no window support: fall back to questions
    if "--text" in args:
        args.remove("--text")
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
