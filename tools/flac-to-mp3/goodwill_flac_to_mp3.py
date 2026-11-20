"""
Goodwill FLAC to MP3  -  for the Creative ZEN Stone (2 GB), played via AUX.

Run from the Desktop with:  pythonw goodwill_flac_to_mp3.py
Needs FFmpeg full build:    winget install --id Gyan.FFmpeg -e

- 320 kbps CBR LAME, highest quality, 44.1 kHz stereo (soxr resampler for hi-res)
- Gapless Info/LAME header kept
- Clipping fixed only where the decoded MP3 peaks above 0 dBFS (target -0.1 dBFS)
- Clean ID3v2.3 tags, Front-cover art up to 500x500 JPEG
- FLAC files are only ever read, never modified
"""

import glob
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

APP_NAME = "Goodwill FLAC to MP3"
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(HERE, "goodwill_flac_to_mp3.json")
LOG_FILE = os.path.join(HERE, "goodwill_flac_to_mp3_log.txt")

STONE_LABEL = "ZEN Stone 2 GB"
STONE_USABLE = 1.86 * 1024 ** 3      # what Windows shows free on a 2 GB player
MP3_BYTES_PER_SEC = 320000 / 8
COVER_ALLOWANCE = 50 * 1024
COVER_MAX = 500
TARGET_PEAK_DB = -0.1
LENGTH_TOLERANCE = 0.1
LONG_TRACK_SEC = 20 * 60
DEFAULT_WORKERS = 3
OUT_RATE = 44100

NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW

ID3V1_GENRES = [
    "Blues", "Classic Rock", "Country", "Dance", "Disco", "Funk", "Grunge", "Hip-Hop", "Jazz",
    "Metal", "New Age", "Oldies", "Other", "Pop", "R&B", "Rap", "Reggae", "Rock", "Techno",
    "Industrial", "Alternative", "Ska", "Death Metal", "Pranks", "Soundtrack", "Euro-Techno",
    "Ambient", "Trip-Hop", "Vocal", "Jazz+Funk", "Fusion", "Trance", "Classical", "Instrumental",
    "Acid", "House", "Game", "Sound Clip", "Gospel", "Noise", "Alternative Rock", "Bass", "Soul",
    "Punk", "Space", "Meditative", "Instrumental Pop", "Instrumental Rock", "Ethnic", "Gothic",
    "Darkwave", "Techno-Industrial", "Electronic", "Pop-Folk", "Eurodance", "Dream",
    "Southern Rock", "Comedy", "Cult", "Gangsta", "Top 40", "Christian Rap", "Pop/Funk", "Jungle",
    "Native American", "Cabaret", "New Wave", "Psychedelic", "Rave", "Showtunes", "Trailer",
    "Lo-Fi", "Tribal", "Acid Punk", "Acid Jazz", "Polka", "Retro", "Musical", "Rock & Roll",
    "Hard Rock", "Folk", "Folk-Rock", "National Folk", "Swing", "Fast Fusion", "Bebop", "Latin",
    "Revival", "Celtic", "Bluegrass", "Avantgarde", "Gothic Rock", "Progressive Rock",
    "Psychedelic Rock", "Symphonic Rock", "Slow Rock", "Big Band", "Chorus", "Easy Listening",
    "Acoustic", "Humour", "Speech", "Chanson", "Opera", "Chamber Music", "Sonata", "Symphony",
    "Booty Bass", "Primus", "Porn Groove", "Satire", "Slow Jam", "Club", "Tango", "Samba",
    "Folklore", "Ballad", "Power Ballad", "Rhythmic Soul", "Freestyle", "Duet", "Punk Rock",
    "Drum Solo", "A Cappella", "Euro-House", "Dance Hall", "Goa", "Drum & Bass", "Club-House",
    "Hardcore Techno", "Terror", "Indie", "BritPop", "Afro-Punk", "Polsk Punk", "Beat",
    "Christian Gangsta Rap", "Heavy Metal", "Black Metal", "Crossover", "Contemporary Christian",
    "Christian Rock", "Merengue", "Salsa", "Thrash Metal", "Anime", "J-Pop", "Synthpop",
    "Abstract", "Art Rock", "Baroque", "Bhangra", "Big Beat", "Breakbeat", "Chillout",
    "Downtempo", "Dub", "EBM", "Eclectic", "Electro", "Electroclash", "Emo", "Experimental",
    "Garage", "Global", "IDM", "Illbient", "Industro-Goth", "Jam Band", "Krautrock", "Leftfield",
    "Lounge", "Math Rock", "New Romantic", "Nu-Breakz", "Post-Punk", "Post-Rock", "Psytrance",
    "Shoegaze", "Space Rock", "Trop Rock", "World Music", "Neoclassical", "Audiobook",
    "Audio Theatre", "Neue Deutsche Welle", "Podcast", "Indie Rock", "G-Funk", "Dubstep",
    "Garage Rock", "Psybient",
]

RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
COVER_FILE_NAMES = ["cover", "folder", "front", "albumart"]
COVER_EXTS = [".jpg", ".jpeg", ".png"]


# ---------------------------------------------------------------- helpers

def find_tool(name):
    """Real ffmpeg.exe / ffprobe.exe only - never a .cmd/.bat redirect."""
    exe = name + ".exe" if os.name == "nt" else name
    found = shutil.which(exe)
    if found:
        return found
    if os.name != "nt":
        return None
    local = os.environ.get("LOCALAPPDATA", "")
    progs = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = []
    for base in (os.path.join(local, "Microsoft", "WinGet"), os.path.join(progs, "WinGet")):
        candidates.append(os.path.join(base, "Links", exe))
        candidates += glob.glob(os.path.join(base, "Packages", "Gyan.FFmpeg*", "*", "bin", exe))
    candidates.append(os.path.join(r"C:\ffmpeg\bin", exe))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def fmt_time(sec):
    sec = int(round(sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def fmt_size(b):
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.2f} GB"
    return f"{b / 1024 ** 2:.1f} MB"


def norm(p):
    return os.path.normcase(os.path.realpath(p))


def is_inside(child, parent):
    child, parent = norm(child), norm(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:          # different drives
        return False


def safe_name(s, maxlen=120):
    """FAT32/Windows-safe file or folder name. Apostrophes kept, no underscores added."""
    s = s.replace('"', "'").replace(":", " -").replace("/", "-").replace("\\", "-").replace("|", "-")
    s = re.sub(r"[<>?*\x00-\x1f\x7f]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s[:maxlen].strip().rstrip(" .")
    if not s:
        s = "Unknown"
    if s.split(".")[0].strip().upper() in RESERVED_NAMES:
        s += " (x)"
    return s


def parse_pair(text):
    """'3/12' -> (3, 12); '03' -> (3, None); '' -> (None, None)"""
    m = re.match(r"\s*(\d+)\s*(?:/\s*(\d+))?", text or "")
    if not m:
        return None, None
    n = int(m.group(1)) or None
    t = int(m.group(2)) if m.group(2) else None
    return n, (t or None)


def fix_genre(g):
    """'17', '(17)', '(17)Rock' -> 'Rock'; text genres unchanged."""
    m = re.fullmatch(r"\((\d{1,3})\)(.*)", g)
    if m:
        rest = m.group(2).strip()
        if rest:
            return rest
        n = int(m.group(1))
        return ID3V1_GENRES[n] if n < len(ID3V1_GENRES) else ""
    if re.fullmatch(r"\d{1,3}", g):
        n = int(g)
        return ID3V1_GENRES[n] if n < len(ID3V1_GENRES) else ""
    return g


def read_text(path):
    data = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1")


class Stopped(Exception):
    pass


class ProcRunner:
    """Runs FFmpeg without console windows; Stop kills every running process."""

    def __init__(self):
        self.lock = threading.Lock()
        self.procs = set()
        self.stop = threading.Event()

    def run(self, args):
        if self.stop.is_set():
            raise Stopped()
        p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, creationflags=NO_WINDOW)
        with self.lock:
            self.procs.add(p)
        try:
            out, err = p.communicate()
        finally:
            with self.lock:
                self.procs.discard(p)
        if self.stop.is_set():
            raise Stopped()
        return p.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")

    def kill_all(self):
        self.stop.set()
        with self.lock:
            procs = list(self.procs)
        for p in procs:
            try:
                p.kill()
            except OSError:
                pass


# ---------------------------------------------------------------- data

@dataclass
class Song:
    src: str
    duration: float = 0.0
    rate: int = 0
    bits: int = 0
    channels: int = 0
    tags: dict = field(default_factory=dict)     # ffmpeg keys, written to the MP3
    track: int = None
    tracktotal: int = None
    disc: int = None
    disctotal: int = None
    missing: list = field(default_factory=list)
    cover: dict = None                            # {'kind','src','index','w','h','codec'}
    out: str = ""
    rel: str = ""
    note: str = ""                                # reason it is left out (Stage 2)


@dataclass
class ScanResult:
    inp: str
    out_root: str
    songs: list = field(default_factory=list)     # to be on the Stone
    todo: list = field(default_factory=list)      # not yet converted
    stage2: list = field(default_factory=list)
    errors: list = field(default_factory=list)


# ---------------------------------------------------------------- engine

class Engine:
    def __init__(self, ffmpeg, ffprobe, log, progress, workers=DEFAULT_WORKERS):
        self.ffmpeg, self.ffprobe = ffmpeg, ffprobe
        self.log, self.progress = log, progress
        self.workers = workers
        self.runner = ProcRunner()
        self.cover_lock = threading.Lock()
        self.cover_cache = {}
        self.tmp = None

    def stop(self):
        self.runner.kill_all()

    # ---------- scan

    def scan(self, inp, out_root):
        single = os.path.isfile(inp)
        if single:
            files = [inp] if inp.lower().endswith(".flac") else []
        else:
            files = []
            for root, dirs, names in os.walk(inp):
                dirs.sort(key=str.lower)
                for n in sorted(names, key=str.lower):
                    if n.lower().endswith(".flac"):
                        files.append(os.path.join(root, n))
        res = ScanResult(inp, out_root)
        if not files:
            self.log("No FLAC files found.")
            return res

        cue_refs, cue_count = self._cue_references({os.path.dirname(f) for f in files})
        self.log(f"Scanning {len(files)} FLAC file(s)...")
        done = [0]
        lock = threading.Lock()

        def job(path):
            try:
                return self._probe_song(path, single)
            finally:
                with lock:
                    done[0] += 1
                    self.progress(done[0], len(files))

        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(lambda f: (f, self._safe(job, f)), files))

        for path, (song, err) in results:
            if err:
                res.errors.append((path, err))
                continue
            stem = os.path.splitext(os.path.basename(path))[0].lower()
            refs = cue_refs.get(os.path.dirname(path), set())
            if os.path.basename(path).lower() in refs or stem in refs:
                song.note = "has a .cue sheet (whole album)"
            elif song.duration > LONG_TRACK_SEC:
                song.note = f"longer than 20 min ({fmt_time(song.duration)})"
            (res.stage2 if song.note else res.songs).append(song)

        self._plan_paths(res)
        res.todo = [s for s in res.songs if not os.path.exists(s.out)]
        self._report_scan(res, cue_count)
        return res

    def _safe(self, fn, arg):
        try:
            return fn(arg), None
        except Stopped:
            raise
        except Exception as e:
            return None, str(e).strip().splitlines()[-1] if str(e).strip() else repr(e)

    def _cue_references(self, dirs):
        refs, count = {}, 0
        for d in dirs:
            try:
                cues = [n for n in os.listdir(d) if n.lower().endswith(".cue")]
            except OSError:
                continue
            for c in cues:
                count += 1
                names = refs.setdefault(d, set())
                names.add(os.path.splitext(c)[0].lower())
                try:
                    text = read_text(os.path.join(d, c))
                except OSError:
                    continue
                for m in re.finditer(r'^\s*FILE\s+"?(.+?)"?\s+\w+\s*$', text, re.M | re.I):
                    names.add(os.path.basename(m.group(1)).lower())
        return refs, count

    def _ffprobe(self, path):
        rc, out, err = self.runner.run([self.ffprobe, "-v", "error", "-print_format", "json",
                                        "-show_format", "-show_streams", path])
        if rc != 0:
            raise RuntimeError(err.strip() or "ffprobe could not read the file")
        return json.loads(out)

    def _probe_song(self, path, single):
        d = self._ffprobe(path)
        streams = d.get("streams", [])
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not audio:
            raise RuntimeError("no audio stream")
        s = Song(src=path)
        s.rate = int(audio.get("sample_rate") or 0)
        s.channels = int(audio.get("channels") or 0)
        s.bits = int(audio.get("bits_per_raw_sample") or 0)
        dur = None
        if audio.get("duration_ts") and audio.get("time_base"):
            num, den = audio["time_base"].split("/")
            dur = int(audio["duration_ts"]) * int(num) / int(den)
        s.duration = dur or float(audio.get("duration") or d.get("format", {}).get("duration") or 0)

        raw = {}
        for src in (audio.get("tags") or {}, d.get("format", {}).get("tags") or {}):
            for k, v in src.items():
                raw.setdefault(k.upper(), v)
        self._clean_tags(s, raw)

        pics = [st for st in streams if st.get("codec_type") == "video"
                and st.get("disposition", {}).get("attached_pic")]
        if pics:
            front = [p for p in pics if (p.get("tags") or {}).get("comment", "").lower() == "cover (front)"]
            p = (front or pics)[0]
            s.cover = {"kind": "embedded", "src": path, "index": p["index"],
                       "w": int(p.get("width") or 0), "h": int(p.get("height") or 0),
                       "codec": p.get("codec_name", "")}
        elif not single:
            s.cover = self._folder_cover(os.path.dirname(path))
        return s

    def _clean_tags(self, s, raw):
        def first(*keys):
            for k in keys:
                v = raw.get(k)
                if v is not None:
                    v = v.replace("\x00", "").strip()
                    if v:
                        return v
            return ""

        title = first("TITLE")
        artist = first("ARTIST")
        album = first("ALBUM")
        album_artist = first("ALBUM_ARTIST", "ALBUMARTIST", "ALBUM ARTIST")
        s.track, s.tracktotal = parse_pair(first("TRACK", "TRACKNUMBER"))
        s.tracktotal = s.tracktotal or parse_pair(first("TRACKTOTAL", "TOTALTRACKS"))[0]
        s.disc, s.disctotal = parse_pair(first("DISC", "DISCNUMBER"))
        s.disctotal = s.disctotal or parse_pair(first("DISCTOTAL", "TOTALDISCS"))[0]
        ym = re.search(r"\d{4}", first("DATE", "YEAR"))
        genre = fix_genre(first("GENRE"))

        if not title:
            title = os.path.splitext(os.path.basename(s.src))[0]
            s.missing.append("Title (used file name)")
        for name, val in (("Artist", artist), ("Album", album), ("Track", s.track)):
            if not val:
                s.missing.append(name)

        t = {"title": title, "artist": artist, "album": album, "album_artist": album_artist}
        if s.track:
            t["track"] = f"{s.track}/{s.tracktotal}" if s.tracktotal else str(s.track)
        if s.disc:
            t["disc"] = f"{s.disc}/{s.disctotal}" if s.disctotal else str(s.disc)
        t["date"] = ym.group(0) if ym else ""
        t["genre"] = genre
        s.tags = {k: v for k, v in t.items() if v}

    def _folder_cover(self, folder):
        try:
            names = {n.lower(): n for n in os.listdir(folder)}
        except OSError:
            return None
        for base in COVER_FILE_NAMES:
            for ext in COVER_EXTS:
                n = names.get(base + ext)
                if n:
                    path = os.path.join(folder, n)
                    try:
                        st = next(x for x in self._ffprobe(path)["streams"] if x.get("codec_type") == "video")
                    except Exception:
                        continue
                    return {"kind": "file", "src": path, "index": 0,
                            "w": int(st.get("width") or 0), "h": int(st.get("height") or 0),
                            "codec": st.get("codec_name", "")}
        return None

    def _plan_paths(self, res):
        used = set()
        for s in res.songs:
            t = s.tags
            artist_dir = safe_name(t.get("album_artist") or t.get("artist") or "Unknown Artist")
            album_dir = safe_name(t.get("album") or "Unknown Album")
            width = 3 if max(s.track or 0, s.tracktotal or 0) >= 100 else 2
            multi = (s.disctotal or 0) > 1 or (s.disc or 0) > 1
            prefix = ""
            if s.track:
                prefix = f"{s.track:0{width}d} - "
                if multi:
                    prefix = f"{s.disc or 1}-{prefix}"
            folder = os.path.join(res.out_root, artist_dir, album_dir)
            title = safe_name(t["title"])
            room = 245 - len(folder) - len(prefix) - len(".mp3") - 5
            if len(title) > room:
                title = safe_name(title[:max(room, 10)])
            name = prefix + title
            out = os.path.join(folder, name + ".mp3")
            k = 2
            while out.lower() in used:
                out = os.path.join(folder, f"{name} ({k}).mp3")
                k += 1
            used.add(out.lower())
            s.out = out
            s.rel = os.path.relpath(out, res.out_root)

    def _report_scan(self, res, cue_count):
        songs = res.songs
        total_sec = sum(s.duration for s in songs)
        est = sum(s.duration * MP3_BYTES_PER_SEC + (COVER_ALLOWANCE if s.cover else 0) for s in songs)
        albums = {os.path.dirname(s.rel) for s in songs}
        hires = [s for s in songs if s.rate != OUT_RATE]
        L = self.log
        L("-" * 60)
        L(f"Songs: {len(songs)}   Albums: {len(albums)}   Total time: {fmt_time(total_sec)}")
        L(f"Estimated MP3 size: {fmt_size(est)}  ({STONE_LABEL}: about {fmt_size(STONE_USABLE)} usable)")
        if est > STONE_USABLE:
            L(f"WARNING: does not fit on the Stone - about {fmt_size(est - STONE_USABLE)} too much.")
        else:
            L(f"Fits on the Stone - {fmt_size(STONE_USABLE - est)} left.")
        L(f"Already converted (will be skipped): {len(songs) - len(res.todo)}   To convert: {len(res.todo)}")
        if hires:
            kinds = sorted({f"{s.bits or '?'}-bit/{s.rate / 1000:g} kHz" for s in hires})
            L(f"Resampled to 44.1 kHz (soxr): {len(hires)}  ({', '.join(kinds)})")
        multi = [s for s in songs if s.channels > 2]
        for s in multi:
            L(f"Note: {s.channels} channels, will be downmixed to stereo: {s.rel}")
        no_cover = [s for s in songs if not s.cover]
        if no_cover:
            L(f"No cover art: {len(no_cover)} song(s)")
        for s in songs:
            if s.missing:
                L(f"Missing tags ({', '.join(s.missing)}): {s.src}")
        if cue_count or res.stage2:
            L(f".cue files found: {cue_count}")
        for s in res.stage2:
            L(f"Left out for Stage 2 - {s.note}: {s.src}")
        for path, err in res.errors:
            L(f"CANNOT READ: {path} - {err}")
        L("-" * 60)

    # ---------- convert

    def convert(self, res):
        todo = res.todo
        if not todo:
            self.log("Nothing to convert - every song is already done.")
            return None
        self.tmp = tempfile.mkdtemp(prefix="goodwill_mp3_")
        start = time.time()
        stats = {"ok": [], "gain": [], "fail": [], "stopped": 0}
        lock = threading.Lock()
        done = [0]
        self.progress(0, len(todo))

        def job(song):
            if self.runner.stop.is_set():
                result = ("stopped", None)
            else:
                try:
                    result = self._convert_one(song)
                except Stopped:
                    result = ("stopped", None)
                except Exception as e:
                    result = ("fail", f"{type(e).__name__}: {e}")
                    self._write_log_file(traceback.format_exc())
            kind, info = result
            with lock:
                if kind == "stopped":
                    stats["stopped"] += 1
                    return
                done[0] += 1
                n = f"[{done[0]}/{len(todo)}]"
                if kind == "ok":
                    stats["ok"].append(song)
                    self.log(f"{n} OK    {song.rel}   peak {info['peak']:+.2f} dB")
                elif kind == "gain":
                    stats["ok"].append(song)
                    stats["gain"].append((song, info))
                    self.log(f"{n} GAIN  {song.rel}   {info['gain']:+.2f} dB  "
                             f"(peak {info['peak0']:+.2f} -> {info['peak']:+.2f} dB)")
                else:
                    stats["fail"].append((song, info))
                    self.log(f"{n} FAIL  {song.rel}   {info}")
                self.progress(done[0], len(todo))

        try:
            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                list(ex.map(job, todo))
        finally:
            shutil.rmtree(self.tmp, ignore_errors=True)

        L = self.log
        L("=" * 60)
        if self.runner.stop.is_set():
            L(f"STOPPED after {fmt_time(time.time() - start)}. Press Start to resume - finished songs are kept.")
        else:
            L(f"Finished in {fmt_time(time.time() - start)}")
        L(f"Converted: {len(stats['ok'])}   Skipped (already done): {len(res.songs) - len(todo)}   "
          f"Gain reduced: {len(stats['gain'])}   Failed: {len(stats['fail'])}")
        if stats["gain"]:
            L("Gain reduced (all other songs untouched):")
            for s, info in stats["gain"]:
                L(f"   {info['gain']:+.2f} dB   {s.rel}")
        if stats["fail"]:
            L("FAILED:")
            for s, info in stats["fail"]:
                L(f"   {s.src}  ->  {info}")
        L("=" * 60)
        return stats

    def _convert_one(self, s):
        if os.path.exists(s.out):
            return "ok", {"peak": 0.0}
        os.makedirs(os.path.dirname(s.out), exist_ok=True)
        part = s.out + ".part"
        try:
            cover = self._prepare_cover(s)
            gain, peak0, a = 0.0, None, None
            for attempt in range(4):
                self._encode(s, part, cover, gain)
                a = self._analyse(part)
                if a["errors"]:
                    return "fail", "decode error: " + a["errors"][0]
                if peak0 is None:
                    peak0 = a["peak"]
                if a["peak"] <= 0.0:
                    break
                if attempt == 3:
                    return "fail", f"still clipping at {a['peak']:+.2f} dB after gain {gain:+.2f} dB"
                new = math.floor((gain + TARGET_PEAK_DB - a["peak"]) * 100 + 1e-9) / 100
                gain = min(new, gain - 0.05) if attempt else new

            mp3_len = a["samples"] / OUT_RATE
            if abs(mp3_len - s.duration) > LENGTH_TOLERANCE:
                return "fail", f"length {mp3_len:.3f} s vs FLAC {s.duration:.3f} s"
            problem = self._check_tags(part, s, cover)
            if problem:
                return "fail", problem
            os.replace(part, s.out)
            if gain:
                return "gain", {"gain": gain, "peak0": peak0, "peak": a["peak"]}
            return "ok", {"peak": a["peak"]}
        finally:
            if os.path.exists(part):
                try:
                    os.remove(part)
                except OSError:
                    pass

    def _prepare_cover(self, s):
        c = s.cover
        if not c:
            return None
        key = (c["kind"], os.path.dirname(c["src"]) if c["kind"] == "embedded" else c["src"],
               s.tags.get("album", ""), c["w"], c["h"], c["codec"])
        with self.cover_lock:
            if key in self.cover_cache:
                return self.cover_cache[key]
            out = os.path.join(self.tmp, f"cover{len(self.cover_cache)}.jpg")
            small_jpeg = c["codec"] == "mjpeg" and 0 < c["w"] <= COVER_MAX and 0 < c["h"] <= COVER_MAX
            args = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", c["src"],
                    "-map", f"0:{c['index']}", "-frames:v", "1"]
            if small_jpeg:
                args += ["-c:v", "copy"]
            else:
                if c["w"] > COVER_MAX or c["h"] > COVER_MAX:
                    args += ["-vf", f"scale={COVER_MAX}:{COVER_MAX}:force_original_aspect_ratio=decrease:flags=lanczos"]
                args += ["-c:v", "mjpeg", "-q:v", "2"]
            args += ["-f", "image2", out]
            rc, _, err = self.runner.run(args)
            if rc != 0 or not os.path.exists(out):
                self.log(f"Note: cover art could not be read, song kept without it: {s.src}")
                out = None
            self.cover_cache[key] = out
            return out

    def _encode(self, s, part, cover, gain):
        a = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", s.src]
        if cover:
            a += ["-i", cover]
        a += ["-map", "0:a:0"]
        if cover:
            a += ["-map", "1:v:0"]
        filters = []
        if s.rate != OUT_RATE:
            filters.append(f"aresample=resampler=soxr:precision=28:osr={OUT_RATE}")
        if gain:
            filters.append(f"volume={gain:.2f}dB")
        if filters:
            a += ["-af", ",".join(filters)]
        a += ["-ac", "2", "-ar", str(OUT_RATE), "-c:a", "libmp3lame", "-b:a", "320k",
              "-compression_level", "0", "-threads", "1",
              "-map_metadata", "-1", "-map_chapters", "-1"]
        for k, v in s.tags.items():
            a += ["-metadata", f"{k}={v}"]
        if cover:
            a += ["-c:v", "copy", "-disposition:v:0", "attached_pic",
                  "-metadata:s:v:0", "title=Album cover", "-metadata:s:v:0", "comment=Cover (front)"]
        a += ["-id3v2_version", "3", "-write_id3v1", "0", "-write_xing", "1",
              "-fflags", "+bitexact", "-f", "mp3", part]
        rc, _, err = self.runner.run(a)
        if rc != 0:
            raise RuntimeError("FFmpeg encode failed: " + (err.strip().splitlines() or ["?"])[-1])

    def _analyse(self, path):
        """Full decode: errors, true peak of the decoded float samples, sample count."""
        rc, _, err = self.runner.run([
            self.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "level+info", "-i", path,
            "-map", "0:a:0", "-af",
            "astats=measure_perchannel=none:measure_overall=Peak_level+Number_of_samples",
            "-f", "null", "-"])
        errors = [ln.strip() for ln in err.splitlines() if "[error]" in ln or "[fatal]" in ln]
        peaks = re.findall(r"Peak level dB:\s*(\S+)", err)
        counts = re.findall(r"Number of samples:\s*(\d+)", err)
        if rc != 0 and not errors:
            errors = ["FFmpeg exit code " + str(rc)]
        if not errors and (not peaks or not counts):
            errors = ["could not measure peak/length"]
        peak = float(peaks[-1]) if peaks else 0.0
        return {"errors": errors, "peak": peak, "samples": int(counts[-1]) if counts else 0}

    def _check_tags(self, path, s, cover):
        d = self._ffprobe(path)
        audio = next((x for x in d.get("streams", []) if x.get("codec_type") == "audio"), {})
        if audio.get("codec_name") != "mp3" or int(audio.get("sample_rate") or 0) != OUT_RATE \
                or int(audio.get("channels") or 0) != 2:
            return "not a 44.1 kHz stereo MP3"
        got = {k.lower(): v for k, v in (d.get("format", {}).get("tags") or {}).items()}
        for k, v in s.tags.items():
            if got.get(k, "").strip() != v:
                return f"tag '{k}' missing or wrong in MP3"
        if cover:
            pics = [x for x in d.get("streams", []) if x.get("disposition", {}).get("attached_pic")]
            if not pics or (pics[0].get("tags") or {}).get("comment") != "Cover (front)":
                return "front cover missing in MP3"
        return None

    def _write_log_file(self, text):
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(text.rstrip() + "\n")
        except OSError:
            pass


# ---------------------------------------------------------------- checks

def check_ffmpeg(ffmpeg):
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-buildconf"], capture_output=True,
                             creationflags=NO_WINDOW).stdout.decode("utf-8", "replace")
    except OSError as e:
        return str(e)
    missing = [x for x in ("libmp3lame", "libsoxr") if f"--enable-{x}" not in out]
    if missing:
        return "This FFmpeg build lacks: " + ", ".join(missing) + ". Install the full build: winget install --id Gyan.FFmpeg -e"
    return None


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


def validate_paths(inp, out):
    if not inp or not os.path.exists(inp):
        return "Choose a FLAC file or folder."
    if os.path.isfile(inp) and not inp.lower().endswith(".flac"):
        return "The chosen file is not a .flac file."
    if not out:
        return "Choose an output folder."
    if os.path.isdir(inp) and (is_inside(out, inp) or is_inside(inp, out)):
        return "The output folder must be separate from the FLAC folder (not inside it, not the same)."
    return None


# ---------------------------------------------------------------- GUI

def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText

    class App:
        def __init__(self, root):
            self.root = root
            self.q = queue.Queue()
            self.engine = None
            self.busy = False
            cfg = load_config()
            root.title(APP_NAME)
            root.geometry("860x600")
            root.minsize(700, 450)

            frm = ttk.Frame(root, padding=10)
            frm.pack(fill="both", expand=True)
            frm.columnconfigure(1, weight=1)

            self.inp = tk.StringVar(value=cfg.get("input", ""))
            self.out = tk.StringVar(value=cfg.get("output", ""))
            self.workers = tk.IntVar(value=int(cfg.get("workers", DEFAULT_WORKERS)))

            ttk.Label(frm, text="FLAC file or folder:").grid(row=0, column=0, sticky="w")
            ttk.Entry(frm, textvariable=self.inp).grid(row=0, column=1, sticky="ew", padx=5)
            ttk.Button(frm, text="File...", command=self.pick_file).grid(row=0, column=2)
            ttk.Button(frm, text="Folder...", command=self.pick_in_dir).grid(row=0, column=3, padx=(5, 0))

            ttk.Label(frm, text="Output folder:").grid(row=1, column=0, sticky="w", pady=6)
            ttk.Entry(frm, textvariable=self.out).grid(row=1, column=1, sticky="ew", padx=5)
            ttk.Button(frm, text="Browse...", command=self.pick_out_dir).grid(row=1, column=2)

            bar = ttk.Frame(frm)
            bar.grid(row=2, column=0, columnspan=4, sticky="ew", pady=4)
            ttk.Label(bar, text="Songs at once:").pack(side="left")
            ttk.Spinbox(bar, from_=1, to=4, width=3, textvariable=self.workers, state="readonly").pack(side="left", padx=(4, 16))
            self.b_scan = ttk.Button(bar, text="Scan", command=self.scan)
            self.b_scan.pack(side="left")
            self.b_start = ttk.Button(bar, text="Start", command=self.start)
            self.b_start.pack(side="left", padx=6)
            self.b_stop = ttk.Button(bar, text="Stop", command=self.stop, state="disabled")
            self.b_stop.pack(side="left")
            self.status = ttk.Label(bar, text="")
            self.status.pack(side="right")

            self.pb = ttk.Progressbar(frm, mode="determinate")
            self.pb.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(4, 8))

            self.logbox = ScrolledText(frm, height=20, font=("Consolas", 9), wrap="none", state="disabled")
            self.logbox.grid(row=4, column=0, columnspan=4, sticky="nsew")
            frm.rowconfigure(4, weight=1)

            root.protocol("WM_DELETE_WINDOW", self.on_close)
            root.after(100, self.poll)

            self.ffmpeg, self.ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
            if not self.ffmpeg or not self.ffprobe:
                self.log("FFmpeg not found. Install it with:  winget install --id Gyan.FFmpeg -e")
            else:
                self.log(f"FFmpeg: {self.ffmpeg}")
                problem = check_ffmpeg(self.ffmpeg)
                if problem:
                    self.log(problem)

        # thread-safe messages
        def log(self, msg):
            self.q.put(("log", msg))

        def progress(self, done, total):
            self.q.put(("progress", done, total))

        def poll(self):
            try:
                while True:
                    m = self.q.get_nowait()
                    if m[0] == "log":
                        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.logbox.configure(state="normal")
                        self.logbox.insert("end", m[1] + "\n")
                        self.logbox.see("end")
                        self.logbox.configure(state="disabled")
                        try:
                            with open(LOG_FILE, "a", encoding="utf-8") as f:
                                f.write(f"{stamp}  {m[1]}\n")
                        except OSError:
                            pass
                    elif m[0] == "progress":
                        _, done, total = m
                        self.pb.configure(maximum=max(total, 1), value=done)
                        self.status.configure(text=f"{done} / {total}")
                    elif m[0] == "idle":
                        self.set_busy(False)
            except queue.Empty:
                pass
            self.root.after(100, self.poll)

        def pick_file(self):
            p = filedialog.askopenfilename(filetypes=[("FLAC files", "*.flac")])
            if p:
                self.inp.set(os.path.normpath(p))

        def pick_in_dir(self):
            p = filedialog.askdirectory()
            if p:
                self.inp.set(os.path.normpath(p))

        def pick_out_dir(self):
            p = filedialog.askdirectory()
            if p:
                self.out.set(os.path.normpath(p))

        def set_busy(self, busy):
            self.busy = busy
            st = "disabled" if busy else "normal"
            self.b_scan.configure(state=st)
            self.b_start.configure(state=st)
            self.b_stop.configure(state="normal" if busy else "disabled")

        def save(self):
            save_config({"input": self.inp.get(), "output": self.out.get(), "workers": self.workers.get()})

        def begin(self, convert):
            if self.busy:
                return
            if not self.ffmpeg or not self.ffprobe:
                messagebox.showerror(APP_NAME, "FFmpeg not found.\n\nInstall it with:\nwinget install --id Gyan.FFmpeg -e")
                return
            problem = check_ffmpeg(self.ffmpeg)
            if problem:
                messagebox.showerror(APP_NAME, problem)
                return
            inp, out = self.inp.get().strip(), self.out.get().strip()
            problem = validate_paths(inp, out)
            if problem:
                messagebox.showwarning(APP_NAME, problem)
                return
            self.save()
            self.set_busy(True)
            self.engine = Engine(self.ffmpeg, self.ffprobe, self.log, self.progress, self.workers.get())
            threading.Thread(target=self.work, args=(inp, out, convert), daemon=True).start()

        def work(self, inp, out, convert):
            try:
                self.log(f"\n=== {'Convert' if convert else 'Scan'}: {inp}  ->  {out}")
                res = self.engine.scan(inp, out)
                if convert and res.todo and not self.engine.runner.stop.is_set():
                    self.engine.convert(res)
            except Stopped:
                self.log("STOPPED. Press Start to resume - finished songs are kept.")
            except Exception:
                self.log("ERROR:\n" + traceback.format_exc())
            finally:
                self.q.put(("idle",))

        def scan(self):
            self.begin(convert=False)

        def start(self):
            self.begin(convert=True)

        def stop(self):
            if self.engine:
                self.log("Stopping...")
                self.engine.stop()

        def on_close(self):
            if self.busy:
                if not messagebox.askyesno(APP_NAME, "Conversion is running. Stop and exit?"):
                    return
                self.engine.stop()
            self.save()
            self.root.destroy()

    root = tk.Tk()
    App(root)
    root.mainloop()


def run_cli(inp, out):
    """Text-mode run for testing:  python goodwill_flac_to_mp3.py --cli INPUT OUTPUT"""
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        sys.exit("FFmpeg not found.")
    problem = check_ffmpeg(ffmpeg) or validate_paths(inp, out)
    if problem:
        sys.exit(problem)
    eng = Engine(ffmpeg, ffprobe, print, lambda d, t: None)
    res = eng.scan(inp, out)
    stats = eng.convert(res)
    sys.exit(1 if stats and stats["fail"] else 0)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--cli":
        run_cli(sys.argv[2], sys.argv[3])
    else:
        run_gui()
