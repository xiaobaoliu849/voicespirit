from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from services.qwen_voice_service import QwenVoiceService

VoiceType = Literal["voice_design", "voice_clone"]

router = APIRouter()
voice_service = QwenVoiceService()


class VoiceDesignRequest(BaseModel):
    voice_prompt: str = Field(..., min_length=1, max_length=4000)
    preview_text: str = Field(..., min_length=1, max_length=1200)
    preferred_name: str = Field(..., min_length=1, max_length=80)
    language: str = Field(default="zh", min_length=1, max_length=20)


class VoiceCreateResponse(BaseModel):
    voice: str
    type: VoiceType
    target_model: str
    preferred_name: str
    language: str | None = None
    preview_audio_data: str | None = None


class VoiceListResponse(BaseModel):
    voice_type: VoiceType
    count: int
    voices: list[dict[str, Any]]


class VoiceDeleteResponse(BaseModel):
    voice: str
    type: VoiceType
    deleted: bool


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


@router.post(
    "/design",
    response_model=VoiceCreateResponse,
    responses={
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
        400: {"description": "Invalid voice design request.", "model": StructuredErrorResponse},
        502: {"description": "Provider upstream request failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def create_voice_design(payload: VoiceDesignRequest) -> VoiceCreateResponse:
    try:
        result = await voice_service.create_voice_design(
            voice_prompt=payload.voice_prompt,
            preview_text=payload.preview_text,
            preferred_name=payload.preferred_name,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VOICE_DESIGN_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "VOICE_DESIGN_PROVIDER_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "VOICE_DESIGN_INTERNAL_ERROR",
                "message": f"Create voice design failed: {exc}",
                "meta": {},
            },
        ) from exc
    return VoiceCreateResponse(**result)


@router.post(
    "/clone",
    response_model=VoiceCreateResponse,
    responses={
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
        400: {"description": "Invalid voice clone request.", "model": StructuredErrorResponse},
        502: {"description": "Provider upstream request failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def create_voice_clone(
    preferred_name: str = Form(..., min_length=1, max_length=80),
    audio_file: UploadFile = File(...),
) -> VoiceCreateResponse:
    if not audio_file.filename:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VOICE_CLONE_BAD_REQUEST",
                "message": "audio_file is required.",
                "meta": {},
            },
        )

    data = await audio_file.read()
    if not data:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VOICE_CLONE_BAD_REQUEST",
                "message": "audio_file is empty.",
                "meta": {},
            },
        )

    try:
        result = await voice_service.create_voice_clone(
            audio_bytes=data,
            mime_type=audio_file.content_type or "",
            preferred_name=preferred_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VOICE_CLONE_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "VOICE_CLONE_PROVIDER_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "VOICE_CLONE_INTERNAL_ERROR",
                "message": f"Create voice clone failed: {exc}",
                "meta": {},
            },
        ) from exc
    return VoiceCreateResponse(**result)


@router.get(
    "/",
    response_model=VoiceListResponse,
    responses={
        400: {"description": "Invalid voice list query.", "model": StructuredErrorResponse},
        502: {"description": "Provider upstream request failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def list_voices(
    voice_type: VoiceType = Query(default="voice_design"),
    page_index: int = Query(default=0, ge=0),
    page_size: int = Query(default=100, ge=1, le=200),
) -> VoiceListResponse:
    try:
        result = await voice_service.list_voices(
            voice_type=voice_type,
            page_index=page_index,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VOICE_LIST_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "VOICE_LIST_PROVIDER_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "VOICE_LIST_INTERNAL_ERROR",
                "message": f"List voices failed: {exc}",
                "meta": {},
            },
        ) from exc
    return VoiceListResponse(**result)


@router.delete(
    "/{voice_name}",
    response_model=VoiceDeleteResponse,
    responses={
        401: {"description": "Missing Bearer token when write auth is enabled.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid.", "model": StructuredErrorResponse},
        400: {"description": "Invalid delete request.", "model": StructuredErrorResponse},
        502: {"description": "Provider upstream request failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def delete_voice(
    voice_name: str,
    voice_type: VoiceType = Query(default="voice_design"),
) -> VoiceDeleteResponse:
    try:
        result = await voice_service.delete_voice(voice_name=voice_name, voice_type=voice_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VOICE_DELETE_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "VOICE_DELETE_PROVIDER_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "VOICE_DELETE_INTERNAL_ERROR",
                "message": f"Delete voice failed: {exc}",
                "meta": {},
            },
        ) from exc
    return VoiceDeleteResponse(**result)
