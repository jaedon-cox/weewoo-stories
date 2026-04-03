#!/usr/bin/env python3
"""
AutoStory — CLI entry point.

Commands:
  python main.py generate   Run the full story generation pipeline once
  python main.py post       Check DB for due parts and upload them
  python main.py cleanup    Delete any R2 objects for already-posted parts
  python main.py migrate    Initialize the PostgreSQL schema
"""
import logging
import os
import sys
import smtplib
import yaml
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pipeline.log"),
    ],
)
logger = logging.getLogger("autostory.main")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def send_alert_email(subject: str, body: str, config: dict):
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    to_email = config["alerts"]["alert_email"]

    if not all([smtp_host, smtp_user, smtp_password]):
        logger.warning("SMTP not configured, skipping alert email")
        return

    msg = EmailMessage()
    msg["Subject"] = f"[AutoStory] {subject}"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    logger.info(f"Alert email sent to {to_email}: {subject}")


def safe_run(fn, name: str, config: dict):
    try:
        fn()
    except Exception as e:
        logger.exception(f"{name} crashed: {e}")
        try:
            send_alert_email(f"{name} crashed", str(e), config)
        except Exception:
            pass
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    config = load_config()

    if command == "generate":
        from scheduler.generator_job import run_generation_pipeline
        safe_run(run_generation_pipeline, "GenerationPipeline", config)

    elif command == "post":
        from scheduler.poster_job import run_poster_job
        safe_run(run_poster_job, "PosterJob", config)

    elif command == "cleanup":
        from pipeline.storage import cleanup_posted_parts
        count = cleanup_posted_parts()
        logger.info(f"Cleanup complete: {count} objects removed from R2")

    elif command == "migrate":
        from db.setup import setup
        setup()

    else:
        print(f"Unknown command: {command!r}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
