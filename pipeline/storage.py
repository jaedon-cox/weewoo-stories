import os
import random
import logging
import boto3
from botocore.config import Config
from db import database

logger = logging.getLogger(__name__)

PARTS_BUCKET = os.environ.get("R2_PARTS_BUCKET", "autostory-parts")
BACKGROUNDS_BUCKET = os.environ.get("R2_BACKGROUNDS_BUCKET", "autostory-backgrounds")


def _client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_part(story_id: str, part_number: int, local_path: str) -> str:
    key = f"{story_id}/part{part_number}.mp4"
    _client().upload_file(local_path, PARTS_BUCKET, key)
    logger.info(f"Uploaded part to R2: {PARTS_BUCKET}/{key}")
    return key


def download_part(storage_path: str, local_path: str) -> None:
    _client().download_file(PARTS_BUCKET, storage_path, local_path)
    logger.info(f"Downloaded part from R2: {storage_path}")


def delete_part(storage_path: str) -> None:
    try:
        _client().delete_object(Bucket=PARTS_BUCKET, Key=storage_path)
        logger.info(f"Deleted part from R2: {storage_path}")
    except Exception as e:
        logger.warning(f"R2 delete failed for {storage_path}: {e} (part already marked posted, safe to ignore)")


def delete_parts_batch(storage_paths: list[str]) -> None:
    if not storage_paths:
        return
    objects = [{"Key": p} for p in storage_paths]
    # R2 delete_objects supports up to 1000 keys at a time
    for i in range(0, len(objects), 1000):
        batch = objects[i:i + 1000]
        try:
            _client().delete_objects(Bucket=PARTS_BUCKET, Delete={"Objects": batch, "Quiet": True})
            logger.info(f"Batch deleted {len(batch)} objects from R2")
        except Exception as e:
            logger.warning(f"R2 batch delete failed: {e}")


def download_random_background(local_path: str) -> None:
    s3 = _client()
    response = s3.list_objects_v2(Bucket=BACKGROUNDS_BUCKET)
    objects = response.get("Contents", [])
    if not objects:
        raise FileNotFoundError(f"No background clips found in R2 bucket: {BACKGROUNDS_BUCKET}")
    chosen = random.choice(objects)
    s3.download_file(BACKGROUNDS_BUCKET, chosen["Key"], local_path)
    logger.info(f"Downloaded background from R2: {chosen['Key']}")


def cleanup_posted_parts() -> int:
    """Delete any R2 objects for parts already marked 'posted' in the database.
    Returns the number of objects deleted."""
    posted = database.get_posted_parts()
    if not posted:
        logger.info("Cleanup: no posted parts to clean up")
        return 0

    paths = [p["file_path"] for p in posted if p["file_path"]]
    if not paths:
        return 0

    delete_parts_batch(paths)
    logger.info(f"Cleanup: swept {len(paths)} posted parts from R2")
    return len(paths)
