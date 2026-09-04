"""Auto-tagging: derive tags for an intent from its URL and unfurled metadata.

Two passes, cheapest first:

1. Heuristics - a domain map. Free, instant, covers the common share-sheet
   sources (Zomato, YouTube, Netflix, ...).
2. LLM - Vertex AI (gemini flash lite tier) picks from a closed vocabulary of
   canonical tags plus the circle's existing tags. Closed vocabulary keeps the
   filter chips coherent ("movies" never fragments into "movie"/"film"/"cinema").

The LLM pass degrades gracefully: any failure logs at ERROR and the heuristic
tags (possibly none) still land. Tags written here also land in auto_tags so
every surface can render them as machine suggestions.
"""

import json
from urllib.parse import urlparse

from google import genai
from google.genai import types as genai_types

from app_util.log_util import errorlogger, infologger
from config.settings import settings
from modules.tagging import tagging_queries as q
from schemas.intents_schema import normalize_tags

# Small on purpose. Every tag the model may emit must be defensible as a filter
# chip. Circle-specific tags get merged in at call time.
CANONICAL_TAGS = [
    "food", "cafe", "drinks", "dessert",
    "movies", "series", "videos", "anime", "music",
    "books", "games",
    "travel", "outdoors", "trek", "beach", "places",
    "date night", "events", "shopping", "gifts",
    "home", "fitness", "learning",
]

# Registrable-domain suffix -> tags. Matched with endswith on the hostname so
# subdomains (www., m., open.) hit without listing every variant.
DOMAIN_TAGS: dict[str, list[str]] = {
    "zomato.com": ["food"],
    "swiggy.com": ["food"],
    "eazydiner.com": ["food"],
    "youtube.com": ["videos"],
    "youtu.be": ["videos"],
    "netflix.com": ["movies"],
    "primevideo.com": ["movies"],
    "hotstar.com": ["movies"],
    "jiocinema.com": ["movies"],
    "imdb.com": ["movies"],
    "letterboxd.com": ["movies"],
    "goodreads.com": ["books"],
    "spotify.com": ["music"],
    "airbnb.com": ["travel"],
    "airbnb.co.in": ["travel"],
    "booking.com": ["travel"],
    "makemytrip.com": ["travel"],
    "tripadvisor.com": ["travel"],
    "tripadvisor.in": ["travel"],
    "bookmyshow.com": ["events"],
    "store.steampowered.com": ["games"],
    "myntra.com": ["shopping"],
    "flipkart.com": ["shopping"],
    "amazon.in": ["shopping"],
}

SYSTEM_INSTRUCTION = (
    "You tag saved links and ideas for a small shared wishlist app used by "
    "couples and friend groups. Given one saved item, pick the tags that best "
    "describe it. Rules: choose ONLY from the provided vocabulary, return at "
    "most 3 tags, prefer fewer accurate tags over more vague ones, and return "
    "an empty array when nothing fits. Respond with a JSON array of strings."
)

GENAI_CLIENT: genai.Client | None = None


def get_genai_client() -> genai.Client:
    global GENAI_CLIENT
    if GENAI_CLIENT is None:
        GENAI_CLIENT = genai.Client(
            vertexai=True,
            project=settings.GCP_PROJECT,
            location=settings.GCP_LOCATION,
        )
    return GENAI_CLIENT


def heuristic_tags(url: str | None, link_meta: dict | None) -> list[str]:
    tags: list[str] = []
    if url:
        host = urlparse(url).netloc.lower()
        for domain, domain_tags in DOMAIN_TAGS.items():
            if host == domain or host.endswith("." + domain):
                tags.extend(domain_tags)
                break
    if link_meta and link_meta.get("site") == "Google Maps":
        tags.append("places")
    return tags


def build_prompt(intent: dict, vocabulary: list[str]) -> str:
    link_meta = intent.get("link_meta") or {}
    if isinstance(link_meta, str):
        try:
            link_meta = json.loads(link_meta)
        except json.JSONDecodeError:
            link_meta = {}
    parts = [f"Title: {intent['title']}"]
    if intent.get("category"):
        parts.append(f"Category: {intent['category']}")
    if intent.get("url"):
        parts.append(f"Domain: {urlparse(intent['url']).netloc}")
    if link_meta.get("site"):
        parts.append(f"Site: {link_meta['site']}")
    if link_meta.get("description"):
        parts.append(f"Page description: {link_meta['description'][:400]}")
    if intent.get("note"):
        parts.append(f"User note: {intent['note'][:200]}")
    parts.append("Vocabulary: " + ", ".join(vocabulary))
    return "\n".join(parts)


def fetch_llm_tags(intent: dict, vocabulary: list[str]) -> list[str]:
    response = get_genai_client().models.generate_content(
        model=settings.TAGGER_MODEL,
        contents=build_prompt(intent, vocabulary),
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema={"type": "ARRAY", "items": {"type": "STRING"}},
            temperature=0.0,
            labels={"app": "someday"},
        ),
    )
    raw = json.loads(response.text or "[]")
    allowed = set(vocabulary)
    tags = [t for t in normalize_tags(raw) if t in allowed]
    infologger.info(
        f"tagging_helper.fetch_llm_tags | model={settings.TAGGER_MODEL} "
        f"raw={raw!r} kept={tags!r}"
    )
    return tags


def build_vocabulary(db, circle_id: str) -> list[str]:
    rows = db.execute_query_with_value(q.LIST_CIRCLE_TAG_VOCAB, {"circle_id": circle_id})
    merged: list[str] = list(CANONICAL_TAGS)
    for r in rows:
        tag = r["tag"]
        if tag not in merged:
            merged.append(tag)
    return merged


def auto_tag_intent(db, intent_id: str, dry_run: bool = False) -> list[str]:
    """Tag one untagged intent. Returns the tags written (empty if none).

    With dry_run the full pipeline runs (including the LLM call, so the picks
    are inspectable) but nothing is written."""
    rows = db.execute_query_with_value(q.GET_INTENT_FOR_TAGGING, {"intent_id": intent_id})
    if not rows:
        infologger.warning(f"tagging_helper.auto_tag_intent | not found | intent_id={intent_id}")
        return []
    intent = rows[0]
    if intent["tags"]:
        infologger.info(f"tagging_helper.auto_tag_intent | already tagged, skipping | intent_id={intent_id}")
        return intent["tags"]

    link_meta = intent.get("link_meta")
    if isinstance(link_meta, str):
        try:
            link_meta = json.loads(link_meta)
        except json.JSONDecodeError:
            link_meta = None

    tags = heuristic_tags(intent.get("url"), link_meta)

    if settings.TAGGER_LLM_ENABLED and len(tags) < settings.TAGGER_MAX_TAGS:
        vocabulary = build_vocabulary(db, intent["circle_id"])
        try:
            for tag in fetch_llm_tags(intent, vocabulary):
                if tag not in tags:
                    tags.append(tag)
        except Exception as exc:
            # Degraded path: heuristic tags still land. ADC missing locally and
            # quota errors both end up here.
            errorlogger.error(
                f"tagging_helper.auto_tag_intent | LLM pass failed, using heuristics only "
                f"| intent_id={intent_id} | {exc}"
            )

    tags = normalize_tags(tags)[: settings.TAGGER_MAX_TAGS]
    if not tags:
        infologger.info(f"tagging_helper.auto_tag_intent | nothing fits | intent_id={intent_id}")
        return []

    if dry_run:
        infologger.info(f"tagging_helper.auto_tag_intent | DRY | intent_id={intent_id} would_tag={tags}")
        return tags

    row = db.execute_query_with_value_returning(
        q.SET_AUTO_TAGS, {"intent_id": intent_id, "tags": tags}
    )
    if not row:
        infologger.info(
            f"tagging_helper.auto_tag_intent | lost race to a manual edit | intent_id={intent_id}"
        )
        return []
    infologger.info(f"tagging_helper.auto_tag_intent | tagged | intent_id={intent_id} tags={tags}")
    return tags
