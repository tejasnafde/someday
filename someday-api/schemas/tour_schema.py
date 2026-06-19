"""Request/response models for tour endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class TourSeenRequest(BaseModel):
    step_ids: list[str] = Field(min_length=1)


class TourStateOut(BaseModel):
    tour_state: Optional[dict] = None
