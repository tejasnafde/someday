from pydantic import BaseModel, field_validator
from typing import Optional

VALID_CATEGORIES = {"watch", "eat", "visit", "read", "play", "trip", "talk", "other"}
VALID_TASK_STATUSES = {"saved", "interested", "planned", "done", "archived"}

MAX_TAGS = 12
MAX_TAG_LENGTH = 40


def normalize_tags(tags: list[str]) -> list[str]:
    """Lowercase, trim, collapse inner whitespace, dedupe preserving order.

    Applied at the API boundary so every surface (web, share sheet, auto-tagger,
    backfill) stores the same canonical form and the filter chips never split
    into case variants ("Design" next to "design")."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in tags:
        tag = " ".join(raw.strip().lower().split())[:MAX_TAG_LENGTH]
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
        if len(out) >= MAX_TAGS:
            break
    return out


class CreateIntentRequest(BaseModel):
    title: str
    url: Optional[str] = None
    note: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = []

    @field_validator("title")
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be blank")
        return v

    @field_validator("category")
    def category_valid(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("tags")
    def tags_normalized(cls, v: list[str]) -> list[str]:
        return normalize_tags(v)


class UpdateIntentRequest(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    task_status:  Optional[str] = None
    planned_for:  Optional[str] = None
    done_note:    Optional[str] = None
    done_photos:  Optional[list[str]] = None

    @field_validator("task_status")
    def status_valid(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_TASK_STATUSES:
            raise ValueError(f"task_status must be one of {VALID_TASK_STATUSES}")
        return v

    @field_validator("category")
    def category_valid(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("tags")
    def tags_normalized(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return normalize_tags(v) if v is not None else None


class IntentOut(BaseModel):
    id: str
    circle_id: str
    created_by: str
    title: str
    url: Optional[str]
    note: Optional[str]
    category: Optional[str]
    tags: list[str]
    auto_tags: list[str] = []
    task_status: str
    link_meta: Optional[dict]
    planned_for: Optional[str]
    done_note: Optional[str]
    done_photos: Optional[list]
    reaction_count: int
    reacted_by_me: bool
    boosted_by_me: bool
    created_at: str
    updated_at: str


class IntentPageOut(BaseModel):
    """Paginated intent list. next_cursor is None when there are no more pages."""
    items: list[IntentOut]
    next_cursor: Optional[str]
