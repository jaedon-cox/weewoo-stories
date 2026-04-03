import os
import shutil
import logging
import tempfile
from datetime import datetime, timezone
from db import database
from pipeline import storage

logger = logging.getLogger(__name__)


def _get_youtube_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_part(part: dict, story: dict, description: str) -> str:
    tmp_dir = tempfile.mkdtemp()
    local_path = os.path.join(tmp_dir, "part.mp4")

    try:
        storage.download_part(part["file_path"], local_path)
        video_id = _upload_to_youtube(local_path, story, description)
        # Mark posted in DB first, then delete from R2
        database.update_part_status(
            part["id"], "posted",
            youtube_video_id=video_id,
            posted_at=datetime.now(timezone.utc).isoformat(),
        )
        storage.delete_part(part["file_path"])
        logger.info(f"YouTube posted: video_id={video_id}, part={part['id']}")
        return video_id
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _upload_to_youtube(local_path: str, story: dict, description: str) -> str:
    from googleapiclient.http import MediaFileUpload

    youtube = _get_youtube_service()
    tags = [w.lstrip("#") for w in description.split() if w.startswith("#")][:10]

    body = {
        "snippet": {
            "title": story["title"][:100],
            "description": description,
            "tags": tags,
            "categoryId": "22",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(local_path, mimetype="video/mp4", resumable=True, chunksize=10 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")

    return response["id"]
