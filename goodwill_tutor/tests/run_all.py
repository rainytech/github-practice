"""Run every check and print one answer.

    python tests\\run_all.py          (Windows)
    python tests/run_all.py          (Linux, Mac)

Nothing here touches your chapters, sends anything to Gemini, or costs a paisa.
Each file runs on its own, so one crash cannot hide the rest.
"""

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("test_house_style.py", "the document rules"),
    ("test_library.py", "chapters and documents"),
    ("test_answer.py", "a whole answer"),
    ("test_bad_model.py", "a weak model"),
    ("test_window.py", "the window"),
    ("test_pdf.py", "the printed page"),
]


def main():
    print("Goodwill Gemini Tutor — checking everything\n")
    started = time.time()
    failed = []
    for name, what in FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            print(f"  MISSING  {name}")
            failed.append(name)
            continue
        print(f"  running  {what:<26}", end="", flush=True)
        run = subprocess.run([sys.executable, path], cwd=HERE,
                             capture_output=True, text=True)
        passed = "ok" if run.returncode == 0 else "FAILED"
        print(passed)
        if run.returncode != 0:
            failed.append(name)
            print(run.stdout.rstrip())
            if run.stderr.strip():
                print(run.stderr.rstrip())

    print(f"\n  {len(FILES) - len(failed)} of {len(FILES)} groups passed "
          f"in {time.time() - started:.0f} seconds")
    if failed:
        print("\n  SOMETHING IS BROKEN:")
        for name in failed:
            print(f"    {name}    — run it on its own:  python tests/{name}")
        print("\n  Send this whole message to Claude.")
        return 1
    print("\n  ALL PASS — the app is behaving.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
