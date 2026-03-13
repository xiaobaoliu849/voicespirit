from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.evermem_config import EverMemConfig

router = APIRouter()


class ConversationMetaRequest(BaseModel):
    group_id: str | None = Field(default=None, min_length=1, max_length=256)


class ConversationMetaResponse(BaseModel):
    group_id: str
    user_id: str


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


@router.post(
    "/conversation-meta",
    response_model=ConversationMetaResponse,
    responses={
        400: {"description": "EverMem is not enabled for the request.", "model": StructuredErrorResponse},
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
        502: {"description": "EverMem upstream request failed.", "model": StructuredErrorResponse},
    },
)
async def create_conversation_meta(
    payload: ConversationMetaRequest,
    request: Request,
) -> ConversationMetaResponse:
    config = EverMemConfig()
    config.update_from_headers(dict(request.headers))
    service = config.get_service()
    if not service:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EVERMEM_NOT_CONFIGURED",
                "message": "EverMem is not enabled or configured for this request.",
                "meta": {},
            },
        )

    requested_group_id = (payload.group_id or "").strip() or None
    result = await service.create_conversation_meta(
        user_id=config.memory_scope,
        group_id=requested_group_id,
    )
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EVERMEM_CONVERSATION_META_FAILED",
                "message": "EverMem did not return valid conversation metadata.",
                "meta": {},
            },
        )

    resolved_group_id = str(result.get("group_id", "")).strip()
    if not resolved_group_id:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EVERMEM_GROUP_ID_MISSING",
                "message": "EverMem response did not include a group_id.",
                "meta": {},
            },
        )

    resolved_user_id = str(result.get("user_id", "")).strip() or config.memory_scope
    return ConversationMetaResponse(group_id=resolved_group_id, user_id=resolved_user_id)
