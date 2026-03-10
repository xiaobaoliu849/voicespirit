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
