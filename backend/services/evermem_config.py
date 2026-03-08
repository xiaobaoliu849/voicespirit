"""Shared EverMemOS configuration helpers."""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from .evermem_service import EverMemService

logger = logging.getLogger(__name__)

DEFAULT_EVERMEM_URL = os.getenv("EVERMEM_API_URL", "https://api.evermind.ai").strip()


def _clean_header_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _hash_scope(prefix: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


class EverMemConfig:
    def __init__(self) -> None:
        self.enabled: bool = False
        self.url: str = DEFAULT_EVERMEM_URL
        self.key: str | None = None
        self.memory_scope: str = "anonymous"
        self._service: EverMemService | None = None

    def _resolve_scope(self, headers: dict[str, Any]) -> str:
        authorization = _clean_header_value(headers.get("Authorization"))
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
            if token:
                return _hash_scope("token", token)

        client_id = _clean_header_value(headers.get("X-Client-ID"))
        if client_id:
            return _hash_scope("client", client_id)

        request_id = _clean_header_value(headers.get("X-Request-ID"))
        if request_id:
            return _hash_scope("request", request_id)

        return "anonymous"

    def update_from_headers(self, headers: dict[str, Any]) -> None:
        enabled_header = _clean_header_value(headers.get("X-EverMem-Enabled")).lower()
        header_url = _clean_header_value(headers.get("X-EverMem-Url"))
        header_key = _clean_header_value(headers.get("X-EverMem-Key"))
        env_key = os.getenv("EVERMEM_API_KEY", "").strip()

        self.enabled = enabled_header == "true"
        self.url = header_url or DEFAULT_EVERMEM_URL
        self.key = header_key or env_key or None
        self.memory_scope = self._resolve_scope(headers)

        if self.enabled and self.key:
            self._service = EverMemService(api_url=self.url, api_key=self.key)
        else:
            self._service = None

    def get_service(self) -> EverMemService | None:
        return self._service
