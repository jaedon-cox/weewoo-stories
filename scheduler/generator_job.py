import logging
import yaml
import os
from pipeline import prompt_generator, story_writer, tts, compositor, splitter

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def run_generation_pipeline():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    logger.info("=== Generation pipeline started ===")

    # 1. Prompt
    prompt_obj = prompt_generator.build_prompt_object(config)
    logger.info(f"Prompt: {prompt_obj}")

    # 2. Story
    story = story_writer.generate_story(prompt_obj)
    logger.info(f"Story written: {story['story_id']}")

    # 3. TTS
    audio_path = tts.generate_audio(story, config)
    logger.info(f"Audio: {audio_path}")

    # 4. Video composition
    video_path = compositor.compose_video(story["story_id"], config)
    logger.info(f"Video: {video_path}")

    # 5. Split + schedule
    post_times = splitter.compute_post_times(config)
    parts = splitter.split_video(story["story_id"], config, post_times)
    logger.info(f"Split into {len(parts)} parts, queued for posting")

    logger.info("=== Generation pipeline complete ===")
    return story, parts
