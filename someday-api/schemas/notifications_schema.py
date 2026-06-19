from pydantic import BaseModel


class NotificationFeedOut(BaseModel):
    unseen: int
    items: list[dict]


class OkOut(BaseModel):
    ok: bool
