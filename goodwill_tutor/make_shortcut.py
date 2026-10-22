"""Make the "Goodwill Tutor" shortcut, ready to pin to the taskbar.

    python make_shortcut.py

Windows gives every Python app the same taskbar identity — pythonw.exe — so a
shortcut made by hand can be folded into another Python app's pin (TeachMark
opened instead). This shortcut carries the app's own ID, the same one the
window uses, so its pin is its own.

Puts "Goodwill Tutor" on the Desktop and in the Start menu. Needs pywin32:

    python -m pip install pywin32
"""

import os
import sys

APP_ID = "GoodwillTuitionCentre.GeminiTutor"     # the same as in goodwill_tutor.py
NAME = "Goodwill Tutor"
HERE = os.path.dirname(os.path.abspath(__file__))


def pythonw():
    """pythonw.exe beside the Python running this — no black window."""
    folder = os.path.dirname(sys.executable)
    candidate = os.path.join(folder, "pythonw.exe")
    return candidate if os.path.exists(candidate) else sys.executable


def make(path, target, args, workdir):
    import pythoncom
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon

    link = Dispatch("WScript.Shell").CreateShortcut(path)
    link.TargetPath = target
    link.Arguments = args
    link.WorkingDirectory = workdir
    link.Description = "Goodwill Gemini Tutor"
    link.IconLocation = target + ",0"
    link.Save()

    store = propsys.SHGetPropertyStoreFromParsingName(path, None, 2)   # read-write
    store.SetValue(pscon.PKEY_AppUserModel_ID,
                   propsys.PROPVARIANTType(APP_ID, pythoncom.VT_LPWSTR))
    store.Commit()


def main():
    if os.name != "nt":
        print("This makes a Windows shortcut; run it on Windows.")
        return 1
    try:
        import win32com.client  # noqa: F401
        from win32com.propsys import propsys  # noqa: F401
    except ImportError:
        print("One thing is needed first. Run:\n\n    python -m pip install pywin32\n\n"
              "then run  python make_shortcut.py  again.")
        return 1

    target = pythonw()
    args = f'"{os.path.join(HERE, "goodwill_tutor.py")}"'
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    start_menu = os.path.join(os.environ.get("APPDATA", ""),
                              "Microsoft", "Windows", "Start Menu", "Programs")
    made = []
    for folder in (desktop, start_menu):
        if not os.path.isdir(folder):
            continue
        path = os.path.join(folder, NAME + ".lnk")
        try:
            if os.path.exists(path):
                os.remove(path)
            make(path, target, args, HERE)
            made.append(path)
        except Exception as exc:
            print(f"Could not make {path}: {exc}")
    if not made:
        return 1
    print("Made:")
    for path in made:
        print("   ", path)
    print(f"\nNow right-click  {NAME}  on the Desktop, choose Show more options,"
          "\nthen Pin to taskbar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
