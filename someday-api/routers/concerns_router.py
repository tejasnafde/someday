from fastapi import APIRouter, BackgroundTasks, Depends

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.discord_alert import send_concern_alert
from common_helper.response_helper import create_response
from handler.concerns_handler import ConcernsHandler
from schemas.concerns_schema import ConcernReportOut, ConcernReportRequest

router = APIRouter()
handler = ConcernsHandler()


@router.post("/concerns", response_model=ConcernReportOut, status_code=201)
@log_timing("POST /concerns")
async def report_concern(
    request: ConcernReportRequest,
    background: BackgroundTasks,
    current_user: dict = Depends(jwt_required),
):
    """Store a user's report, then alert Discord. Storing comes first so a
    failed alert never loses the report; the alert logs ERROR on failure."""
    user_id = current_user["sub"]
    # The body may hold sensitive detail, so only its size is logged.
    infologger.info(
        f"POST /concerns | user_id={user_id} category={request.category} "
        f"subject={request.subject is not None} body_len={len(request.body)}"
    )
    status, result = handler.create_report(user_id, request.category, request.subject, request.body)
    if status == 201:
        background.add_task(send_concern_alert, result["id"], user_id, request.category, request.subject, request.body)
    return create_response(status, result)
