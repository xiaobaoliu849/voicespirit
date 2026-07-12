from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.agent_run_service import AgentRunService, AgentRunServiceError


router = APIRouter()
agent_run_service = AgentRunService()


class AgentRunLinkResponse(BaseModel):
    id: int
    agent_run_id: str
    voice_session_id: str
    voice_turn_id: str
    relation_type: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class AgentRunResponse(BaseModel):
    id: str
    run_type: str
    source_kind: str
    source_run_id: str
    title: str = ""
    status: str
    current_step: str = ""
    provider: str = ""
    model: str = ""
    input_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    completed_at: str = ""
    links: list[AgentRunLinkResponse] = Field(default_factory=list)


class AgentRunListResponse(BaseModel):
    count: int
    runs: list[AgentRunResponse] = Field(default_factory=list)


class AgentRunEventResponse(BaseModel):
    id: str
    agent_run_id: str
    event_type: str
    source: str
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentRunEventListResponse(BaseModel):
    count: int
    events: list[AgentRunEventResponse] = Field(default_factory=list)


def _not_found(exc: AgentRunServiceError) -> HTTPException:
    return HTTPException(status_code=404, detail=exc.to_dict())


@router.get("/", response_model=AgentRunListResponse)
async def list_agent_runs(
    limit: int = Query(default=50, ge=1, le=200),
    run_type: str = Query(default="", max_length=80),
) -> AgentRunListResponse:
    runs = agent_run_service.list_runs(limit=limit, run_type=run_type)
    return AgentRunListResponse(count=len(runs), runs=runs)


@router.get("/{agent_run_id}", response_model=AgentRunResponse)
async def get_agent_run(agent_run_id: str) -> AgentRunResponse:
    try:
        return AgentRunResponse(**agent_run_service.get_run(agent_run_id))
    except AgentRunServiceError as exc:
        raise _not_found(exc) from exc


@router.get("/{agent_run_id}/events", response_model=AgentRunEventListResponse)
async def list_agent_run_events(
    agent_run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
) -> AgentRunEventListResponse:
    try:
        events = agent_run_service.list_events(agent_run_id, limit=limit)
    except AgentRunServiceError as exc:
        status_code = 404 if exc.code == "AGENT_RUN_NOT_FOUND" else 502
        raise HTTPException(status_code=status_code, detail=exc.to_dict()) from exc
    return AgentRunEventListResponse(count=len(events), events=events)
