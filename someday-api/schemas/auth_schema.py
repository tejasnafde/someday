from pydantic import BaseModel
from typing import Optional


class UserOut(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]


class MeOut(BaseModel):
    user: UserOut
    circles: list[dict]  # lightweight circle list for home screen
