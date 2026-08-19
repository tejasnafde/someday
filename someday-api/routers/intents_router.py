from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.notify import Notify
from common_helper.product_analytics import track_product_event
from common_helper.response_helper import create_response
from handler.intents_handler import IntentsHandler
from handler.unfurl_handler import fetch_link_meta
from schemas.intents_schema import CreateIntentRequest, UpdateIntentRequest

router = APIRouter()
handler = IntentsHandler()
notify = Notify()


@router.get("/circles/{circle_id}/intents")
@log_timing("GET /circles/:id/intents")
async def list_intents(
    circle_id: str,
    current_user: dict = Depends(jwt_required),
    task_status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    shortlist: bool = Query(default=False),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    infologger.info(
        f"GET /circles/{circle_id}/intents | user_id={current_user['sub']} "
        f"task_status={task_status} category={category} shortlist={shortlist} cursor={cursor!r}"
    )
    status, result = handler.list_intents(
        circle_id, current_user["sub"], task_status, category, tag, shortlist, cursor, limit
    )
    return create_response(status, result)


@router.post("/circles/{circle_id}/intents")
@log_timing("POST /circles/:id/intents")
async def create_intent(
    circle_id: str,
    request: CreateIntentRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(jwt_required),
):
    infologger.info(
        f"POST /circles/{circle_id}/intents | user_id={current_user['sub']} "
        f"payload={request.model_dump()}"
    )
    link_meta = None
    if request.url:
        link_meta = fetch_link_meta(request.url)

    status, result = handler.create_intent(circle_id, request, current_user["sub"], link_meta)
    if status == 201:
        background_tasks.add_task(notify.intent_created, result["id"], current_user["sub"])
        background_tasks.add_task(track_product_event, "item_created", "items")
        if handler.count_created_intents(current_user["sub"]) == 1:
            background_tasks.add_task(
                track_product_event,
                "activation_milestone_reached",
                "items",
            )
    return create_response(status, result)


@router.get("/intents/{intent_id}")
@log_timing("GET /intents/:id")
async def get_intent(intent_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /intents/{intent_id} | user_id={current_user['sub']}")
    status, result = handler.get_intent(intent_id, current_user["sub"])
    return create_response(status, result)


@router.patch("/intents/{intent_id}")
@log_timing("PATCH /intents/:id")
async def update_intent(
    intent_id: str,
    request: UpdateIntentRequest,
    current_user: dict = Depends(jwt_required),
):
    infologger.info(
        f"PATCH /intents/{intent_id} | user_id={current_user['sub']} "
        f"payload={request.model_dump(exclude_none=True)}"
    )
    status, result = handler.update_intent(intent_id, request, current_user["sub"])
    return create_response(status, result)


@router.delete("/intents/{intent_id}")
@log_timing("DELETE /intents/:id")
async def delete_intent(intent_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"DELETE /intents/{intent_id} | user_id={current_user['sub']}")
    status, result = handler.delete_intent(intent_id, current_user["sub"])
    return create_response(status, result)


@router.post("/intents/{intent_id}/photos")
@log_timing("POST /intents/:id/photos")
async def upload_memory_photo(
    intent_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(jwt_required),
):
    infologger.info(f"POST /intents/{intent_id}/photos | user_id={current_user['sub']}")
    content = await file.read()
    status, result = handler.upload_memory_photo(
        intent_id, current_user["sub"], content, file.content_type or ""
    )
    return create_response(status, result)


@router.post("/intents/{intent_id}/react")
@log_timing("POST /intents/:id/react")
async def toggle_reaction(
    intent_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(jwt_required),
):
    infologger.info(f"POST /intents/{intent_id}/react | user_id={current_user['sub']}")
    status, result = handler.toggle_reaction(intent_id, current_user["sub"])
    if result.get("reacted"):
        background_tasks.add_task(notify.reaction_added, intent_id, current_user["sub"])
    return create_response(status, result)


@router.post("/intents/{intent_id}/refresh-preview")
@log_timing("POST /intents/:id/refresh-preview")
async def refresh_preview(intent_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /intents/{intent_id}/refresh-preview | user_id={current_user['sub']}")
    status, result = handler.refresh_preview(intent_id, current_user["sub"])
    return create_response(status, result)


@router.post("/intents/{intent_id}/boost")
@log_timing("POST /intents/:id/boost")
async def toggle_boost(
    intent_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(jwt_required),
):
    infologger.info(f"POST /intents/{intent_id}/boost | user_id={current_user['sub']}")
    status, result = handler.toggle_boost(intent_id, current_user["sub"])
    if result.get("boosted"):
        background_tasks.add_task(notify.boost_added, intent_id, current_user["sub"])
    return create_response(status, result)
