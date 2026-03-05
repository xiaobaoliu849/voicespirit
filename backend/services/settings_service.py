from __future__ import annotations

import copy
from typing import Any

from .config_loader import BackendConfig, DEFAULT_BASE_URLS, PROVIDER_KEY_MAP

SETTINGS_PROVIDERS = tuple(PROVIDER_KEY_MAP.keys())

DEFAULT_SETTINGS_TEMPLATE: dict[str, Any] = {
    "api_keys": {
        "deepseek_api_key": "",
        "openrouter_api_key": "",
        "groq_api_key": "",
        "siliconflow_api_key": "",
        "google_api_key": "",
        "dashscope_api_key": "",
    },
    "api_urls": {
        "Google": "",
        "OpenAI": "",
        "DeepSeek": "",
        "OpenRouter": "",
        "Groq": "",
        "SiliconFlow": "",
        "DashScope": "",
        "MiniMax": "",
    },
    "default_models": {
        "DeepSeek": {"default": "", "available": []},
        "OpenRouter": {"default": "", "available": []},
        "SiliconFlow": {"default": "", "available": []},
        "Groq": {"default": "", "available": []},
        "DashScope": {"default": "", "available": []},
        "Google": {"default": "", "available": []},
        "MiniMax": {"default": "", "available": []},
    },
    "general_settings": {
        "display_language": "English",
        "history_retention": "Keep all history",
        "log_level": "INFO",
    },
    "output_directory": "",
    "tts_settings": {
        "default_voice": "",
        "auto_play_preview": False,
        "output_folder": "",
        "speech_speed": 1.0,
        "speech_pitch": 1.0,
        "provider": "System TTS",
    },
    "qwen_tts_settings": {
        "voice_design_voices": [],
        "voice_clone_voices": [],
        "default_vd_model": "qwen3-tts-vd-realtime-2025-12-16",
        "default_vc_model": "qwen3-tts-vc-realtime-2025-11-27",
    },
    "minimax": {
        "api_key": "",
        "api_url": "",
    },
    "auth_settings": {
        "api_token": "",
        "admin_token": "",
    },
    "ui_settings": {
        "theme": "default",
        "window_size": [1000, 800],
        "remember_window_position": False,
        "always_on_top": False,
        "show_tray_icon": False,
    },
    "shortcuts": {
        "wake_app": "Alt+Shift+S",
    },
}

ALLOWED_UPDATE_SECTIONS = {
    "api_keys",
    "api_urls",
    "default_models",
    "general_settings",
    "output_directory",
    "tts_settings",
    "qwen_tts_settings",
    "minimax",
    "auth_settings",
    "ui_settings",
    "shortcuts",
}


class SettingsService:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()

    @staticmethod
    def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                SettingsService._deep_merge(target[key], value)
            else:
                target[key] = value
        return target

    def _normalize_models(self, value: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for provider, model_data in value.items():
            provider_name = str(provider).strip()
            if not provider_name:
                continue
            if isinstance(model_data, str):
                normalized[provider_name] = model_data.strip()
                continue
            if not isinstance(model_data, dict):
                raise ValueError(f"default_models.{provider_name} must be a string or object.")

            default_model = str(model_data.get("default", "")).strip()
            available_raw = model_data.get("available", [])
            if not isinstance(available_raw, list):
                raise ValueError(f"default_models.{provider_name}.available must be an array.")
            available = [str(item).strip() for item in available_raw if str(item).strip()]
            normalized[provider_name] = {
                "default": default_model,
                "available": available,
            }
        return normalized

    @staticmethod
    def _normalize_str_dict(value: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, item in value.items():
            normalized[str(key)] = str(item).strip()
        return normalized

    def _normalize_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            raise ValueError("settings must be an object.")
        unknown = [key for key in patch.keys() if key not in ALLOWED_UPDATE_SECTIONS]
        if unknown:
            raise ValueError(f"Unsupported settings section: {', '.join(sorted(unknown))}")

        normalized: dict[str, Any] = {}
        for key, value in patch.items():
            if key == "output_directory":
                normalized[key] = str(value).strip()
                continue

            if key in {"api_keys", "api_urls"}:
                if not isinstance(value, dict):
                    raise ValueError(f"{key} must be an object.")
                normalized[key] = self._normalize_str_dict(value)
                continue

            if key == "default_models":
                if not isinstance(value, dict):
                    raise ValueError("default_models must be an object.")
                normalized[key] = self._normalize_models(value)
                continue

            if not isinstance(value, dict):
                raise ValueError(f"{key} must be an object.")
            normalized[key] = copy.deepcopy(value)

        return normalized

    def _build_settings_response(self, data: dict[str, Any]) -> dict[str, Any]:
        merged = copy.deepcopy(DEFAULT_SETTINGS_TEMPLATE)
        self._deep_merge(merged, data)
        api_urls = merged.get("api_urls", {})
        if isinstance(api_urls, dict):
            for provider, default_url in DEFAULT_BASE_URLS.items():
                if provider not in api_urls:
                    api_urls[provider] = default_url
        return {
            "config_path": str(self.config.config_path),
            "providers": list(SETTINGS_PROVIDERS),
            "settings": merged,
        }

    def get_settings(self) -> dict[str, Any]:
        self.config.reload()
        return self._build_settings_response(self.config.get_all())

    def update_settings(self, patch: dict[str, Any], merge: bool = True) -> dict[str, Any]:
        normalized_patch = self._normalize_patch(patch)
        updated = self.config.update(normalized_patch, merge=merge)
        return self._build_settings_response(updated)
