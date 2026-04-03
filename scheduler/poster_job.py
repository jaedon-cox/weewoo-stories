import logging
import yaml
import os
from datetime import datetime, timezone
from db import database
from pipeline import caption_writer, tiktok_poster, youtube_poster

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
MAX_RETRIES = 3


def run_poster_job():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    now_iso = datetime.now(timezone.utc).isoformat()
    due_parts = database.get_parts_due(now_iso)

    if not due_parts:
        logger.debug("No parts due for posting.")
        return

    logger.info(f"Poster job: {len(due_parts)} part(s) due")

    for part in due_parts:
        if part["retry_count"] >= MAX_RETRIES:
            logger.error(f"Part {part['id']} exceeded max retries, marking failed")
            database.update_part_status(part["id"], "failed")
            continue

        story = database.get_story(part["story_id"])
        if not story:
            logger.error(f"Story not found for part {part['id']}")
            database.update_part_status(part["id"], "failed")
            continue

        captions = caption_writer.generate_captions(story)
        database.update_part_status(part["id"], "uploading")

        try:
            _post_part(part, story, captions, config)
        except Exception as e:
            logger.exception(f"Failed to post part {part['id']}: {e}")
            database.increment_retry(part["id"])


def _post_part(part: dict, story: dict, captions: dict, config: dict):
    tiktok_enabled = config["posting"].get("tiktok_enabled", True)
    youtube_enabled = config["posting"].get("youtube_enabled", True)

    if tiktok_enabled:
        try:
            tiktok_poster.upload_part(part, captions["tiktok_caption"])
        except Exception as e:
            logger.error(f"TikTok upload failed for part {part['id']}: {e}")
            raise

    if youtube_enabled:
        try:
            youtube_poster.upload_part(part, story, captions["youtube_description"])
        except Exception as e:
            logger.error(f"YouTube upload failed for part {part['id']}: {e}")
            raise
