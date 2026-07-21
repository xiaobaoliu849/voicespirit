import io
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

try:
    import pypdf
except ImportError:
    pypdf = None  # type: ignore[assignment]

from services.evermem_config import EverMemConfig
from services.llm_service import LLMService

router = APIRouter()
llm_service = LLMService()

class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)

class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail

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
    if pypdf is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "PDF_EXTRACT_MISSING_DEP", "message": "pypdf is not installed. Run: pip install pypdf", "meta": {}},
        )

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
