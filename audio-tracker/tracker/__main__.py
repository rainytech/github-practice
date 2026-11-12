"""Start the tracker:  py -m tracker   (or double-click 'Start Tracker.bat').

Options:
  --scan-only    process new screenshots, print a summary and exit (no web page)
  --no-browser   start the web page but do not open the browser
"""
import argparse
import logging
import sys
import webbrowser


def _setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # Windows console and the ₹ sign
        except Exception:
            pass

    ap = argparse.ArgumentParser(prog="tracker")
    ap.add_argument("--scan-only", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    try:
        from . import config
        settings = config.load()
        settings.make_dirs()
    except Exception as exc:
        print("\nPROBLEM:", exc)
        return 1

    _setup_logging(settings.log_file)
    log = logging.getLogger("tracker")

    try:
        from . import db, pipeline, server
    except ImportError as exc:
        print("\nPROBLEM: a required package is missing:", exc)
        print("Open a Command Prompt in the tracker folder and run:\n  py -m pip install -r requirements.txt")
        return 1

    try:
        db.init(settings.db_path)
        print("Audio Equipment Tracker")
        print("  Screenshot folder :", settings.screenshot_folder)
        print("  Database          :", settings.db_path)
        if not settings.screenshot_folder.exists():
            print("\nWARNING: the screenshot folder was not found. Check 'screenshot_folder' in settings.ini.")

        if args.scan_only:
            summary = pipeline.scan(settings, lambda d, t, n: n and print(f"  reading {d + 1}/{t}: {n}"))
            print("\n" + summary["message"])
            for e in summary["errors"]:
                print("  -", e)
            return 0

        httpd, port = server.create_server(settings)
        url = f"http://127.0.0.1:{port}/"
        print(f"\nCatalogue: {url}")
        print("Keep this window open while you use the catalogue. Close it to stop the tracker.\n")
        log.info("Started on %s", url)
        pipeline.start_background_scan(settings)
        if settings.open_browser and not args.no_browser:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
        return 0
    except Exception as exc:
        log.exception("Fatal error")
        print("\nPROBLEM:", exc)
        print("Details are saved in", settings.log_file)
        return 1


if __name__ == "__main__":
    sys.exit(main())
