from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

PROVIDER_KEY_MAP = {
    "DeepSeek": "deepseek_api_key",
    "OpenRouter": "openrouter_api_key",
    "SiliconFlow": "siliconflow_api_key",
    "Groq": "groq_api_key",
    "DashScope": "dashscope_api_key",
    "Google": "google_api_key",
}

DEFAULT_BASE_URLS = {
    "DeepSeek": "https://api.deepseek.com/v1",
    "OpenRouter": "https://openrouter.ai/api/v1",
    "SiliconFlow": "https://api.siliconflow.cn/v1",
    "Groq": "https://api.groq.com/openai/v1",
    "DashScope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


class BackendConfig:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or self._default_config_path()
        self._config: dict[str, Any] = {}
        self.reload()

    @staticmethod
    def _default_config_path() -> Path:
        # /backend/services/config_loader.py -> project root/config.json
        return Path(__file__).resolve().parents[2] / "config.json"

    def reload(self) -> None:
        if not self.config_path.exists():
            self._config = {}
            return
        try:
            self._config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            self._config = {}

    def get_all(self) -> dict[str, Any]:
        return copy.deepcopy(self._config)

    @staticmethod
    def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                BackendConfig._deep_merge(target[key], value)
            else:
                target[key] = value
        return target

    def save_all(self, data: dict[str, Any]) -> dict[str, Any]:
        self._config = copy.deepcopy(data)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self._config, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        return self.get_all()

    def update(self, patch: dict[str, Any], merge: bool = True) -> dict[str, Any]:
        if not isinstance(patch, dict):
            raise ValueError("settings patch must be a JSON object.")
        current = self.get_all()
        if merge:
            self._deep_merge(current, patch)
        else:
            current = copy.deepcopy(patch)
        return self.save_all(current)

    def _extract_default_model(self, provider: str) -> str:
        models = self._config.get("default_models", {})
        value = models.get(provider)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            default_model = value.get("default")
            if isinstance(default_model, str):
                return default_model
        return ""

    def get_provider_settings(self, provider: str, model: str | None = None) -> dict[str, str]:
        self.reload()
        api_keys = self._config.get("api_keys", {})
        api_urls = self._config.get("api_urls", {})

        key_field = PROVIDER_KEY_MAP.get(provider)
        api_key = str(api_keys.get(key_field, "")).strip() if key_field else ""

        base_url = str(api_urls.get(provider, "")).strip()
        if not base_url:
            base_url = DEFAULT_BASE_URLS.get(provider, "").strip()
        base_url = base_url.rstrip("/")

        selected_model = (model or "").strip() or self._extract_default_model(provider)

        return {
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model": selected_model,
        }
