from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import httpx

from .config_loader import BackendConfig

try:
    import edge_tts
except ImportError:
    edge_tts = None


TTS_ENGINE_EDGE = "edge"
TTS_ENGINE_QWEN_FLASH = "qwen_flash"
TTS_ENGINE_MINIMAX = "minimax"
SUPPORTED_TTS_ENGINES = {
    TTS_ENGINE_EDGE,
    TTS_ENGINE_QWEN_FLASH,
    TTS_ENGINE_MINIMAX,
}

DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_QWEN_FLASH_MODEL = "qwen3-tts-flash-2025-11-27"
DEFAULT_MINIMAX_MODEL = "speech-02-turbo"
DEFAULT_MINIMAX_URL = "https://api.minimax.chat/v1/t2a_v2"

FALLBACK_EDGE_VOICES = [
    {"name": "zh-CN-XiaoxiaoNeural", "short_name": "Xiaoxiao", "locale": "zh-CN", "gender": "Female"},
    {"name": "zh-CN-YunxiNeural", "short_name": "Yunxi", "locale": "zh-CN", "gender": "Male"},
    {"name": "en-US-JennyNeural", "short_name": "Jenny", "locale": "en-US", "gender": "Female"},
    {"name": "en-US-GuyNeural", "short_name": "Guy", "locale": "en-US", "gender": "Male"},
]

QWEN_FLASH_VOICES = [
    {"name": "Cherry", "short_name": "芊悦 (Cherry)", "locale": "zh-CN", "gender": "Female"},
    {"name": "Serena", "short_name": "苏瑶 (Serena)", "locale": "zh-CN", "gender": "Female"},
    {"name": "Ethan", "short_name": "晨煦 (Ethan)", "locale": "zh-CN", "gender": "Male"},
    {"name": "Bella", "short_name": "萌宝 (Bella)", "locale": "zh-CN", "gender": "Female"},
    {"name": "Ryan", "short_name": "甜茶 (Ryan)", "locale": "zh-CN", "gender": "Male"},
    {"name": "Mia", "short_name": "乖小妹 (Mia)", "locale": "zh-CN", "gender": "Female"},
    {"name": "Moon", "short_name": "月白 (Moon)", "locale": "zh-CN", "gender": "Male"},
    {"name": "Ono Anna", "short_name": "小野杏 (Ono Anna)", "locale": "ja-JP", "gender": "Female"},
    {"name": "Sohee", "short_name": "素熙 (Sohee)", "locale": "ko-KR", "gender": "Female"},
    {"name": "Andre", "short_name": "安德雷 (Andre)", "locale": "multi", "gender": "Male"},
]

MINIMAX_VOICES = [
    {"name": "female-shaonv", "short_name": "少女音色", "locale": "zh-CN", "gender": "Female"},
    {"name": "female-yujie", "short_name": "御姐音色", "locale": "zh-CN", "gender": "Female"},
    {"name": "male-qn-jingying", "short_name": "精英青年音色", "locale": "zh-CN", "gender": "Male"},
    {"name": "male-qn-badao", "short_name": "霸道青年音色", "locale": "zh-CN", "gender": "Male"},
    {"name": "female-tianmei", "short_name": "甜美女性音色", "locale": "zh-CN", "gender": "Female"},
    {"name": "clever_boy", "short_name": "聪明男童", "locale": "zh-CN", "gender": "Male"},
    {"name": "English_Graceful_Lady", "short_name": "Graceful Lady", "locale": "en-US", "gender": "Female"},
    {"name": "English_Trustworthy_Man", "short_name": "Trustworthy Man", "locale": "en-US", "gender": "Male"},
    {"name": "Japanese_GracefulMaiden", "short_name": "Graceful Maiden", "locale": "ja-JP", "gender": "Female"},
    {"name": "Korean_CalmLady", "short_name": "Calm Lady", "locale": "ko-KR", "gender": "Female"},
]


class TTSService:
    def __init__(
        self,
        output_dir: Path | None = None,
        config: BackendConfig | None = None,
    ):
        self.config = config or BackendConfig()
        root = Path(__file__).resolve().parents[1]
        resolved_output = output_dir or (root / "temp_audio")
        self.output_dir = resolved_output
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _clean_text(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", cleaned)
        cleaned = cleaned.strip()
        if not cleaned:
            raise ValueError("Text is empty after cleanup.")
        if len(cleaned) > 3000:
            raise ValueError("Text is too long. Maximum length is 3000 characters.")
        return cleaned

    def _normalize_engine(self, engine: str | None) -> str:
        candidate = str(engine or TTS_ENGINE_EDGE).strip().lower()
        if candidate not in SUPPORTED_TTS_ENGINES:
            raise ValueError(f"Unsupported TTS engine: {candidate}")
        return candidate

    def _detect_edge_voice(self, text: str) -> str:
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh-CN-XiaoxiaoNeural"
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja-JP-NanamiNeural"
        if re.search(r"[\uac00-\ud7af]", text):
            return "ko-KR-SunHiNeural"
        return DEFAULT_EDGE_VOICE

    def _make_filename(self, text: str, voice: str, rate: str, engine: str) -> str:
        digest = hashlib.md5(f"{engine}|{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:16]
        return f"{engine}_{digest}.mp3"

    def _filter_by_locale(self, voices: list[dict[str, Any]], locale: str | None) -> list[dict[str, Any]]:
        if not locale:
            return voices
        return [voice for voice in voices if str(voice.get("locale", "")).startswith(locale)]

    def _dashscope_key(self) -> str:
        return self.config.get_provider_settings("DashScope").get("api_key", "").strip()

    def _minimax_settings(self) -> tuple[str, str]:
        settings = self.config.get_all().get("minimax", {})
        api_key = str(settings.get("api_key", "")).strip()
        base_url = str(settings.get("api_url", "")).strip()
        if not base_url:
            base_url = str(self.config.get_all().get("api_urls", {}).get("MiniMax", "")).strip()
        if not base_url:
            base_url = DEFAULT_MINIMAX_URL
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        return api_key, base_url

    async def _generate_edge_audio(self, text: str, voice: str, rate: str, path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed on backend.")
        communicator = edge_tts.Communicate(text, voice, rate=rate)
        await communicator.save(str(path))

    async def _generate_qwen_flash_audio(self, text: str, voice: str, path: Path) -> None:
        api_key = self._dashscope_key()
        if not api_key:
            raise RuntimeError("DashScope API Key is not configured.")
        try:
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer
        except ImportError as exc:
            raise RuntimeError("dashscope SDK is not installed on backend.") from exc

        dashscope.api_key = api_key
        synthesizer = SpeechSynthesizer(model=DEFAULT_QWEN_FLASH_MODEL, voice=voice)
        audio = synthesizer.call(text)
        path.write_bytes(audio)

    async def _generate_minimax_audio(self, text: str, voice: str, path: Path) -> None:
        api_key, base_url = self._minimax_settings()
        if not api_key:
            raise RuntimeError("MiniMax API Key is not configured.")

        payload = {
            "model": DEFAULT_MINIMAX_MODEL,
            "text": text,
            "voice_setting": {
                "voice_id": voice,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            },
            "stream": False,
            "audio_setting": {
                "sample_rate": 32000,
                "format": "mp3",
            },
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(base_url, json=payload, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"MiniMax API error: {response.status_code} - {response.text}")

        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError("MiniMax returned an invalid JSON payload.") from exc

        if data.get("base_resp", {}).get("status_code", 0) != 0:
            raise RuntimeError(data.get("base_resp", {}).get("status_msg", "MiniMax TTS failed."))

        audio_obj = data.get("data", {}).get("audio")
        if isinstance(audio_obj, dict):
            audio_hex = str(audio_obj.get("data", "")).strip()
        elif isinstance(audio_obj, str):
            audio_hex = audio_obj.strip()
        else:
            audio_hex = str(data.get("audio", "")).strip()

        if not audio_hex:
            raise RuntimeError("MiniMax returned no audio data.")

        path.write_bytes(bytes.fromhex(audio_hex))

    async def generate_audio(
        self,
        text: str,
        voice: str | None,
        rate: str = "+0%",
        engine: str = TTS_ENGINE_EDGE,
    ) -> tuple[str, str, bool]:
        cleaned = self._clean_text(text)
        normalized_engine = self._normalize_engine(engine)

        if normalized_engine == TTS_ENGINE_EDGE:
            selected_voice = voice or self._detect_edge_voice(cleaned)
        elif normalized_engine == TTS_ENGINE_QWEN_FLASH:
            selected_voice = voice or QWEN_FLASH_VOICES[0]["name"]
        else:
            selected_voice = voice or MINIMAX_VOICES[0]["name"]

        filename = self._make_filename(cleaned, selected_voice, rate, normalized_engine)
        path = self.output_dir / filename

        if path.exists() and path.stat().st_size > 0:
            return str(path), selected_voice, True

        if normalized_engine == TTS_ENGINE_EDGE:
            await self._generate_edge_audio(cleaned, selected_voice, rate, path)
        elif normalized_engine == TTS_ENGINE_QWEN_FLASH:
            await self._generate_qwen_flash_audio(cleaned, selected_voice, path)
        else:
            await self._generate_minimax_audio(cleaned, selected_voice, path)

        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("Failed to generate audio file.")

        return str(path), selected_voice, False

    async def list_voices(
        self,
        locale: str | None = None,
        engine: str = TTS_ENGINE_EDGE,
    ) -> list[dict[str, Any]]:
        normalized_engine = self._normalize_engine(engine)
        if normalized_engine == TTS_ENGINE_QWEN_FLASH:
            return self._filter_by_locale(QWEN_FLASH_VOICES, locale)
        if normalized_engine == TTS_ENGINE_MINIMAX:
            return self._filter_by_locale(MINIMAX_VOICES, locale)

        if edge_tts is None:
            return self._filter_by_locale(FALLBACK_EDGE_VOICES, locale)

        try:
            voices_manager = await edge_tts.VoicesManager.create()
            voices = voices_manager.voices
            normalized = [
                {
                    "name": item.get("Name", ""),
                    "short_name": item.get("ShortName", ""),
                    "locale": item.get("Locale", ""),
                    "gender": item.get("Gender", ""),
                }
                for item in voices
            ]
            normalized = [v for v in normalized if v["name"]]
            return self._filter_by_locale(normalized[:120], locale)
        except Exception:
            return self._filter_by_locale(FALLBACK_EDGE_VOICES, locale)
