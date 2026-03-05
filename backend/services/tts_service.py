import hashlib
import re
from pathlib import Path
from typing import Any

try:
    import edge_tts
except ImportError:
    edge_tts = None


DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
FALLBACK_VOICES = [
    {"name": "zh-CN-XiaoxiaoNeural", "short_name": "Xiaoxiao", "locale": "zh-CN", "gender": "Female"},
    {"name": "zh-CN-YunxiNeural", "short_name": "Yunxi", "locale": "zh-CN", "gender": "Male"},
    {"name": "en-US-JennyNeural", "short_name": "Jenny", "locale": "en-US", "gender": "Female"},
    {"name": "en-US-GuyNeural", "short_name": "Guy", "locale": "en-US", "gender": "Male"},
]


class TTSService:
    def __init__(self, output_dir: Path | None = None):
        root = Path(__file__).resolve().parents[1]
        self.output_dir = output_dir or (root / "temp_audio")
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

    def _detect_voice(self, text: str) -> str:
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh-CN-XiaoxiaoNeural"
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja-JP-NanamiNeural"
        if re.search(r"[\uac00-\ud7af]", text):
            return "ko-KR-SunHiNeural"
        return DEFAULT_VOICE

    def _make_filename(self, text: str, voice: str, rate: str) -> str:
        digest = hashlib.md5(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:16]
        return f"{digest}.mp3"

    async def generate_audio(self, text: str, voice: str | None, rate: str = "+0%") -> tuple[str, str, bool]:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed on backend.")

        cleaned = self._clean_text(text)
        selected_voice = voice or self._detect_voice(cleaned)
        filename = self._make_filename(cleaned, selected_voice, rate)
        path = self.output_dir / filename

        if path.exists() and path.stat().st_size > 0:
            return str(path), selected_voice, True

        communicator = edge_tts.Communicate(cleaned, selected_voice, rate=rate)
        await communicator.save(str(path))

        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("Failed to generate audio file.")

        return str(path), selected_voice, False

    async def list_voices(self, locale: str | None = None) -> list[dict[str, Any]]:
        if edge_tts is None:
            return self._filter_by_locale(FALLBACK_VOICES, locale)

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
            if locale:
                normalized = [v for v in normalized if v["locale"].startswith(locale)]
            return normalized[:120]
        except Exception:
            return self._filter_by_locale(FALLBACK_VOICES, locale)

    @staticmethod
    def _filter_by_locale(voices: list[dict[str, Any]], locale: str | None) -> list[dict[str, Any]]:
        if not locale:
            return voices
        return [voice for voice in voices if str(voice.get("locale", "")).startswith(locale)]
