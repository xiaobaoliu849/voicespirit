from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent_run_repository import AgentRunRepository
from .audio_agent_service import AudioAgentService, AudioAgentServiceError


class AgentRunServiceError(Exception):
    def __init__(self, *, code: str, message: str, meta: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.meta = meta or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "meta": self.meta}


class AgentRunService:
    """Adapter that projects source-specific runs into a stable canonical contract."""

    def __init__(
        self,
        *,
        db_path: Path | None = None,
        repository: AgentRunRepository | None = None,
        audio_agent_service: AudioAgentService | None = None,
    ) -> None:
        self.repository = repository or AgentRunRepository(db_path=db_path)
        self.audio_agent_service = audio_agent_service or AudioAgentService(db_path=db_path)

    def _refresh_audio_run(self, source_run_id: str) -> dict[str, Any] | None:
        try:
            source_run = self.audio_agent_service.get_run(int(source_run_id))
        except (AudioAgentServiceError, TypeError, ValueError):
            return None
        return self.repository.upsert_audio_run(source_run)

    def get_run(self, run_id: str) -> dict[str, Any]:
        clean_run_id = str(run_id or "").strip()
        run = self.repository.get_run(clean_run_id)
        if run is None:
            raise AgentRunServiceError(
                code="AGENT_RUN_NOT_FOUND",
                message=f"Agent run not found: {clean_run_id}",
                meta={"agent_run_id": clean_run_id},
            )
        if run["source_kind"] == AgentRunRepository.AUDIO_RUN_TYPE:
            run = self._refresh_audio_run(str(run["source_run_id"])) or run
        run["links"] = self.repository.list_links_for_run(clean_run_id)
        return run

    def list_runs(self, limit: int = 50, *, run_type: str = "") -> list[dict[str, Any]]:
        for source_run in self.audio_agent_service.list_runs(limit=min(max(int(limit), 1), 200)):
            self.repository.upsert_audio_run(source_run)
        return self.repository.list_runs(limit=limit, run_type=run_type)

    def list_events(self, run_id: str, limit: int = 200) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        if run["source_kind"] != AgentRunRepository.AUDIO_RUN_TYPE:
            return []
        try:
            source_events = self.audio_agent_service.list_events(
                int(run["source_run_id"]),
                limit=limit,
            )
        except (AudioAgentServiceError, TypeError, ValueError) as exc:
            raise AgentRunServiceError(
                code="AGENT_RUN_SOURCE_UNAVAILABLE",
                message=f"Source events unavailable for agent run: {run_id}",
                meta={"agent_run_id": run_id, "source_run_id": run["source_run_id"]},
            ) from exc
        return [
            {
                "id": f"audio_agent_event:{event['id']}",
                "agent_run_id": str(run["id"]),
                "event_type": str(event.get("event_type", "")),
                "source": AgentRunRepository.AUDIO_RUN_TYPE,
                "timestamp": str(event.get("created_at", "")),
                "payload": event.get("payload") if isinstance(event.get("payload"), dict) else {},
            }
            for event in source_events
        ]
