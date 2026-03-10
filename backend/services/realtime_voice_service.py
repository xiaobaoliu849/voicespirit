from __future__ import annotations

import asyncio
import base64
import json
import sys
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

print(f"DEBUG: Realtime service using Python: {sys.executable}")
print(f"DEBUG: Python Path: {sys.path}")

from .config_loader import BackendConfig

try:
    from google import genai
    from google.genai import types
except ImportError as e:  # pragma: no cover - validated at runtime in deployed env
    print(f"DEBUG: Google GenAI Import Error: {e}")
    genai = None
    types = None
except Exception as e:
    print(f"DEBUG: Google GenAI Unexpected Error: {e}")
    genai = None
    types = None

try:
    from dashscope.audio.qwen_omni import AudioFormat, MultiModality, OmniRealtimeConversation
except ImportError as e:  # pragma: no cover - validated at runtime in deployed env
    print(f"DEBUG: DashScope Realtime Import Error: {e}")
    AudioFormat = None
    MultiModality = None
    OmniRealtimeConversation = None
except Exception as e:
    print(f"DEBUG: DashScope Realtime Unexpected Error: {e}")
    AudioFormat = None
    MultiModality = None
    OmniRealtimeConversation = None


DEFAULT_GOOGLE_REALTIME_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_GOOGLE_REALTIME_VOICE = "Puck"
DEFAULT_DASHSCOPE_REALTIME_MODEL = "qwen3-omni-flash-realtime-2025-12-01"
DEFAULT_DASHSCOPE_REALTIME_VOICE = "Cherry"


class DashScopeRealtimeCallback:
    def __init__(self, *, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.loop = loop
        self.queue = queue

    def _push(self, event: dict[str, Any]) -> None:
        self.loop.call_soon_threadsafe(self.queue.put_nowait, event)

    def on_open(self) -> None:
        return None

    def on_event(self, response: Any) -> None:
        if not isinstance(response, dict):
            return

        event_type = str(response.get("type", "")).strip()
        if event_type == "input_audio_buffer.speech_started":
            self._push({"type": "interrupted"})
            return
        if event_type == "conversation.item.input_audio_transcription.completed":
            transcript = str(response.get("transcript", "")).strip()
            if transcript:
                self._push({"type": "user_transcript", "text": transcript})
            return
        if event_type == "response.audio.delta":
            delta = str(response.get("delta", "")).strip()
            if delta:
                self._push(
                    {
                        "type": "assistant_audio",
                        "audio": delta,
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000,
                    }
                )
            return
        if event_type in {"response.audio_transcript.delta", "response.text.delta"}:
            delta = str(response.get("delta", ""))
            if delta:
                self._push({"type": "assistant_text", "text": delta})
            return
        if event_type == "response.done":
            self._push({"type": "turn_complete"})
            return
        if event_type == "error":
            error_data = response.get("error")
            if isinstance(error_data, dict):
                message = str(error_data.get("message", "")).strip() or str(response)
            else:
                message = str(error_data or response).strip()
            self._push({"type": "error", "message": message})

    def on_close(self, close_status_code: Any, close_msg: Any) -> None:
        self._push(
            {
                "type": "closed",
                "code": int(close_status_code or 1000),
                "message": str(close_msg or "").strip(),
            }
        )


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

    def _resolve_dashscope_settings(self, model: str | None) -> dict[str, str]:
        provider_settings = self.config.get_provider_settings("DashScope", model)
        resolved_model = provider_settings["model"].strip() or DEFAULT_DASHSCOPE_REALTIME_MODEL
        api_key = provider_settings["api_key"].strip()
        base_url = provider_settings["base_url"].strip().lower()
        if not api_key:
            raise RuntimeError("DashScope API Key 未配置，无法启动实时语音会话。")
        if OmniRealtimeConversation is None or MultiModality is None or AudioFormat is None:
            raise RuntimeError("DashScope Omni Realtime 依赖未安装，无法启动实时语音会话。")
        region = "intl" if "dashscope-intl" in base_url else "cn"
        return {
            "api_key": api_key,
            "model": resolved_model,
            "region": region,
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
                    prefix_padding_ms=500,
                    silence_duration_ms=800,
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

    async def _client_to_dashscope_loop(self, websocket: WebSocket, conversation: Any) -> None:
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
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "stop":
                    break
                continue

            audio_bytes = message.get("bytes")
            if audio_bytes:
                conversation.append_audio(base64.b64encode(audio_bytes).decode("ascii"))

    async def _dashscope_to_client_loop(
        self,
        websocket: WebSocket,
        queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        while True:
            event = await queue.get()
            event_type = str(event.get("type", "")).strip()
            if event_type == "closed":
                break
            await websocket.send_json(event)
            if event_type == "error":
                break

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
        except Exception as e:
            print(f"DEBUG: Google Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_event(websocket, "error", message=f"Google 实时会话启动失败: {str(e)}")
            return

    async def stream_dashscope_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_DASHSCOPE_REALTIME_VOICE,
    ) -> None:
        settings = self._resolve_dashscope_settings(model)
        import dashscope

        dashscope.api_key = settings["api_key"]
        base_domain = "dashscope.aliyuncs.com" if settings["region"] == "cn" else "dashscope-intl.aliyuncs.com"
        url = f"wss://{base_domain}/api-ws/v1/realtime"
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        callback = DashScopeRealtimeCallback(loop=loop, queue=event_queue)
        conversation = OmniRealtimeConversation(  # type: ignore[misc]
            model=settings["model"],
            callback=callback,
            url=url,
        )

        try:
            conversation.connect()
            await asyncio.sleep(0.5)
            conversation.update_session(
                output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],  # type: ignore[union-attr]
                voice=voice,
                input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,  # type: ignore[union-attr]
                output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # type: ignore[union-attr]
                enable_input_audio_transcription=True,
                enable_turn_detection=True,
                instructions=(
                    "You are a helpful, friendly, and intelligent AI assistant. "
                    "Respond naturally and conversationally in the same language the user speaks."
                ),
            )
            await asyncio.sleep(0.5)
            await self._send_event(
                websocket,
                "session_open",
                provider="DashScope",
                model=settings["model"],
                voice=voice,
            )

            send_task = asyncio.create_task(self._client_to_dashscope_loop(websocket, conversation))
            receive_task = asyncio.create_task(self._dashscope_to_client_loop(websocket, event_queue))
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
        except Exception as e:
            print(f"DEBUG: DashScope Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_event(websocket, "error", message=f"DashScope 实时会话启动失败: {str(e)}")
            return
        finally:
            try:
                conversation.close()
            except Exception:
                pass
