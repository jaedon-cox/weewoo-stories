import os
import logging
import anthropic

logger = logging.getLogger(__name__)

CAPTION_PROMPT = """Write a TikTok/YouTube Shorts caption for this video.

Story category: {category}
Story title: {title}

Requirements:
- Under 150 characters (TikTok limit)
- Hook the viewer in the first few words
- Include 3-5 relevant hashtags at the end
- Conversational and intriguing tone
- Do NOT use the word "Reddit" (fair use/branding reasons)

Write only the caption text with hashtags, nothing else:"""

DESCRIPTION_PROMPT = """Write a YouTube Shorts description for this video.

Story category: {category}
Story title: {title}

Requirements:
- 2-3 sentences max
- Tease the conflict without spoiling it
- End with a call to action (like, follow, comment opinion)
- Add a line: "⚠️ AI-generated content"
- Include 5-8 relevant hashtags on separate lines at the end

Write only the description, nothing else:"""


def generate_captions(story: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    tiktok_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": CAPTION_PROMPT.format(
                category=story["category"],
                title=story["title"],
            ),
        }],
    )
    tiktok_caption = tiktok_response.content[0].text.strip()

    youtube_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": DESCRIPTION_PROMPT.format(
                category=story["category"],
                title=story["title"],
            ),
        }],
    )
    youtube_description = youtube_response.content[0].text.strip()

    logger.info(f"Captions generated for story: {story['title']!r}")
    return {
        "tiktok_caption": tiktok_caption,
        "youtube_description": youtube_description,
    }
