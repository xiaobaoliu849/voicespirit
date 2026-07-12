# VoiceSpirit Voice Agent Evolution Roadmap

Last updated: 2026-07-12

## Executive View

VoiceSpirit already has three valuable foundations:

- realtime voice chat through Google Native Audio, DashScope Qwen Omni, and OpenAI Realtime
- two-phase interruption handling with provider-normalized decisions and interrupted turn boundaries
- an audio/podcast agent flow with retrieval, research sources, draft generation, persistence, and synthesis

The next product jump is not "add another TTS model". It is to turn voice chat from a realtime talking interface into a task-capable agent runtime.

## What Defines A Voice Agent

A production voice agent is different from voice chat in these areas:

- low-latency full-duplex audio: capture, transcribe, reason, and speak with minimal dead air
- turn detection: decide when the user started, paused, finished, or only backchanneled
- barge-in: stop speaking when the user truly interrupts, then repair the conversation state
- tool use: search, read files, call APIs, create drafts, update local app state, and report progress
- grounded response synthesis: collect sources, compress evidence, cite or explain provenance, then answer
- memory: recall persistent user preferences and session context without flooding the prompt
- task state: represent in-progress work as cancellable, resumable runs rather than one-shot replies
- observability: log speech state, agent state, tool calls, interruption decisions, errors, and latency
- safety and permissions: separate read-only tools from actions that need user approval

## Current VoiceSpirit State

### Realtime voice chat

Implemented:

- WebSocket route: `backend/routers/voice_chat.py`
- provider bridge: `backend/services/realtime_voice_service.py`
- frontend capture/playback: `frontend/src/hooks/useVoiceChat.ts`
- active UI surface: `frontend/src/pages/ChatPage.tsx` with `frontend/src/components/VoiceAgentHistoryPanel.tsx`
- memory integration: `RealtimeMemorySession` with EverMem retrieval and writeback
- local playback interruption: frontend handles `interrupted` by stopping queued audio buffers
- voice search tool session: `backend/services/voice_agent_tools.py`
- structured realtime tool events: `tool_call_started`, `agent_progress`, `tool_call_completed`, `tool_call_failed`, `tool_call_cancelled`, `tool_context_injected`, `agent_result`
- realtime web search/fetch path using `AudioResearchService`
- application action tool for creating queued audio agent runs from voice
- application action tool for translating short spoken text through `LLMService.translate_text`
- application action tool for summarizing spoken transcript text through `LLMService.chat_completion`
- application action tool for generating TTS audio files through `TTSService.generate_audio`
- tool result injection back into Google, DashScope, and OpenAI realtime sessions for voice answers
- frontend tool status, run metadata, and source cards
- frontend-local session history now stores structured realtime tool call records on assistant messages
- backend SQLite persistence for realtime voice agent sessions, turn transcripts, and tool event payloads
- read API for persisted realtime voice agent sessions and detail records
- frontend browsing/export UI for persisted realtime voice agent sessions
- canonical voice agent timeline built from session, turn, tool, memory, and completion events
- response gating for search turns through `response_gated`, suppressing direct generic replies while tool results are pending
- runtime interruption classification into `TRUE_BARGE_IN`, `BACKCHANNEL`, and `NOISE_OR_SILENCE`
- two-phase `interruption_pending` -> `interruption_decision` protocol with delayed tool/response cancellation
- explicit response cancellation/manual response creation for OpenAI and DashScope; client-side VAD plus application-level output suppression for Google (whose Live session has no explicit response-cancel method)
- monotonic canonical session-event ledger with interruption decisions, first-audio metrics, and interrupted assistant boundaries
- provider-independent timeline-first rendering with raw records in a supporting disclosure
- deterministic raw Provider event replay coverage for Google, DashScope, and OpenAI
- lightweight live/history UI for first-audio latency, interruption-stop latency, and the false-interruption proxy
- cross-session/provider metric aggregation for first audio, interruption decision, actual playback stop, and turn completion latency
- reachable timeline filtering by event family and turn
- durable voice-turn links to canonical Agent Run projections, with resume navigation into the audio/podcast workspace

Missing:

- richer retrieval and application tools beyond web search, audio-run creation, translation, transcript summarization, and TTS synthesis
- strict remote Google response cancellation after semantic classification (the public Live session exposes no explicit response-cancel method)
- an operator-oriented long-range metrics dashboard; the current API/UI summary is intentionally lightweight and bounded to recent sessions

### Audio/podcast agent

Implemented:

- run repository and state tables through `backend/services/audio_agent_repository.py`
- orchestration service: `backend/services/audio_agent_service.py`
- research fetch/search: `backend/services/audio_research_service.py`
- retrieval aggregation: `backend/services/audio_retrieval_service.py`
- script writer: `backend/services/audio_script_writer.py`
- API router: `backend/routers/audio_agent.py`
- frontend API integration in `frontend/src/api.ts`
- tests around research, agent run flow, and podcast sidebar rendering
- cancellation endpoint
- retry endpoint (whole-run retry)
- SSE progress stream for long-running agent runs
- canonical `agent_runs` projection and read API without replacing the existing audio-run execution engine
- durable voice-session/turn-to-run links and migration backfill from historical `agent_result` artifacts
- resume navigation from voice history into the existing audio/podcast run workspace

Missing:

- per-step retry policy
- source quality ranking beyond simple caps and dedupe
- stricter grounding/citation validation
- shared tool abstraction reusable by realtime voice chat

## Architecture Direction

Keep two layers separate:

1. Realtime voice session layer
   - owns audio transport, turn detection, interruption, transcript events, playback control
   - should stay small and latency-sensitive

2. Agent task layer
   - owns tools, run state, retrieval, research, synthesis, retries, cancellation, audit logs
   - should be usable from voice chat, text chat, and podcast workflows

The bridge between them should be a typed voice tool event protocol:

- `tool_call_started`
- `agent_progress`
- `tool_call_completed`
- `tool_call_failed`
- `tool_call_cancelled`
- `response_gated`
- `tool_context_injected`
- `agent_result`

Current event payloads should carry:

- `turn_id`
- `tool_name`
- `query`
- `source_count`
- `elapsed_ms`
- `reason` for cancellations

The clean target is a single event ledger:

- realtime providers emit raw transport events
- VoiceSpirit normalizes them into a canonical voice agent timeline
- frontend history, replay, export, debugging, and future metrics consume the timeline
- LiveKit or WebRTC can become a transport adapter without changing the agent history model

## Proposed Milestones

### Milestone 1: Realtime Voice Agent MVP

Goal: user can ask by voice for a searched/grounded answer and interrupt the agent while it is working or speaking.

Backend:

- done: add first lightweight voice tool session in `backend/services/voice_agent_tools.py`
- done: add `search_web` behavior by wrapping `AudioResearchService.search` and `fetch_document`
- done: emit structured tool/progress events over `/api/voice-chat/ws`
- done: track cancellable tool tasks per voice turn
- done: inject completed search context into Google, DashScope, and OpenAI realtime models
- done: gate search-intent turns so raw realtime replies are suppressed until tool context is ready
- done: add lightweight multi-tool request dispatch
- done: add `create_audio_agent_run` as a callable voice action
- done: add `translate_text` as a callable voice action
- done: add `summarize_transcript` as a callable voice action
- done: add `synthesize_tts` as a callable voice action
- done: persist realtime tool calls into frontend-local session history
- done: persist realtime tool transcripts and artifacts in the backend
- done: expose persisted voice agent sessions through a read API
- done: add frontend browsing/export UI for persisted voice agent sessions
- done: expose a canonical backend timeline for persisted voice agent sessions
- done: render the canonical timeline as the primary history view with raw records collapsed
- done: add deterministic Google, DashScope, and OpenAI raw event sequence replay tests

Frontend:

- done: show current tool status in `VoiceChatPage`
- done: show source snippets for grounded answers
- done: show run metadata such as `turn_id`, source count, and elapsed time
- done: treat interruption as both playback stop and current-turn cancellation request
- done: attach structured tool call records to archived voice assistant messages
- done: browse, inspect, and export persisted backend voice agent sessions
- done: make the canonical timeline the primary replay/debugging surface

Success criteria:

- voice prompt: "帮我查一下 X，然后总结三个重点"
- done: app searches/fetches/summarizes
- done: UI shows progress and sources
- done: user interruption cancels active tool work
- done: search context is passed back to the realtime model for a voice answer
- done: reduce risk of raw model reply racing with tool-grounded reply through response gating
- done: add scenario tests with recorded realtime event sequences built around the canonical timeline

### Milestone 2: Robust Interruption Policy

Goal: make barge-in feel natural rather than just technically possible.

Backend:

- done: persist provider-normalized interruption decisions with classification, rule, turn, and latency
- done: distinguish true interruption, short backchannel, and noise/silence-like transcriptions
- done: add a bounded client watchdog that resolves missing-transcript candidates as noise and restores playback
- done: keep the interrupted assistant text boundary and mark its turn `interrupted`

Frontend:

- done: show a subtle evaluating/interrupted state
- done: archive partial assistant messages with an explicit interrupted marker

Metrics:

- done: time to first audio (per-turn event and live/history UI)
- done: client-local interruption-to-stop latency measured at the actual playback stop
- done: server decision latency shown separately in persisted history
- done: false interruption proxy `(BACKCHANNEL + NOISE_OR_SILENCE) / candidates`
- done: aggregate these metrics across recent sessions and providers
- done: add turn-completion latency and exclude superseded timeout decisions from interruption rates

### Milestone 3: Unified Agent Runs

Goal: voice chat can start durable tasks and resume them later.

Tasks:

- done: promote audio agent run state to a shared `agent_runs` projection/adapter while retaining the existing audio execution source of truth
- done: add cancellation and whole-run retry APIs to audio agent runs
- done: add SSE progress for run execution
- done: persist voice session transcripts and run artifacts in event payloads
- done: add a durable relational link from voice turns to unified agent runs, including legacy artifact backfill
- done: expose unified run detail/events reads and resume linked audio runs from active voice history UI
- next: add capability-aware unified lifecycle commands and event streaming before introducing a second durable run type

Current boundary:

- `agent_runs` is a canonical projection and cross-feature identity, not a second orchestration engine
- audio cancellation, retry, and SSE remain owned by `AudioAgentService`; the adapter refreshes from that source of truth
- the minimal product loop is complete for audio runs: voice creates task -> durable link -> history inspection -> resume in audio workspace

### Milestone 4: Action Agent

Goal: user can ask the voice agent to do app-local work.

Candidate actions:

- done: create a podcast/audio-agent draft from a spoken topic
- done: summarize transcript text
- done: translate selected text
- done: generate TTS from a drafted answer
- save user voice preferences

Permission model:

- read-only actions can run immediately
- destructive or external side effects require explicit confirmation

## Immediate Development Backlog

1. **[DONE]** Promote the canonical voice agent timeline to the primary frontend history/replay view.
2. **[DONE]** Add deterministic Provider event sequence tests for interruption/cancellation, while retaining projection tests for search and memory-write turns.
3. **[DONE]** Add aggregate latency fields to timeline events (`elapsed_ms`, provider, transport, stage).
4. **[DONE]** Add runtime interruption classification plus a bounded missing-transcript timeout.
5. **[DONE]** Add audio agent cancellation/retry endpoints.
6. **[DONE]** Add SSE or WebSocket progress for durable audio agent runs.
7. **[DONE]** Add a shared tool/action permission model for read-only versus confirm-required actions.
8. **[DONE]** Evaluate LiveKit after the timeline contract survives Google, DashScope, and OpenAI session replay; defer migration and keep transport behind the canonical timeline/session boundary.

## Recommended Next Code Iteration

The timeline/interruption slice is complete:

- done: backend timeline builder from a monotonic session event ledger
- done: API detail response that includes both raw records and canonical timeline
- done: frontend history view that renders the timeline first and raw records as supporting detail
- done: deterministic Google, DashScope, and OpenAI recorded event sequences
- done: cross-session metric aggregation and timeline filtering

The next narrow slice is Milestone 3 hardening:

- define run capabilities (`cancel`, `retry`, `stream`, `resume`) without duplicating source orchestration
- expose capability-aware unified commands that delegate to the owning run service
- normalize durable-run progress into the canonical event contract
- retain the independent-ASR option if strict remote Google cancellation before audio reaches Gemini becomes a product requirement

This proves VoiceSpirit can reason about voice agent sessions independently of provider transport before taking on a LiveKit/WebRTC migration.

## Transport Decision: LiveKit

Decision as of 2026-07-12: do not migrate the current realtime path to LiveKit yet.

The present product is a desktop-first, mostly one-user/one-agent application with three provider-native realtime protocols. Its hardest problems are semantic interruption, canonical state, task durability, and replay consistency. LiveKit would improve media transport, room/participant management, telephony, horizontal worker dispatch, and managed network traversal, but it would not remove the provider-specific cancellation and semantic turn-repair work already normalized here.

Keep the current WebSocket/provider adapters while preserving a transport-neutral session boundary. Reconsider LiveKit when at least one of these becomes a committed requirement:

- browser/mobile clients on unreliable networks need production-grade WebRTC and TURN
- PSTN/SIP or multi-party rooms become a product surface
- concurrent agent sessions need a distributed worker/dispatch plane
- managed noise cancellation and media observability justify the operational/cost tradeoff

If those requirements arrive, add LiveKit as a transport adapter behind the existing canonical timeline and Agent Run contracts. Do not rewrite history, metrics, interruption classification, or task orchestration around LiveKit-specific room events.

Pipecat is also not a near-term replacement. It is more relevant if VoiceSpirit later moves from provider-native speech-to-speech sessions to a modular STT -> LLM -> TTS pipeline and wants interchangeable WebRTC/WebSocket transports. At the current stage, adopting it would duplicate orchestration and event normalization that VoiceSpirit already owns. If that pipeline transition becomes intentional, evaluate Pipecat and LiveKit separately: Pipecat for pipeline composition, LiveKit (or a smaller WebRTC transport) for media delivery.
