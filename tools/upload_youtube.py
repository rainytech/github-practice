#!/usr/bin/env python3
"""Upload a finished Goodwill video to YouTube with the YouTube Data API v3.

Usage (run on your own PC, from the repository folder):
    python tools/upload_youtube.py videos/mgu-cost-q13
    python tools/upload_youtube.py videos/mgu-cost-q13 --dry-run      # check only, no upload
    python tools/upload_youtube.py videos/mgu-cost-q13 --privacy private
    python tools/upload_youtube.py --login                            # sign in once, upload nothing

It reads from the project folder:
    <project>/*.mp4                  the rendered video (the newest .mp4 if there are several)
    <project>/upload/title.txt       title (max 100 characters)
    <project>/upload/description.txt description (max 5,000 characters)
    <project>/upload/tags.txt        comma-separated tags (max 500 characters, YouTube's way of counting)
    <project>/upload/settings.json   optional: {"playlist": "...", "privacy": "public", "category": "27"}

One-time setup: see tools/UPLOAD_SETUP.md.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/youtube"]  # upload + playlists
DEFAULT_SECRET = REPO / "tools" / "client_secret.json"
TOKEN_FILE = Path.home() / ".goodwill_youtube_token.json"
EDUCATION = "27"


def tag_length(tags):
    # YouTube counts a comma between tags, and quotes around a tag that has a space.
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)


def load_project(project):
    up = project / "upload"
    title = (up / "title.txt").read_text(encoding="utf-8").strip()
    description = (up / "description.txt").read_text(encoding="utf-8").strip()
    tags = [t.strip() for t in (up / "tags.txt").read_text(encoding="utf-8").split(",") if t.strip()]
    settings = {}
    if (up / "settings.json").exists():
        settings = json.loads((up / "settings.json").read_text(encoding="utf-8"))
    videos = sorted(project.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not videos:
        sys.exit(f"No .mp4 found in {project}")
    return title, description, tags, settings, videos[-1]


def check(title, description, tags):
    problems = []
    if not title:
        problems.append("title is empty")
    if len(title) > 100:
        problems.append(f"title is {len(title)} characters (max 100)")
    if len(description) > 5000:
        problems.append(f"description is {len(description)} characters (max 5,000)")
    if re.search(r"[<>]", title + description):
        problems.append("title/description contain < or > (YouTube rejects them)")
    if tag_length(tags) > 500:
        problems.append(f"tags are {tag_length(tags)} characters as YouTube counts them (max 500): remove a few")
    return problems


def youtube_client(secret):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit("Missing libraries. Run:  pip install google-api-python-client google-auth-oauthlib")
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secret.exists():
                sys.exit(f"OAuth file not found: {secret}\nSee tools/UPLOAD_SETUP.md, step 3.")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
            creds = flow.run_local_server(port=0)  # opens the browser once to sign in
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload(yt, video, title, description, tags, privacy, category):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response, retries = None, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"  uploaded {int(status.progress() * 100)}%")
            retries = 0
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < 5:
                retries += 1
                time.sleep(2 ** retries)
                continue
            raise
    return response["id"]


def add_to_playlist(yt, video_id, name):
    page = None
    playlist_id = None
    while True:
        res = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page).execute()
        for p in res.get("items", []):
            if p["snippet"]["title"].strip() == name.strip():
                playlist_id = p["id"]
        page = res.get("nextPageToken")
        if playlist_id or not page:
            break
    if not playlist_id:
        print(f"  playlist '{name}' not found: creating it (Public)")
        playlist_id = yt.playlists().insert(
            part="snippet,status",
            body={"snippet": {"title": name}, "status": {"privacyStatus": "public"}},
        ).execute()["id"]
    yt.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
    ).execute()


def note_in_claude_md(title, url):
    md = REPO / "CLAUDE.md"
    if not md.exists():
        return
    text = md.read_text(encoding="utf-8")
    marker = "- Channel views:"
    if url in text or marker not in text:
        return
    line = f"- {title} — {url} (published {time.strftime('%d %b %Y')}, uploaded by script)\n"
    md.write_text(text.replace(marker, line + marker, 1), encoding="utf-8")
    print("  added the link to CLAUDE.md (commit and push it)")


def main():
    ap = argparse.ArgumentParser(description="Upload a Goodwill video project to YouTube.")
    ap.add_argument("project", nargs="?", help="project folder, e.g. videos/mgu-cost-q13")
    ap.add_argument("--login", action="store_true", help="sign in and show the channel name; upload nothing")
    ap.add_argument("--privacy", choices=["public", "unlisted", "private"], help="default: settings.json or public")
    ap.add_argument("--playlist", help="playlist name (overrides settings.json)")
    ap.add_argument("--client-secret", default=str(DEFAULT_SECRET), help="path to the OAuth client_secret.json")
    ap.add_argument("--dry-run", action="store_true", help="check the files and stop before uploading")
    args = ap.parse_args()

    if args.login:
        yt = youtube_client(Path(args.client_secret))
        items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
        name = items[0]["snippet"]["title"] if items else "(no channel found on this account)"
        print(f"Signed in. Channel: {name}")
        return
    if not args.project:
        ap.error("give the project folder, e.g. videos/mgu-cost-q13")

    project = Path(args.project).resolve()
    title, description, tags, settings, video = load_project(project)
    privacy = args.privacy or settings.get("privacy", "public")
    playlist = args.playlist or settings.get("playlist")
    category = str(settings.get("category", EDUCATION))

    size_mb = video.stat().st_size / 1e6
    print(f"Video:       {video.name} ({size_mb:.1f} MB)")
    print(f"Title:       {title} ({len(title)}/100)")
    print(f"Description: {len(description)}/5000 characters")
    print(f"Tags:        {len(tags)} tags, {tag_length(tags)}/500 as YouTube counts")
    print(f"Privacy:     {privacy} · Category {category} · Made for kids: No")
    print(f"Playlist:    {playlist or '(none)'}")
    problems = check(title, description, tags)
    if problems:
        print("\nFix these first:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    if args.dry_run:
        print("\nDry run OK: nothing uploaded.")
        return

    yt = youtube_client(Path(args.client_secret))
    print("\nUploading…")
    video_id = upload(yt, video, title, description, tags, privacy, category)
    url = f"https://youtu.be/{video_id}"
    print(f"  done: {url}")
    if playlist:
        add_to_playlist(yt, video_id, playlist)
        print(f"  added to playlist '{playlist}'")
    (project / "upload" / "youtube.json").write_text(
        json.dumps({"id": video_id, "url": url, "privacy": privacy, "playlist": playlist}, indent=1), encoding="utf-8"
    )
    note_in_claude_md(title, url)
    print("\nStill manual in YouTube Studio: Education fields (Type, Level, Exam) and the pinned comment.")
    if privacy == "public":
        print("If the video shows 'locked as private', the API project still needs Google's audit (see UPLOAD_SETUP.md).")


if __name__ == "__main__":
    main()
