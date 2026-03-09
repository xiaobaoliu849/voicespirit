from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .config_loader import BackendConfig

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - validated at runtime in deployed env
    genai = None
    types = None


DEFAULT_GOOGLE_REALTIME_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_GOOGLE_REALTIME_VOICE = "Puck"


class RealtimeVoiceService:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()

    def _resolve_google_settings(self, model: str | None) -> dict[str, str]:
        provider_settings = self.config.get_provider_settings("Google", model)
        resolved_model = provider_settings["model"].strip() or DEFAULT_GOOGLE_REALTIME_MODEL
        api_key = provider_settings["api_key"].strip()
        base_url = provider_settings["base_url"].strip()
        if not api_key:
            raise RuntimeError("Google API Key 未配置，无法启动实时语音会话。")
        if genai is None or types is None:
            raise RuntimeError("google-genai 依赖未安装，无法启动实时语音会话。")
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": resolved_model,
        }

    @staticmethod
    async def _send_event(websocket: WebSocket, event_type: str, **payload: Any) -> None:
        await websocket.send_json({"type": event_type, **payload})

    @staticmethod
    def _extract_transcript_text(server_content: Any, candidate_names: tuple[str, ...]) -> str:
        for attr_name in candidate_names:
            if not hasattr(server_content, attr_name):
                continue
            value = getattr(server_content, attr_name)
            if not value:
                continue
            if hasattr(value, "text") and getattr(value, "text", ""):
                return str(value.text).strip()
            return str(value).strip()
        return ""

    @staticmethod
    def _build_live_config(voice: str):
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=(
                "You are a helpful, friendly, and intelligent AI assistant. "
                "Respond naturally and conversationally in the same language the user speaks."
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=300,
                    silence_duration_ms=500,
                )
            ),
        )

    async def _client_to_google_loop(self, websocket: WebSocket, session: Any) -> None:
        while True:
            message = await websocket.receive()
            message_type = message.get("type")
            if message_type == "websocket.disconnect":
                break

            text_data = message.get("text")
            if text_data:
                try:
                    payload = json.loads(text_data)
                except Exception:
                    await self._send_event(websocket, "error", message="无效的实时语音消息。")
                    continue
                command_type = str(payload.get("type", "")).strip()
                if command_type == "text_input":
                    content = str(payload.get("text", "")).strip()
                    if content:
                        await session.send(input=content, end_of_turn=True)
                    continue
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "stop":
                    break
                continue

            audio_bytes = message.get("bytes")
            if audio_bytes:
                await session.send_realtime_input(
                    audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                )

    async def _google_to_client_loop(self, websocket: WebSocket, session: Any) -> None:
        while True:
            turn = session.receive()
            async for response in turn:
                audio_data = getattr(response, "data", None)
                if audio_data:
                    await self._send_event(
                        websocket,
                        "assistant_audio",
                        audio=base64.b64encode(audio_data).decode("ascii"),
                        encoding="pcm_s16le",
                        sample_rate=24000,
                    )

                response_text = getattr(response, "text", None)
                if response_text:
                    await self._send_event(websocket, "assistant_text", text=str(response_text))

                server_content = getattr(response, "server_content", None)
                if not server_content:
                    continue

                if getattr(server_content, "interrupted", False):
                    await self._send_event(websocket, "interrupted")

                if getattr(server_content, "turn_complete", False):
                    await self._send_event(websocket, "turn_complete")

                user_text = self._extract_transcript_text(
                    server_content,
                    ("input_transcription", "input_audio_transcription", "transcription"),
                )
                if user_text:
                    await self._send_event(websocket, "user_transcript", text=user_text)

                assistant_transcript = self._extract_transcript_text(
                    server_content,
                    ("output_transcription", "output_audio_transcription"),
                )
                if assistant_transcript:
                    await self._send_event(websocket, "assistant_text", text=assistant_transcript)

    async def stream_google_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_GOOGLE_REALTIME_VOICE,
    ) -> None:
        settings = self._resolve_google_settings(model)
        http_options: dict[str, str] = {"api_version": "v1beta"}
        if settings["base_url"]:
            http_options["base_url"] = settings["base_url"]

        client = genai.Client(api_key=settings["api_key"], http_options=http_options)
        live_config = self._build_live_config(voice)

        try:
            async with client.aio.live.connect(model=settings["model"], config=live_config) as session:
                await self._send_event(
                    websocket,
                    "session_open",
                    provider="Google",
                    model=settings["model"],
                    voice=voice,
                )
                send_task = asyncio.create_task(self._client_to_google_loop(websocket, session))
                receive_task = asyncio.create_task(self._google_to_client_loop(websocket, session))
                done, pending = await asyncio.wait(
                    {send_task, receive_task},
                    return_when=asyncio.FIRST_EXCEPTION,
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    task.result()
        except WebSocketDisconnect:
            return
