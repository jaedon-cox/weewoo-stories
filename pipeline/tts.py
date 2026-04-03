import os
import logging
import yaml
import requests
from db import database

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "media", "audio")


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def generate_audio(story: dict, config=None) -> str:
    if config is None:
        config = _load_config()

    provider = config["tts"]["provider"]
    story_id = story["story_id"]
    output_path = os.path.join(AUDIO_DIR, f"{story_id}.mp3")

    try:
        if provider == "elevenlabs":
            _elevenlabs_tts(story["body"], output_path, config)
        else:
            _google_tts(story["body"], output_path)
    except Exception as e:
        logger.warning(f"Primary TTS ({provider}) failed: {e}. Trying fallback.")
        fallback = config["tts"].get("fallback_provider", "google")
        if fallback == "google":
            _google_tts(story["body"], output_path)
        else:
            raise

    database.update_story_status(story_id, "pending_video")
    logger.info(f"Audio generated: {output_path}")
    return output_path


def _elevenlabs_tts(text: str, output_path: str, config: dict):
    api_key = os.environ["ELEVENLABS_API_KEY"]
    voice_id = config["tts"]["elevenlabs_voice_id"]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    response = requests.post(url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)


def _google_tts(text: str, output_path: str):
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-D",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as f:
        f.write(response.audio_content)
