from pydantic import BaseModel
from typing import Optional


class SmartPick(BaseModel):
    intent_id: str
    title: str
    link_meta: Optional[dict]
    score: float
    breakdown: dict  # {"mutual_ratio": 0.9, "days_saved": 42, "has_boost": True, "points": {...}}


class SmartPickOut(BaseModel):
    pick: Optional[SmartPick]  # None when nothing is eligible; reason says why
    reason: Optional[str]


class SpinOut(BaseModel):
    shortlist: list[dict]  # shuffled shortlisted intents - frontend animates the wheel
