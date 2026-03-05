from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import Header, HTTPException, status

from .config_loader import BackendConfig

_config = BackendConfig()
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _read_token_from_config() -> str:
    try:
        _config.reload()
        data: dict[str, Any] = _config.get_all()
    except Exception:
        return ""

    auth_settings = data.get("auth_settings", {})
    if not isinstance(auth_settings, dict):
        return ""
    return str(auth_settings.get("api_token", "")).strip()


def resolve_api_token() -> str:
    env_token = os.getenv("VOICESPIRIT_API_TOKEN", "").strip()
    if env_token:
        return env_token
    return _read_token_from_config()


def resolve_admin_token() -> str:
    env_token = os.getenv("VOICESPIRIT_ADMIN_TOKEN", "").strip()
    if env_token:
        return env_token
    try:
        _config.reload()
        data: dict[str, Any] = _config.get_all()
    except Exception:
        return ""
    auth_settings = data.get("auth_settings", {})
    if not isinstance(auth_settings, dict):
        return ""
    return str(auth_settings.get("admin_token", "")).strip()


def is_auth_enabled() -> bool:
    return bool(resolve_api_token() or resolve_admin_token())


def should_enforce_auth(method: str, path: str) -> bool:
    if not is_auth_enabled():
        return False
    return path.startswith("/api/") and method.upper() in WRITE_METHODS


def should_require_admin_auth(method: str, path: str) -> bool:
    if not should_enforce_auth(method, path):
        return False
    if not resolve_admin_token():
        return False
    return path.startswith("/api/settings")


def _missing_token_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "AUTH_TOKEN_MISSING",
            "message": "Missing Bearer token.",
            "meta": {"hint": "Use Authorization: Bearer <token>."},
        },
    )


def _invalid_token_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "AUTH_TOKEN_INVALID",
            "message": "Invalid Bearer token.",
            "meta": {},
        },
    )


def _missing_admin_token_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "AUTH_ADMIN_TOKEN_MISSING",
            "message": "Missing admin Bearer token.",
            "meta": {"hint": "Use Authorization: Bearer <admin-token>."},
        },
    )


def _invalid_admin_token_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "AUTH_ADMIN_TOKEN_INVALID",
            "message": "Invalid admin Bearer token.",
            "meta": {},
        },
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _missing_token_exception()
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        raise _missing_token_exception()
    token = value[7:].strip()
    if not token:
        raise _missing_token_exception()
    return token


def validate_auth_header(authorization: str | None, *, require_admin: bool = False) -> None:
    expected_api = resolve_api_token()
    expected_admin = resolve_admin_token()
    if not expected_api and not expected_admin:
        return

    if require_admin and expected_admin:
        if not authorization:
            raise _missing_admin_token_exception()
        value = authorization.strip()
        if not value.lower().startswith("bearer "):
            raise _missing_admin_token_exception()
        provided = value[7:].strip()
        if not provided:
            raise _missing_admin_token_exception()
        if not secrets.compare_digest(provided, expected_admin):
            raise _invalid_admin_token_exception()
        return

    provided_token = _extract_bearer_token(authorization)
    allowed = [token for token in (expected_api, expected_admin) if token]
    if not any(secrets.compare_digest(provided_token, token) for token in allowed):
        raise _invalid_token_exception()


async def require_api_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    validate_auth_header(authorization)
