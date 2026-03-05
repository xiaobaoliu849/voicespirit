from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.llm_service import LLMService

router = APIRouter()
llm_service = LLMService()


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000)
    target_language: str = Field(..., min_length=1, max_length=40)
    source_language: str | None = Field(default="auto", max_length=40)
    provider: str = Field(default="DashScope")
    model: str | None = None


class TranslateResponse(BaseModel):
    provider: str
    model: str
    translated_text: str


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, str] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


@router.post(
    "/",
    response_model=TranslateResponse,
    responses={
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        400: {"description": "Invalid translation request payload.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
        502: {"description": "Provider upstream request failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    try:
        result = await llm_service.translate_text(
            text=payload.text,
            target_language=payload.target_language,
            source_language=payload.source_language,
            provider=payload.provider,
            model=payload.model,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "TRANSLATE_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "TRANSLATE_PROVIDER_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "TRANSLATE_INTERNAL_ERROR",
                "message": f"Translation failed: {exc}",
                "meta": {},
            },
        ) from exc
    return TranslateResponse(**result)
