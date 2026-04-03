import os
import time
import shutil
import logging
import tempfile
import requests
from db import database
from pipeline import storage

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


def _refresh_access_token() -> str:
    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    client_secret = os.environ["TIKTOK_CLIENT_SECRET"]
    refresh_token = os.environ["TIKTOK_REFRESH_TOKEN"]

    resp = requests.post(TOKEN_URL, data={
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def upload_part(part: dict, caption: str) -> str:
    tmp_dir = tempfile.mkdtemp()
    local_path = os.path.join(tmp_dir, "part.mp4")

    try:
        storage.download_part(part["file_path"], local_path)
        video_id = _upload_to_tiktok(local_path, part, caption)
        # Mark posted in DB first, then delete from R2
        database.update_part_status(
            part["id"], "posted",
            tiktok_video_id=str(video_id),
            posted_at=_now_iso(),
        )
        storage.delete_part(part["file_path"])
        logger.info(f"TikTok posted: video_id={video_id}, part={part['id']}")
        return str(video_id)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _upload_to_tiktok(local_path: str, part: dict, caption: str) -> str:
    access_token = _refresh_access_token()
    file_size = os.path.getsize(local_path)

    # Step 1: Initialize upload
    init_resp = requests.post(
        f"{TIKTOK_API_BASE}/post/publish/video/init/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
                "ai_generated_content": True,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()["data"]
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]

    # Step 2: Upload video bytes
    with open(local_path, "rb") as f:
        video_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Length": str(file_size),
        },
        data=video_bytes,
        timeout=300,
    )
    upload_resp.raise_for_status()

    # Step 3: Poll for status
    for attempt in range(20):
        time.sleep(5)
        status_resp = requests.post(
            f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"publish_id": publish_id},
            timeout=30,
        )
        status_resp.raise_for_status()
        status_data = status_resp.json()["data"]
        status = status_data.get("status")
        logger.info(f"TikTok publish status [{attempt+1}]: {status}")
        if status == "PUBLISH_COMPLETE":
            return str(status_data.get("publicaly_available_post_id", [publish_id])[0])
        elif status in ("FAILED", "PUBLISH_FAILED"):
            raise RuntimeError(f"TikTok publish failed: {status_data}")

    raise TimeoutError("TikTok publish did not complete within polling window")


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
