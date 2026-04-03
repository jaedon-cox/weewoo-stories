import random
import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

CATEGORY_PROMPTS = {
    "AITA": {
        "subreddit": "AmItheAsshole",
        "tones": ["conflicted", "defensive", "oblivious", "self-aware"],
        "templates": [
            "family holiday drama",
            "wedding conflict",
            "workplace boundary violation",
            "roommate dispute",
            "friend group falling out",
            "parent vs adult child clash",
            "money dispute between relatives",
            "pet-related neighborhood conflict",
        ],
    },
    "TIFU": {
        "subreddit": "tifu",
        "tones": ["embarrassed", "horrified", "self-deprecating", "darkly humorous"],
        "templates": [
            "embarrassing workplace incident",
            "disastrous date story",
            "public humiliation via technology",
            "accidental oversharing",
            "DIY project gone wrong",
            "misread social situation",
        ],
    },
    "relationship_advice": {
        "subreddit": "relationship_advice",
        "tones": ["desperate", "confused", "hurt", "seeking clarity"],
        "templates": [
            "partner hiding something suspicious",
            "long-distance relationship crisis",
            "cheating suspicion",
            "in-law interference",
            "growing apart after major life change",
            "secret discovered years later",
        ],
    },
    "prorevenge": {
        "subreddit": "ProRevenge",
        "tones": ["triumphant", "methodical", "patient", "satisfyingly petty"],
        "templates": [
            "coworker who stole credit gets exposed",
            "landlord ignores repairs until karma hits",
            "bully from high school gets comeuppance",
            "HOA tyrant meets their match",
            "contractor scam backfires spectacularly",
        ],
    },
}


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def select_category(config=None):
    if config is None:
        config = _load_config()
    categories = config["generation"]["categories"]
    names = [c["name"] for c in categories]
    weights = [c["weight"] for c in categories]
    return random.choices(names, weights=weights, k=1)[0]


def build_prompt_object(config=None):
    if config is None:
        config = _load_config()

    category = select_category(config)
    meta = CATEGORY_PROMPTS[category]
    tone = random.choice(meta["tones"])
    template = random.choice(meta["templates"])
    word_count = random.randint(
        config["generation"]["min_word_count"],
        config["generation"]["max_word_count"],
    )

    return {
        "category": category,
        "subreddit": meta["subreddit"],
        "tone": tone,
        "template": template,
        "word_count_target": word_count,
    }
