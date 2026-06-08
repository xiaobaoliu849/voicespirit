from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.desktop_diagnostics_service import DesktopDiagnosticsService
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

    base_url = (payload.base_url or "").strip()
    if not base_url and cfg_settings:
        base_url = cfg_settings.get("base_url", "").strip()

    if not base_url:
        from services.config_loader import DEFAULT_BASE_URLS
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

    url = f"{base_url}/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
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
        raw_models = data.get("data", [])
        if not isinstance(raw_models, list):
            if isinstance(data, list):
                raw_models = data
            else:
                raw_models = []

        model_ids = []
        for m in raw_models:
            if isinstance(m, dict) and "id" in m:
                model_ids.append(str(m["id"]))
            elif isinstance(m, str):
                model_ids.append(m)

        model_ids = sorted(list(set(model_ids)))

        return FetchModelsResponse(provider=provider, models=model_ids)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "FETCH_MODELS_PARSE_FAILED",
                "message": f"Failed to parse models list from provider response: {exc}",
                "meta": {},
            },
        ) from exc

