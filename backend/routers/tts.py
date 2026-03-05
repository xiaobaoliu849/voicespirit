from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services import TTSService

router = APIRouter()
tts_service = TTSService()


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


@router.get(
    "/voices",
    responses={
        400: {"description": "Invalid voices query.", "model": StructuredErrorResponse},
        500: {"description": "Failed to list voices.", "model": StructuredErrorResponse},
    },
)
async def list_voices(locale: str | None = Query(default=None, description="Locale prefix, e.g. zh-CN")) -> dict:
    try:
        voices = await tts_service.list_voices(locale=locale)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "TTS_VOICES_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "TTS_VOICES_INTERNAL_ERROR", "message": f"List voices failed: {exc}", "meta": {}},
        ) from exc
    return {"count": len(voices), "voices": voices}


@router.get(
    "/speak",
    responses={
        400: {"description": "Invalid TTS request.", "model": StructuredErrorResponse},
        503: {"description": "TTS dependency unavailable.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected server error.", "model": StructuredErrorResponse},
    },
)
async def speak(
    text: str = Query(..., min_length=1, max_length=3000),
    voice: str | None = Query(default=None),
    rate: str = Query(default="+0%"),
) -> FileResponse:
    try:
        file_path, used_voice, cache_hit = await tts_service.generate_audio(text=text, voice=voice, rate=rate)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "TTS_SPEAK_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "TTS_SPEAK_DEPENDENCY_ERROR", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "TTS_SPEAK_INTERNAL_ERROR",
                "message": f"TTS generation failed: {exc}",
                "meta": {},
            },
        ) from exc

    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename="tts_output.mp3",
        headers={
            "X-TTS-Voice": used_voice,
            "X-Cache": "HIT" if cache_hit else "MISS",
        },
    )
