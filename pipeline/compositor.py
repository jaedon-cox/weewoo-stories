import os
import logging
import subprocess
import tempfile
import json
from db import database
from pipeline import storage

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
AUDIO_DIR = os.path.join(BASE_DIR, "media", "audio")
COMPOSED_DIR = os.path.join(BASE_DIR, "media", "composed")


def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def _pick_background() -> str:
    tmp = tempfile.mktemp(suffix=".mp4")
    storage.download_random_background(tmp)
    return tmp


def compose_video(story_id: str, config: dict) -> str:
    audio_path = os.path.join(AUDIO_DIR, f"{story_id}.mp3")
    output_path = os.path.join(COMPOSED_DIR, f"{story_id}.mp4")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    audio_duration = _get_duration(audio_path)
    background = _pick_background()
    bg_duration = _get_duration(background)

    resolution = config["video"].get("resolution", "1080x1920")
    width, height = resolution.split("x")
    subtitle_font = config["video"].get("subtitle_font", "Arial")
    subtitle_size = config["video"].get("subtitle_size", 18)

    # Build looped background input if needed
    loop_count = max(1, int(audio_duration / bg_duration) + 1)

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w") as srt_file:
        srt_path = srt_file.name
        # Placeholder SRT — real implementation would use Whisper or ElevenLabs timestamps
        srt_file.write(_generate_placeholder_srt(audio_duration))

    bg_is_temp = background.startswith(tempfile.gettempdir())
    try:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_count),
            "-i", background,
            "-i", audio_path,
            "-filter_complex",
            (
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1[bg];"
                f"[bg]subtitles={srt_path}:force_style="
                f"'FontName={subtitle_font},FontSize={subtitle_size},"
                f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                f"BorderStyle=3,Outline=2,Shadow=1,Alignment=2,"
                f"MarginV=80'[v]"
            ),
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(audio_duration),
            "-movflags", "+faststart",
            output_path,
        ]
        logger.info(f"Compositing video for story {story_id}")
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        os.unlink(srt_path)
        if bg_is_temp and os.path.exists(background):
            os.unlink(background)

    database.update_story_status(story_id, "pending_split")
    logger.info(f"Composed video: {output_path}")
    return output_path


def _generate_placeholder_srt(duration: float) -> str:
    """Generate a minimal SRT file. Replace with real transcript alignment."""
    return (
        "1\n"
        f"00:00:00,000 --> {_fmt_srt_time(duration)}\n"
        " \n\n"
    )


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
