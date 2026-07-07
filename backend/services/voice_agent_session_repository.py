from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .audio_agent_repository import ClosingConnection


class VoiceAgentSessionRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or self._default_db_path()
        self._init_db()

    @staticmethod
    def _default_db_path() -> Path:
        from .config_loader import get_data_dir

        return get_data_dir() / "voice_spirit.db"

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            factory=ClosingConnection,
        )
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _encode_json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False)

    @staticmethod
    def _decode_json(value: Any, *, fallback: Any) -> Any:
        if isinstance(value, str) and value.strip():
            try:
                return json.loads(value)
            except Exception:
                return fallback
        return fallback

    @staticmethod
    def _row_to_session(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "provider": str(row["provider"]),
            "model": str(row["model"] or ""),
            "voice": str(row["voice"] or ""),
            "status": str(row["status"]),
            "started_at": str(row["started_at"]),
            "ended_at": str(row["ended_at"] or ""),
            "meta": VoiceAgentSessionRepository._decode_json(row["meta_json"], fallback={}),
        }

    @staticmethod
    def _row_to_turn(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "session_id": str(row["session_id"]),
            "turn_id": str(row["turn_id"]),
            "user_text": str(row["user_text"] or ""),
            "assistant_text": str(row["assistant_text"] or ""),
            "memory_payload": VoiceAgentSessionRepository._decode_json(row["memory_json"], fallback={}),
            "completed": bool(row["completed"]),
            "started_at": str(row["started_at"]),
            "completed_at": str(row["completed_at"] or ""),
        }

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "session_id": str(row["session_id"]),
            "turn_id": str(row["turn_id"] or ""),
            "event_type": str(row["event_type"]),
            "tool_name": str(row["tool_name"] or ""),
            "query": str(row["query"] or ""),
            "payload": VoiceAgentSessionRepository._decode_json(row["payload_json"], fallback={}),
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _timeline_event(
        *,
        event_id: str,
        event_type: str,
        source: str,
        timestamp: str,
        turn_id: str = "",
        tool_name: str = "",
        query: str = "",
        text: str = "",
        payload: dict[str, Any] | None = None,
        order: int,
    ) -> dict[str, Any]:
        return {
            "id": event_id,
            "event_type": event_type,
            "source": source,
            "turn_id": turn_id,
            "tool_name": tool_name,
            "query": query,
            "text": text,
            "timestamp": timestamp,
            "payload": payload or {},
            "_order": order,
        }

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_agent_sessions (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model TEXT,
                    voice TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    meta_json TEXT NOT NULL DEFAULT '{}',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_agent_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    user_text TEXT,
                    assistant_text TEXT,
                    memory_json TEXT NOT NULL DEFAULT '{}',
                    completed INTEGER NOT NULL DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    UNIQUE(session_id, turn_id),
                    FOREIGN KEY(session_id) REFERENCES voice_agent_sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_agent_tool_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_id TEXT,
                    event_type TEXT NOT NULL,
                    tool_name TEXT,
                    query TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES voice_agent_sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_voice_agent_turns_session
                ON voice_agent_turns(session_id, id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_voice_agent_tool_events_session
                ON voice_agent_tool_events(session_id, id)
                """
            )
            conn.commit()

    def create_session(
        self,
        *,
        provider: str,
        model: str,
        voice: str,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO voice_agent_sessions (
                    id,
                    provider,
                    model,
                    voice,
                    status,
                    meta_json
                ) VALUES (?, ?, ?, ?, 'open', ?)
                """,
                (
                    session_id,
                    provider,
                    model,
                    voice,
                    self._encode_json(meta or {}),
                ),
            )
            conn.commit()
        session = self.get_session(session_id)
        if session is None:
            raise RuntimeError("Failed to load created voice agent session.")
        return session

    def finish_session(self, session_id: str, *, status: str = "closed") -> None:
        clean_status = str(status or "closed").strip() or "closed"
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE voice_agent_sessions
                SET status = ?, ended_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (clean_status, str(session_id or "")),
            )
            conn.commit()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, provider, model, voice, status, started_at, ended_at, meta_json
                FROM voice_agent_sessions
                WHERE id = ?
                """,
                (str(session_id or ""),),
            ).fetchone()
        return self._row_to_session(row)

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, provider, model, voice, status, started_at, ended_at, meta_json
                FROM voice_agent_sessions
                ORDER BY started_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [session for row in rows if (session := self._row_to_session(row)) is not None]

    def upsert_turn(
        self,
        session_id: str,
        turn_id: str,
        *,
        user_text: str | None = None,
        assistant_text: str | None = None,
        memory_payload: dict[str, Any] | None = None,
        completed: bool = False,
    ) -> dict[str, Any]:
        clean_turn_id = str(turn_id or "").strip()
        if not clean_turn_id:
            raise ValueError("turn_id is required.")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO voice_agent_turns (
                    session_id,
                    turn_id,
                    user_text,
                    assistant_text,
                    memory_json,
                    completed,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END)
                ON CONFLICT(session_id, turn_id) DO UPDATE SET
                    user_text = CASE
                        WHEN excluded.user_text IS NOT NULL AND excluded.user_text != '' THEN excluded.user_text
                        ELSE voice_agent_turns.user_text
                    END,
                    assistant_text = CASE
                        WHEN excluded.assistant_text IS NOT NULL AND excluded.assistant_text != '' THEN
                            COALESCE(voice_agent_turns.assistant_text, '') || excluded.assistant_text
                        ELSE voice_agent_turns.assistant_text
                    END,
                    memory_json = CASE
                        WHEN excluded.memory_json != '{}' THEN excluded.memory_json
                        ELSE voice_agent_turns.memory_json
                    END,
                    completed = CASE
                        WHEN excluded.completed = 1 THEN 1
                        ELSE voice_agent_turns.completed
                    END,
                    completed_at = CASE
                        WHEN excluded.completed = 1 THEN CURRENT_TIMESTAMP
                        ELSE voice_agent_turns.completed_at
                    END
                """,
                (
                    str(session_id or ""),
                    clean_turn_id,
                    user_text,
                    assistant_text,
                    self._encode_json(memory_payload or {}),
                    1 if completed else 0,
                    1 if completed else 0,
                ),
            )
            conn.commit()
        turns = [turn for turn in self.list_turns(session_id) if turn["turn_id"] == clean_turn_id]
        if not turns:
            raise RuntimeError("Failed to load voice agent turn.")
        return turns[-1]

    def add_tool_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        turn_id = str(payload.get("turn_id", "") or "")
        tool_name = str(payload.get("tool_name", "") or "")
        query = str(payload.get("query", "") or "")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO voice_agent_tool_events (
                    session_id,
                    turn_id,
                    event_type,
                    tool_name,
                    query,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(session_id or ""),
                    turn_id or None,
                    str(event_type or ""),
                    tool_name or None,
                    query or None,
                    self._encode_json(payload),
                ),
            )
            conn.commit()
            event_id = int(cursor.lastrowid)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, session_id, turn_id, event_type, tool_name, query, payload_json, created_at
                FROM voice_agent_tool_events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to load voice agent tool event.")
        return self._row_to_event(row)

    def list_turns(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    session_id,
                    turn_id,
                    user_text,
                    assistant_text,
                    memory_json,
                    completed,
                    started_at,
                    completed_at
                FROM voice_agent_turns
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (str(session_id or ""),),
            ).fetchall()
        return [self._row_to_turn(row) for row in rows]

    def list_tool_events(self, session_id: str, limit: int = 200) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, turn_id, event_type, tool_name, query, payload_json, created_at
                FROM voice_agent_tool_events
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (str(session_id or ""), safe_limit),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def build_timeline(self, session_id: str) -> list[dict[str, Any]]:
        session = self.get_session(session_id)
        if session is None:
            return []

        timeline: list[dict[str, Any]] = [
            self._timeline_event(
                event_id=f"session:{session['id']}:open",
                event_type="session_open",
                source="session",
                timestamp=str(session.get("started_at", "")),
                payload={
                    "provider": session.get("provider", ""),
                    "model": session.get("model", ""),
                    "voice": session.get("voice", ""),
                    "status": session.get("status", ""),
                    "meta": session.get("meta", {}),
                },
                order=0,
            )
        ]

        for turn in self.list_turns(session_id):
            turn_id = str(turn.get("turn_id", ""))
            if str(turn.get("user_text", "")).strip():
                timeline.append(
                    self._timeline_event(
                        event_id=f"turn:{turn['id']}:user",
                        event_type="user_transcript",
                        source="turn",
                        turn_id=turn_id,
                        text=str(turn.get("user_text", "")),
                        timestamp=str(turn.get("started_at", "")),
                        payload={"completed": bool(turn.get("completed", False))},
                        order=20,
                    )
                )
            if str(turn.get("assistant_text", "")).strip():
                timeline.append(
                    self._timeline_event(
                        event_id=f"turn:{turn['id']}:assistant",
                        event_type="assistant_response",
                        source="turn",
                        turn_id=turn_id,
                        text=str(turn.get("assistant_text", "")),
                        timestamp=str(turn.get("completed_at") or turn.get("started_at", "")),
                        payload={"completed": bool(turn.get("completed", False))},
                        order=60,
                    )
                )
            memory_payload = turn.get("memory_payload", {})
            if isinstance(memory_payload, dict) and memory_payload:
                timeline.append(
                    self._timeline_event(
                        event_id=f"turn:{turn['id']}:memory",
                        event_type="memory_commit",
                        source="memory",
                        turn_id=turn_id,
                        timestamp=str(turn.get("completed_at") or turn.get("started_at", "")),
                        payload=memory_payload,
                        order=70,
                    )
                )
            if bool(turn.get("completed", False)):
                timeline.append(
                    self._timeline_event(
                        event_id=f"turn:{turn['id']}:complete",
                        event_type="turn_completed",
                        source="turn",
                        turn_id=turn_id,
                        timestamp=str(turn.get("completed_at") or turn.get("started_at", "")),
                        payload={},
                        order=80,
                    )
                )

        for event in self.list_tool_events(session_id):
            payload = event.get("payload", {})
            timeline.append(
                self._timeline_event(
                    event_id=f"tool_event:{event['id']}",
                    event_type=str(event.get("event_type", "")),
                    source="tool_event",
                    turn_id=str(event.get("turn_id", "")),
                    tool_name=str(event.get("tool_name", "")),
                    query=str(event.get("query", "")),
                    text=str(payload.get("message") or payload.get("answer") or "") if isinstance(payload, dict) else "",
                    timestamp=str(event.get("created_at", "")),
                    payload=payload if isinstance(payload, dict) else {},
                    order=40,
                )
            )

        if str(session.get("ended_at", "")).strip():
            timeline.append(
                self._timeline_event(
                    event_id=f"session:{session['id']}:closed",
                    event_type="session_closed",
                    source="session",
                    timestamp=str(session.get("ended_at", "")),
                    payload={"status": session.get("status", "")},
                    order=900,
                )
            )

        timeline.sort(
            key=lambda item: (
                str(item.get("timestamp", "")),
                int(item.get("_order", 0)),
                str(item.get("id", "")),
            )
        )
        for item in timeline:
            item.pop("_order", None)
        return timeline
