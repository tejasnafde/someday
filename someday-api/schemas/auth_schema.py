from pydantic import BaseModel
from typing import Optional

from schemas.circles_schema import CircleOut


class UserOut(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    tour_state: Optional[dict] = None


class UserResponse(BaseModel):
    user: UserOut


class MeOut(BaseModel):
    user: UserOut
    circles: list[CircleOut]


class WebviewSessionOut(BaseModel):
    access_token: str
    refresh_token: str
