from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.desktop_diagnostics_service import DesktopDiagnosticsService
from services.config_loader import GOOGLE_INTERACTIONS_BASE_URL
from services.settings_service import SettingsService

router = APIRouter()
settings_service = SettingsService()
desktop_diagnostics_service = DesktopDiagnosticsService()


class SettingsResponse(BaseModel):
    config_path: str
    providers: list[str]
    settings: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    merge: bool = Field(default=True, description="Merge into existing config when true; replace when false.")
    settings: dict[str, Any] = Field(default_factory=dict, description="Partial settings object to update.")


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


class DesktopStatusResponse(BaseModel):
    runtime_dir: str
    diagnostics_dir: str
    preflight: dict[str, Any]
    latest_error: dict[str, Any]


@router.get(
    "/",
    response_model=SettingsResponse,
    responses={
        500: {"description": "Failed to load settings.", "model": StructuredErrorResponse},
    },
)
async def get_settings() -> SettingsResponse:
    try:
        result = settings_service.get_settings()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SETTINGS_LOAD_FAILED",
                "message": f"Load settings failed: {exc}",
                "meta": {},
            },
        ) from exc
    return SettingsResponse(**result)


@router.get(
    "/desktop-status",
    response_model=DesktopStatusResponse,
    responses={
        500: {"description": "Failed to load desktop status.", "model": StructuredErrorResponse},
    },
)
async def get_desktop_status() -> DesktopStatusResponse:
    try:
        result = desktop_diagnostics_service.get_status()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DESKTOP_STATUS_LOAD_FAILED",
                "message": f"Load desktop status failed: {exc}",
                "meta": {},
            },
        ) from exc
    return DesktopStatusResponse(**result)


@router.put(
    "/",
    response_model=SettingsResponse,
    responses={
        401: {"description": "Missing admin Bearer token when admin token is enabled.", "model": StructuredErrorResponse},
        400: {"description": "Settings patch validation failed.", "model": StructuredErrorResponse},
        403: {"description": "Authentication token invalid or non-admin token used.", "model": StructuredErrorResponse},
        500: {"description": "Settings update failed.", "model": StructuredErrorResponse},
    },
)
async def update_settings(payload: SettingsUpdateRequest) -> SettingsResponse:
    try:
        result = settings_service.update_settings(payload.settings, merge=payload.merge)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "SETTINGS_BAD_REQUEST", "message": str(exc), "meta": {}},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SETTINGS_UPDATE_FAILED",
                "message": f"Update settings failed: {exc}",
                "meta": {},
            },
        ) from exc
    return SettingsResponse(**result)


class FetchModelsRequest(BaseModel):
    api_key: str | None = Field(default=None, description="Optional API key override")
    base_url: str | None = Field(default=None, description="Optional API base URL override")


class FetchModelsResponse(BaseModel):
    provider: str
    models: list[str]
    tts_models: list[str] = Field(default_factory=list)


GOOGLE_MODEL_LIST_SUPPLEMENTS = [
    "gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini-3.1-flash-live-preview",
    "gemini-3.5-live-translate-preview",
]
DASHSCOPE_MODEL_LIST_SUPPLEMENTS = [
    "qwen-audio-3.0-tts-plus",
    "qwen-audio-3.0-tts-flash",
    "qwen3-tts-flash-2025-11-27",
    "cosyvoice-v2-1.5",
    "cosyvoice-v1",
    "qwen-tts-v2",
    "sambert-zhichu-v1",
]
GOOGLE_MODELS_BASE_URL = GOOGLE_INTERACTIONS_BASE_URL


def _filter_dashscope_models(model_ids: list[str]) -> list[str]:
    """
    Filter DashScope model list down to production-grade API alias models only.

    Strategy: blocklist noise rather than whitelist specific model names.
    DashScope exposes two distinct categories:
      - Product API aliases  (e.g. qwen-max, qwen-plus, deepseek-r1, qwq-32b)
        -> no or symbolic parameter-count suffix; these track "latest" automatically.
      - Raw academic checkpoints  (e.g. qwen2.5-72b-instruct, deepseek-r1-distill-llama-8b)
        -> carry explicit size suffixes like -7b / -72b; NOT meant for product API use.

    Noise patterns we strip:
      1. Explicit parameter-size suffixes  (-7b, -14b, -32b, -72b, -0.5b, -1.5b, -3b, etc.)
      2. Distillation checkpoints          (-distill-)
      3. Quantization variants             (-int4, -int8, -fp16)
      4. Date-stamped snapshots            (-20xxxxxx or -2025xxxx style 6-8 digit suffix)
         EXCEPTION: keep qwen3-tts-flash-2025-11-27 which is a production TTS model
      5. Non-DashScope models that leaked in from gateway responses
    """
    import re

    # VoiceSpirit only uses DashScope for:
    #   - Qwen/QwQ chat models  (qwen-max, qwen-plus, qwq-32b …)  → back AI conversation
    #   - Voice synthesis models (qwen-audio-*, cosyvoice-*, sambert-*) → TTS
    # Excluded intentionally:
    #   - deepseek-* : pure text/coding LLMs, no voice relevance
    #   - paraformer-*, sensevoice-* : ASR (speech recognition), separate concern
    #   - farui-* : enterprise compliance tool, out of scope
    _DASHSCOPE_PREFIXES = (
        "qwen", "qwq", "cosyvoice", "sambert",
    )

    # Parameter-size-like suffixes that indicate raw academic checkpoints, NOT product APIs.
    # We match things like -7b, -14b, -72b, -0.5b, -1.5b, -3b at a word boundary.
    # NOTE: MoE models use -235b-a22b pattern; the -a22b part is the active-param suffix
    # which we do NOT want to block — only block the raw dense parameter suffixes.
    _SIZE_SUFFIX_RE = re.compile(r"(?<!-a)-\d*\.?\d+b\b", re.IGNORECASE)

    # Date-snapshot suffix: 6–8 consecutive digits at end (e.g. -20241018, -20250601)
    _DATE_SUFFIX_RE = re.compile(r"-\d{6,8}$")

    # Known TTS production model that happens to end with a date string — keep it
    _TTS_DATE_WHITELIST = {"qwen3-tts-flash-2025-11-27"}

    filtered: list[str] = []
    for m in model_ids:
        raw = m.strip()
        if not raw:
            continue
        low = raw.lower()

        # 1. Must belong to a DashScope official model family
        if not any(low.startswith(p) for p in _DASHSCOPE_PREFIXES):
            continue

        # 2. Strip distillation checkpoints (e.g. deepseek-r1-distill-qwen-7b)
        if "-distill-" in low:
            continue

        # 3. Strip quantization variants
        if any(q in low for q in ("-int4", "-int8", "-fp16")):
            continue

        # 4. Strip models with an explicit parameter-size suffix (raw checkpoints)
        #    e.g. qwen2.5-72b-instruct, qwen3-7b-instruct  → skip (raw dense checkpoints)
        #    but  qwen-max, qwq-32b, deepseek-r1            → keep (product aliases)
        #    and  qwen3-235b-a22b, qwen3-30b-a3b            → keep (MoE flagship products)
        if _SIZE_SUFFIX_RE.search(low):
            # MoE models (e.g. qwen3-235b-a22b) have a dense total followed by -a<N>b active params.
            # They are product-grade and should be kept despite having a size in their name.
            is_moe = bool(re.search(r"-\d+b-a\d+b", low))
            if not is_moe:
                # Block versioned raw dense checkpoints: qwen\d.x-Nb-instruct style
                if re.match(r"(qwen\d|deepseek-v\d)", low):
                    continue
                # Also block if there's a role suffix after the size
                if re.search(r"-\d*\.?\d+b-(instruct|chat|base|preview)", low):
                    continue

        # 5. Strip date-snapshot suffixes (e.g. qwen-max-20241018)
        if raw not in _TTS_DATE_WHITELIST and _DATE_SUFFIX_RE.search(low):
            continue

        filtered.append(raw)

    return filtered


@router.post(
    "/providers/{provider}/fetch-models",
    response_model=FetchModelsResponse,
    responses={
        400: {"description": "Validation error or invalid provider.", "model": StructuredErrorResponse},
        500: {"description": "Failed to fetch models.", "model": StructuredErrorResponse},
    },
)
async def fetch_models(provider: str, payload: FetchModelsRequest) -> FetchModelsResponse:
    cfg_settings = {}
    try:
        cfg_settings = settings_service.config.get_provider_settings(provider)
    except Exception:
        pass

    api_key = (payload.api_key or "").strip()
    if not api_key and cfg_settings:
        api_key = cfg_settings.get("api_key", "").strip()

    if provider == "Ollama" and not api_key:
        api_key = "ollama"

    base_url = (payload.base_url or "").strip()
    if not base_url and cfg_settings:
        base_url = cfg_settings.get("base_url", "").strip()

    if not base_url:
        from services.config_loader import DEFAULT_BASE_URLS
        if provider == "Google":
            base_url = GOOGLE_MODELS_BASE_URL
        else:
            base_url = DEFAULT_BASE_URLS.get(provider, "").strip()

    base_url = base_url.rstrip("/")

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_API_KEY",
                "message": f"API key is required to fetch models for {provider}.",
                "meta": {},
            },
        )
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_BASE_URL",
                "message": f"Base URL is required to fetch models for {provider}.",
                "meta": {},
            },
        )

    if provider == "Ollama":
        base = base_url
        if base.endswith("/v1"):
            base = base[:-3]
        url = f"{base}/api/tags"
        headers = {
            "Accept": "application/json",
        }
        if api_key and api_key != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"
    else:
        url = f"{base_url}/models"
        headers = {"Accept": "application/json"}
        if provider == "Google":
            headers["x-goog-api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        if provider == "OpenRouter":
            headers["HTTP-Referer"] = "https://voicespirit.local"
            headers["X-Title"] = "VoiceSpirit"

    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "FETCH_MODELS_HTTP_ERROR",
                "message": f"Provider returned status {exc.response.status_code}: {detail}",
                "meta": {},
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "FETCH_MODELS_FAILED",
                "message": f"Failed to connect to provider: {exc}",
                "meta": {},
            },
        ) from exc

    try:
        data = response.json()
        model_ids = []
        if provider == "Ollama":
            raw_models = data.get("models", [])
            for m in raw_models:
                if isinstance(m, dict) and "name" in m:
                    model_ids.append(str(m["name"]))
        else:
            if provider == "Google":
                raw_models = data.get("models", [])
            else:
                raw_models = data.get("data", [])
            if not isinstance(raw_models, list):
                if isinstance(data, list):
                    raw_models = data
                else:
                    raw_models = []

            for m in raw_models:
                if isinstance(m, dict) and provider == "Google":
                    model_id = str(m.get("name") or m.get("baseModelId") or "").strip()
                    if model_id.startswith("models/"):
                        model_id = model_id.removeprefix("models/")
                    if model_id:
                        model_ids.append(model_id)
                elif isinstance(m, dict) and "id" in m:
                    model_ids.append(str(m["id"]))
                elif isinstance(m, str):
                    model_ids.append(m)

        if provider == "Google":
            model_ids.extend(GOOGLE_MODEL_LIST_SUPPLEMENTS)
        elif provider == "DashScope":
            model_ids.extend(DASHSCOPE_MODEL_LIST_SUPPLEMENTS)
            model_ids = _filter_dashscope_models(model_ids)

        model_ids = sorted(list(set(model_ids)))
        tts_keywords = ("tts", "speech", "cosyvoice", "sambert", "voice", "eleven", "qwen-audio")
        tts_ids = [m for m in model_ids if any(kw in m.lower() for kw in tts_keywords)]
        chat_ids = [m for m in model_ids if m not in tts_ids]

        return FetchModelsResponse(provider=provider, models=chat_ids, tts_models=tts_ids)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "FETCH_MODELS_PARSE_FAILED",
                "message": f"Failed to parse models list from provider response: {exc}",
                "meta": {},
            },
        ) from exc
