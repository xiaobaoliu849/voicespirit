from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services import TTSService
from services.evermem_config import EverMemConfig

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
async def list_voices(
    locale: str | None = Query(default=None, description="Locale prefix, e.g. zh-CN"),
    engine: str = Query(default="edge", description="TTS engine: edge, qwen_flash, minimax"),
) -> dict:
    try:
        voices = await tts_service.list_voices(locale=locale, engine=engine)
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
    request: Request,
    text: str = Query(..., min_length=1, max_length=3000),
    voice: str | None = Query(default=None),
    rate: str = Query(default="+0%"),
    engine: str = Query(default="edge", description="TTS engine: edge, qwen_flash, minimax"),
) -> FileResponse:
    try:
        file_path, used_voice, cache_hit = await tts_service.generate_audio(
            text=text,
            voice=voice,
            rate=rate,
            engine=engine,
        )
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

    memory_saved = False
    evermem_config = EverMemConfig()
    evermem_config.update_from_headers(dict(request.headers))
    evermem_service = evermem_config.get_service()
    if evermem_service:
        snippet = text.strip().replace("\n", " ")[:180]
        memory_text = (
            f"VoiceSpirit 语音合成已生成。音色：{used_voice}。语速：{rate}。"
            f"文本摘要：{snippet}"
        )
        try:
            saved = await evermem_service.add_memory(
                content=memory_text,
                user_id=evermem_config.memory_scope,
                sender=f"{evermem_config.memory_scope}_tts",
                sender_name="VoiceSpirit TTS",
            )
            memory_saved = saved is not None
        except Exception:
            memory_saved = False

    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename="tts_output.mp3",
        headers={
            "X-TTS-Voice": used_voice,
            "X-TTS-Engine": engine,
            "X-Cache": "HIT" if cache_hit else "MISS",
            "X-EverMem-Saved": "true" if memory_saved else "false",
        },
    )
