from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket
from pydantic import BaseModel, Field

from services.realtime_voice_service import (
    DEFAULT_DASHSCOPE_REALTIME_VOICE,
    DEFAULT_GOOGLE_REALTIME_VOICE,
    RealtimeVoiceService,
)
from services.voice_agent_session_repository import VoiceAgentSessionRepository

router = APIRouter()
voice_chat_service = RealtimeVoiceService()
voice_agent_session_repository = VoiceAgentSessionRepository()


class VoiceAgentSessionResponse(BaseModel):
    id: str
    provider: str
    model: str = ""
    voice: str = ""
    status: str
    started_at: str
    ended_at: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class VoiceAgentTurnResponse(BaseModel):
    id: int
    session_id: str
    turn_id: str
    user_text: str = ""
    assistant_text: str = ""
    memory_payload: dict[str, Any] = Field(default_factory=dict)
    completed: bool
    started_at: str
    completed_at: str = ""


class VoiceAgentToolEventResponse(BaseModel):
    id: int
    session_id: str
    turn_id: str = ""
    event_type: str
    tool_name: str = ""
    query: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class VoiceAgentSessionListResponse(BaseModel):
    count: int
    sessions: list[VoiceAgentSessionResponse] = Field(default_factory=list)


class VoiceAgentSessionDetailResponse(VoiceAgentSessionResponse):
    turns: list[VoiceAgentTurnResponse] = Field(default_factory=list)
    tool_events: list[VoiceAgentToolEventResponse] = Field(default_factory=list)


def _raise_not_found(session_id: str) -> None:
    raise HTTPException(
        status_code=404,
        detail={
            "code": "VOICE_AGENT_SESSION_NOT_FOUND",
            "message": f"Voice agent session not found: {session_id}",
            "meta": {"session_id": session_id},
        },
    )


@router.get("/sessions", response_model=VoiceAgentSessionListResponse)
async def list_voice_agent_sessions(
    limit: int = Query(default=20, ge=1, le=200),
) -> VoiceAgentSessionListResponse:
    sessions = voice_agent_session_repository.list_sessions(limit=limit)
    return VoiceAgentSessionListResponse(count=len(sessions), sessions=sessions)


@router.get("/sessions/{session_id}", response_model=VoiceAgentSessionDetailResponse)
async def get_voice_agent_session(session_id: str) -> VoiceAgentSessionDetailResponse:
    session = voice_agent_session_repository.get_session(session_id)
    if session is None:
        _raise_not_found(session_id)
    assert session is not None
    return VoiceAgentSessionDetailResponse(
        **session,
        turns=voice_agent_session_repository.list_turns(session_id),
        tool_events=voice_agent_session_repository.list_tool_events(session_id),
    )


@router.websocket("/ws")
async def voice_chat_ws(
    websocket: WebSocket,
    provider: str = "Google",
    model: str | None = None,
    voice: str | None = None,
) -> None:
    await websocket.accept()

    selected_provider = (provider or "Google").strip()
    if selected_provider not in {"Google", "DashScope"}:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"当前 Web 实时语音暂不支持 {selected_provider} 供应商。",
                "provider": selected_provider,
            }
        )
        await websocket.close(code=1003)
        return

    try:
        if selected_provider == "DashScope":
            await voice_chat_service.stream_dashscope_session(
                websocket,
                model=model,
                voice=(voice or DEFAULT_DASHSCOPE_REALTIME_VOICE).strip(),
            )
        else:
            await voice_chat_service.stream_google_session(
                websocket,
                model=model,
                voice=(voice or DEFAULT_GOOGLE_REALTIME_VOICE).strip(),
            )
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=1011)
