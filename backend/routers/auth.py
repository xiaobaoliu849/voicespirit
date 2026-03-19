from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services.user_auth_service import user_auth_service

router = APIRouter()


class AuthUserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: str


class AuthSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


def _extract_bearer_token(authorization: str | None) -> str:
    value = str(authorization or "").strip()
    if not value.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_TOKEN_MISSING",
                "message": "Missing Bearer token.",
                "meta": {},
            },
        )
    token = value[7:].strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_TOKEN_MISSING",
                "message": "Missing Bearer token.",
                "meta": {},
            },
        )
    return token


def _build_session(user: dict[str, Any]) -> AuthSessionResponse:
    return AuthSessionResponse(
        access_token=user_auth_service.create_access_token(user),
        user=AuthUserResponse(**user),
    )


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    responses={
        400: {"description": "Registration failed.", "model": StructuredErrorResponse},
    },
)
async def register(payload: RegisterRequest) -> AuthSessionResponse:
    try:
        user = user_auth_service.register_user(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "AUTH_REGISTER_FAILED",
                "message": str(exc),
                "meta": {},
            },
        ) from exc
    return _build_session(user)


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    responses={
        401: {"description": "Invalid credentials.", "model": StructuredErrorResponse},
    },
)
async def login(payload: LoginRequest) -> AuthSessionResponse:
    user = user_auth_service.authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_LOGIN_FAILED",
                "message": "Incorrect email or password.",
                "meta": {},
            },
        )
    return _build_session(user)


@router.get(
    "/me",
    response_model=AuthUserResponse,
    responses={
        401: {"description": "Invalid credentials.", "model": StructuredErrorResponse},
    },
)
async def me(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthUserResponse:
    token = _extract_bearer_token(authorization)
    user = user_auth_service.verify_access_token(token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Invalid Bearer token.",
                "meta": {},
            },
        )
    return AuthUserResponse(**user)
