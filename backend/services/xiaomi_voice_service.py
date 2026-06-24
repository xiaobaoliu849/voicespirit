"""Xiaomi MiMo voice design and voice clone service.

Uses the OpenAI-compatible chat completions API:
- Voice Design: mimo-v2.5-tts-voicedesign (text description → custom voice)
- Voice Clone:  mimo-v2.5-tts-voiceclone  (audio sample → cloned voice)
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from .config_loader import BackendConfig

MIMO_TTS_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MIMO_VOICE_DESIGN_MODEL = "mimo-v2.5-tts-voicedesign"
MIMO_VOICE_CLONE_MODEL = "mimo-v2.5-tts-voiceclone"


class XiaomiVoiceService:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()

    def _get_api_key_and_url(self) -> tuple[str, str]:
        self.config.reload()
        settings = self.config.get_provider_settings("Xiaomi")
        api_key = str(settings.get("api_key", "")).strip()
        if not api_key:
            raise ValueError("Missing Xiaomi API key.")
        base_url = str(settings.get("base_url", "")).strip().rstrip("/")
        if not base_url:
            base_url = "https://api.xiaomimimo.com"
        url = f"{base_url}/v1/chat/completions"
        return api_key, url

    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key, url = self._get_api_key_and_url()
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise RuntimeError(f"Xiaomi voice request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Xiaomi voice network error: {exc}") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Xiaomi voice API returned invalid response.")
        return data

    async def create_voice_design(
        self,
        *,
        voice_prompt: str,
        preview_text: str,
        language: str = "zh",
    ) -> dict[str, Any]:
        """Design a voice from text description, return preview audio.

        Args:
            voice_prompt: Text description of the desired voice (1-4 sentences).
            preview_text: Text to synthesize with the designed voice.
            language: Language hint (not directly used by API, for metadata).

        Returns:
            dict with preview_audio_data (base64 wav), model, voice_prompt, etc.
        """
        prompt = voice_prompt.strip()
        preview = preview_text.strip()
        if not prompt:
            raise ValueError("voice_prompt is required.")
        if not preview:
            raise ValueError("preview_text is required.")

        payload = {
            "model": MIMO_VOICE_DESIGN_MODEL,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": preview},
            ],
            "audio": {
                "format": "wav",
                "optimize_text_preview": True,
            },
        }
        result = await self._request(payload)

        # Extract audio from response
        choices = result.get("choices", [])
        if not choices:
            raise RuntimeError("Xiaomi voice design returned no choices.")

        message = choices[0].get("message", {})
        audio_data = message.get("audio", {}).get("data", "")
        if not audio_data:
            raise RuntimeError("Xiaomi voice design returned no audio data.")

        return {
            "preview_audio_data": audio_data,
            "type": "voice_design",
            "model": MIMO_VOICE_DESIGN_MODEL,
            "voice_prompt": prompt,
            "language": language,
        }

    async def create_voice_clone(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        preview_text: str = "你好，这是一个语音克隆的测试。",
    ) -> dict[str, Any]:
        """Clone a voice from audio sample, return preview audio.

        Args:
            audio_bytes: Raw audio file bytes (mp3 or wav, max 10MB after base64).
            mime_type: MIME type of the audio (audio/mpeg or audio/wav).
            preview_text: Text to synthesize with the cloned voice.

        Returns:
            dict with preview_audio_data (base64 wav), model, etc.
        """
        if not audio_bytes:
            raise ValueError("audio file is empty.")

        media_type = (mime_type or "").strip().lower()
        if media_type not in ("audio/mpeg", "audio/mp3", "audio/wav"):
            media_type = "audio/mpeg"

        encoded = base64.b64encode(audio_bytes).decode("ascii")
        voice_ref = f"data:{media_type};base64,{encoded}"

        text = preview_text.strip() or "你好，这是一个语音克隆的测试。"
        payload = {
            "model": MIMO_VOICE_CLONE_MODEL,
            "messages": [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": text},
            ],
            "audio": {
                "format": "wav",
                "voice": voice_ref,
            },
        }
        result = await self._request(payload)

        choices = result.get("choices", [])
        if not choices:
            raise RuntimeError("Xiaomi voice clone returned no choices.")

        message = choices[0].get("message", {})
        audio_data = message.get("audio", {}).get("data", "")
        if not audio_data:
            raise RuntimeError("Xiaomi voice clone returned no audio data.")

        return {
            "preview_audio_data": audio_data,
            "type": "voice_clone",
            "model": MIMO_VOICE_CLONE_MODEL,
        }
