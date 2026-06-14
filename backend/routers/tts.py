import io
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import pypdf

from services import TTSService
from services.evermem_config import EverMemConfig
from services.llm_service import LLMService

router = APIRouter()
tts_service = TTSService()
llm_service = LLMService()


def _normalize_query_optional(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_query_string(value: Any, default: str) -> str:
    if not isinstance(value, str):
        return default
    normalized = value.strip()
    return normalized or default


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
    engine: str = Query(default="edge", description="TTS engine: edge, qwen_flash, minimax, xiaomi"),
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
    voice_b: str | None = Query(default=None),
    rate: str = Query(default="+0%"),
    engine: str = Query(default="edge", description="TTS engine: edge, qwen_flash, minimax, xiaomi"),
) -> FileResponse:
    # FastAPI injects concrete values for HTTP requests. Direct route tests pass
    # Query objects for omitted defaults, so normalize all optional inputs here.
    voice = _normalize_query_optional(voice)
    voice_b = _normalize_query_optional(voice_b)
    rate = _normalize_query_string(rate, "+0%")
    engine = _normalize_query_string(engine, "edge")

    try:
        if voice_b:
            file_path = await tts_service.generate_dialogue_audio(
                text=text,
                voice_a=voice,
                voice_b=voice_b,
                rate=rate,
                engine=engine,
            )
            used_voice = f"{voice} + {voice_b}"
            cache_hit = False
        else:
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


@router.post(
    "/extract-pdf",
    responses={
        400: {"description": "Invalid PDF file or extraction failed.", "model": StructuredErrorResponse},
        500: {"description": "Unexpected error during extraction.", "model": StructuredErrorResponse},
    },
)
async def extract_pdf(
    file: UploadFile = File(..., description="The PDF file to extract text from")
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PDF_EXTRACT_BAD_REQUEST",
                "message": "Only PDF files are supported.",
                "meta": {},
            },
        )

    try:
        content = await file.read()
        pdf_file = io.BytesIO(content)
        reader = pypdf.PdfReader(pdf_file)

        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)

        full_text = "\n\n".join(extracted_text)

        return {
            "filename": file.filename,
            "page_count": len(reader.pages),
            "text": full_text,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PDF_EXTRACT_INTERNAL_ERROR",
                "message": f"Failed to extract text from PDF: {exc}",
                "meta": {},
            },
        ) from exc


class PolishTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=30000)
    provider: str | None = Field(default=None)
    model: str | None = Field(default=None)


class PolishTextResponse(BaseModel):
    provider: str
    model: str | None
    polished_text: str


@router.post(
    "/polish-pdf-text",
    response_model=PolishTextResponse,
    responses={
        400: {"description": "Invalid request.", "model": StructuredErrorResponse},
        500: {"description": "Failed to polish text.", "model": StructuredErrorResponse},
    },
)
async def polish_pdf_text(payload: PolishTextRequest) -> PolishTextResponse:
    cleaned = payload.text.strip()
    if not cleaned:
        raise HTTPException(
            status_code=400,
            detail={"code": "TTS_POLISH_BAD_REQUEST", "message": "Text is empty.", "meta": {}},
        )

    # Resolve provider and model if not provided
    provider = payload.provider
    model = payload.model
    if not provider:
        # Check active API keys in configuration
        config_data = llm_service.config.get_all()
        api_keys = config_data.get("api_keys", {})
        from services.config_loader import PROVIDER_KEY_MAP
        for p in ["DashScope", "DeepSeek", "SiliconFlow", "Google", "Groq", "OpenRouter", "Ollama"]:
            key_name = PROVIDER_KEY_MAP.get(p)
            if key_name and (api_keys.get(key_name) or p == "Ollama"):
                provider = p
                break
        if not provider:
            provider = "DashScope"  # fallback default

    system_prompt = (
        "You are an expert assistant designed to optimize text for Text-to-Speech (TTS) synthesis.\n"
        "Your task is to take raw extracted PDF text (which contains LaTeX, math formulas, headers, footers, page numbers, citation brackets) and rewrite/polish it so it reads smoothly as natural spoken language.\n"
        "Follow these rules strictly:\n"
        "1. Remove reading noise: page numbers, running headers/footers, citation brackets (e.g. [1], Ref [2]), URLs, and bibliography references.\n"
        "2. Convert math equations and formulas: Translate mathematical symbols and LaTeX expressions into their spoken language equivalents (e.g., '$n \\ge 3$' to 'n大于等于3' or 'n is greater than or equal to 3').\n"
        "3. Resolve word breaks: Connect hyphenated words split across line breaks (e.g., 'sub- stantial' to 'substantial').\n"
        "4. Preserve core meaning: Do not summarize or omit sentences. Just clean up noise and expand notations.\n"
        "5. Output format: Return ONLY the polished text. Do not output any markdown blocks, introductions, notes, or explanations."
    )

    try:
        result = await llm_service.chat_completion(
            provider=provider,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cleaned},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        return PolishTextResponse(
            provider=result["provider"],
            model=result["model"],
            polished_text=result["reply"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "TTS_POLISH_INTERNAL_ERROR",
                "message": f"Failed to polish text: {exc}",
                "meta": {},
            },
        ) from exc

