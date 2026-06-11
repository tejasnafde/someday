from pydantic import BaseModel, field_validator
from typing import Optional

VALID_CATEGORIES = {"watch", "eat", "visit", "read", "play", "trip", "talk", "other"}
VALID_TASK_STATUSES = {"saved", "interested", "planned", "done", "archived"}


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


class UpdateIntentRequest(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    task_status: Optional[str] = None
    planned_for: Optional[str] = None

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


class IntentOut(BaseModel):
    id: str
    circle_id: str
    created_by: str
    title: str
    url: Optional[str]
    note: Optional[str]
    category: Optional[str]
    tags: list[str]
    task_status: str
    link_meta: Optional[dict]
    planned_for: Optional[str]
    reaction_count: int
    boosted_by_me: bool
    created_at: str
    updated_at: str
