"""Request/response models for tour endpoints."""

from pydantic import BaseModel, Field


class TourSeenRequest(BaseModel):
    step_ids: list[str] = Field(min_length=1)
