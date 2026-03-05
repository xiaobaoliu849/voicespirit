from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx

from main import create_app
from routers import audio_overview as audio_overview_router
from routers import chat as chat_router
from routers import settings as settings_router
from routers import translate as translate_router
from routers import tts as tts_router
from routers import voices as voices_router
from services.audio_overview_service import AudioOverviewService, AudioOverviewServiceError
from services.config_loader import BackendConfig
from services.settings_service import SettingsService


class ApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        async def runner() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(runner())

    def test_health_endpoint(self) -> None:
        response = self._request("GET", "/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})
        self.assertTrue(bool(response.headers.get("x-request-id")))

    def test_request_id_passthrough(self) -> None:
        request_id = "req-smoke-001"
        response = self._request("GET", "/health", headers={"X-Request-ID": request_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("x-request-id"), request_id)

    def test_error_log_contains_request_id(self) -> None:
        async def fake_generate_audio(text: str, voice: str | None, rate: str = "+0%") -> tuple[str, str, bool]:
            _ = (text, voice, rate)
            raise ValueError("Text is empty after cleanup.")

        request_id = "req-error-log-001"
        with patch.object(tts_router.tts_service, "generate_audio", new=fake_generate_audio):
            with self.assertLogs("voicespirit.error", level="ERROR") as logs:
                response = self._request(
                    "GET",
                    "/api/tts/speak",
                    params={"text": "hello"},
                    headers={"X-Request-ID": request_id},
                )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(logs.output)
        last_line = logs.output[-1].split(":", maxsplit=2)[-1].strip()
        payload = json.loads(last_line)
        self.assertEqual(payload["event"], "http_error")
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["status"], 400)

    def test_tts_voices_endpoint(self) -> None:
        async def fake_list_voices(locale: str | None = None) -> list[dict[str, Any]]:
            _ = locale
            return [{"name": "zh-CN-XiaoxiaoNeural", "short_name": "Xiaoxiao", "locale": "zh-CN", "gender": "Female"}]

        with patch.object(tts_router.tts_service, "list_voices", new=fake_list_voices):
            response = self._request("GET", "/api/tts/voices")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["voices"][0]["name"], "zh-CN-XiaoxiaoNeural")

    def test_auth_token_protection(self) -> None:
        async def fake_list_voices(locale: str | None = None) -> list[dict[str, Any]]:
            _ = locale
            return [{"name": "zh-CN-XiaoxiaoNeural", "short_name": "Xiaoxiao", "locale": "zh-CN", "gender": "Female"}]

        async def fake_chat_completion(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            return {
                "provider": "DashScope",
                "model": "qwen-plus",
                "reply": "ok",
                "raw": {"id": "auth-test"},
            }

        with patch.dict(os.environ, {"VOICESPIRIT_API_TOKEN": "test-token"}, clear=False):
            with patch.object(tts_router.tts_service, "list_voices", new=fake_list_voices):
                # Read endpoints remain available without token in write-only mode.
                read_ok = self._request("GET", "/api/tts/voices")
                self.assertEqual(read_ok.status_code, 200)

            with patch.object(chat_router.llm_service, "chat_completion", new=fake_chat_completion):
                missing = self._request(
                    "POST",
                    "/api/chat/completions",
                    json={"provider": "DashScope", "messages": [{"role": "user", "content": "hello"}]},
                )
                self.assertEqual(missing.status_code, 401)
                self.assertEqual(missing.json()["detail"]["code"], "AUTH_TOKEN_MISSING")
                self.assertTrue(bool(missing.json()["detail"].get("meta", {}).get("request_id")))
                self.assertTrue(bool(missing.headers.get("x-request-id")))

                invalid = self._request(
                    "POST",
                    "/api/chat/completions",
                    headers={"Authorization": "Bearer wrong-token"},
                    json={"provider": "DashScope", "messages": [{"role": "user", "content": "hello"}]},
                )
                self.assertEqual(invalid.status_code, 403)
                self.assertEqual(invalid.json()["detail"]["code"], "AUTH_TOKEN_INVALID")

                ok = self._request(
                    "POST",
                    "/api/chat/completions",
                    headers={"Authorization": "Bearer test-token"},
                    json={"provider": "DashScope", "messages": [{"role": "user", "content": "hello"}]},
                )
                self.assertEqual(ok.status_code, 200)

    def test_settings_admin_token_protection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text("{}", encoding="utf-8")
            test_service = SettingsService(config=BackendConfig(config_path))

            original_service = settings_router.settings_service
            settings_router.settings_service = test_service
            try:
                with patch.dict(
                    os.environ,
                    {
                        "VOICESPIRIT_API_TOKEN": "user-token",
                        "VOICESPIRIT_ADMIN_TOKEN": "admin-token",
                    },
                    clear=False,
                ):
                    missing = self._request(
                        "PUT",
                        "/api/settings/",
                        json={"merge": True, "settings": {"general_settings": {"log_level": "INFO"}}},
                    )
                    self.assertEqual(missing.status_code, 401)
                    self.assertEqual(missing.json()["detail"]["code"], "AUTH_ADMIN_TOKEN_MISSING")

                    user = self._request(
                        "PUT",
                        "/api/settings/",
                        headers={"Authorization": "Bearer user-token"},
                        json={"merge": True, "settings": {"general_settings": {"log_level": "DEBUG"}}},
                    )
                    self.assertEqual(user.status_code, 403)
                    self.assertEqual(user.json()["detail"]["code"], "AUTH_ADMIN_TOKEN_INVALID")

                    admin = self._request(
                        "PUT",
                        "/api/settings/",
                        headers={"Authorization": "Bearer admin-token"},
                        json={"merge": True, "settings": {"general_settings": {"log_level": "WARNING"}}},
                    )
                    self.assertEqual(admin.status_code, 200)
                    self.assertEqual(
                        admin.json()["settings"]["general_settings"]["log_level"], "WARNING"
                    )
            finally:
                settings_router.settings_service = original_service

    def test_tts_speak_endpoint(self) -> None:
        async def fake_generate_audio(text: str, voice: str | None, rate: str = "+0%") -> tuple[str, str, bool]:
            _ = (text, voice, rate)
            raise ValueError("Text is empty after cleanup.")

        with patch.object(tts_router.tts_service, "generate_audio", new=fake_generate_audio):
            response = self._request("GET", "/api/tts/speak", params={"text": "hello"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Text is empty after cleanup", response.text)

    def test_chat_completion_endpoint(self) -> None:
        async def fake_chat_completion(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            return {
                "provider": "DashScope",
                "model": "qwen-plus",
                "reply": "ok",
                "raw": {"id": "test"},
            }

        with patch.object(chat_router.llm_service, "chat_completion", new=fake_chat_completion):
            response = self._request(
                "POST",
                "/api/chat/completions",
                json={
                    "provider": "DashScope",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "ok")

    def test_chat_stream_endpoint(self) -> None:
        async def fake_stream(**kwargs: Any):
            _ = kwargs
            yield {"type": "meta", "provider": "DashScope", "model": "qwen-plus"}
            yield {"type": "delta", "content": "he"}
            yield {"type": "delta", "content": "llo"}
            yield {"type": "done", "provider": "DashScope", "model": "qwen-plus", "reply": "hello"}

        with patch.object(chat_router.llm_service, "chat_completion_stream", new=fake_stream):
            response = self._request(
                "POST",
                "/api/chat/completions/stream",
                json={
                    "provider": "DashScope",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )
        self.assertEqual(response.status_code, 200)
        text = response.text
        self.assertIn("event: delta", text)
        self.assertIn('"content": "he"', text)
        self.assertIn("event: done", text)

    def test_translate_endpoint(self) -> None:
        async def fake_translate_text(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            return {"provider": "DashScope", "model": "qwen-plus", "translated_text": "Hello"}

        with patch.object(translate_router.llm_service, "translate_text", new=fake_translate_text):
            response = self._request(
                "POST",
                "/api/translate/",
                json={
                    "text": "你好",
                    "target_language": "English",
                    "provider": "DashScope",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["translated_text"], "Hello")

    def test_voices_endpoints(self) -> None:
        async def fake_create_voice_design(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            return {
                "voice": "voice_design_x",
                "type": "voice_design",
                "target_model": "qwen3-tts-vd-realtime-2025-12-16",
                "preferred_name": "demo",
                "language": "zh",
                "preview_audio_data": "",
            }

        async def fake_create_voice_clone(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            return {
                "voice": "voice_clone_x",
                "type": "voice_clone",
                "target_model": "qwen3-tts-vc-realtime-2025-11-27",
                "preferred_name": "demo",
            }

        async def fake_list_voices(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            return {
                "voice_type": "voice_design",
                "count": 1,
                "voices": [{"voice": "voice_design_x", "type": "voice_design", "target_model": "qwen3-tts-vd-realtime-2025-12-16"}],
            }

        async def fake_delete_voice(**kwargs: Any) -> dict[str, Any]:
            voice_name = kwargs.get("voice_name", "")
            voice_type = kwargs.get("voice_type", "voice_design")
            return {"voice": str(voice_name), "type": str(voice_type), "deleted": True}

        with patch.object(voices_router.voice_service, "create_voice_design", new=fake_create_voice_design):
            r_design = self._request(
                "POST",
                "/api/voices/design",
                json={
                    "voice_prompt": "warm",
                    "preview_text": "hello",
                    "preferred_name": "demo",
                    "language": "zh",
                },
            )
        self.assertEqual(r_design.status_code, 200)
        self.assertEqual(r_design.json()["voice"], "voice_design_x")

        with patch.object(voices_router.voice_service, "create_voice_clone", new=fake_create_voice_clone):
            r_clone = self._request(
                "POST",
                "/api/voices/clone",
                data={"preferred_name": "demo"},
                files={"audio_file": ("demo.wav", b"RIFFdata", "audio/wav")},
            )
        self.assertEqual(r_clone.status_code, 200)
        self.assertEqual(r_clone.json()["voice"], "voice_clone_x")

        with patch.object(voices_router.voice_service, "list_voices", new=fake_list_voices):
            r_list = self._request("GET", "/api/voices/?voice_type=voice_design")
        self.assertEqual(r_list.status_code, 200)
        self.assertEqual(r_list.json()["count"], 1)

        with patch.object(voices_router.voice_service, "delete_voice", new=fake_delete_voice):
            r_delete = self._request("DELETE", "/api/voices/voice_design_x?voice_type=voice_design")
        self.assertEqual(r_delete.status_code, 200)
        self.assertTrue(r_delete.json()["deleted"])

    def test_settings_get_and_update_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text("{}", encoding="utf-8")
            test_service = SettingsService(config=BackendConfig(config_path))

            original_service = settings_router.settings_service
            settings_router.settings_service = test_service
            try:
                r_get = self._request("GET", "/api/settings/")
                self.assertEqual(r_get.status_code, 200)
                self.assertIn("settings", r_get.json())

                r_put = self._request(
                    "PUT",
                    "/api/settings/",
                    json={
                        "merge": True,
                        "settings": {
                            "api_keys": {"dashscope_api_key": "test-key"},
                            "default_models": {
                                "DashScope": {
                                    "default": "qwen-plus",
                                    "available": ["qwen-plus", "qwen-turbo"],
                                }
                            },
                        },
                    },
                )
                self.assertEqual(r_put.status_code, 200)
                payload = r_put.json()
                self.assertEqual(payload["settings"]["api_keys"]["dashscope_api_key"], "test-key")
                self.assertEqual(payload["settings"]["default_models"]["DashScope"]["default"], "qwen-plus")
            finally:
                settings_router.settings_service = original_service

    def test_audio_overview_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "voice_spirit_test.db"
            output_dir = Path(tmp_dir) / "audio_out"
            test_service = AudioOverviewService(db_path=db_path, output_dir=output_dir)
            original_service = audio_overview_router.audio_overview_service
            audio_overview_router.audio_overview_service = test_service
            try:
                async def fake_generate_script(
                    *,
                    topic: str,
                    language: str = "zh",
                    turn_count: int = 10,
                    provider: str = "DashScope",
                    model: str | None = None,
                ) -> dict[str, Any]:
                    _ = model
                    return {
                        "topic": topic,
                        "language": language,
                        "turn_count": turn_count,
                        "provider": provider,
                        "model": "qwen-plus",
                        "script_lines": [
                            {"role": "A", "text": "欢迎来到节目"},
                            {"role": "B", "text": "今天我们聊 AI"},
                        ],
                        "raw_reply": "",
                    }

                async def fake_synthesize(
                    podcast_id: int,
                    *,
                    voice_a: str | None = None,
                    voice_b: str | None = None,
                    rate: str = "+0%",
                    language: str | None = None,
                    gap_ms: int = 250,
                    merge_strategy: str = "auto",
                ) -> dict[str, Any]:
                    _ = (voice_a, voice_b, language, merge_strategy)
                    audio_file = output_dir / f"podcast_{podcast_id}.mp3"
                    audio_file.parent.mkdir(parents=True, exist_ok=True)
                    audio_file.write_bytes(b"ID3test-audio")
                    test_service.update_podcast(podcast_id, audio_path=str(audio_file))
                    return {
                        "podcast_id": podcast_id,
                        "audio_path": str(audio_file),
                        "line_count": 2,
                        "voice_a": "zh-CN-YunxiNeural",
                        "voice_b": "zh-CN-XiaoxiaoNeural",
                        "rate": rate,
                        "cache_hits": 1,
                        "gap_ms": gap_ms,
                        "gap_ms_applied": 0,
                        "merge_strategy": "ffmpeg",
                    }

                r_create = self._request(
                    "POST",
                    "/api/audio-overview/podcasts",
                    json={
                        "topic": "AI Podcast Demo",
                        "language": "zh",
                        "script_lines": [
                            {"role": "A", "text": "你好"},
                            {"role": "B", "text": "你好，很高兴见到你"},
                        ],
                    },
                )
                self.assertEqual(r_create.status_code, 200)
                created = r_create.json()
                self.assertEqual(created["topic"], "AI Podcast Demo")
                podcast_id = created["id"]

                r_list = self._request("GET", "/api/audio-overview/podcasts?limit=10")
                self.assertEqual(r_list.status_code, 200)
                self.assertEqual(r_list.json()["count"], 1)

                r_get = self._request("GET", f"/api/audio-overview/podcasts/{podcast_id}")
                self.assertEqual(r_get.status_code, 200)
                self.assertEqual(len(r_get.json()["script_lines"]), 2)

                r_script = self._request(
                    "PUT",
                    f"/api/audio-overview/podcasts/{podcast_id}/script",
                    json={
                        "script_lines": [
                            {"role": "A", "text": "更新后的第一句"},
                            {"role": "B", "text": "更新后的第二句"},
                            {"role": "A", "text": "更新后的第三句"},
                        ]
                    },
                )
                self.assertEqual(r_script.status_code, 200)
                self.assertEqual(len(r_script.json()["script_lines"]), 3)

                with patch.object(test_service, "generate_script", new=fake_generate_script):
                    r_generate = self._request(
                        "POST",
                        "/api/audio-overview/scripts/generate",
                        json={
                            "topic": "AI Podcast Demo",
                            "language": "zh",
                            "turn_count": 6,
                            "provider": "DashScope",
                        },
                    )
                self.assertEqual(r_generate.status_code, 200)
                self.assertEqual(len(r_generate.json()["script_lines"]), 2)

                with patch.object(test_service, "synthesize_podcast_audio", new=fake_synthesize):
                    r_synth = self._request(
                        "POST",
                        f"/api/audio-overview/podcasts/{podcast_id}/synthesize",
                        json={
                            "voice_a": "zh-CN-YunxiNeural",
                            "voice_b": "zh-CN-XiaoxiaoNeural",
                            "gap_ms": 300,
                            "merge_strategy": "auto",
                        },
                    )
                self.assertEqual(r_synth.status_code, 200)
                self.assertIn("/api/audio-overview/podcasts/", r_synth.json()["audio_download_url"])
                self.assertEqual(r_synth.json()["gap_ms"], 300)

                async def fake_synthesize_error(
                    podcast_id: int,
                    *,
                    voice_a: str | None = None,
                    voice_b: str | None = None,
                    rate: str = "+0%",
                    language: str | None = None,
                    gap_ms: int = 250,
                    merge_strategy: str = "auto",
                ) -> dict[str, Any]:
                    _ = (podcast_id, voice_a, voice_b, rate, language, gap_ms, merge_strategy)
                    raise AudioOverviewServiceError(
                        code="AUDIO_MERGE_STRATEGY_INVALID",
                        message="Unsupported merge strategy: invalid",
                        meta={"strategy": "invalid"},
                    )

                with patch.object(test_service, "synthesize_podcast_audio", new=fake_synthesize_error):
                    r_synth_error = self._request(
                        "POST",
                        f"/api/audio-overview/podcasts/{podcast_id}/synthesize",
                        json={"merge_strategy": "invalid"},
                    )
                self.assertEqual(r_synth_error.status_code, 400)
                detail = r_synth_error.json()["detail"]
                self.assertEqual(detail["code"], "AUDIO_MERGE_STRATEGY_INVALID")

                r_audio = self._request("GET", f"/api/audio-overview/podcasts/{podcast_id}/audio")
                self.assertEqual(r_audio.status_code, 200)
                self.assertIn("audio/mpeg", r_audio.headers.get("content-type", ""))

                r_latest = self._request("GET", "/api/audio-overview/podcasts/latest")
                self.assertEqual(r_latest.status_code, 200)
                self.assertEqual(r_latest.json()["id"], podcast_id)

                r_delete = self._request("DELETE", f"/api/audio-overview/podcasts/{podcast_id}")
                self.assertEqual(r_delete.status_code, 200)
                self.assertTrue(r_delete.json()["deleted"])
            finally:
                audio_overview_router.audio_overview_service = original_service


if __name__ == "__main__":
    unittest.main()
