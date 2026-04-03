import os
import uuid
import logging
import subprocess
import json
from datetime import datetime, timedelta
from db import database
from pipeline import storage

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
COMPOSED_DIR = os.path.join(BASE_DIR, "media", "composed")
PARTS_DIR = os.path.join(BASE_DIR, "media", "parts")


def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def split_video(story_id: str, config: dict, post_times: list[datetime]) -> list[dict]:
    input_path = os.path.join(COMPOSED_DIR, f"{story_id}.mp4")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Composed video not found: {input_path}")

    duration = _get_duration(input_path)
    min_seg = config["video"]["min_part_duration_seconds"]
    max_seg = config["video"]["max_part_duration_seconds"]

    # Choose segment duration: try to keep parts between min/max
    # Pick largest segment_time that keeps each part >= min_seg
    segment_time = max_seg
    num_parts = max(1, int(duration / segment_time))
    actual_seg = duration / num_parts

    if actual_seg < min_seg:
        # Fewer, longer parts
        num_parts = max(1, int(duration / min_seg))
        actual_seg = duration / num_parts

    logger.info(f"Splitting story {story_id}: {duration:.1f}s into ~{num_parts} parts ({actual_seg:.1f}s each)")

    output_pattern = os.path.join(PARTS_DIR, f"{story_id}_part%d.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c", "copy",
        "-f", "segment",
        "-segment_time", str(int(actual_seg)),
        "-reset_timestamps", "1",
        output_pattern,
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # Register parts in DB with scheduled post times
    parts = []
    for i in range(num_parts):
        part_file = os.path.join(PARTS_DIR, f"{story_id}_part{i}.mp4")
        if not os.path.exists(part_file):
            logger.warning(f"Expected part not found: {part_file}")
            continue

        part_id = str(uuid.uuid4())
        scheduled_at = post_times[i % len(post_times)].isoformat()
        storage_path = storage.upload_part(story_id, i + 1, part_file)
        os.unlink(part_file)
        database.insert_part(part_id, story_id, i + 1, storage_path, scheduled_at)
        parts.append({"part_id": part_id, "part_number": i + 1, "file_path": storage_path, "scheduled_at": scheduled_at})
        logger.info(f"Part {i+1} uploaded to R2 and queued → {scheduled_at}")

    database.update_story_status(story_id, "done")
    return parts


def compute_post_times(config: dict, base_time: datetime | None = None) -> list[datetime]:
    if base_time is None:
        base_time = datetime.utcnow()

    post_time_strs = config["posting"]["post_times"]
    slots = []
    day = base_time.date()

    for ts in post_time_strs:
        h, m = map(int, ts.split(":"))
        candidate = datetime(day.year, day.month, day.day, h, m)
        if candidate <= base_time:
            candidate += timedelta(days=1)
        slots.append(candidate)

    # Sort and extend into the future as needed
    slots.sort()
    extended = []
    day_offset = 0
    idx = 0
    for _ in range(50):  # enough for any video
        for ts in post_time_strs:
            h, m = map(int, ts.split(":"))
            t = datetime(day.year, day.month, day.day, h, m) + timedelta(days=day_offset)
            if t > base_time:
                extended.append(t)
        day_offset += 1
        if len(extended) >= 20:
            break

    extended.sort()
    return extended
