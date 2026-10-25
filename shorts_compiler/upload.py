#!/usr/bin/env python3
"""Upload a video to YouTube (private by default).

    python upload.py out/compilation.mp4 --title "..." --metadata out/metadata.json

One-time setup: create an OAuth "Desktop app" client in Google Cloud with the
YouTube Data API v3 enabled, and save it as client_secret.json next to this
file. The first run opens a browser for consent and caches token.json.
Unverified API projects can only upload private videos until audited.
"""
import argparse
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
HERE = Path(__file__).parent


def credentials() -> Credentials:
    token = HERE / "token.json"
    creds = Credentials.from_authorized_user_file(token, SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        creds = InstalledAppFlow.from_client_secrets_file(HERE / "client_secret.json", SCOPES).run_local_server(port=0)
    token.write_text(creds.to_json())
    return creds


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--title")
    p.add_argument("--description", default="")
    p.add_argument("--tags", nargs="*", default=[])
    p.add_argument("--metadata", type=Path, help="metadata.json from metadata.py (uses its first title)")
    p.add_argument("--thumbnail", type=Path)
    p.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    args = p.parse_args()

    title, description, tags = args.title, args.description, args.tags
    if args.metadata:
        meta = json.loads(args.metadata.read_text())
        title = title or meta["titles"][0]
        description = description or meta["description"]
        tags = tags or meta["tags"]
    if not title:
        p.error("provide --title or --metadata")

    yt = build("youtube", "v3", credentials=credentials())
    req = yt.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": "22"},
            "status": {"privacyStatus": args.privacy, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(args.video), chunksize=8 * 1024 * 1024, resumable=True),
    )
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    video_id = resp["id"]
    if args.thumbnail:
        yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(args.thumbnail))).execute()
    print(f"https://youtu.be/{video_id} ({args.privacy})")


if __name__ == "__main__":
    main()
