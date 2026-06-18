from pydantic import BaseModel


class WebPushSubscription(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
