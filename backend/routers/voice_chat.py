from __future__ import annotations

from fastapi import APIRouter, WebSocket

from services.realtime_voice_service import (
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
    voice: str = DEFAULT_GOOGLE_REALTIME_VOICE,
) -> None:
    await websocket.accept()

    selected_provider = provider.strip() or "Google"
    if selected_provider != "Google":
        await websocket.send_json(
            {
                "type": "error",
                "message": "当前 Web 实时语音仅先支持 Google native realtime。",
                "provider": selected_provider,
            }
        )
        await websocket.close(code=1003)
        return

    try:
        await voice_chat_service.stream_google_session(
            websocket,
            model=model,
            voice=voice.strip() or DEFAULT_GOOGLE_REALTIME_VOICE,
        )
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=1011)

