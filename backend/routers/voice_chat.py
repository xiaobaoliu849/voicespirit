from __future__ import annotations

from fastapi import APIRouter, WebSocket

from services.realtime_voice_service import (
    DEFAULT_DASHSCOPE_REALTIME_VOICE,
    DEFAULT_GOOGLE_REALTIME_VOICE,
    RealtimeVoiceService,
)

router = APIRouter()
voice_chat_service = RealtimeVoiceService()


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

