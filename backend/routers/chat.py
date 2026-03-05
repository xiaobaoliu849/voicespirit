from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.llm_service import LLMService

router = APIRouter()
llm_service = LLMService()


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    provider: str = Field(default="DashScope")
    model: str | None = None
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class ChatResponse(BaseModel):
    provider: str
    model: str
    reply: str
    raw: dict[str, Any]


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


def _sse_event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post(
    "/completions",
    response_model=ChatResponse,
    responses={
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        400: {"description": "Invalid chat request payload.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
        502: {"description": "Provider upstream request failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def create_chat_completion(payload: ChatRequest) -> ChatResponse:
    try:
        result = await llm_service.chat_completion(
            provider=payload.provider,
            model=payload.model,
            messages=[item.model_dump() for item in payload.messages],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "CHAT_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "CHAT_PROVIDER_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "CHAT_INTERNAL_ERROR",
                "message": f"Chat request failed: {exc}",
                "meta": {},
            },
        ) from exc
    return ChatResponse(**result)


@router.post(
    "/completions/stream",
    responses={
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
    },
)
async def create_chat_completion_stream(payload: ChatRequest) -> StreamingResponse:
    async def event_generator():
        try:
            async for event in llm_service.chat_completion_stream(
                provider=payload.provider,
                model=payload.model,
                messages=[item.model_dump() for item in payload.messages],
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ):
                event_type = str(event.get("type", "message"))
                event_data = {k: v for k, v in event.items() if k != "type"}
                yield _sse_event(event_type, event_data)
        except ValueError as exc:
            yield _sse_event("error", {"detail": str(exc), "code": "bad_request"})
        except RuntimeError as exc:
            yield _sse_event("error", {"detail": str(exc), "code": "provider_error"})
        except Exception as exc:
            yield _sse_event(
                "error",
                {"detail": f"Chat stream failed: {exc}", "code": "internal_error"},
            )

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )
