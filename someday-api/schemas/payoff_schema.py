from pydantic import BaseModel
from typing import Optional


class SmartPickOut(BaseModel):
    intent_id: str
    title: str
    link_meta: Optional[dict]
    score: float
    breakdown: dict  # {"mutual_ratio": 0.9, "days_saved": 42, "has_boost": True, "points": {...}}


class SpinOut(BaseModel):
    shortlist: list[dict]  # shuffled shortlisted intents - frontend animates the wheel
