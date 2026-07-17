from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .voice_agent_tools import VoiceToolRequest


@dataclass(frozen=True)
class RealtimeToolCall:
    provider: str
    provider_call_id: str
    tool_name: str
    arguments: dict[str, Any]


_TOOL_DECLARATIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "search_web",
        "description": "Search current public web information. Use only when the user asks to search, verify, look up, or needs current information.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A concise standalone search query."}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "translate_text",
        "description": "Translate text when the user explicitly asks for a translation.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The exact source text."},
                "target_language": {"type": "string", "description": "The requested target language."},
            },
            "required": ["text", "target_language"],
            "additionalProperties": False,
        },
    },
    {
        "name": "summarize_transcript",
        "description": "Summarize a transcript or long text only when the user explicitly asks for a summary.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The transcript or text to summarize."}},
            "required": ["text"],
            "additionalProperties": False,
        },
    },
)


def native_tool_declarations() -> list[dict[str, Any]]:
    """Return detached declaration dictionaries safe for provider serialization."""
    return json.loads(json.dumps(_TOOL_DECLARATIONS, ensure_ascii=False))


def dashscope_tool_declarations() -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": declaration}
        for declaration in native_tool_declarations()
    ]


def dashscope_supports_native_tools(model: str | None) -> bool:
    normalized = str(model or "").strip().lower()
    return bool(
        re.fullmatch(
            r"(?:qwen3\.5-omni-(?:plus|flash)-realtime(?:-\d{4}-\d{2}-\d{2})?|qwen-audio-3\.0-realtime(?:-(?:plus|flash))?)",
            normalized,
        )
    )


def parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return dict(arguments)
    if isinstance(arguments, str):
        try:
            decoded = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("Tool arguments are not valid JSON.") from exc
        if isinstance(decoded, dict):
            return decoded
    raise ValueError("Tool arguments must be a JSON object.")


def tool_call_to_request(call: RealtimeToolCall) -> VoiceToolRequest:
    call_id = str(call.provider_call_id or "").strip()
    if not call_id:
        raise ValueError("Native tool call is missing provider_call_id.")
    arguments = parse_tool_arguments(call.arguments)
    name = str(call.tool_name or "").strip()

    if name == "search_web":
        return VoiceToolRequest(name, _required_text(arguments, "query", max_length=240), "搜索网页资料")
    if name == "translate_text":
        source = _required_text(arguments, "text", max_length=4000)
        target = _required_text(arguments, "target_language", max_length=80)
        return VoiceToolRequest(name, f"{source}\n目标语言:{target}", "翻译文本")
    if name == "summarize_transcript":
        return VoiceToolRequest(name, _required_text(arguments, "text", max_length=4000), "总结转录文本")
    raise ValueError(f"Unsupported realtime tool: {name or '<empty>'}")


def tool_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Keep provider responses structured and JSON-safe without prompt injection."""
    return {
        "ok": True,
        "tool_name": str(result.get("tool_name", "")),
        "query": str(result.get("query", "")),
        "answer": str(result.get("answer", "")),
        "sources": result.get("sources", []) if isinstance(result.get("sources"), list) else [],
        "artifact": result.get("artifact", {}) if isinstance(result.get("artifact"), dict) else {},
        "source_count": int(result.get("source_count", 0) or 0),
        "elapsed_ms": int(result.get("elapsed_ms", 0) or 0),
    }


def tool_error_payload(message: str) -> dict[str, Any]:
    return {"ok": False, "error": str(message or "Tool execution failed.")[:1000]}


def _required_text(arguments: dict[str, Any], name: str, *, max_length: int) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Tool argument '{name}' must be a non-empty string.")
    return value.strip()[:max_length]
