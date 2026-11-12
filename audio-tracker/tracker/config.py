"""Reads settings.ini and works out where everything lives."""
import configparser
import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = APP_DIR / "web"


class SettingsError(Exception):
    """A problem with settings.ini, explained in plain English."""


@dataclass
class Settings:
    settings_file: Path
    screenshot_folder: Path
    data_dir: Path
    port: int
    open_browser: bool

    @property
    def db_path(self) -> Path:
        return self.data_dir / "tracker.db"

    @property
    def thumbs_dir(self) -> Path:
        return self.data_dir / "thumbs"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def log_file(self) -> Path:
        return self.data_dir / "tracker.log"

    def make_dirs(self) -> None:
        for d in (self.data_dir, self.thumbs_dir, self.backups_dir, self.exports_dir):
            d.mkdir(parents=True, exist_ok=True)


def _clean(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


def load() -> Settings:
    settings_file = Path(os.environ.get("TRACKER_SETTINGS", APP_DIR / "settings.ini"))
    if not settings_file.exists():
        raise SettingsError(
            f"The settings file was not found:\n  {settings_file}\n"
            "It should be next to 'Start Tracker.bat'."
        )
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(settings_file, encoding="utf-8-sig")
    except configparser.Error as exc:
        raise SettingsError(f"settings.ini could not be read: {exc}") from exc
    if not parser.has_section("tracker"):
        raise SettingsError("settings.ini must contain a [tracker] section.")
    sec = parser["tracker"]

    folder_text = _clean(sec.get("screenshot_folder", ""))
    if not folder_text:
        raise SettingsError("settings.ini: 'screenshot_folder' is empty. Put the path of your screenshot folder there.")

    data_text = _clean(sec.get("data_folder", "data")) or "data"
    data_dir = Path(data_text)
    if not data_dir.is_absolute():
        data_dir = settings_file.parent / data_dir
    data_dir = data_dir.resolve()

    port_text = _clean(sec.get("port", "8765"))
    try:
        port = int(port_text)
        if not 1024 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SettingsError(f"settings.ini: port must be a number between 1024 and 65535 (found '{port_text}').")

    open_browser = _clean(sec.get("open_browser", "yes")).lower() in ("yes", "y", "true", "1", "on")

    from . import transport
    transport.configure(parser["transport"] if parser.has_section("transport") else None)

    return Settings(
        settings_file=settings_file,
        screenshot_folder=Path(folder_text),
        data_dir=data_dir,
        port=port,
        open_browser=open_browser,
    )
