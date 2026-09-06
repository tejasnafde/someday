from pydantic import BaseModel, field_validator
from typing import Optional


VALID_ROLES = {"owner", "member"}


class CreateCircleRequest(BaseModel):
    name: str
    emoji: Optional[str] = None

    @field_validator("name")
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v


class UpdateCircleRequest(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    moments_cadence: Optional[int] = None

    @field_validator("name")
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip() if v else v

    @field_validator("moments_cadence")
    def cadence_in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 3:
            raise ValueError("moments_cadence must be between 0 and 3")
        return v


class MemberOut(BaseModel):
    user_id: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    joined_at: str


class CircleOut(BaseModel):
    id: str
    name: str
    emoji: Optional[str]
    owner_id: str
    invite_token: str
    member_count: int
    open_intent_count: int
    created_at: str


class CircleDetailOut(CircleOut):
    members: list[MemberOut]
