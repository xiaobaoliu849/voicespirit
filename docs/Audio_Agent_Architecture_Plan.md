# VoiceSpirit Audio Agent Architecture Plan

## Goal

Build a lightweight, production-oriented audio agent inside the existing VoiceSpirit FastAPI + React application for a domestic consumer audience.

The target workflow is:

1. User enters a topic or request.
2. System gathers supporting material with simple retrieval tools.
3. System writes a grounded two-speaker audio script.
4. User can inspect and edit the script.
5. System synthesizes final audio with the existing TTS pipeline.

This plan intentionally avoids a full rewrite onto a third-party agent framework.

## Why This Direction

### What already exists in the repo

- `backend/services/audio_overview_service.py`
  - already manages podcast drafts, scripts, storage, and TTS synthesis
- `backend/services/tts_service.py`
  - already handles voice selection, caching, and audio generation
- `backend/services/llm_service.py`
  - already provides provider abstraction for LLM calls
- `frontend/src/hooks/useAudioOverview.ts`
  - already provides the user workflow for script generation and synthesis

### Why not rewrite around a framework now

A rewrite onto AgentScope, Bailian Workflow, or another agent framework would add migration cost before improving the actual product experience.

For the current product stage, the real missing capability is not "an agent framework". It is:

- explicit task state
- evidence collection
- tool orchestration
- progress visibility
- resumable long-running jobs

These can be added on top of the current architecture with much less risk.

### Product constraints

This product is aimed at domestic mainstream users. That means the architecture should optimize for:

- stable domestic provider access
- low operational complexity
- predictable latency
- clear UI feedback
- easy debugging and manual correction

That makes a lightweight internal orchestration layer more appropriate than a full multi-agent system.

## Architecture Decision

### Primary decision

Keep the current application architecture and add an internal orchestration layer:

- Keep FastAPI as the application backend
- Keep React as the frontend
- Keep existing TTS and podcast storage code
- Add a new agent runtime service for orchestration
- Use Bailian-compatible model capabilities only as model and tool providers, not as the whole application runtime

### First-phase model strategy

Use the current provider abstraction in `LLMService`, but define the orchestration flow locally in VoiceSpirit.

This gives:

- provider flexibility
- local control over state and retries
- no dependency on a hosted workflow editor
- easier integration with EverMem, existing podcast drafts, and TTS

## Target User Experience

The user should feel that the product is "agentic" without introducing unnecessary complexity.

### Expected user flow

1. User enters a topic such as "帮我做一期关于年轻人睡眠焦虑的播客".
2. UI shows execution stages:
   - understanding topic
   - retrieving materials
   - organizing evidence
   - drafting script
   - ready for review
   - synthesizing audio
3. UI displays sources used by the draft.
4. User can edit the generated script.
5. User clicks synthesize to produce the final audio.

### What the user should not see in phase 1

- multiple visible agents
- complex planner trees
- autonomous browsing loops with unclear stopping conditions
- long background jobs with no visible progress

## Scope Boundaries

### Phase 1 in scope

- single orchestrated agent flow
- simple retrieval tool layer
- evidence pack generation
- grounded script generation
- existing TTS synthesis
- execution progress and source visibility
- draft persistence and retry support

### Phase 1 out of scope

- multi-agent collaboration
- autonomous open-ended deep research
- advanced web crawling infrastructure
- vector database migration
- agent sandbox execution
- human approval checkpoints between every step

## System Design

### Core concept

Introduce a durable `audio_agent_run` object that tracks a single end-to-end generation attempt.

One run owns:

- user input
- normalized task specification
- execution state
- evidence artifacts
- generated script draft
- synthesis output
- errors and retries

### High-level execution graph

The first implementation should use a fixed directed flow rather than a free-form planner:

1. `prepare`
2. `retrieve`
3. `assemble_evidence`
4. `generate_script`
5. `persist_draft`
6. `synthesize_audio` (optional, explicit user action in phase 1)

This is deliberately not a generic agent runtime yet. It is a controlled orchestration flow with agent-like behavior.

## New Backend Modules

### `backend/services/audio_agent_service.py`

Main orchestration service.

Responsibilities:

- create and resume runs
- drive step transitions
- collect progress events
- call retrieval, writing, and synthesis services
- persist run state

Key methods:

- `create_run(...)`
- `get_run(run_id)`
- `list_runs(limit=...)`
- `execute_until_draft(run_id)`
- `synthesize_run(run_id, ...)`
- `retry_step(run_id, step_name)`

### `backend/services/audio_agent_repository.py`

Storage layer for agent runs and artifacts.

Responsibilities:

- schema initialization
- CRUD for runs
- CRUD for steps
- CRUD for evidence sources
- CRUD for artifacts and event logs

This keeps orchestration logic out of raw SQL blocks.

### `backend/services/audio_retrieval_service.py`

Retrieval aggregation layer.

Responsibilities:

- collect candidate evidence from allowed sources
- normalize source objects
- deduplicate evidence
- produce a compact evidence pack for prompting

Initial source adapters:

- EverMem context retrieval
- optional user-supplied source text
- optional manual URL list
- optional provider-native web search if enabled later

Phase 1 should not depend on general web crawling for correctness.

### `backend/services/audio_script_writer.py`

Script drafting layer.

Responsibilities:

- build grounded prompts from evidence pack
- generate structured two-speaker scripts
- request citations or source mapping metadata
- validate the output format

This should eventually absorb the script generation logic currently in `AudioOverviewService.generate_script`.

### `backend/services/audio_agent_models.py`

Shared typed structures for the orchestration layer.

Suggested models:

- `AudioAgentRun`
- `AudioAgentStep`
- `AudioEvidenceSource`
- `AudioEvidencePack`
- `AudioDraftArtifact`
- `AudioAgentError`

## Database Design

Reuse the existing SQLite database `voice_spirit.db`.

### New table: `audio_agent_runs`

Purpose:

- one row per execution attempt

Suggested columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `podcast_id INTEGER NULL`
- `topic TEXT NOT NULL`
- `language TEXT NOT NULL DEFAULT 'zh'`
- `status TEXT NOT NULL`
- `current_step TEXT NOT NULL DEFAULT 'prepare'`
- `provider TEXT NOT NULL DEFAULT 'DashScope'`
- `model TEXT`
- `use_memory INTEGER NOT NULL DEFAULT 1`
- `input_payload TEXT NOT NULL`
- `result_payload TEXT`
- `error_code TEXT`
- `error_message TEXT`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- `completed_at TIMESTAMP NULL`

Status values:

- `queued`
- `running`
- `awaiting_review`
- `draft_ready`
- `synthesizing`
- `completed`
- `failed`
- `cancelled`

### New table: `audio_agent_steps`

Purpose:

- detailed execution trace for each run

Suggested columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `run_id INTEGER NOT NULL`
- `step_name TEXT NOT NULL`
- `status TEXT NOT NULL`
- `attempt_index INTEGER NOT NULL DEFAULT 1`
- `started_at TIMESTAMP`
- `finished_at TIMESTAMP`
- `meta_json TEXT`
- `error_code TEXT`
- `error_message TEXT`

Step names:

- `prepare`
- `retrieve`
- `assemble_evidence`
- `generate_script`
- `persist_draft`
- `synthesize_audio`

### New table: `audio_agent_sources`

Purpose:

- store all evidence sources used by a run

Suggested columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `run_id INTEGER NOT NULL`
- `source_type TEXT NOT NULL`
- `title TEXT`
- `uri TEXT`
- `snippet TEXT`
- `content TEXT`
- `score REAL`
- `meta_json TEXT`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

Source types:

- `evermem`
- `manual_text`
- `manual_url`
- `provider_search`
- `transcript`

### New table: `audio_agent_events`

Purpose:

- UI progress stream and debugging

Suggested columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `run_id INTEGER NOT NULL`
- `event_type TEXT NOT NULL`
- `payload_json TEXT NOT NULL`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

Example event types:

- `run_created`
- `step_started`
- `step_completed`
- `retrieval_summary`
- `draft_created`
- `podcast_saved`
- `synthesis_started`
- `synthesis_completed`
- `run_failed`

## API Design

Add a new router:

- `backend/routers/audio_agent.py`

Mount path:

- `/api/audio-agent`

### `POST /runs`

Create a run and optionally execute until draft generation.

Request:

- `topic`
- `language`
- `provider`
- `model`
- `use_memory`
- `source_urls`
- `source_text`
- `turn_count`
- `auto_execute`

Response:

- run metadata
- current status
- optional latest podcast draft id

### `GET /runs/{run_id}`

Return full run details:

- status
- steps
- evidence sources
- generated draft
- linked podcast id
- latest error

### `GET /runs`

List recent runs for the current user context.

### `POST /runs/{run_id}/execute`

Resume execution until the next stable checkpoint.

### `POST /runs/{run_id}/synthesize`

Use the current draft to synthesize audio via existing `TTSService`.

### `GET /runs/{run_id}/events`

Return ordered event list.

This can be polled in phase 1.
SSE can be added later if needed.

### `POST /runs/{run_id}/retry`

Retry the failed or selected step.

## Backend Flow Details

### Step 1: `prepare`

Responsibilities:

- validate input
- normalize language and provider
- create run row
- create initial step/event rows

Failure policy:

- fail fast on malformed input

### Step 2: `retrieve`

Responsibilities:

- gather relevant context from EverMem if enabled
- incorporate any user-provided source text
- incorporate any user-provided URLs as explicit source targets

Phase 1 retrieval policy:

- keep retrieval deterministic
- do not allow unbounded browsing loops
- cap total source count and content size

Initial defaults:

- max 5 sources
- max 1200 chars per source excerpt
- max 4000 chars total evidence pack

### Step 3: `assemble_evidence`

Responsibilities:

- deduplicate overlapping source text
- convert raw sources into a compact evidence summary
- preserve a source map for UI display

Output shape:

- `evidence_summary`
- `source_cards`
- `evidence_stats`

### Step 4: `generate_script`

Responsibilities:

- ask the model to produce a strict structured script
- require clear segmentation by role
- request grounded tone and audio-friendly cadence
- optionally include source references in metadata

Prompting rules:

- no unsupported claims
- prefer using evidence when available
- if evidence is sparse, explicitly keep claims generic
- keep output editable, not final-polished beyond user control

Validation rules:

- at least 2 lines
- only allowed speaker roles in phase 1: `A`, `B`
- each line must have non-empty text
- total line count within configured range

### Step 5: `persist_draft`

Responsibilities:

- create or update a `podcasts` row
- save `podcast_scripts`
- link `audio_agent_runs.podcast_id`

Important design choice:

The `podcasts` table remains the canonical content entity.

The new agent tables track generation execution.

This avoids breaking current UI assumptions.

### Step 6: `synthesize_audio`

Responsibilities:

- call the existing `AudioOverviewService.synthesize_podcast_audio`
- append events
- update run status

Important design choice:

Do not rewrite TTS orchestration in phase 1.
Reuse the stable synthesis path that already exists.

## Frontend Design

Do not replace the current Audio Overview page.
Enhance it.

### Existing page to extend

- `frontend/src/pages/AudioOverviewPage.tsx`
- `frontend/src/hooks/useAudioOverview.ts`

### New UI areas

#### Execution status panel

Show:

- current run status
- current step
- step checklist
- latest system message

#### Source panel

Show:

- evidence cards used for draft generation
- source type
- title
- snippet

#### Run history

Show recent agent runs separately from saved podcasts.

This distinction matters:

- podcast history = content objects
- agent run history = generation attempts

### UX principles

- make every long action visible
- keep the edit loop manual and explicit
- never hide where the draft came from
- preserve the current simple "generate then edit then synthesize" workflow

## Integration with Existing Services

### `AudioOverviewService`

Refactor plan:

- keep CRUD and synthesis responsibilities
- move script generation responsibility into `audio_script_writer.py`
- optionally expose helper methods for saving drafts

### `LLMService`

Keep it as a provider adapter, not an agent runtime.

Desired role after refactor:

- provider settings resolution
- plain completion request
- streaming completion request
- shared provider error normalization

Avoid putting orchestration logic here.

### `EverMemService`

Use only as one retrieval source.

Do not treat EverMem as the primary evidence engine for factual content.

Its role in this feature should be:

- personalization
- continuity
- user preference grounding

Not:

- replacing external evidence
- acting as the only retrieval method

## Implementation Sequence

### Milestone 1: durable run state

Implement:

- agent run tables
- repository
- router skeleton
- create/get/list run APIs

No retrieval or generation yet.

Success criteria:

- runs can be created and inspected
- tests cover schema and CRUD

### Milestone 2: draft generation path

Implement:

- retrieval service
- evidence assembly
- script writer
- execute-to-draft flow
- draft persistence into existing podcast tables

Success criteria:

- a run can produce a saved draft-backed podcast
- sources and step state are visible

### Milestone 3: synthesis integration

Implement:

- synthesize endpoint on run
- event logging for synthesis
- frontend step display for synthesis progress

Success criteria:

- the run object and podcast object stay linked end-to-end

### Milestone 4: UX refinement

Implement:

- source cards in UI
- run history
- retry action
- richer error rendering

## Error Handling Policy

Errors must be explicit and resumable where possible.

### Recoverable errors

- provider timeout
- temporary retrieval failure
- synthesis dependency unavailable

Behavior:

- mark step failed
- preserve run state
- allow retry

### Non-recoverable errors

- invalid request payload
- invalid script structure after repeated repair attempts
- missing draft on synthesis

Behavior:

- fail the run
- return structured errors

## Testing Strategy

### Backend tests

Add tests for:

- table initialization
- run creation and listing
- step lifecycle transitions
- evidence storage
- draft persistence linkage to podcast tables
- synthesis handoff
- retry behavior

### Frontend tests

Add tests for:

- run creation flow
- execution progress rendering
- source rendering
- draft load after run completion
- synthesis from run-backed draft

## Operational Notes

### Why polling first

Polling `GET /runs/{id}` and `GET /runs/{id}/events` is simpler than introducing SSE immediately.

The workload here is not a high-frequency stream like realtime voice chat.

SSE can be added later if the UX needs finer progress granularity.

### Why fixed-step orchestration first

A fixed graph is easier to:

- test
- debug
- explain to users
- recover from failures
- integrate with current tables and UI

This is the correct tradeoff for phase 1.

## Framework Positioning

### Bailian Assistant API

Recommended usage:

- model and tool provider
- optional function-calling integration

Not recommended usage for now:

- full application orchestration host

### AgentScope

Recommended usage:

- possible phase 2 or phase 3 upgrade if we need:
  - more complex branching
  - distributed workers
  - stronger runtime observability
  - sandboxed tool execution

Not recommended usage for phase 1:

- full rewrite

## Final Recommendation

Implement a lightweight internal audio agent orchestration layer inside the existing VoiceSpirit backend.

Use the current app as the product shell.
Use Bailian-compatible model/tool capabilities as providers.
Do not rewrite the product around an external agent framework yet.

This gives the best balance of:

- domestic usability
- implementation speed
- product control
- incremental risk
- future extensibility

## Immediate Next Implementation Task

The first coding task should be:

1. add new SQLite schema for `audio_agent_runs`, `audio_agent_steps`, `audio_agent_sources`, and `audio_agent_events`
2. add `audio_agent_repository.py`
3. add `audio_agent_service.py` with run creation and inspection only
4. add `backend/routers/audio_agent.py`
5. wire the router into `backend/main.py`

Only after that should the retrieval and script-generation steps be moved into the new orchestration flow.
