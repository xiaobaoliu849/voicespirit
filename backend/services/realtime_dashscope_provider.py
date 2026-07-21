"""DashScope Qwen-Omni (SDK) realtime voice provider mixin."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

from fastapi import WebSocket, WebSocketDisconnect

try:
    from dashscope.audio.qwen_omni import AudioFormat, MultiModality, OmniRealtimeConversation
except ImportError:  # pragma: no cover
    AudioFormat = None
    MultiModality = None
    OmniRealtimeConversation = None

from .realtime_constants import (
    DEFAULT_DASHSCOPE_REALTIME_MODEL,
    DEFAULT_DASHSCOPE_REALTIME_VOICE,
    QWEN_OMNI_REALTIME_VOICES,
    _is_dashscope_audio_realtime_model,
    _is_dashscope_omni_realtime_model,
    _merge_streaming_text,
    _normalize_dashscope_realtime_voice,
)
from .interruption_classifier import InterruptionClassifier, InterruptionDecisionCoordinator, InterruptionIntent
from .background_tasks import spawn_background_task
from .realtime_dashscope_client import DashScopeAudioRealtimeConversation, DashScopeRealtimeCallback
from .realtime_memory_session import RealtimeMemorySession, _merge_memory_text
from .realtime_session_recorder import VoiceAgentSessionRecorder
from .realtime_tool_protocol import (
    RealtimeToolCall,
    dashscope_supports_native_tools,
    dashscope_tool_declarations,
    tool_call_to_request,
    tool_error_payload,
    tool_result_payload,
)
from .voice_agent_tools import VoiceAgentToolSession, VoiceToolRequest

logger = logging.getLogger(__name__)


class DashScopeRealtimeMixin:
    """DashScope Qwen-Omni SDK provider methods for RealtimeVoiceService."""

    async def _send_dashscope_tool_response(
        self,
        websocket: WebSocket,
        conversation: Any,
        *,
        provider_call_id: str,
        tool_name: str,
        response_payload: dict[str, Any],
        result: dict[str, Any] | None = None,
        create_response: bool = True,
        conversation_turn_id: str = "",
        tool_call_id: str = "",
        recorder: VoiceAgentSessionRecorder | None = None,
    ) -> None:
        if not provider_call_id:
            raise ValueError("DashScope native tool response requires a provider call ID.")
        try:
            conversation.send_raw(
                json.dumps(
                    {
                        "event_id": f"event_{uuid.uuid4().hex}",
                        "type": "conversation.item.create",
                        "item": {
                            "id": f"item_{uuid.uuid4().hex}",
                            "type": "function_call_output",
                            "call_id": provider_call_id,
                            "output": json.dumps(response_payload, ensure_ascii=False),
                        },
                    },
                    ensure_ascii=False,
                )
            )
            if create_response:
                conversation.create_response()
        except Exception as exc:
            try:
                await self._send_event(
                    websocket,
                    "error",
                    provider="DashScope",
                    message=f"Qwen 工具结果回传失败，会话已关闭: {exc}",
                )
            except Exception:
                pass
            try:
                conversation.close()
            except Exception:
                logger.exception("dashscope_session_close_after_tool_delivery_failed")
            raise
        result = result or {}
        payload = {
            "provider": "DashScope",
            "provider_call_id": provider_call_id,
            "tool_name": tool_name,
            "query": str(result.get("query", "")),
            "turn_id": conversation_turn_id,
            "tool_call_id": tool_call_id,
            "route": "native",
            "source_count": int(result.get("source_count", 0) or 0),
            "elapsed_ms": int(result.get("elapsed_ms", 0) or 0),
            "status": "completed" if response_payload.get("ok") else "failed",
        }
        if recorder is not None:
            await recorder.record_tool_event("tool_result_delivered", payload)
        await self._send_event(
            websocket,
            "tool_result_delivered",
            **payload,
        )
    @staticmethod
    def _resolve_dashscope_voiceprint_audio_urls(
        provider_settings: dict[str, Any],
        urls: list[str] | None,
    ) -> list[str]:
        raw_values = []
        if urls:
            raw_values.extend(urls)
        
        raw_config = provider_settings.get('voiceprint_audio_urls')
        if isinstance(raw_config, list):
            raw_values.extend(raw_config)
        elif isinstance(raw_config, str):
            raw_values.extend(re.split(r'[\r\n,]+', raw_config))
            
        env_config = os.environ.get('DASHSCOPE_VOICEPRINT_AUDIO_URLS', '')
        if env_config:
            raw_values.extend(re.split(r'[\r\n,]+', env_config))
            
        normalized = []
        seen = set()
        for value in raw_values:
            item = str(value or '').strip()
            if not item or item in seen:
                continue
            if not item.startswith(('http://', 'https://')):
                continue
            normalized.append(item)
            seen.add(item)
            if len(normalized) >= 5:
                return normalized
                
        return normalized
    @staticmethod
    def _configure_dashscope_conversation(conversation: Any, *, voice: str, instructions: str) -> None:
        conversation.update_session(
            output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],  # type: ignore[union-attr]
            voice=voice,
            input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,  # type: ignore[union-attr]
            output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,  # type: ignore[union-attr]
            enable_input_audio_transcription=True,
            enable_turn_detection=True,
            turn_detection_param={"create_response": False, "interrupt_response": False},
            turn_detection_silence_duration_ms=5000,
            instructions=instructions,
            tools=dashscope_tool_declarations(),
        )
    async def _client_to_dashscope_loop(
        self,
        websocket: WebSocket,
        conversation: Any,
        memory_session: RealtimeMemorySession,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        interruption: InterruptionDecisionCoordinator | None = None,
    ) -> None:
        interruption = interruption or InterruptionDecisionCoordinator()
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
                if command_type == "config":
                    memory_session.configure(payload.get("memory"))
                    await self._send_event(
                        websocket,
                        "memory_config",
                        enabled=bool(memory_session._config.get_service()),
                        scope=memory_session._config.memory_scope,
                        group_id=memory_session._config.group_id,
                    )
                    continue
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "interruption_client_stopped":
                    await self._record_client_interruption_stop(recorder, payload, provider="DashScope")
                    continue
                if command_type == "interruption_timeout" and interruption.pending is not None:
                    timeout_candidate_id = str(payload.get("candidate_id", ""))
                    if timeout_candidate_id and timeout_candidate_id != interruption.pending.candidate_id:
                        continue
                    should_process_user, _ = await self._decide_interruption(
                        websocket,
                        interruption,
                        "",
                        memory_session=memory_session,
                        tool_session=tool_session,
                        recorder=recorder,
                        expected_candidate_id=(timeout_candidate_id or interruption.pending.candidate_id),
                        timeout_resolution=True,
                    )
                    if (
                        not should_process_user
                        and interruption.take_deferred_terminal() is not None
                    ):
                        await self._finalize_realtime_turn(
                            websocket,
                            memory_session,
                            recorder,
                            gated=tool_session.has_active_task,
                        )
                    continue
                if command_type == "stop":
                    async def send_stop_tool_event(event_type: str, payload: dict[str, Any]) -> None:
                        if recorder is not None:
                            await recorder.record_tool_event(event_type, payload)
                        await self._send_event(websocket, event_type, **payload)

                    await tool_session.cancel(
                        send_event=send_stop_tool_event,
                        reason="session_stopped",
                    )
                    break
                continue

            audio_bytes = message.get("bytes")
            if audio_bytes:
                conversation.append_audio(base64.b64encode(audio_bytes).decode("ascii"))
    async def _dashscope_to_client_loop(
        self,
        websocket: WebSocket,
        queue: asyncio.Queue[dict[str, Any]],
        memory_session: RealtimeMemorySession,
        conversation: Any,
        voice: str,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        interruption: InterruptionDecisionCoordinator | None = None,
    ) -> None:
        async def send_tool_event(event_type: str, payload: dict[str, Any]) -> None:
            if recorder is not None:
                await recorder.record_tool_event(event_type, payload)
            await self._send_event(websocket, event_type, **payload)

        interruption = interruption or InterruptionDecisionCoordinator()
        suppressed_response_ids: set[str] = set()
        tool_phase_response_ids: set[str] = set()
        cannot_create_response_retries = 0
        gated_tool_turn_id = ""
        while True:
            event = await queue.get()
            event_type = str(event.get("type", "")).strip()
            if event_type == "closed":
                break
            if event_type == "speech_started":
                if interruption.active_response_id or tool_session.has_active_task or (
                    recorder is not None and bool(recorder.current_assistant_text)
                ):
                    await self._begin_interruption(
                        websocket,
                        interruption,
                        provider="DashScope",
                        provider_event_type=str(event.get("provider_event_type", "input_audio_buffer.speech_started")),
                        recorder=recorder,
                        tool_session=tool_session,
                    )
                continue
            if event_type == "response_started":
                interruption.active_response_id = (
                    str(event.get("response_id", "")) or interruption.active_response_id or "active"
                )
                continue
            if event_type == "function_call":
                function_response_id = str(event.get("response_id", "")).strip()
                if function_response_id:
                    tool_phase_response_ids.add(function_response_id)
                provider_call_id = str(event.get("provider_call_id", "")).strip()
                tool_name = str(event.get("tool_name", "")).strip()
                if not provider_call_id:
                    await self._send_event(
                        websocket,
                        "error",
                        provider="DashScope",
                        message="Qwen 返回了缺少 call ID 的工具请求，已拒绝执行。",
                    )
                    continue
                if tool_session.has_seen_provider_call(provider_call_id):
                    continue
                conversation_turn_id = recorder.current_turn_id if recorder is not None else ""
                tool_turn_id = tool_session.reserve_tool_call_id()
                try:
                    native_call = RealtimeToolCall(
                        provider="DashScope",
                        provider_call_id=provider_call_id,
                        tool_name=tool_name,
                        arguments=event.get("arguments", "{}"),
                    )
                    request = tool_call_to_request(native_call)
                except Exception as exc:
                    tool_session.mark_provider_call_seen(provider_call_id)
                    await self._send_dashscope_tool_response(
                        websocket,
                        conversation,
                        provider_call_id=provider_call_id,
                        tool_name=tool_name or "unknown_tool",
                        response_payload=tool_error_payload(str(exc)),
                        conversation_turn_id=conversation_turn_id,
                        recorder=recorder,
                    )
                    continue

                async def on_dashscope_native_result(
                    result: dict[str, Any],
                    *,
                    call_id: str = provider_call_id,
                    name: str = tool_name,
                    canonical_turn_id: str = conversation_turn_id,
                    local_tool_call_id: str = tool_turn_id,
                ) -> None:
                    nonlocal gated_tool_turn_id
                    gated_tool_turn_id = ""
                    await self._send_dashscope_tool_response(
                        websocket,
                        conversation,
                        provider_call_id=call_id,
                        tool_name=name,
                        response_payload=tool_result_payload(result),
                        result=result,
                        conversation_turn_id=canonical_turn_id,
                        tool_call_id=local_tool_call_id,
                        recorder=recorder,
                    )

                async def on_dashscope_native_error(
                    message: str,
                    *,
                    call_id: str = provider_call_id,
                    name: str = tool_name,
                    canonical_turn_id: str = conversation_turn_id,
                    local_tool_call_id: str = tool_turn_id,
                ) -> None:
                    nonlocal gated_tool_turn_id
                    gated_tool_turn_id = ""
                    await self._send_dashscope_tool_response(
                        websocket,
                        conversation,
                        provider_call_id=call_id,
                        tool_name=name,
                        response_payload=tool_error_payload(message),
                        conversation_turn_id=canonical_turn_id,
                        tool_call_id=local_tool_call_id,
                        recorder=recorder,
                    )

                async def on_dashscope_native_cancel(
                    message: str,
                    *,
                    call_id: str = provider_call_id,
                    name: str = tool_name,
                    canonical_turn_id: str = conversation_turn_id,
                    local_tool_call_id: str = tool_turn_id,
                ) -> None:
                    nonlocal gated_tool_turn_id
                    gated_tool_turn_id = ""
                    await self._send_dashscope_tool_response(
                        websocket,
                        conversation,
                        provider_call_id=call_id,
                        tool_name=name,
                        response_payload=tool_error_payload(message),
                        create_response=False,
                        conversation_turn_id=canonical_turn_id,
                        tool_call_id=local_tool_call_id,
                        recorder=recorder,
                    )

                gated_tool_turn_id = tool_turn_id
                await self._send_response_gated(
                    websocket,
                    provider="DashScope",
                    tool_name=tool_name,
                    query=request.query,
                    turn_id=tool_turn_id,
                    recorder=recorder,
                )

                await tool_session.handle_request(
                    request,
                    send_event=send_tool_event,
                    on_result=on_dashscope_native_result,
                    on_error=on_dashscope_native_error,
                    on_cancel=on_dashscope_native_cancel,
                    provider_call_id=provider_call_id,
                    conversation_turn_id=conversation_turn_id,
                    tool_call_id=tool_turn_id,
                )
                continue
            if event_type == "tool_phase_complete":
                response_id = str(event.get("response_id", "")).strip()
                tool_phase_response_ids.discard(response_id)
                if response_id == interruption.active_response_id:
                    interruption.active_response_id = ""
                continue
            if event_type == "user_transcript":
                cannot_create_response_retries = 0
                user_text = str(event.get("text", ""))
                if interruption.pending is None and (
                    interruption.active_response_id
                    or tool_session.has_active_task
                    or (recorder is not None and bool(recorder.current_assistant_text))
                ):
                    await self._begin_interruption(
                        websocket,
                        interruption,
                        provider="DashScope",
                        provider_event_type=str(
                            event.get("provider_event_type", "input_transcription.without_pending_vad")
                        ),
                        recorder=recorder,
                        tool_session=tool_session,
                        supersede_timed_out=True,
                    )
                interrupted_response_id = interruption.active_response_id
                had_deferred_terminal = interruption.has_deferred_terminal()
                async def cancel_dashscope_response() -> None:
                    try:
                        conversation.cancel_response()
                    except Exception:
                        logger.exception("dashscope_response_cancel_failed")

                should_process_user, interruption_decision = await self._decide_interruption(
                    websocket,
                    interruption,
                    user_text,
                    memory_session=memory_session,
                    tool_session=tool_session,
                    recorder=recorder,
                    cancel_provider=(cancel_dashscope_response if (interrupted_response_id and not had_deferred_terminal) else None),
                )
                if interruption_decision is not None and (
                    interruption_decision.get("classification") == InterruptionIntent.TRUE_BARGE_IN.value
                ) and interrupted_response_id and not had_deferred_terminal:
                    suppressed_response_ids.add(interrupted_response_id)
                if not should_process_user:
                    if had_deferred_terminal and interruption.take_deferred_terminal() is not None:
                        await self._finalize_realtime_turn(
                            websocket,
                            memory_session,
                            recorder,
                            gated=False,
                        )
                        self._configure_dashscope_conversation(
                            conversation,
                            voice=voice,
                            instructions=self._build_realtime_instructions(),
                        )
                    continue
                if InterruptionClassifier.classify_interruption(user_text) == InterruptionIntent.NOISE_OR_SILENCE:
                    continue
                memory_session.note_user_transcript(user_text)
                voice_turn_id = ""
                if recorder is not None:
                    voice_turn_id = await recorder.note_user_transcript(user_text)
                retrieval = await memory_session.retrieve_memory_context()
                memory_context = str(retrieval.get("context", ""))
                memory_count = int(retrieval.get("memories_retrieved", 0))
                local_pending_count = int(retrieval.get("local_pending_count", 0))
                cloud_count = int(retrieval.get("cloud_count", 0))
                if retrieval.get("attempted"):
                    await self._send_event(
                        websocket,
                        "memory_context",
                        memories_retrieved=memory_count,
                        local_pending_count=local_pending_count,
                        cloud_count=cloud_count,
                        attempted=True,
                    )
                if memory_context:
                    logger.info(
                        "voice_memory_inject provider=DashScope scope=%s count=%s local_pending=%s cloud=%s",
                        memory_session._config.memory_scope,
                        memory_count,
                        local_pending_count,
                        cloud_count,
                    )
                    self._configure_dashscope_conversation(
                        conversation,
                        voice=voice,
                        instructions=self._build_realtime_instructions(memory_context),
                    )
                elif memory_session.is_forced_recall_query(user_text):
                    logger.info(
                        "voice_memory_inject provider=DashScope scope=%s count=0 forced_recall=true",
                        memory_session._config.memory_scope,
                    )
                    self._configure_dashscope_conversation(
                        conversation,
                        voice=voice,
                        instructions=self._build_recall_miss_instructions(user_text),
                    )
                if interrupted_response_id and not had_deferred_terminal:
                    await asyncio.sleep(0.2)
                # Note: Qwen Server VAD automatically triggers response generation when speech ends,
                # so calling create_response() here is redundant and causes collision errors.
                # conversation.create_response()
                await self._send_event(websocket, "user_transcript", text=user_text, turn_id=voice_turn_id)
                continue
            elif event_type == "assistant_text":
                response_id = str(event.get("response_id", ""))
                if response_id in suppressed_response_ids:
                    continue
                if not gated_tool_turn_id:
                    await self._emit_assistant_output(
                        websocket,
                        interruption,
                        event,
                        memory_session=memory_session,
                        recorder=recorder,
                    )
                continue
            elif event_type == "assistant_audio":
                response_id = str(event.get("response_id", ""))
                if response_id in suppressed_response_ids:
                    continue
                if not gated_tool_turn_id:
                    await self._emit_assistant_output(
                        websocket,
                        interruption,
                        event,
                        memory_session=memory_session,
                        recorder=recorder,
                    )
                continue
            elif event_type == "turn_complete":
                response_id = str(event.get("response_id", ""))
                if response_id in tool_phase_response_ids:
                    tool_phase_response_ids.discard(response_id)
                    if response_id == interruption.active_response_id:
                        interruption.active_response_id = ""
                    continue
                if response_id in suppressed_response_ids:
                    suppressed_response_ids.discard(response_id)
                    if response_id == interruption.active_response_id:
                        interruption.active_response_id = ""
                    continue
                if interruption.defer_terminal(dict(event)):
                    continue
                if not response_id or response_id == interruption.active_response_id:
                    interruption.active_response_id = ""
                if str(event.get("status", "completed")) in {"cancelled", "canceled", "failed"}:
                    continue
                if not gated_tool_turn_id:
                    memory_result = await memory_session.flush_turn()
                    completed_turn_id = ""
                    if recorder is not None:
                        completed_turn_id = await recorder.complete_turn(memory_result)
                    await self._send_event(
                        websocket,
                        "memory_write",
                        attempted_count=int(memory_result.get("attempted_count", 0)),
                        saved_count=int(memory_result.get("saved_count", 0)),
                        failed_count=int(memory_result.get("failed_count", 0)),
                        local_pending_count=int(memory_result.get("local_pending_count", 0)),
                        reason=str(memory_result.get("reason", "")),
                    )
                    self._configure_dashscope_conversation(
                        conversation,
                        voice=voice,
                        instructions=self._build_realtime_instructions(),
                    )
                    await self._send_event(
                        websocket,
                        "turn_complete",
                        turn_id=completed_turn_id,
                        interrupted=False,
                    )
                continue
            if event_type == "error":
                error_msg = str(event.get("message", ""))
                if "no active response" in error_msg.lower():
                    logger.warning("DashScope returned non-fatal error: %s. Ignoring.", error_msg)
                    continue
                if "cannot create response" in error_msg.lower():
                    if cannot_create_response_retries < 2:
                        cannot_create_response_retries += 1
                        logger.warning(
                            "DashScope returned error: %s. Retrying create_response (attempt %d/2) after 300ms.",
                            error_msg,
                            cannot_create_response_retries,
                        )
                        async def delayed_retry():
                            await asyncio.sleep(0.3)
                            try:
                                conversation.create_response()
                            except Exception as exc:
                                logger.exception("dashscope_retry_create_response_failed")
                        spawn_background_task(delayed_retry())
                    else:
                        logger.warning("DashScope returned error: %s. Max retries exceeded. Ignoring.", error_msg)
                    continue
                await websocket.send_json(event)
                break
            await websocket.send_json(event)
    async def stream_dashscope_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_DASHSCOPE_REALTIME_VOICE,
        voiceprint_audio_urls: list[str] | None = None,
    ) -> None:
        settings = self._resolve_dashscope_settings(model)
        voice = _normalize_dashscope_realtime_voice(settings["model"], voice)
        memory_session = RealtimeMemorySession()
        tool_session = VoiceAgentToolSession()
        resolved_voice = (voice or DEFAULT_QWEN_OMNI_REALTIME_VOICE).strip()
        if "qwen3.5-omni" in settings["model"].lower() and resolved_voice not in QWEN_OMNI_REALTIME_VOICES:
            logger.warning(
                "qwen_omni_unsupported_voice voice=%s fallback=%s",
                resolved_voice, DEFAULT_QWEN_OMNI_REALTIME_VOICE,
            )
            resolved_voice = DEFAULT_QWEN_OMNI_REALTIME_VOICE
        recorder = await self._create_voice_session_recorder(
            provider="DashScope",
            model=settings["model"],
            voice=resolved_voice,
        )
        url = settings["realtime_base_url"]
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        callback = DashScopeRealtimeCallback(loop=loop, queue=event_queue)
        if _is_dashscope_audio_realtime_model(settings["model"]):
            all_settings = self.config.get_all()
            dashscope_realtime_settings = all_settings.get("dashscope_realtime")
            voiceprint_settings = dashscope_realtime_settings if isinstance(dashscope_realtime_settings, dict) else {}
            if "voiceprint_audio_urls" not in voiceprint_settings and "voiceprint_audio_urls" in all_settings:
                voiceprint_settings = {
                    **voiceprint_settings,
                    "voiceprint_audio_urls": all_settings.get("voiceprint_audio_urls"),
                }
            conversation = DashScopeAudioRealtimeConversation(
                model=settings["model"],
                api_key=settings["api_key"],
                callback=callback,
                url=url,
                voiceprint_audio_urls=self._resolve_dashscope_voiceprint_audio_urls(
                    voiceprint_settings,
                    voiceprint_audio_urls,
                ),
            )
        else:
            import dashscope

            dashscope.api_key = settings["api_key"]
            conversation = OmniRealtimeConversation(  # type: ignore[misc]
                model=settings["model"],
                callback=callback,
                url=url,
            )

        try:
            if isinstance(conversation, DashScopeAudioRealtimeConversation):
                await conversation.connect()
            else:
                conversation.connect()
            await asyncio.sleep(0.5)
            self._configure_dashscope_conversation(
                conversation,
                voice=resolved_voice,
                instructions=self._build_realtime_instructions(),
            )
            await asyncio.sleep(0.5)
            await self._send_event(
                websocket,
                "session_open",
                provider="DashScope",
                model=settings["model"],
                voice=resolved_voice,
                session_id=recorder.session_id if recorder is not None else "",
            )

            interruption = InterruptionDecisionCoordinator()
            send_task = asyncio.create_task(
                self._client_to_dashscope_loop(
                    websocket, conversation, memory_session, tool_session, recorder, interruption
                )
            )
            receive_task = asyncio.create_task(
                self._dashscope_to_client_loop(
                    websocket,
                    event_queue,
                    memory_session,
                    conversation,
                    voice,
                    tool_session,
                    recorder,
                    interruption,
                )
            )
            await self._run_duplex_tasks(send_task, receive_task)
        except WebSocketDisconnect:
            return
        except Exception as e:
            logger.exception("DashScope realtime session failed: %s", e)
            await self._send_event(websocket, "error", message=f"DashScope 实时会话启动失败: {str(e)}")
            return
        finally:
            memory_result = await memory_session.flush_turn()
            if recorder is not None:
                await recorder.complete_turn(memory_result)
            await memory_session.drain()
            await tool_session.drain(cancel=True)
            if recorder is not None:
                await recorder.finish()
            try:
                conversation.close()
            except Exception:
                pass
