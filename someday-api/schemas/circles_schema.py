from pydantic import BaseModel, field_validator
from typing import Optional


VALID_ROLES = {"owner", "member"}


class CreateCircleRequest(BaseModel):
    name: str
    emoji: Optional[str] = None

    @field_validator("name")
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip()


class UpdateCircleRequest(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None

    @field_validator("name")
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip() if v else v


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
