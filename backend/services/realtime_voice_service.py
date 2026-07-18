from __future__ import annotations

import asyncio
import base64
import inspect
import json
import logging
import os
import re
import struct
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode

import websockets
from fastapi import WebSocket, WebSocketDisconnect

print(f"DEBUG: Realtime service using Python: {sys.executable}")
print(f"DEBUG: Python Path: {sys.path}")

logger = logging.getLogger(__name__)

from .config_loader import BackendConfig
from .evermem_config import EverMemConfig
from .evermem_service import EverMemService
from .interruption_classifier import (
    InterruptionClassifier,
    InterruptionDecisionCoordinator,
    InterruptionIntent,
)
from .voice_agent_session_repository import VoiceAgentSessionRepository
from .voice_agent_tools import VoiceAgentToolService, VoiceAgentToolSession, VoiceToolRequest
from .realtime_tool_protocol import (
    RealtimeToolCall,
    dashscope_supports_native_tools,
    dashscope_tool_declarations,
    native_tool_declarations,
    tool_call_to_request,
    tool_error_payload,
    tool_result_payload,
)
from .realtime_memory_session import RealtimeMemorySession, _merge_memory_text
from .realtime_dashscope_client import DashScopeRealtimeCallback, DashScopeAudioRealtimeConversation
from .realtime_session_recorder import VoiceAgentSessionRecorder

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
GOOGLE_LIVE_TRANSLATE_MODEL = "gemini-3.5-live-translate-preview"
DEFAULT_GOOGLE_REALTIME_VOICE = "Puck"
DEFAULT_DASHSCOPE_REALTIME_MODEL = "qwen3.5-omni-plus-realtime"
DEFAULT_DASHSCOPE_REALTIME_VOICE = "Tina"
# Voices supported by qwen3.5-omni-*-realtime models (default: Tina), per the
# official omni voice list. The provider rejects voices from the older
# qwen3-omni / qwen-omni-turbo family (e.g. "Cherry"), so the backend
# defensively falls back to a valid default instead of failing the session.
QWEN_OMNI_REALTIME_VOICES = (
    "Tina", "Cindy", "Liora Mira", "Sunnybobi", "Raymond", "Ethan", "Theo Calm",
    "Serena", "Harvey", "Maia", "Evan", "Qiao", "Momo", "Wil", "Angel",
    "Li Cassian", "Mia", "Joyner", "Gold", "Katerina", "Ryan", "Jennifer",
    "Aiden", "Mione", "Sunny", "Dylan", "Eric", "Peter", "Joseph Chen",
    "Marcus", "Li", "Kiki", "Rocky", "Sohee", "Lenn", "Ono Anna", "Sonrisa",
    "Bodega", "Emilien", "Andre", "Radio Gol", "Alek", "Rizky", "Roya", "Arda",
    "Hana", "Dolce", "Jakub", "Griet", "Eliška", "Marina", "Siiri", "Ingrid",
    "Sigga", "Bea", "Chloe",
)
DEFAULT_QWEN_OMNI_REALTIME_VOICE = "Tina"
# Voices supported by Qwen-Audio realtime models (qwen-audio-*). The provider rejects
# any voice outside this allow-list, so the backend defensively falls back to a valid
# default instead of forwarding an unsupported voice and failing the whole session.
QWEN_AUDIO_REALTIME_VOICES = (
    "longanqian", "longanlingxin", "longanlufeng", "longanlingxi", "longanxiaoxin",
    "longanfengyue", "longanyuanfei", "longanhuan_v3.6", "longjielidou_v3.6",
    "longpaopao_v3.6", "longhuohuo_v3.6", "longchuanshu_v3.6", "loongmary",
    "loongeva_v3.6", "loongjohn",
)
DEFAULT_QWEN_AUDIO_REALTIME_VOICE = "longanqian"
# Server-side error messages that indicate a benign race with the server's own
# turn management rather than a real failure; logged and ignored so the session
# survives them.
QWEN_AUDIO_BENIGN_ERROR_PATTERNS = (
    "Cannot create response while user is speaking",
    "no active response",
    "Cannot cancel",
    "already has an active response",
)
DEFAULT_OPENAI_REALTIME_MODEL = "gpt-realtime-2"
DEFAULT_OPENAI_REALTIME_VOICE = "alloy"
OPENAI_REALTIME_VOICES = ("alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse")
BASE_REALTIME_INSTRUCTIONS = (
    "You are a helpful, friendly, and intelligent AI assistant. "
    "Respond naturally and conversationally in the same language the user speaks. "
    "Use an available tool when current information or an explicit transformation requires it. "
    "Do not state a factual result before the tool response arrives, and give exactly one concise final answer. "
    "Respond in natural, clean, spoken-style conversational text. "
    "Absolutely do not use any Markdown formatting, bolding, list indicators, asterisks (*), hashtags (#), or other special formatting symbols, "
    "as your response is read aloud by real-time Text-to-Speech (TTS). Write all numbers, formulas, and abbreviations in their "
    "fully spoken-out verbal forms in the language of the conversation."
)

QWEN_AUDIO_REALTIME_INSTRUCTIONS = (
    "你是一位智能语音助手，你的名字是小云，性别女，声音甜美，举止亲切，你能回复用户的各种问题。"
    "请你按照下面的要求聊天：\n"
    "1. 像朋友之间聊天那样，语气自然友好，避免使用正式的称谓和模板化的表达。"
    "口语化只影响你的措辞和语气，不影响内容的完整性，该说的细节、数字、具体建议一个都不能少，"
    "只是用轻松自然的方式说出来。\n"
    "2. 充分考虑对话上下文中提到的所有约束条件（如预算、偏好、禁忌、之前达成的共识等），"
    "涉及多个条件或需要综合判断时逐一回应，不要遗漏关键信息。\n"
    "3. 除非用户要求，不要输出emoji等特殊符号，不要输出Markdown格式，尽量输出纯文本。\n"
    "4. 对于简单的日常闲聊、打招呼、情感回应，保持简洁自然。"
    "对于涉及事实判断、推理计算、多条件约束、推荐列表、安全建议的问题，"
    "以回答完整正确为优先，确保关键信息完整且正确，多说的内容必须是解决问题所必需的"
    "具体信息（如价格、地点、条件），而不是铺垫、重复或修辞。\n"
    "5. 适当引入追问，遵循\"先把用户当前的问题答好、再在结尾自然地追问，"
    "推动话题向前发展\"的原则，一次只问一个问题，不要连续追问或反复确认。"
    "用户明确要求背诵某篇文章、古诗词时，须遵循指令完整背诵。\n"
    "6. 当你需要搜索、查询外部信息时，请主动调用对应的工具函数来获取实时数据。"
    "调用工具后，必须等待工具返回结果再继续回复。"
    "绝对禁止凭空编造或猜测信息——如果工具返回的结果不包含用户想要的答案，"
    "请如实告知用户「抱歉，搜索未找到相关信息」，并建议用户换一种方式提问。"
    "工具返回的搜索结果可能包含英文内容，请用中文自然流畅地转述关键信息，"
    "不要直接复制粘贴来源文本。"
)


def _is_google_live_translate_model(model: str | None) -> bool:
    return "live-translate" in str(model or "").strip().lower()


def _is_dashscope_audio_realtime_model(model: str | None) -> bool:
    return bool(
        re.fullmatch(
            r"qwen-audio-3\.0-realtime(?:-(?:plus|flash))?",
            str(model or "").strip().lower(),
        )
    )


def _is_dashscope_omni_realtime_model(model: str | None) -> bool:
    return bool(
        re.fullmatch(
            r"qwen3\.5-omni-(?:plus|flash)-realtime(?:-\d{4}-\d{2}-\d{2})?",
            str(model or "").strip().lower(),
        )
    )


def _normalize_dashscope_realtime_voice(model: str | None, voice: str | None) -> str:
    selected = str(voice or "").strip()
    if _is_dashscope_audio_realtime_model(model):
        if selected in QWEN_AUDIO_REALTIME_VOICES:
            return selected
        return DEFAULT_QWEN_AUDIO_REALTIME_VOICE
    return selected or DEFAULT_DASHSCOPE_REALTIME_VOICE


def _is_google_public_rest_base_url(base_url: str | None) -> bool:
    normalized = str(base_url or "").strip().rstrip("/").lower()
    return normalized in {
        "https://generativelanguage.googleapis.com",
        "https://generativelanguage.googleapis.com/v1",
        "https://generativelanguage.googleapis.com/v1beta",
    }


# Extracted _resolve_pending_cache_path and _merge_memory_text to realtime_memory_session.py"


def _merge_streaming_text(previous: str, incoming: str) -> tuple[str, str]:
    """Return canonical stream text and only the novel suffix to publish."""
    before = str(previous or "").strip()
    next_text = str(incoming or "").strip()
    if not next_text:
        return before, ""
    if not before:
        return next_text, next_text
    if next_text.startswith(before):
        delta = next_text[len(before):]
        return next_text, delta
    if before.endswith(next_text):
        return before, ""

    overlap = 0
    for size in range(min(len(before), len(next_text)), 0, -1):
        if before[-size:] == next_text[:size]:
            overlap = size
            break
    novel = next_text[overlap:]
    if not novel:
        return before, ""

    separator = ""
    if (
        before[-1:].isalnum()
        and novel[:1].isalnum()
        and re.search(r"[A-Za-z]", before[-1:] + novel[:1])
    ):
        separator = " "
    delta = f"{separator}{novel}"
    return f"{before}{delta}", delta

def _audio_energy_qwen(audio_data: bytes) -> float:
    """Compute mean absolute sample amplitude for 16-bit PCM audio."""
    count = len(audio_data) // 2
    if count == 0:
        return 0.0
    samples = struct.unpack(f'<{count}h', audio_data)
    return sum(abs(s) for s in samples) / count


# Extracted RealtimeMemorySession, DashScopeRealtimeCallback, DashScopeAudioRealtimeConversation, VoiceAgentSessionRecorder


class RealtimeVoiceService:
    def __init__(
        self,
        config: BackendConfig | None = None,
        voice_session_repository: VoiceAgentSessionRepository | None = None,
    ):
        self.config = config or BackendConfig()
        self.voice_session_repository = voice_session_repository

    @staticmethod
    async def _run_duplex_tasks(*tasks: asyncio.Task[Any]) -> None:
        """Stop the peer loop on normal disconnect as well as on exceptions."""
        done, pending = await asyncio.wait(set(tasks), return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task.result()

    async def _create_voice_session_recorder(
        self,
        *,
        provider: str,
        model: str,
        voice: str,
    ) -> "VoiceAgentSessionRecorder | None":
        try:
            repository = self.voice_session_repository or VoiceAgentSessionRepository()
            session = await asyncio.to_thread(
                repository.create_session,
                provider=provider,
                model=model,
                voice=voice,
                meta={"transport": "websocket"},
            )
            recorder = VoiceAgentSessionRecorder(repository, str(session["id"]))
            await recorder.start(
                {
                    "provider": provider,
                    "model": model,
                    "voice": voice,
                    "status": "open",
                    "meta": {"transport": "websocket"},
                }
            )
            return recorder
        except Exception:
            logger.exception("voice_agent_session_create_failed provider=%s model=%s", provider, model)
            return None

    @staticmethod
    def _get_base_instructions() -> str:
        import datetime
        current_date = datetime.date.today().isoformat()
        return f"{BASE_REALTIME_INSTRUCTIONS}\nCurrent Date: {current_date}."

    @staticmethod
    def _build_realtime_instructions(memory_context: str = "") -> str:
        base_inst = RealtimeVoiceService._get_base_instructions()
        if not memory_context:
            return base_inst
        return (
            f"{base_inst}\n\n"
            "Relevant long-term memories for personalization are provided below. Use them whenever they are relevant. "
            "If the user asks what they said earlier, what the current focus is, or asks you to recall/search memory, "
            "answer from this memory block directly. Do not claim you cannot remember, do not say each conversation is "
            "independent, and do not ignore the memory block when it is relevant. Only avoid quoting the block verbatim "
            "unless the user directly asks.\n"
            f"{memory_context}"
        )

    @staticmethod
    def _build_recall_miss_instructions(user_query: str) -> str:
        base_inst = RealtimeVoiceService._get_base_instructions()
        return (
            f"{base_inst}\n\n"
            "The user is explicitly asking you to recall prior conversation memory, but no matching long-term "
            "memory was retrieved for this turn. Do not pretend you remember specific prior facts. "
            "State briefly that you could not retrieve a matching saved memory, then ask the user to restate "
            "the detail if needed.\n"
            f"Current user query: {user_query}"
        )

    @staticmethod
    def _build_google_memory_prefill_turns(memory_context: str) -> list[dict[str, Any]]:
        if not memory_context.strip():
            return []
        return [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Context note for personalization only. These long-term memories may help with "
                            "the user's next turn. Use them only when relevant, and do not mention this note.\n"
                            f"{memory_context}"
                        )
                    }
                ],
            }
        ]

    async def _apply_google_memory_prefill(self, session: Any, memory_context: str) -> None:
        turns = self._build_google_memory_prefill_turns(memory_context)
        if not turns:
            return
        try:
            await session.send_client_content(turns=turns, turn_complete=False)
        except Exception:
            return

    async def _send_google_tool_response(
        self,
        websocket: WebSocket,
        session: Any,
        *,
        provider_call_id: str,
        tool_name: str,
        response_payload: dict[str, Any],
        result: dict[str, Any] | None = None,
        conversation_turn_id: str = "",
        tool_call_id: str = "",
        recorder: VoiceAgentSessionRecorder | None = None,
    ) -> None:
        await self._send_google_tool_response_batch(
            websocket,
            session,
            responses=[
                {
                    "provider_call_id": provider_call_id,
                    "tool_name": tool_name,
                    "response_payload": response_payload,
                    "result": result or {},
                    "conversation_turn_id": conversation_turn_id,
                    "tool_call_id": tool_call_id,
                }
            ],
            recorder=recorder,
        )

    async def _send_google_tool_response_batch(
        self,
        websocket: WebSocket,
        session: Any,
        *,
        responses: list[dict[str, Any]],
        recorder: VoiceAgentSessionRecorder | None = None,
    ) -> None:
        if not responses:
            return
        function_responses = []
        for item in responses:
            provider_call_id = str(item.get("provider_call_id", "")).strip()
            tool_name = str(item.get("tool_name", "")).strip()
            response_payload = item.get("response_payload") or {}
            if not provider_call_id:
                raise ValueError("Google native tool response requires a provider call ID.")
            function_responses.append(
                types.FunctionResponse(
                    id=provider_call_id,
                    name=tool_name,
                    response={"output": response_payload} if response_payload.get("ok") else {"error": response_payload},
                )
            )
        try:
            await session.send_tool_response(function_responses=function_responses)
        except Exception as exc:
            try:
                await self._send_event(
                    websocket,
                    "error",
                    provider="Google",
                    message=f"Google 工具结果回传失败，会话已关闭: {exc}",
                )
            except Exception:
                pass
            close_session = getattr(session, "close", None)
            if callable(close_session):
                try:
                    close_result = close_session()
                    if inspect.isawaitable(close_result):
                        await close_result
                except Exception:
                    logger.exception("google_session_close_after_tool_delivery_failed")
            raise
        for item in responses:
            provider_call_id = str(item.get("provider_call_id", "")).strip()
            tool_name = str(item.get("tool_name", "")).strip()
            response_payload = item.get("response_payload") or {}
            result = item.get("result") or {}
            payload = {
                "provider": "Google",
                "provider_call_id": provider_call_id,
                "tool_name": tool_name,
                "query": str(result.get("query", "")),
                "turn_id": str(item.get("conversation_turn_id", "")),
                "tool_call_id": str(item.get("tool_call_id", "")),
                "route": "native",
                "source_count": int(result.get("source_count", 0) or 0),
                "elapsed_ms": int(result.get("elapsed_ms", 0) or 0),
                "status": "completed" if response_payload.get("ok") else "failed",
            }
            if recorder is not None:
                await recorder.record_tool_event("tool_result_delivered", payload)
            await self._send_event(websocket, "tool_result_delivered", **payload)

    async def _send_response_gated(
        self,
        websocket: WebSocket,
        *,
        provider: str,
        tool_name: str,
        query: str,
        turn_id: str,
        recorder: VoiceAgentSessionRecorder | None = None,
    ) -> None:
        payload = {
            "provider": provider,
            "tool_name": tool_name,
            "query": query,
            "turn_id": turn_id,
            "message": "检测到工具请求，已暂停直接回答，等待工具结果。",
        }
        if recorder is not None:
            await recorder.record_tool_event("response_gated", payload)
        await self._send_event(
            websocket,
            "response_gated",
            **payload,
        )

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

    def _resolve_google_settings(self, model: str | None) -> dict[str, str]:
        provider_settings = self.config.get_provider_settings("Google", model)
        resolved_model = provider_settings["model"].strip() or DEFAULT_GOOGLE_REALTIME_MODEL
        api_key = provider_settings["api_key"].strip()
        base_url = provider_settings["base_url"].strip()
        if _is_google_public_rest_base_url(base_url):
            base_url = ""
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
        if not api_key:
            raise RuntimeError("DashScope API Key 未配置，无法启动实时语音会话。")
        if _is_dashscope_omni_realtime_model(resolved_model):
            if OmniRealtimeConversation is None or MultiModality is None or AudioFormat is None:
                raise RuntimeError("DashScope Omni Realtime 依赖未安装，无法启动实时语音会话。")
        if not dashscope_supports_native_tools(resolved_model):
            raise RuntimeError(
                "VoiceSpirit 实时语音仅支持具备原生 Function Calling 的 "
                "qwen3.5-omni-plus-realtime、qwen3.5-omni-flash-realtime，或 qwen-audio-3.0-realtime-plus/flash；请在设置中升级模型。"
            )
        realtime_base_url = (
            str(provider_settings.get("realtime_base_url", "")).strip()
            or os.environ.get("DASHSCOPE_REALTIME_BASE_URL", "").strip()
        ).rstrip("/")
        if not realtime_base_url.startswith("wss://") or not realtime_base_url.endswith("/api-ws/v1/realtime"):
            raise RuntimeError(
                "请在设置中配置 Qwen 的业务空间 Realtime WebSocket URL，"
                "格式如 wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime。"
            )
        parsed_url = urlparse(realtime_base_url)
        endpoint_host = (parsed_url.hostname or "").lower()
        if _is_dashscope_audio_realtime_model(resolved_model) and not endpoint_host.endswith(".cn-beijing.maas.aliyuncs.com"):
            raise RuntimeError(
                "qwen-audio-3.0-realtime 仅支持北京地域业务空间 Realtime WebSocket URL，"
                "格式如 wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime。"
            )
        return {
            "api_key": api_key,
            "model": resolved_model,
            "realtime_base_url": realtime_base_url,
        }

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

    @staticmethod
    async def _send_event(websocket: WebSocket, event_type: str, **payload: Any) -> None:
        await websocket.send_json({"type": event_type, **payload})

    async def _begin_interruption(
        self,
        websocket: WebSocket,
        coordinator: InterruptionDecisionCoordinator,
        *,
        provider: str,
        provider_event_type: str,
        recorder: VoiceAgentSessionRecorder | None,
        tool_session: VoiceAgentToolSession,
        supersede_timed_out: bool = False,
    ) -> None:
        interrupted_turn_id = recorder.current_turn_id if recorder is not None else ""
        if not interrupted_turn_id:
            interrupted_turn_id = tool_session.current_turn_id
        payload = coordinator.begin(
            provider=provider,
            interrupted_turn_id=interrupted_turn_id,
            provider_event_type=provider_event_type,
            supersede_timed_out=supersede_timed_out,
        )
        if payload is None:
            return
        if recorder is not None:
            await recorder.record_session_event(
                "interruption_pending",
                source="interruption",
                turn_id=interrupted_turn_id,
                payload=dict(payload),
            )
        await self._send_event(websocket, "interruption_pending", **payload)

    async def _deliver_assistant_output(
        self,
        websocket: WebSocket,
        event: dict[str, Any],
        *,
        memory_session: RealtimeMemorySession,
        recorder: VoiceAgentSessionRecorder | None,
        record_memory: bool = True,
    ) -> None:
        event_type = str(event.get("type", ""))
        if event_type == "assistant_text":
            text = str(event.get("text", ""))
            # Strip Markdown symbols to prevent TTS from reading them aloud
            text = re.sub(r"[\*#`]", "", text)
            if record_memory:
                memory_session.note_assistant_text(text)
            turn_id = await recorder.note_assistant_text(text) if recorder is not None else ""
            await self._send_event(websocket, "assistant_text", text=text, turn_id=turn_id)
            return
        if event_type == "assistant_audio":
            turn_id = ""
            first_audio_ms: int | None = None
            if recorder is not None:
                turn_id, first_audio_ms = await recorder.note_assistant_audio()
            payload = {
                "audio": str(event.get("audio", "")),
                "encoding": str(event.get("encoding", "pcm_s16le")),
                "sample_rate": int(event.get("sample_rate", 24000) or 24000),
                "turn_id": turn_id,
            }
            if first_audio_ms is not None:
                payload["first_audio_ms"] = first_audio_ms
            await self._send_event(websocket, "assistant_audio", **payload)

    async def _emit_assistant_output(
        self,
        websocket: WebSocket,
        coordinator: InterruptionDecisionCoordinator,
        event: dict[str, Any],
        *,
        memory_session: RealtimeMemorySession,
        recorder: VoiceAgentSessionRecorder | None,
        record_memory: bool = True,
    ) -> None:
        async with coordinator.output_lock:
            if coordinator.pending is not None:
                coordinator.buffer_output(event)
                return
            await self._deliver_assistant_output(
                websocket,
                event,
                memory_session=memory_session,
                recorder=recorder,
                record_memory=record_memory,
            )

    async def _flush_interruption_output(
        self,
        websocket: WebSocket,
        coordinator: InterruptionDecisionCoordinator,
        *,
        memory_session: RealtimeMemorySession,
        recorder: VoiceAgentSessionRecorder | None,
        record_memory: bool = True,
    ) -> None:
        for event in coordinator.take_buffered_output():
            await self._deliver_assistant_output(
                websocket,
                dict(event),
                memory_session=memory_session,
                recorder=recorder,
                record_memory=record_memory,
            )

    async def _decide_interruption(
        self,
        websocket: WebSocket,
        coordinator: InterruptionDecisionCoordinator,
        text: str,
        *,
        memory_session: RealtimeMemorySession,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None,
        cancel_provider: Callable[[], Awaitable[None]] | None = None,
        resume_provider: Callable[[], Awaitable[None]] | None = None,
        record_memory: bool = True,
        expected_candidate_id: str = "",
        timeout_resolution: bool = False,
    ) -> tuple[bool, dict[str, Any] | None]:
        async with coordinator.decision_lock:
            if expected_candidate_id and (
                coordinator.pending is None
                or coordinator.pending.candidate_id != expected_candidate_id
            ):
                return True, None
            decision = coordinator.decide(text)
            if decision is None:
                return True, None
            classification = str(decision.get("classification", ""))
            interrupted_turn_id = str(decision.get("interrupted_turn_id", ""))
            is_true_barge_in = classification == InterruptionIntent.TRUE_BARGE_IN.value
            decision["assistant_interrupted"] = is_true_barge_in
            decision["provider_cancel_requested"] = bool(is_true_barge_in and cancel_provider is not None)
            decision["tool_cancelled"] = bool(is_true_barge_in and tool_session.has_active_task)
            decision["stop_latency_ms"] = int(decision.get("decision_latency_ms", 0) or 0)
            decision["timeout_resolution"] = bool(timeout_resolution)
            try:
                if recorder is not None:
                    await recorder.record_session_event(
                        "interruption_decision",
                        source="interruption",
                        turn_id=interrupted_turn_id,
                        text=str(text or "").strip(),
                        payload=dict(decision),
                    )
                async with coordinator.output_lock:
                    if is_true_barge_in:
                        coordinator.discard_buffered_output()
                        coordinator.discard_deferred_terminal()
                        await self._send_event(websocket, "interruption_decision", **decision)
                        if cancel_provider is not None:
                            try:
                                await cancel_provider()
                            except Exception:
                                logger.exception(
                                    "provider_response_cancel_failed provider=%s turn_id=%s",
                                    decision.get("provider", ""),
                                    interrupted_turn_id,
                                )
                        await tool_session.cancel(
                            send_event=self._tool_event_sender(websocket, recorder),
                            reason="true_barge_in",
                        )
                        discard_memory_turn = getattr(memory_session, "discard_turn", None)
                        if callable(discard_memory_turn):
                            discard_memory_turn()
                        if recorder is not None:
                            await recorder.interrupt_current_turn()
                        await self._send_event(
                            websocket,
                            "interrupted",
                            candidate_id=str(decision.get("candidate_id", "")),
                            turn_id=interrupted_turn_id,
                            interrupted=True,
                            stop_latency_ms=decision["stop_latency_ms"],
                        )
                    else:
                        effective_resume_provider = resume_provider or coordinator.resume_provider
                        if effective_resume_provider is not None:
                            await effective_resume_provider()
                        await self._send_event(websocket, "interruption_decision", **decision)
                        await self._flush_interruption_output(
                            websocket,
                            coordinator,
                            memory_session=memory_session,
                            recorder=recorder,
                            record_memory=record_memory,
                        )
                return is_true_barge_in, decision
            finally:
                coordinator.complete_decision(timed_out=timeout_resolution)

    def _tool_event_sender(
        self,
        websocket: WebSocket,
        recorder: VoiceAgentSessionRecorder | None,
    ) -> Callable[[str, dict[str, Any]], Awaitable[None]]:
        async def send_tool_event(event_type: str, payload: dict[str, Any]) -> None:
            if recorder is not None:
                await recorder.record_tool_event(event_type, payload)
            await self._send_event(websocket, event_type, **payload)

        return send_tool_event

    async def _record_client_interruption_stop(
        self,
        recorder: VoiceAgentSessionRecorder | None,
        payload: dict[str, Any],
        *,
        provider: str,
    ) -> None:
        if recorder is None:
            return
        candidate_id = str(payload.get("candidate_id", "") or "").strip()
        turn_id = str(payload.get("turn_id", "") or "").strip()
        raw_latency = payload.get("stop_latency_ms")
        if not candidate_id or not isinstance(raw_latency, (int, float)):
            return
        await recorder.record_session_event(
            "interruption_client_stopped",
            source="metric",
            turn_id=turn_id,
            payload={
                "candidate_id": candidate_id,
                "provider": provider,
                "stop_latency_ms": max(0, min(int(raw_latency), 120_000)),
                "stage": "client_playback_stopped",
            },
        )

    async def _finalize_realtime_turn(
        self,
        websocket: WebSocket,
        memory_session: RealtimeMemorySession,
        recorder: VoiceAgentSessionRecorder | None,
        *,
        gated: bool = False,
    ) -> tuple[dict[str, Any], str]:
        memory_result = await memory_session.flush_turn()
        completed_turn_id = ""
        if recorder is not None and not gated:
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
        if not gated:
            await self._send_event(
                websocket,
                "turn_complete",
                turn_id=completed_turn_id,
                interrupted=False,
            )
        return memory_result, completed_turn_id

    @staticmethod
    def _extract_transcript_text(server_content: Any, candidate_names: tuple[str, ...]) -> str:
        for attr_name in candidate_names:
            if not hasattr(server_content, attr_name):
                continue
            value = getattr(server_content, attr_name)
            if not value:
                continue
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, dict):
                text = value.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
                continue
            if hasattr(value, "text"):
                text = getattr(value, "text", None)
                if isinstance(text, str) and text.strip():
                    return text.strip()
                continue
        return ""

    @staticmethod
    def _has_transcript_field(server_content: Any, candidate_names: tuple[str, ...]) -> bool:
        return any(
            hasattr(server_content, attr_name) and getattr(server_content, attr_name) is not None
            for attr_name in candidate_names
        )

    @staticmethod
    def _build_live_config(voice: str, instructions: str = ""):
        declarations = [
            types.FunctionDeclaration(
                name=declaration["name"],
                description=declaration["description"],
                parameters_json_schema=declaration["parameters"],
            )
            for declaration in native_tool_declarations()
        ]
        system_inst = instructions or RealtimeVoiceService._build_realtime_instructions()
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=system_inst,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            tools=[types.Tool(function_declarations=declarations)],
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
                    silence_duration_ms=1500,
                ),
                activity_handling=types.ActivityHandling.NO_INTERRUPTION,
            ),
        )

    @staticmethod
    def _build_live_translate_config(target_language_code: str, echo_target_language: bool):
        target = (target_language_code or "en").strip() or "en"
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            translation_config=types.TranslationConfig(
                target_language_code=target,
                echo_target_language=bool(echo_target_language),
            ),
        )

    async def _client_to_google_loop(
        self,
        websocket: WebSocket,
        session: Any,
        memory_session: RealtimeMemorySession,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        is_live_translate: bool = False,
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
                if command_type == "text_input":
                    if is_live_translate:
                        await self._send_event(
                            websocket,
                            "error",
                            message="Gemini Live Translate 仅支持实时音频输入，不支持文本输入。",
                        )
                        continue
                    content = str(payload.get("text", "")).strip()
                    if content:
                        await session.send(input=content, end_of_turn=True)
                    continue
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "interruption_client_stopped":
                    await self._record_client_interruption_stop(recorder, payload, provider="Google")
                    continue
                if command_type == "speech_activity_started":
                    if not is_live_translate and (
                        tool_session.has_active_task
                        or (recorder is not None and bool(recorder.current_turn_id))
                    ):
                        await self._begin_interruption(
                            websocket,
                            interruption,
                            provider="Google",
                            provider_event_type="client_vad.speech_started",
                            recorder=recorder,
                            tool_session=tool_session,
                        )
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
                        record_memory=not is_live_translate,
                        expected_candidate_id=(timeout_candidate_id or interruption.pending.candidate_id),
                        timeout_resolution=True,
                    )
                    if (
                        not should_process_user
                        and interruption.take_deferred_terminal() is not None
                    ):
                        if not is_live_translate:
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
                if not tool_session.has_active_task:
                    await session.send_realtime_input(
                        audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                    )

    async def _google_to_client_loop(
        self,
        websocket: WebSocket,
        session: Any,
        memory_session: RealtimeMemorySession,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        is_live_translate: bool = False,
        interruption: InterruptionDecisionCoordinator | None = None,
    ) -> None:
        pending_prefill_context = ""
        gated_tool_turn_id = ""
        interruption = interruption or InterruptionDecisionCoordinator()
        pending_google_user_transcript = ""
        finalized_google_user_transcript = ""
        google_provider_interrupted_early = False
        suppress_interrupted_google_response = False
        consume_next_google_terminal = False
        last_activity_time = time.time()
        live_translate_has_content = False
        pending_google_response_text = ""
        google_output_transcription_seen = False
        google_output_transcription_text = ""
        live_translate_input_finished = False
        live_translate_output_finished = False

        async def finalize_user_transcript_if_needed(clear_transcript: bool = False) -> None:
            nonlocal pending_google_user_transcript, finalized_google_user_transcript, google_provider_interrupted_early
            nonlocal suppress_interrupted_google_response, consume_next_google_terminal
            nonlocal gated_tool_turn_id, pending_prefill_context
            nonlocal last_activity_time

            user_text = pending_google_user_transcript.strip()
            if pending_google_user_transcript == finalized_google_user_transcript:
                if clear_transcript:
                    pending_google_user_transcript = ""
                    finalized_google_user_transcript = ""
                return

            if clear_transcript:
                pending_google_user_transcript = ""
                finalized_google_user_transcript = ""
            else:
                finalized_google_user_transcript = pending_google_user_transcript

            if not user_text:
                return

            if is_live_translate:
                # In live translate mode, VAD and interruption logic are bypassed
                voice_turn_id = ""
                if recorder is not None:
                    voice_turn_id = await recorder.note_user_transcript(user_text)
                await self._send_event(websocket, "user_transcript", text=user_text, turn_id=voice_turn_id)
                last_activity_time = time.time()
                return

            if interruption.pending is None and (
                google_provider_interrupted_early
                or tool_session.has_active_task
                or (recorder is not None and bool(recorder.current_assistant_text))
            ):
                await self._begin_interruption(
                    websocket,
                    interruption,
                    provider="Google",
                    provider_event_type="input_transcription.without_pending_vad",
                    recorder=recorder,
                    tool_session=tool_session,
                    supersede_timed_out=True,
                )
            had_deferred_terminal = interruption.has_deferred_terminal()

            should_process_user, interruption_decision = await self._decide_interruption(
                websocket,
                interruption,
                user_text,
                memory_session=memory_session,
                tool_session=tool_session,
                recorder=recorder,
                record_memory=not is_live_translate,
            )
            if not should_process_user:
                google_provider_interrupted_early = False
                if interruption.take_deferred_terminal() is not None and not is_live_translate:
                    await self._finalize_realtime_turn(
                        websocket,
                        memory_session,
                        recorder,
                        gated=bool(gated_tool_turn_id),
                    )
                return
            if interruption_decision is not None:
                is_true_barge_in = (
                    interruption_decision.get("classification")
                    == InterruptionIntent.TRUE_BARGE_IN.value
                )
                suppress_interrupted_google_response = bool(
                    is_true_barge_in
                    and not google_provider_interrupted_early
                    and not had_deferred_terminal
                )
                consume_next_google_terminal = bool(
                    not had_deferred_terminal
                    and is_true_barge_in
                    and not google_provider_interrupted_early
                )
                google_provider_interrupted_early = False
            if InterruptionClassifier.classify_interruption(user_text) == InterruptionIntent.NOISE_OR_SILENCE:
                return
            voice_turn_id = ""
            if not is_live_translate:
                memory_session.note_user_transcript(user_text)
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
                        "voice_memory_inject provider=Google scope=%s count=%s local_pending=%s cloud=%s",
                        memory_session._config.memory_scope,
                        memory_count,
                        local_pending_count,
                        cloud_count,
                    )
                    pending_prefill_context = memory_context
            await self._send_event(websocket, "user_transcript", text=user_text, turn_id=voice_turn_id)

        async def send_tool_event(event_type: str, payload: dict[str, Any]) -> None:
            if recorder is not None:
                await recorder.record_tool_event(event_type, payload)
            await self._send_event(websocket, event_type, **payload)

        google_tool_batches: dict[str, dict[str, Any]] = {}

        async def submit_google_batch_result(
            provider_call_id: str,
            tool_name: str,
            response_payload: dict[str, Any],
            result: dict[str, Any] | None = None,
            *,
            conversation_turn_id: str = "",
            tool_call_id: str = "",
            wait_for_delivery: bool = True,
        ) -> None:
            batch = google_tool_batches.get(provider_call_id)
            if batch is None:
                return
            ready: list[dict[str, Any]] | None = None
            ready_ids: list[str] = []
            acknowledgement: asyncio.Future[Any] = batch["acknowledgements"][provider_call_id]
            async with batch["lock"]:
                if batch["phase"] != "collecting" or provider_call_id not in batch["expected"]:
                    return
                batch["results"][provider_call_id] = {
                    "provider_call_id": provider_call_id,
                    "tool_name": tool_name,
                    "response_payload": response_payload,
                    "result": result or {},
                    "conversation_turn_id": conversation_turn_id,
                    "tool_call_id": tool_call_id,
                }
                if batch["expected"].issubset(batch["results"]):
                    batch["phase"] = "sending"
                    ready_ids = [call_id for call_id in batch["order"] if call_id in batch["expected"]]
                    ready = [batch["results"][call_id] for call_id in ready_ids]
            if ready is not None:
                delivery_error: BaseException | None = None
                try:
                    await self._send_google_tool_response_batch(
                        websocket,
                        session,
                        responses=ready,
                        recorder=recorder,
                    )
                except BaseException as exc:
                    delivery_error = exc
                for call_id in ready_ids:
                    pending_ack = batch["acknowledgements"][call_id]
                    if not pending_ack.done():
                        pending_ack.set_result(delivery_error)
                async with batch["lock"]:
                    batch["phase"] = "failed" if delivery_error is not None else "delivered"
                    for call_id in batch["order"]:
                        google_tool_batches.pop(call_id, None)
                if delivery_error is not None:
                    raise delivery_error
            if wait_for_delivery:
                delivery_error = await acknowledgement
                if isinstance(delivery_error, BaseException):
                    raise delivery_error

        async def drop_google_batch_call(provider_call_id: str) -> bool:
            batch = google_tool_batches.get(provider_call_id)
            if batch is None:
                return False
            ready: list[dict[str, Any]] | None = None
            ready_ids: list[str] = []
            async with batch["lock"]:
                if batch["phase"] != "collecting":
                    return False
                batch["expected"].discard(provider_call_id)
                batch["results"].pop(provider_call_id, None)
                google_tool_batches.pop(provider_call_id, None)
                dropped_ack = batch["acknowledgements"][provider_call_id]
                if not dropped_ack.done():
                    dropped_ack.set_result(asyncio.CancelledError())
                if batch["expected"].issubset(batch["results"]):
                    batch["phase"] = "sending"
                    ready_ids = [call_id for call_id in batch["order"] if call_id in batch["expected"]]
                    ready = [batch["results"][call_id] for call_id in ready_ids]
            if ready:
                delivery_error: BaseException | None = None
                try:
                    await self._send_google_tool_response_batch(
                        websocket,
                        session,
                        responses=ready,
                        recorder=recorder,
                    )
                except BaseException as exc:
                    delivery_error = exc
                for call_id in ready_ids:
                    pending_ack = batch["acknowledgements"][call_id]
                    if not pending_ack.done():
                        pending_ack.set_result(delivery_error)
                async with batch["lock"]:
                    batch["phase"] = "failed" if delivery_error is not None else "delivered"
                    for call_id in batch["order"]:
                        google_tool_batches.pop(call_id, None)
                if delivery_error is not None:
                    raise delivery_error
            elif not batch["expected"]:
                async with batch["lock"]:
                    batch["phase"] = "cancelled"
                    for call_id in batch["order"]:
                        google_tool_batches.pop(call_id, None)
            return True

        async def complete_live_translate_turn_if_needed(*, force: bool = False) -> bool:
            nonlocal pending_google_user_transcript, finalized_google_user_transcript
            nonlocal live_translate_has_content, live_translate_input_finished
            nonlocal live_translate_output_finished, last_activity_time

            if not is_live_translate or not live_translate_has_content:
                return False
            if not force and not (live_translate_input_finished and live_translate_output_finished):
                return False

            completed_turn_id = ""
            if recorder is not None:
                completed_turn_id = await recorder.complete_turn({})
            await self._send_event(
                websocket,
                "turn_complete",
                turn_id=completed_turn_id,
                interrupted=False,
            )
            pending_google_user_transcript = ""
            finalized_google_user_transcript = ""
            live_translate_has_content = False
            live_translate_input_finished = False
            live_translate_output_finished = False
            last_activity_time = time.time()
            return True

        monitor_task = None
        if is_live_translate:
            async def monitor_live_translate_inactivity():
                try:
                    while True:
                        await asyncio.sleep(0.5)
                        if live_translate_has_content:
                            now = time.time()
                            if now - last_activity_time >= 2.0:
                                await complete_live_translate_turn_if_needed(force=True)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.exception("Error in live translate inactivity monitor: %s", e)

            monitor_task = asyncio.create_task(monitor_live_translate_inactivity())

        try:
            while True:
                turn = session.receive()
                async for response in turn:
                    audio_data = getattr(response, "data", None)
                    if audio_data:
                        if is_live_translate:
                            last_activity_time = time.time()
                        if not is_live_translate:
                            await finalize_user_transcript_if_needed(clear_transcript=True)
                        if not gated_tool_turn_id and not suppress_interrupted_google_response:
                            await self._emit_assistant_output(
                                websocket,
                                interruption,
                                {
                                    "type": "assistant_audio",
                                    "audio": base64.b64encode(audio_data).decode("ascii"),
                                    "encoding": "pcm_s16le",
                                    "sample_rate": 24000,
                                },
                                memory_session=memory_session,
                                recorder=recorder,
                                record_memory=not is_live_translate,
                            )

                    response_text = getattr(response, "text", None)
                    if response_text:
                        if is_live_translate:
                            last_activity_time = time.time()
                            live_translate_has_content = True
                        if not is_live_translate:
                            await finalize_user_transcript_if_needed(clear_transcript=True)
                        pending_google_response_text, _ = _merge_streaming_text(
                            pending_google_response_text,
                            str(response_text),
                        )

                    tool_call = getattr(response, "tool_call", None)
                    if tool_call is not None and not is_live_translate:
                        function_calls = list(getattr(tool_call, "function_calls", None) or [])
                        new_calls: list[tuple[Any, str, str]] = []
                        for function_call in function_calls:
                            provider_call_id = str(getattr(function_call, "id", "") or "").strip()
                            tool_name = str(getattr(function_call, "name", "") or "").strip()
                            if not provider_call_id:
                                await self._send_event(
                                    websocket,
                                    "error",
                                    provider="Google",
                                    message="Google 返回了缺少 call ID 的工具请求，已拒绝执行。",
                                )
                                continue
                            if tool_session.has_seen_provider_call(provider_call_id):
                                continue
                            if any(existing_id == provider_call_id for _, existing_id, _ in new_calls):
                                continue
                            new_calls.append((function_call, provider_call_id, tool_name))

                        if new_calls:
                            batch = {
                                "order": [call_id for _, call_id, _ in new_calls],
                                "expected": {call_id for _, call_id, _ in new_calls},
                                "results": {},
                                "acknowledgements": {
                                    call_id: asyncio.get_running_loop().create_future()
                                    for _, call_id, _ in new_calls
                                },
                                "lock": asyncio.Lock(),
                                "phase": "collecting",
                            }
                            for _, call_id, _ in new_calls:
                                google_tool_batches[call_id] = batch

                        for function_call, provider_call_id, tool_name in new_calls:
                            conversation_turn_id = recorder.current_turn_id if recorder is not None else ""
                            tool_turn_id = tool_session.reserve_tool_call_id()
                            raw_arguments = getattr(function_call, "args", {}) or {}
                            try:
                                native_call = RealtimeToolCall(
                                    provider="Google",
                                    provider_call_id=provider_call_id,
                                    tool_name=tool_name,
                                    arguments=raw_arguments,
                                )
                                request = tool_call_to_request(native_call)
                            except Exception as exc:
                                tool_session.mark_provider_call_seen(provider_call_id)
                                await submit_google_batch_result(
                                    provider_call_id,
                                    tool_name or "unknown_tool",
                                    tool_error_payload(str(exc)),
                                    conversation_turn_id=conversation_turn_id,
                                    tool_call_id=tool_turn_id,
                                    wait_for_delivery=False,
                                )
                                continue

                            async def on_google_native_result(
                                 result: dict[str, Any],
                                 *,
                                 call_id: str = provider_call_id,
                                 name: str = tool_name,
                                 canonical_turn_id: str = conversation_turn_id,
                                 local_tool_call_id: str = tool_turn_id,
                             ) -> None:
                                 nonlocal gated_tool_turn_id
                                 gated_tool_turn_id = ""
                                 await submit_google_batch_result(
                                     call_id,
                                     name,
                                     tool_result_payload(result),
                                     result,
                                     conversation_turn_id=canonical_turn_id,
                                     tool_call_id=local_tool_call_id,
                                 )

                            async def on_google_native_error(
                                 message: str,
                                 *,
                                 call_id: str = provider_call_id,
                                 name: str = tool_name,
                                 canonical_turn_id: str = conversation_turn_id,
                                 local_tool_call_id: str = tool_turn_id,
                             ) -> None:
                                 nonlocal gated_tool_turn_id
                                 gated_tool_turn_id = ""
                                 await submit_google_batch_result(
                                     call_id,
                                     name,
                                     tool_error_payload(message),
                                     conversation_turn_id=canonical_turn_id,
                                     tool_call_id=local_tool_call_id,
                                 )

                            async def on_google_cancel_prepare(
                                 _reason: str,
                                 *,
                                 call_id: str = provider_call_id,
                             ) -> bool:
                                 nonlocal gated_tool_turn_id
                                 gated_tool_turn_id = ""
                                 return await drop_google_batch_call(call_id)

                            gated_tool_turn_id = tool_turn_id
                            await self._send_response_gated(
                                websocket,
                                provider="Google",
                                tool_name=tool_name,
                                query=request.query,
                                turn_id=tool_turn_id,
                                recorder=recorder,
                            )

                            await tool_session.handle_request(
                                request,
                                send_event=send_tool_event,
                                on_result=on_google_native_result,
                                on_error=on_google_native_error,
                                on_cancel_prepare=on_google_cancel_prepare,
                                provider_call_id=provider_call_id,
                                conversation_turn_id=conversation_turn_id,
                                tool_call_id=tool_turn_id,
                            )

                    tool_cancellation = getattr(response, "tool_call_cancellation", None)
                    if tool_cancellation is not None and not is_live_translate:
                        for provider_call_id in list(getattr(tool_cancellation, "ids", None) or []):
                            cancelled = await tool_session.cancel_provider_call(
                                str(provider_call_id),
                                send_event=send_tool_event,
                                reason="provider_cancelled",
                                notify_provider=True,
                            )
                            if not cancelled:
                                await drop_google_batch_call(str(provider_call_id))

                    server_content = getattr(response, "server_content", None)
                    if not server_content:
                        continue

                    if getattr(server_content, "interrupted", False) and not is_live_translate:
                        await finalize_user_transcript_if_needed(clear_transcript=True)
                        google_provider_interrupted_early = True
                        pending_google_response_text = ""
                        google_output_transcription_seen = False
                        google_output_transcription_text = ""
                        await self._begin_interruption(
                            websocket,
                            interruption,
                            provider="Google",
                            provider_event_type="server_content.interrupted",
                            recorder=recorder,
                            tool_session=tool_session,
                        )

                    user_transcript_fields = ("input_transcription", "input_audio_transcription", "transcription")
                    input_transcription_value: Any = None
                    for transcript_field in user_transcript_fields:
                        if hasattr(server_content, transcript_field):
                            candidate = getattr(server_content, transcript_field)
                            if candidate is not None:
                                input_transcription_value = candidate
                                break
                    user_text_chunk = self._extract_transcript_text(server_content, user_transcript_fields)
                    if user_text_chunk:
                        if is_live_translate:
                            last_activity_time = time.time()
                            live_translate_has_content = True
                        pending_google_user_transcript = _merge_memory_text(
                            pending_google_user_transcript,
                            user_text_chunk,
                        )
                        if InterruptionClassifier.classify_interruption(pending_google_user_transcript) != InterruptionIntent.NOISE_OR_SILENCE:
                            await self._send_event(websocket, "user_transcript", text=pending_google_user_transcript, turn_id="")
                    supports_finished_marker = (
                        input_transcription_value is not None
                        and hasattr(input_transcription_value, "finished")
                    )
                    transcription_finished = bool(
                        getattr(input_transcription_value, "finished", False)
                    ) if supports_finished_marker else input_transcription_value is not None
                    if input_transcription_value is not None and transcription_finished:
                        await finalize_user_transcript_if_needed(clear_transcript=False)

                    if is_live_translate and input_transcription_value is not None and transcription_finished:
                        live_translate_input_finished = True

                    output_transcription_value: Any = None
                    for transcript_field in ("output_transcription", "output_audio_transcription"):
                        if hasattr(server_content, transcript_field):
                            candidate = getattr(server_content, transcript_field)
                            if candidate is not None:
                                output_transcription_value = candidate
                                break
                    assistant_transcript = self._extract_transcript_text(
                        server_content,
                        ("output_transcription", "output_audio_transcription"),
                    )
                    if assistant_transcript:
                        google_output_transcription_seen = True
                        (
                            google_output_transcription_text,
                            assistant_transcript_delta,
                        ) = _merge_streaming_text(
                            google_output_transcription_text, assistant_transcript
                        )
                        if is_live_translate:
                            last_activity_time = time.time()
                            live_translate_has_content = True
                        if (
                            assistant_transcript_delta
                            and not gated_tool_turn_id
                            and not suppress_interrupted_google_response
                        ):
                            await self._emit_assistant_output(
                                websocket,
                                interruption,
                                {"type": "assistant_text", "text": assistant_transcript_delta},
                                memory_session=memory_session,
                                recorder=recorder,
                                record_memory=not is_live_translate,
                            )

                    if (
                        is_live_translate
                        and output_transcription_value is not None
                        and bool(getattr(output_transcription_value, "finished", False))
                    ):
                        live_translate_output_finished = True

                    if is_live_translate:
                        await complete_live_translate_turn_if_needed()

                    if getattr(server_content, "turn_complete", False):
                        if (
                            pending_google_response_text
                            and not google_output_transcription_seen
                            and not gated_tool_turn_id
                            and not suppress_interrupted_google_response
                        ):
                            await self._emit_assistant_output(
                                websocket,
                                interruption,
                                {"type": "assistant_text", "text": pending_google_response_text},
                                memory_session=memory_session,
                                recorder=recorder,
                                record_memory=not is_live_translate,
                            )
                        pending_google_response_text = ""
                        google_output_transcription_seen = False
                        google_output_transcription_text = ""
                        await finalize_user_transcript_if_needed(clear_transcript=True)
                        if is_live_translate:
                            await complete_live_translate_turn_if_needed(force=True)
                            continue
                        if interruption.defer_terminal(
                            {"type": "turn_complete", "provider": "Google"}
                        ):
                            continue
                        if consume_next_google_terminal:
                            consume_next_google_terminal = False
                            suppress_interrupted_google_response = False
                            continue
                        memory_result: dict[str, Any] = {}
                        if not is_live_translate:
                            memory_result = await memory_session.flush_turn()
                            await self._send_event(
                                websocket,
                                "memory_write",
                                attempted_count=int(memory_result.get("attempted_count", 0)),
                                saved_count=int(memory_result.get("saved_count", 0)),
                                failed_count=int(memory_result.get("failed_count", 0)),
                                local_pending_count=int(memory_result.get("local_pending_count", 0)),
                                reason=str(memory_result.get("reason", "")),
                            )
                        if pending_prefill_context and not is_live_translate:
                            await self._apply_google_memory_prefill(session, pending_prefill_context)
                            pending_prefill_context = ""
                        if not gated_tool_turn_id:
                            completed_turn_id = ""
                            if recorder is not None:
                                completed_turn_id = await recorder.complete_turn(memory_result)
                            await self._send_event(
                                websocket,
                                "turn_complete",
                                turn_id=completed_turn_id,
                                interrupted=False,
                            )
        finally:
            if monitor_task is not None:
                monitor_task.cancel()

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
                        asyncio.create_task(delayed_retry())
                    else:
                        logger.warning("DashScope returned error: %s. Max retries exceeded. Ignoring.", error_msg)
                    continue
                await websocket.send_json(event)
                break
            await websocket.send_json(event)

    # ── OpenAI Realtime ──────────────────────────────────────────────

    def _resolve_openai_settings(self, model: str | None) -> dict[str, str]:
        provider_settings = self.config.get_provider_settings("OpenAI", model)
        resolved_model = provider_settings["model"].strip() or DEFAULT_OPENAI_REALTIME_MODEL
        api_key = provider_settings["api_key"].strip()
        if not api_key:
            raise RuntimeError("OpenAI API Key 未配置，无法启动实时语音会话。")
        return {
            "api_key": api_key,
            "model": resolved_model,
        }

    async def _apply_openai_tool_result(
        self,
        openai_ws: Any,
        result: dict[str, Any],
        recorder: VoiceAgentSessionRecorder | None = None,
    ) -> None:
        prompt = VoiceAgentToolService.build_model_context_prompt(result)
        if not prompt.strip():
            return
        payload = {
            "provider": "OpenAI",
            "tool_name": str(result.get("tool_name", "search_web") or "search_web"),
            "query": str(result.get("query", "")),
            "turn_id": str(result.get("turn_id", "")),
            "source_count": int(result.get("source_count", 0) or 0),
            "elapsed_ms": int(result.get("elapsed_ms", 0) or 0),
        }
        if recorder is not None:
            await recorder.record_tool_event("tool_context_injected", payload)
        await openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        }))
        await openai_ws.send(json.dumps({"type": "response.create"}))

    async def _client_to_openai_loop(
        self,
        websocket: WebSocket,
        openai_ws: Any,
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
                if command_type == "text_input":
                    content = str(payload.get("text", "")).strip()
                    if content:
                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": content}],
                            },
                        }))
                        await openai_ws.send(json.dumps({"type": "response.create"}))
                    continue
                if command_type == "ping":
                    await self._send_event(websocket, "pong")
                    continue
                if command_type == "interruption_client_stopped":
                    await self._record_client_interruption_stop(recorder, payload, provider="OpenAI")
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
                await openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(audio_bytes).decode("ascii"),
                }))

    async def _openai_to_client_loop(
        self,
        websocket: WebSocket,
        openai_ws: Any,
        memory_session: RealtimeMemorySession,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        interruption: InterruptionDecisionCoordinator | None = None,
    ) -> None:
        async def send_tool_event(event_type: str, payload: dict[str, Any]) -> None:
            if recorder is not None:
                await recorder.record_tool_event(event_type, payload)
            await self._send_event(websocket, event_type, **payload)

        gated_tool_turn_id = ""
        pending_prefill_context = ""
        interruption = interruption or InterruptionDecisionCoordinator()
        suppressed_response_ids: set[str] = set()

        async for raw_message in openai_ws:
            try:
                event = json.loads(raw_message) if isinstance(raw_message, str) else json.loads(str(raw_message))
            except Exception:
                continue

            event_type = str(event.get("type", "")).strip()

            # Session created
            if event_type == "session.created":
                session_info = event.get("session", {})
                await self._send_event(
                    websocket,
                    "session_open",
                    provider="OpenAI",
                    model=session_info.get("model", ""),
                    voice=session_info.get("voice", DEFAULT_OPENAI_REALTIME_VOICE),
                    session_id=recorder.session_id if recorder is not None else session_info.get("id", ""),
                )
                continue

            # Session updated confirmation
            if event_type == "session.updated":
                continue

            if event_type == "response.created":
                interruption.active_response_id = str((event.get("response") or {}).get("id", ""))
                continue

            # Input audio transcription completed (user speech)
            if event_type == "conversation.item.input_audio_transcription.completed":
                user_text = str(event.get("transcript", "")).strip()
                item_id = str(event.get("item_id", ""))
                if interruption.pending is None and (
                    interruption.active_response_id
                    or tool_session.has_active_task
                    or (recorder is not None and bool(recorder.current_assistant_text))
                ):
                    await self._begin_interruption(
                        websocket,
                        interruption,
                        provider="OpenAI",
                        provider_event_type="conversation.item.input_audio_transcription.completed_without_vad",
                        recorder=recorder,
                        tool_session=tool_session,
                        supersede_timed_out=True,
                    )
                interrupted_response_id = interruption.active_response_id
                had_deferred_terminal = interruption.has_deferred_terminal()

                async def cancel_openai_response() -> None:
                    payload: dict[str, Any] = {"type": "response.cancel"}
                    if interrupted_response_id:
                        payload["response_id"] = interrupted_response_id
                    await openai_ws.send(json.dumps(payload))

                async def discard_openai_candidate() -> None:
                    if item_id:
                        await openai_ws.send(
                            json.dumps({"type": "conversation.item.delete", "item_id": item_id})
                        )

                should_process_user, interruption_decision = await self._decide_interruption(
                    websocket,
                    interruption,
                    user_text,
                    memory_session=memory_session,
                    tool_session=tool_session,
                    recorder=recorder,
                    cancel_provider=(cancel_openai_response if not had_deferred_terminal else None),
                    resume_provider=discard_openai_candidate,
                )
                if interruption_decision is not None and (
                    interruption_decision.get("classification") == InterruptionIntent.TRUE_BARGE_IN.value
                ) and interrupted_response_id and not had_deferred_terminal:
                    suppressed_response_ids.add(interrupted_response_id)
                if not should_process_user:
                    if interruption_decision is None:
                        await discard_openai_candidate()
                    if had_deferred_terminal and interruption.take_deferred_terminal() is not None:
                        await self._finalize_realtime_turn(
                            websocket,
                            memory_session,
                            recorder,
                            gated=bool(gated_tool_turn_id),
                        )
                    continue
                if InterruptionClassifier.classify_interruption(user_text) == InterruptionIntent.NOISE_OR_SILENCE:
                    await discard_openai_candidate()
                    continue
                if user_text:
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
                            "voice_memory_inject provider=OpenAI scope=%s count=%s local_pending=%s cloud=%s",
                            memory_session._config.memory_scope,
                            memory_count,
                            local_pending_count,
                            cloud_count,
                        )
                        pending_prefill_context = memory_context
                    await self._send_event(websocket, "user_transcript", text=user_text, turn_id=voice_turn_id)
                    # Tool detection
                    async def on_openai_tool_result(result: dict[str, Any]) -> None:
                        nonlocal gated_tool_turn_id
                        gated_tool_turn_id = ""
                        await self._apply_openai_tool_result(openai_ws, result, recorder)

                    tool_request = VoiceAgentToolService.extract_tool_request(user_text)
                    tool_turn_id = await tool_session.handle_user_transcript(
                        user_text,
                        send_event=send_tool_event,
                        on_result=on_openai_tool_result,
                    )
                    if tool_turn_id:
                        gated_tool_turn_id = tool_turn_id
                        await self._send_response_gated(
                            websocket,
                            provider="OpenAI",
                            tool_name=tool_request.tool_name if tool_request else "voice_tool",
                            query=tool_request.query if tool_request else "",
                            turn_id=tool_turn_id,
                            recorder=recorder,
                        )
                    else:
                        await openai_ws.send(json.dumps({"type": "response.create"}))
                continue

            # Speech started (VAD detected user speaking → interruption)
            if event_type == "input_audio_buffer.speech_started":
                if interruption.active_response_id or tool_session.has_active_task or (
                    recorder is not None and bool(recorder.current_assistant_text)
                ):
                    await self._begin_interruption(
                        websocket,
                        interruption,
                        provider="OpenAI",
                        provider_event_type=event_type,
                        recorder=recorder,
                        tool_session=tool_session,
                    )
                continue

            # Assistant audio delta
            if event_type == "response.audio.delta":
                audio_b64 = event.get("delta", "")
                response_id = str(event.get("response_id", ""))
                if response_id in suppressed_response_ids:
                    continue
                if audio_b64 and not gated_tool_turn_id:
                    await self._emit_assistant_output(
                        websocket,
                        interruption,
                        {
                            "type": "assistant_audio",
                            "audio": audio_b64,
                            "encoding": "pcm_s16le",
                            "sample_rate": 24000,
                        },
                        memory_session=memory_session,
                        recorder=recorder,
                    )
                continue

            # Assistant audio transcript delta
            if event_type == "response.audio_transcript.delta":
                text_delta = event.get("delta", "")
                response_id = str(event.get("response_id", ""))
                if response_id in suppressed_response_ids:
                    continue
                if text_delta and not gated_tool_turn_id:
                    await self._emit_assistant_output(
                        websocket,
                        interruption,
                        {"type": "assistant_text", "text": str(text_delta)},
                        memory_session=memory_session,
                        recorder=recorder,
                    )
                continue

            # Response done (turn complete)
            if event_type == "response.done":
                response_data = event.get("response") or {}
                response_status = str(response_data.get("status", "completed"))
                response_id = str(response_data.get("id", ""))
                if response_id in suppressed_response_ids:
                    suppressed_response_ids.discard(response_id)
                    if response_id == interruption.active_response_id:
                        interruption.active_response_id = ""
                    continue
                if interruption.defer_terminal(dict(event)):
                    continue
                if response_id and response_id == interruption.active_response_id:
                    interruption.active_response_id = ""
                if response_status in {"cancelled", "canceled", "failed"}:
                    continue
                if pending_prefill_context:
                    # Inject memory context as a hidden user message
                    await openai_ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "user",
                            "content": [{
                                "type": "input_text",
                                "text": (
                                    "Context note for personalization only. These long-term memories may help with "
                                    "the user's next turn. Use them only when relevant, and do not mention this note.\n"
                                    f"{pending_prefill_context}"
                                ),
                            }],
                        },
                    }))
                    pending_prefill_context = ""
                memory_result = await memory_session.flush_turn()
                completed_turn_id = ""
                if recorder is not None and not gated_tool_turn_id:
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
                if not gated_tool_turn_id:
                    await self._send_event(
                        websocket,
                        "turn_complete",
                        turn_id=completed_turn_id,
                        interrupted=False,
                    )
                continue

            # Error events
            if event_type == "error":
                error_msg = event.get("error", {}).get("message", "") or str(event.get("message", ""))
                await self._send_event(websocket, "error", message=f"OpenAI Realtime: {error_msg}")
                break

    async def stream_openai_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_OPENAI_REALTIME_VOICE,
    ) -> None:
        settings = self._resolve_openai_settings(model)
        memory_session = RealtimeMemorySession()
        tool_session = VoiceAgentToolSession()
        recorder = await self._create_voice_session_recorder(
            provider="OpenAI",
            model=settings["model"],
            voice=voice,
        )

        ws_url = f"wss://api.openai.com/v1/realtime?model={settings['model']}"
        extra_headers = {
            "Authorization": f"Bearer {settings['api_key']}",
        }

        try:
            async with websockets.connect(
                ws_url,
                additional_headers=extra_headers,
                max_size=2**24,
                ping_interval=30,
                ping_timeout=30,
            ) as openai_ws:
                # Configure session
                await openai_ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "modalities": ["text", "audio"],
                        "voice": voice,
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {"model": "whisper-1"},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 500,
                            "create_response": False,
                            "interrupt_response": False,
                        },
                        "instructions": self._build_realtime_instructions(),
                    },
                }))

                interruption = InterruptionDecisionCoordinator()
                send_task = asyncio.create_task(
                    self._client_to_openai_loop(
                        websocket, openai_ws, memory_session, tool_session, recorder, interruption
                    )
                )
                receive_task = asyncio.create_task(
                    self._openai_to_client_loop(
                        websocket, openai_ws, memory_session, tool_session, recorder, interruption
                    )
                )
                await self._run_duplex_tasks(send_task, receive_task)
        except WebSocketDisconnect:
            return
        except Exception as e:
            print(f"DEBUG: OpenAI Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_event(websocket, "error", message=f"OpenAI 实时会话启动失败: {str(e)}")
            return
        finally:
            memory_result = await memory_session.flush_turn()
            if recorder is not None:
                await recorder.complete_turn(memory_result)
            await memory_session.drain()
            await tool_session.drain(cancel=True)
            if recorder is not None:
                await recorder.finish()

    async def stream_google_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str = DEFAULT_GOOGLE_REALTIME_VOICE,
        target_language_code: str = "en",
        echo_target_language: bool = True,
    ) -> None:
        settings = self._resolve_google_settings(model)
        memory_session = RealtimeMemorySession()
        tool_session = VoiceAgentToolSession()
        recorder = await self._create_voice_session_recorder(
            provider="Google",
            model=settings["model"],
            voice=voice,
        )
        http_options: dict[str, str] = {"api_version": "v1beta"}
        if settings["base_url"]:
            http_options["base_url"] = settings["base_url"]

        client = genai.Client(api_key=settings["api_key"], http_options=http_options)
        is_live_translate = _is_google_live_translate_model(settings["model"])
        live_config = (
            self._build_live_translate_config(target_language_code, echo_target_language)
            if is_live_translate
            else self._build_live_config(voice, self._build_realtime_instructions())
        )

        try:
            async with client.aio.live.connect(model=settings["model"], config=live_config) as session:
                await self._send_event(
                    websocket,
                    "session_open",
                    provider="Google",
                    model=settings["model"],
                    voice=voice,
                    session_id=recorder.session_id if recorder is not None else "",
                    mode="live_translate" if is_live_translate else "realtime_chat",
                    target_language_code=target_language_code if is_live_translate else "",
                    echo_target_language=echo_target_language if is_live_translate else False,
                )
                interruption = InterruptionDecisionCoordinator()
                send_task = asyncio.create_task(
                    self._client_to_google_loop(
                        websocket,
                        session,
                        memory_session,
                        tool_session,
                        recorder,
                        is_live_translate,
                        interruption,
                    )
                )
                receive_task = asyncio.create_task(
                    self._google_to_client_loop(
                        websocket,
                        session,
                        memory_session,
                        tool_session,
                        recorder,
                        is_live_translate,
                        interruption,
                    )
                )
                await self._run_duplex_tasks(send_task, receive_task)
        except WebSocketDisconnect:
            return
        except Exception as e:
            print(f"DEBUG: Google Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_event(websocket, "error", message=f"Google 实时会话启动失败: {str(e)}")
            return
        finally:
            memory_result = await memory_session.flush_turn()
            if recorder is not None:
                await recorder.complete_turn(memory_result)
            await memory_session.drain()
            await tool_session.drain(cancel=True)
            if recorder is not None:
                await recorder.finish()

    @staticmethod
    def _is_qwen_audio_model(model: str | None) -> bool:
        """Return True when *model* is a Qwen-Audio realtime model (supports native function calling)."""
        return bool(model and "qwen-audio" in str(model).lower())

    @staticmethod
    def _build_qwen_audio_instructions(memory_context: str = "") -> str:
        if not memory_context:
            return QWEN_AUDIO_REALTIME_INSTRUCTIONS
        return (
            f"{QWEN_AUDIO_REALTIME_INSTRUCTIONS}\n\n"
            "以下是系统检索到的长期记忆，用于个性化回复。当相关时请参考这些记忆，"
            "但不要逐字引用，除非用户直接询问。\n"
            f"{memory_context}"
        )

    async def _client_to_qwen_audio_loop(
        self,
        websocket: WebSocket,
        dash_ws: Any,
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
                    if hasattr(interruption, "expected_playback_end_time"):
                        interruption.expected_playback_end_time = 0.0
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
                # ── Half-duplex echo suppression with energy gate ──
                # During AI playback we block ONLY low-energy audio (speaker echo)
                # and let high-energy audio through so the user can still interrupt.
                # This matches the official Qwen-Audio demo's "headphone mode".
                NOISE_GATE_THRESHOLD = 500
                ai_is_playing = bool(interruption and interruption.active_response_id)
                if ai_is_playing:
                    energy = _audio_energy_qwen(audio_bytes)
                    if energy < NOISE_GATE_THRESHOLD:
                        continue  # low energy → likely echo, suppress
                    # User is speaking loudly enough → let it through to interrupt
                elif interruption and hasattr(interruption, "expected_playback_end_time"):
                    # Add 1.0s buffer for frontend/network delays after AI finishes
                    if time.time() < getattr(interruption, "expected_playback_end_time") + 1.0:
                        continue

                await dash_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(audio_bytes).decode("ascii"),
                }))

    async def _qwen_audio_to_client_loop(
        self,
        websocket: WebSocket,
        dash_ws: Any,
        memory_session: RealtimeMemorySession,
        voice: str,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        interruption: InterruptionDecisionCoordinator | None = None,
    ) -> None:
        async def send_tool_event(event_type: str, payload: dict[str, Any]) -> None:
            if recorder is not None:
                await recorder.record_tool_event(event_type, payload)
            if not _user_transcript_emitted:
                _pending_tool_events.append((event_type, payload))
            else:
                await self._send_event(websocket, event_type, **payload)

        async def _flush_pending_output() -> None:
            """Send all buffered tool + AI text/audio events now that user transcript is emitted."""
            nonlocal _pending_tool_events, _pending_ai_output, _user_transcript_emitted
            _user_transcript_emitted = True
            # 1. Flush tool events first (user transcript → tool status → AI reply)
            for event_type, payload in _pending_tool_events:
                await self._send_event(websocket, event_type, **payload)
            _pending_tool_events.clear()
            # 2. Flush AI text/audio events
            if _pending_ai_output:
                for _, payload in _pending_ai_output:
                    await self._emit_assistant_output(
                        websocket, interruption, payload,
                        memory_session=memory_session, recorder=recorder,
                    )
                _pending_ai_output.clear()

        gated_tool_turn_id = ""
        # Track ALL pending native function_call ids in the current turn. A turn may
        # contain multiple parallel function_calls; the follow-up response.create must
        # only be sent after every call's function_call_output has been written back.
        pending_native_fc_call_ids: set[str] = set()
        # Tracks whether ANY native function call has occurred since the user started
        # speaking. When True, the regex-based tool extraction path is skipped to
        # prevent double-execution (native FC already handled the tool, then regex
        # fires again causing response.cancel + response_gated + duplicate tool call).
        _native_fc_occurred_this_turn = False
        # Buffer tool events AND AI text/audio events until the user transcript has
        # been emitted, so the frontend always shows: user speech → tool status → AI reply.
        _pending_tool_events: list[tuple[str, dict[str, Any]]] = []
        _pending_ai_output: list[tuple[str, dict[str, Any]]] = []
        _user_transcript_emitted = True  # starts True (no pending transcript before first turn)
        # When response.created arrives before the ASR transcript, the server has
        # started responding to the user's speech.  This flag prevents the first
        # transcript of each response cycle from being misclassified as a barge-in
        # interruption (which would silently drop it and break the UI ordering).
        _first_transcript_this_response = True
        # With modalities ["text","audio"] the model streams the SAME content over
        # both response.text.delta and response.audio_transcript.delta. Forward only
        # the first delta family seen per response, otherwise the client transcript
        # shows every sentence twice (audio is unaffected - single audio stream).
        response_text_delta_family: dict[str, str] = {}
        # Marks whether the current response contains function_call(s); such a response
        # is an intermediate round and must NOT finalize the turn on response.done.
        current_response_has_function_call = False
        interruption = interruption or InterruptionDecisionCoordinator()
        suppressed_response_ids: set[str] = set()
        while True:
            try:
                raw = await asyncio.wait_for(dash_ws.recv(), timeout=300)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            try:
                event = json.loads(raw) if isinstance(raw, str) else json.loads(str(raw))
            except Exception:
                continue

            event_type = str(event.get("type", "")).strip()
            if event_type == "closed":
                break
            if event_type in {"session.created", "session.updated"}:
                continue
            if event_type == "input_audio_buffer.speech_started":
                # New user speech starts: reset guards so the upcoming
                # transcription and function calls are handled correctly.
                _first_transcript_this_response = True
                _native_fc_occurred_this_turn = False
                if interruption.active_response_id or tool_session.has_active_task or (
                    recorder is not None and bool(recorder.current_assistant_text)
                ):
                    await self._begin_interruption(
                        websocket,
                        interruption,
                        provider="DashScope",
                        provider_event_type=str(event.get("type", "input_audio_buffer.speech_started")),
                        recorder=recorder,
                        tool_session=tool_session,
                    )
                continue
            if event_type == "response.created":
                interruption.active_response_id = (
                    str((event.get("response") or {}).get("id", "")) or interruption.active_response_id or "active"
                )
                # New response round begins; reset the per-response function_call marker.
                current_response_has_function_call = False
                # Start buffering AI output until the user transcript is sent first.
                _user_transcript_emitted = False
                _first_transcript_this_response = True
                continue
            if event_type == "conversation.item.input_audio_transcription.completed":
                user_text = str(event.get("transcript", "")).strip()
                # ── Interruption vs. first-transcript dispatch ──
                # The server may send response.created before the ASR transcript.
                # When that happens, active_response_id is already set and the
                # transcript would be misclassified as a barge-in interruption,
                # potentially dropped entirely.  The _first_transcript_this_response
                # flag guards against this: the first transcript of each response
                # cycle always reaches the frontend so the UI order is correct.
                if not _first_transcript_this_response:
                    if interruption.pending is None and (
                        interruption.active_response_id
                        or tool_session.has_active_task
                        or (recorder is not None and bool(recorder.current_assistant_text))
                    ):
                        await self._begin_interruption(
                            websocket,
                            interruption,
                            provider="DashScope",
                            provider_event_type=str(event.get("type", "input_transcription.without_pending_vad")),
                            recorder=recorder,
                            tool_session=tool_session,
                            supersede_timed_out=True,
                        )
                    interrupted_response_id = interruption.active_response_id
                    had_deferred_terminal = interruption.has_deferred_terminal()
                    async def cancel_dashscope_response() -> None:
                        try:
                            await dash_ws.send(json.dumps({"type": "response.cancel"}))
                        except Exception:
                            logger.exception("qwen_audio_response_cancel_failed")

                    should_process_user, interruption_decision = await self._decide_interruption(
                        websocket,
                        interruption,
                        user_text,
                        memory_session=memory_session,
                        tool_session=tool_session,
                        recorder=recorder,
                        cancel_provider=cancel_dashscope_response,
                    )
                    if interruption_decision is not None and (
                        interruption_decision.get("classification") == InterruptionIntent.TRUE_BARGE_IN.value
                    ) and interrupted_response_id and not had_deferred_terminal:
                        suppressed_response_ids.add(interrupted_response_id)
                    if not should_process_user:
                        if had_deferred_terminal and interruption.take_deferred_terminal() is not None:
                            await self._finalize_realtime_turn(
                                websocket, memory_session, recorder, gated=bool(gated_tool_turn_id),
                            )
                            await dash_ws.send(json.dumps({
                                "type": "session.update",
                                "session": {"instructions": self._build_qwen_audio_instructions()},
                            }))
                        continue
                    if InterruptionClassifier.classify_interruption(user_text) == InterruptionIntent.NOISE_OR_SILENCE:
                        continue
                else:
                    _first_transcript_this_response = False
                # ── Common path: send user transcript, flush buffered AI output ──
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
                        websocket, "memory_context",
                        memories_retrieved=memory_count,
                        local_pending_count=local_pending_count,
                        cloud_count=cloud_count,
                        attempted=True,
                    )
                base_instructions = self._build_qwen_audio_instructions(memory_context)
                if not memory_context and memory_session.is_forced_recall_query(user_text):
                    base_instructions = self._build_recall_miss_instructions(user_text)
                async def on_qwen_audio_tool_result(result: dict[str, Any]) -> None:
                    nonlocal gated_tool_turn_id
                    gated_tool_turn_id = ""
                    await self._apply_qwen_audio_tool_result(websocket, dash_ws, result, recorder)

                # Native function-call gating: if the model has already called a
                # tool natively this turn, skip backend regex extraction entirely
                # to prevent double-execution (native FC runs the tool, then regex
                # fires again causing response.cancel + response_gated + duplicate).
                if _native_fc_occurred_this_turn:
                    await self._send_event(websocket, "user_transcript", text=user_text, turn_id=voice_turn_id)
                    await _flush_pending_output()
                    continue

                tool_request = VoiceAgentToolService.extract_tool_request(user_text)
                tool_turn_id = await tool_session.handle_user_transcript(
                    user_text,
                    send_event=send_tool_event,
                    on_result=on_qwen_audio_tool_result,
                )
                # Always emit user_transcript FIRST, before any tool events
                # (response_gated, etc.), so the frontend shows the user's
                # transcribed speech above the tool status.
                await self._send_event(websocket, "user_transcript", text=user_text, turn_id=voice_turn_id)
                if tool_turn_id:
                    gated_tool_turn_id = tool_turn_id
                    try:
                        await dash_ws.send(json.dumps({"type": "response.cancel"}))
                    except Exception:
                        pass
                    await self._send_response_gated(
                        websocket, provider="DashScope",
                        tool_name=tool_request.tool_name if tool_request else "voice_tool",
                        query=tool_request.query if tool_request else "",
                        turn_id=tool_turn_id, recorder=recorder,
                    )
                # No manual response.create here: with server-side turn detection
                # (server_vad / smart_turn) the server creates the response on its
                # own once it finalizes the user transcript. An extra
                # response.create races the user's ongoing speech and the server
                # rejects it with "Cannot create response while user is speaking",
                # which used to tear down the whole session.
                await _flush_pending_output()
                continue
            if event_type == "response.output_item.added":
                item = event.get("item") or {}
                if item.get("type") == "function_call":
                    call_id = str(item.get("call_id", ""))
                    if call_id:
                        pending_native_fc_call_ids.add(call_id)
                    current_response_has_function_call = True
                continue
            if event_type == "response.function_call_arguments.done":
                call_id = str(event.get("call_id", ""))
                name = str(event.get("name", ""))
                arguments_str = str(event.get("arguments", "{}"))
                # Mark that native FC occurred this turn so the regex path is
                # skipped when the transcript arrives (prevents double-execution).
                _native_fc_occurred_this_turn = True
                # Execute the tool and write back its function_call_output (without
                # triggering response.create yet). Only when every pending call in this
                # turn has produced its output do we send a single response.create.
                await self._handle_qwen_audio_function_call(
                    websocket, dash_ws, call_id, name, arguments_str,
                    tool_session=tool_session,
                    recorder=recorder,
                    send_tool_event=send_tool_event,
                    trigger_response=False,
                )
                pending_native_fc_call_ids.discard(call_id)
                if not pending_native_fc_call_ids:
                    await dash_ws.send(json.dumps({"type": "response.create"}))
                continue
            if event_type == "response.audio.delta":
                response_id = str(event.get("response_id", ""))
                if response_id in suppressed_response_ids:
                    continue
                if not gated_tool_turn_id:
                    delta_b64 = str(event.get("delta", ""))
                    if delta_b64:
                        try:
                            audio_len = len(delta_b64) * 3 // 4
                            audio_duration = audio_len / 48000.0
                            if not hasattr(interruption, "expected_playback_end_time"):
                                interruption.expected_playback_end_time = time.time()
                            if interruption.expected_playback_end_time < time.time():
                                interruption.expected_playback_end_time = time.time()
                            interruption.expected_playback_end_time += audio_duration
                        except Exception:
                            pass
                    payload = {
                        "type": "assistant_audio",
                        "audio": delta_b64,
                        "response_id": response_id,
                    }
                    if not _user_transcript_emitted:
                        _pending_ai_output.append(("audio", payload))
                    else:
                        await self._emit_assistant_output(
                            websocket, interruption, payload,
                            memory_session=memory_session, recorder=recorder,
                        )
                continue
            if event_type in {"response.audio_transcript.delta", "response.text.delta"}:
                response_id = str(event.get("response_id", ""))
                if response_id in suppressed_response_ids:
                    continue
                family = (
                    "audio_transcript"
                    if event_type.startswith("response.audio_transcript")
                    else "text"
                )
                seen_family = response_text_delta_family.get(response_id)
                if seen_family is None:
                    response_text_delta_family[response_id] = family
                elif seen_family != family:
                    # Duplicate content stream for this response; drop it.
                    continue
                delta = str(event.get("delta", ""))
                if not gated_tool_turn_id and delta:
                    payload = {
                        "type": "assistant_text",
                        "text": delta,
                        "response_id": response_id,
                    }
                    if not _user_transcript_emitted:
                        _pending_ai_output.append(("text", payload))
                    else:
                        await self._emit_assistant_output(
                            websocket, interruption, payload,
                            memory_session=memory_session, recorder=recorder,
                        )
                continue
            if event_type == "response.done":
                # Safety net: flush any buffered AI output (normal flush happens after
                # user_transcript is sent, but this covers edge cases).
                await _flush_pending_output()
                response_data = event.get("response") or {}
                response_id = str(response_data.get("id", ""))
                response_text_delta_family.pop(response_id, None)
                if response_id in suppressed_response_ids:
                    suppressed_response_ids.discard(response_id)
                    if response_id == interruption.active_response_id:
                        interruption.active_response_id = ""
                    continue
                if interruption.defer_terminal({"type": "turn_complete", "response_id": response_id,
                                                 "status": str(response_data.get("status", "completed"))}):
                    continue
                if not response_id or response_id == interruption.active_response_id:
                    interruption.active_response_id = ""
                # A response that carried function_call(s) is an intermediate round:
                # the turn continues after we send response.create, so do NOT finalize
                # (flush memory / emit turn_complete) here. Reset the flag and stop.
                if current_response_has_function_call:
                    current_response_has_function_call = False
                    pending_native_fc_call_ids.clear()
                    continue
                if str(response_data.get("status", "completed")) in {"cancelled", "canceled", "failed"}:
                    continue
                memory_result = await memory_session.flush_turn()
                completed_turn_id = ""
                if recorder is not None and not gated_tool_turn_id:
                    completed_turn_id = await recorder.complete_turn(memory_result)
                await self._send_event(
                    websocket, "memory_write",
                    attempted_count=int(memory_result.get("attempted_count", 0)),
                    saved_count=int(memory_result.get("saved_count", 0)),
                    failed_count=int(memory_result.get("failed_count", 0)),
                    local_pending_count=int(memory_result.get("local_pending_count", 0)),
                    reason=str(memory_result.get("reason", "")),
                )
                await dash_ws.send(json.dumps({
                    "type": "session.update",
                    "session": {"instructions": self._build_qwen_audio_instructions()},
                }))
                if not gated_tool_turn_id:
                    await self._send_event(
                        websocket, "turn_complete",
                        turn_id=completed_turn_id, interrupted=False,
                    )
                continue
            if gated_tool_turn_id and event_type in {"assistant_audio", "assistant_text", "turn_complete"}:
                continue
            if event_type == "error":
                error_data = event.get("error")
                if isinstance(error_data, dict):
                    message = str(error_data.get("message", "")).strip() or str(event)
                else:
                    message = str(error_data or event).strip()
                # Benign race conditions (e.g. our response.create / response.cancel
                # colliding with the server's own turn management) must not kill the
                # session - log them and keep listening.
                if any(pattern in message for pattern in QWEN_AUDIO_BENIGN_ERROR_PATTERNS):
                    logger.warning("qwen_audio_benign_error message=%s", message)
                    continue
                await self._send_event(websocket, "error", message=f"DashScope: {message}")
                break

    @staticmethod
    async def _send_qwen_audio_function_call_output(dash_ws: Any, call_id: str, output: str) -> None:
        """Write a function_call_output conversation item back to the model."""
        await dash_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "call_id": call_id, "output": output},
        }))

    async def _handle_qwen_audio_function_call(
        self,
        websocket: WebSocket,
        dash_ws: Any,
        call_id: str,
        name: str,
        arguments_str: str,
        *,
        tool_session: VoiceAgentToolSession,
        recorder: VoiceAgentSessionRecorder | None = None,
        send_tool_event: Any = None,
        trigger_response: bool = True,
    ) -> None:
        """Handle a native function_call from Qwen-Audio: execute tool and write back its output.

        When *trigger_response* is True (single-call / standalone usage), a follow-up
        ``response.create`` is sent immediately. When False, the caller is responsible
        for sending ``response.create`` once every pending call in the turn has been
        resolved (required for turns that contain multiple parallel function_calls).
        """
        import traceback as tb_module

        logger.info("qwen_audio_function_call call_id=%s name=%s args=%s", call_id, name, arguments_str)
        try:
            arguments = json.loads(arguments_str) if arguments_str else {}
        except json.JSONDecodeError:
            arguments = {}

        # Map function name → query text and tool_name for VoiceAgentToolService
        name_lower = name.lower().strip()
        if name_lower == "search_web":
            query = str(arguments.get("query", "")).strip()
            tool_name = "search_web"
        elif name_lower == "translate_text":
            text = str(arguments.get("text", "")).strip()
            target = str(arguments.get("target_language", "英文")).strip()
            query = f"{text}\n目标语言: {target}"
            tool_name = "translate_text"
        elif name_lower == "summarize_transcript":
            content = str(arguments.get("content", "")).strip()
            query = content
            tool_name = "summarize_transcript"
        elif name_lower == "synthesize_tts":
            content = str(arguments.get("content", "")).strip()
            query = content
            tool_name = "synthesize_tts"
        elif name_lower == "create_audio_agent_run":
            topic = str(arguments.get("topic", "")).strip()
            query = topic
            tool_name = "create_audio_agent_run"
        else:
            await self._send_qwen_audio_function_call_output(
                dash_ws, call_id, json.dumps({"error": f"未知工具: {name}"})
            )
            if trigger_response:
                await dash_ws.send(json.dumps({"type": "response.create"}))
            return

        if not query:
            await self._send_qwen_audio_function_call_output(
                dash_ws, call_id, json.dumps({"error": "缺少必要的查询参数"})
            )
            if trigger_response:
                await dash_ws.send(json.dumps({"type": "response.create"}))
            return

        request = VoiceToolRequest(tool_name=tool_name, query=query, display_name=tool_name, requires_confirmation=False)
        send_event_fn = send_tool_event if send_tool_event is not None else (
            lambda et, p: self._send_event(websocket, et, **p)
        )

        # Execute the tool and write back its output. The follow-up response.create is
        # deferred to the caller unless trigger_response=True.
        try:
            result = await tool_session.service.run_tool(
                request, send_event=send_event_fn, turn_id=f"native-fc-{call_id[:12]}",
            )
        except Exception as exc:
            tb_module.print_exc()
            await self._send_qwen_audio_function_call_output(
                dash_ws, call_id, json.dumps({"error": str(exc)})
            )
            if trigger_response:
                await dash_ws.send(json.dumps({"type": "response.create"}))
            return

        prompt = VoiceAgentToolService.build_model_context_prompt(result)
        output = prompt if prompt.strip() else json.dumps({"status": "completed", "summary": str(result.get("answer", ""))})
        await self._send_qwen_audio_function_call_output(dash_ws, call_id, output)
        if trigger_response:
            await dash_ws.send(json.dumps({"type": "response.create"}))

    async def _apply_qwen_audio_tool_result(
        self,
        websocket: WebSocket,
        dash_ws: Any,
        result: dict[str, Any],
        recorder: VoiceAgentSessionRecorder | None = None,
    ) -> None:
        """Inject backend regex-detected tool result as a user message (non-native fallback)."""
        prompt = VoiceAgentToolService.build_model_context_prompt(result)
        if not prompt.strip():
            return
        payload = {
            "provider": "DashScope",
            "tool_name": str(result.get("tool_name", "search_web") or "search_web"),
            "query": str(result.get("query", "")),
            "turn_id": str(result.get("turn_id", "")),
            "source_count": int(result.get("source_count", 0) or 0),
            "elapsed_ms": int(result.get("elapsed_ms", 0) or 0),
        }
        if recorder is not None:
            await recorder.record_tool_event("tool_context_injected", payload)
        await self._send_event(websocket, "tool_context_injected", **payload)
        # For raw WebSocket, send tool result as a user message then trigger response
        await dash_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        }))
        await dash_ws.send(json.dumps({"type": "response.create"}))

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
            print(f"DEBUG: DashScope Realtime Session Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
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

    async def stream_dashscope_audio_session(
        self,
        websocket: WebSocket,
        *,
        model: str | None = None,
        voice: str | None = None,
    ) -> None:
        """Raw-WebSocket session for Qwen-Audio models with native function calling.

        This bypasses the DashScope SDK (``OmniRealtimeConversation``) and
        uses ``websockets.connect()`` directly so we can send ``tools`` in
        ``session.update`` and handle ``function_call_arguments.done`` events.
        """
        settings = self._resolve_dashscope_settings(model)
        memory_session = RealtimeMemorySession()
        tool_session = VoiceAgentToolSession()
        resolved_voice = (voice or DEFAULT_QWEN_AUDIO_REALTIME_VOICE).strip()
        if resolved_voice not in QWEN_AUDIO_REALTIME_VOICES:
            logger.warning(
                "qwen_audio_unsupported_voice voice=%s fallback=%s",
                resolved_voice, DEFAULT_QWEN_AUDIO_REALTIME_VOICE,
            )
            resolved_voice = DEFAULT_QWEN_AUDIO_REALTIME_VOICE
        recorder = await self._create_voice_session_recorder(
            provider="DashScope",
            model=settings["model"],
            voice=resolved_voice,
        )

        # Use the configured workspace Realtime URL (validated in
        # _resolve_dashscope_settings to be a cn-beijing maas URL for
        # qwen-audio models), same as stream_dashscope_session does.
        ws_url = f"{settings['realtime_base_url']}?model={settings['model']}"
        extra_headers = {
            "Authorization": f"Bearer {settings['api_key']}",
        }
        tools = VoiceAgentToolService.build_tools_schema()

        try:
            async with websockets.connect(
                ws_url,
                additional_headers=extra_headers,
                max_size=2**24,
                ping_interval=None,
                ping_timeout=None,
            ) as dash_ws:
                # ── session.update with tools + server_vad ──
                # Long silence_duration_ms (5000ms) + low threshold (0.3)
                # gives language learners plenty of time to pause and think
                # without the model cutting in. The API allows up to 6000ms.
                session_config: dict[str, Any] = {
                    "modalities": ["text", "audio"],
                    "voice": resolved_voice,
                    "input_audio_format": "pcm",
                    "output_audio_format": "pcm",
                    "instructions": self._build_qwen_audio_instructions(),
                    "tools": tools,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.3,
                        "silence_duration_ms": 5000,
                    },
                    "max_history_turns": 50,
                }
                await dash_ws.send(json.dumps({
                    "type": "session.update",
                    "session": session_config,
                }))

                # Wait for the server's session.created/session.updated handshake.
                # Read events in a loop so a server-side `error` event (e.g. invalid
                # voice/param, wrong workspace URL, model not enabled for the
                # workspace) surfaces its real message instead of being swallowed,
                # and a silent server produces an explicit timeout message instead
                # of a bare empty TimeoutError.
                session_id = ""
                handshake_deadline = time.monotonic() + 15
                while not session_id:
                    remaining = handshake_deadline - time.monotonic()
                    if remaining <= 0:
                        raise RuntimeError(
                            "已连接 DashScope，但 15 秒内未收到 session.created 确认；"
                            "请检查业务空间 Realtime URL 是否属于已开通 "
                            f"{settings['model']} 的空间，以及 API Key 是否匹配该空间。"
                        )
                    try:
                        raw = await asyncio.wait_for(dash_ws.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            "已连接 DashScope，但等待 session.created 超时；"
                            "请检查业务空间 Realtime URL 与 API Key 是否正确。"
                        ) from None
                    try:
                        event = json.loads(raw) if isinstance(raw, str) else {}
                    except Exception:
                        continue
                    event_type = str(event.get("type", "")).strip()
                    logger.info("qwen_audio_handshake event_type=%s", event_type or "<unknown>")
                    if event_type == "error":
                        error_data = event.get("error")
                        if isinstance(error_data, dict):
                            detail = str(error_data.get("message", "")).strip() or str(error_data)
                        else:
                            detail = str(error_data or event).strip()
                        raise RuntimeError(f"DashScope 服务端拒绝会话: {detail}")
                    if event_type in {"session.created", "session.updated"}:
                        session_id = str((event.get("session") or {}).get("id", "") or "ok")

                await self._send_event(
                    websocket,
                    "session_open",
                    provider="DashScope",
                    model=settings["model"],
                    voice=resolved_voice,
                    session_id=recorder.session_id if recorder is not None else session_id,
                )

                interruption = InterruptionDecisionCoordinator()
                send_task = asyncio.create_task(
                    self._client_to_qwen_audio_loop(
                        websocket, dash_ws, memory_session, tool_session, recorder, interruption
                    )
                )
                receive_task = asyncio.create_task(
                    self._qwen_audio_to_client_loop(
                        websocket, dash_ws, memory_session, resolved_voice,
                        tool_session, recorder, interruption,
                    )
                )
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
            detail = str(e).strip() or repr(e)
            print(f"DEBUG: Qwen-Audio Realtime Session Error: {type(e).__name__}: {detail}")
            import traceback
            traceback.print_exc()
            await self._send_event(
                websocket, "error",
                message=f"Qwen-Audio 实时会话启动失败: [{type(e).__name__}] {detail}",
            )
            return
        finally:
            memory_result = await memory_session.flush_turn()
            if recorder is not None:
                await recorder.complete_turn(memory_result)
            await memory_session.drain()
            await tool_session.drain()
            if recorder is not None:
                await recorder.finish()
