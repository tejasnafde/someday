from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.unfurlhandler import UnfurlHandler

router = APIRouter()
handler = UnfurlHandler()


class UnfurlRequest(BaseModel):
    url: str


@router.post("")
@log_timing("POST /unfurl")
async def unfurl(request: UnfurlRequest, current_user: dict = Depends(jwt_required)):
    """Fetch OG metadata for a URL. Used by the share flow."""
    infologger.info(f"POST /unfurl | user_id={current_user['sub']} url={request.url}")
    status, result = handler.unfurl(request.url)
    return create_response(status, result)
