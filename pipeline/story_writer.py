import os
import uuid
import logging
import anthropic
from db import database

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a creative writer specializing in Reddit-style personal stories.
Write in first person, using casual internet language. Include realistic details, emotional beats,
and dialogue. Do NOT include subreddit formatting like "Edit:" sections, vote counts, or award mentions.
Write only the story body — no title, no meta commentary."""

STORY_PROMPT_TEMPLATE = """Write a Reddit-style story for r/{subreddit}.

Style: {tone}
Scenario: {template}
Target length: approximately {word_count_target} words

Requirements:
- Write in first person as the original poster
- Include realistic character names (not placeholders like "Person A")
- Build up context before the main conflict
- Include specific details that make it feel real
- End with a clear resolution or cliffhanger appropriate to the category
- Natural conversational tone, like someone typing out their situation

Write only the story body now:"""

TITLE_PROMPT_TEMPLATE = """Based on this Reddit story, write a compelling post title for r/{subreddit}.
The title should be concise (under 100 characters), hook the reader immediately, and follow
Reddit title conventions for this subreddit.

Story excerpt: {excerpt}

Write only the title, nothing else:"""


def generate_story(prompt_obj: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    story_prompt = STORY_PROMPT_TEMPLATE.format(**prompt_obj)
    logger.info(f"Generating story: category={prompt_obj['category']}, template={prompt_obj['template']}")

    story_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": story_prompt}],
    )
    body = story_response.content[0].text.strip()

    excerpt = body[:300]
    title_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=128,
        messages=[
            {
                "role": "user",
                "content": TITLE_PROMPT_TEMPLATE.format(
                    subreddit=prompt_obj["subreddit"], excerpt=excerpt
                ),
            }
        ],
    )
    title = title_response.content[0].text.strip().strip('"')

    story_id = str(uuid.uuid4())
    database.insert_story(story_id, prompt_obj["category"], title, body)
    logger.info(f"Story saved: id={story_id}, title={title!r}")
    return {"story_id": story_id, "title": title, "body": body, "category": prompt_obj["category"]}
