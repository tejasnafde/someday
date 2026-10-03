"""Request/response models for concern reports."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_BODY = 4000
MAX_SUBJECT = 200


class ConcernReportRequest(BaseModel):
    category: Literal["child_safety", "abuse", "other"]
    subject: str | None = Field(default=None, max_length=MAX_SUBJECT)
    body: str = Field(max_length=MAX_BODY)

    @field_validator("subject")
    def subject_trimmed(cls, v: str | None) -> str | None:
        return (v or "").strip() or None

    @field_validator("body")
    def body_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("body cannot be blank")
        return v


class ConcernReportOut(BaseModel):
    id: str
    category: str
    created_at: str
