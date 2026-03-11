# EverMem Integration Pitfalls

Date: 2026-03-12

This note records the confirmed pitfalls found while integrating EverMind/EverMem
into VoiceSpirit chat, realtime voice, podcast, and ASR flows.

## Confirmed pitfalls

1. "Saved" does not mean "immediately searchable"

- `POST /api/v0/memories` can return accepted/queued rather than immediately searchable data.
- UI badges such as `已记忆` or `已提交 EverMind` only prove that the write request was accepted.
- Immediate follow-up retrieval may still miss if cloud indexing has not finished.

2. `foresight` is visible in Cloud, but not a reliable recall source

- Cloud UI may show content under `Foresights`.
- Per the official search docs, `foresight` is not currently supported for search.
- Realtime recall should rely on `episodic_memory`, `profile`, and `pending_messages`.

3. `pending_messages` must be handled explicitly

- Official `GET /api/v0/memories/search` responses may include `pending_messages`.
- This is important for "just wrote it, ask again immediately" scenarios.
- If the app only reads `memories` and `profiles`, recent writes can look lost even when the cloud accepted them.

4. `scope/user_id` and `group_id` are different layers

- `user_id` identifies the long-term owner namespace.
- `group_id` identifies one concrete conversation/session.
- Cloud-generated `..._group` identifiers are not evidence that the user scope is wrong; they are the conversation grouping layer.

5. New conversation in UI does not automatically mean new conversation in EverMem

- Resetting local chat state only clears the frontend session.
- If the app does not create and persist a new EverMem `group_id`, multiple UI conversations can collapse into the same default grouping behavior.
- Proper alignment requires `conversation-meta` create/get/update support.

6. Sender and owner identity must stay aligned

- Memory writes were previously unstable because sender-like fields could diverge from the effective user scope.
- If write ownership and retrieval ownership do not line up, cloud data may exist but still not be recallable from the app.

7. Realtime voice cannot wait too long for memory

- Realtime voice must remain latency-safe.
- Memory retrieval therefore needs short time budgets and a fail-open fallback.
- This creates a second problem: without a local cache, the model may answer before cloud retrieval becomes usable.

8. In-memory fallback is not enough

- A process-local pending cache improves immediate recall inside one running app instance.
- It does not survive app restart.
- Persisting the pending cache to disk is required for "close app, reopen app, ask immediately" recovery.

9. WebView/runtime issues can hide memory progress

- Desktop microphone failures happen before realtime memory logic begins.
- Windows launcher argument handling also caused false negatives during testing (`--reset-cache` was not accepted end-to-end before the launcher fix).

## Current mitigations already applied

- Read `pending_messages` from search results.
- Persist realtime pending-memory fallback to disk.
- Keep realtime retrieval source-aware (`local pending` vs `cloud`).
- Align memory sender/owner scope in service code.
- Expand recall-trigger detection for explicit memory-style questions.
- Add clearer launcher support for `--reset-cache`.

## Recommended next step

Implement the official conversation lifecycle:

1. On new chat/voice session, call `POST /api/v0/memories/conversation-meta`.
2. Persist returned `group_id` in frontend and backend session state.
3. Include that `group_id` in subsequent memory writes.
4. Use `group_ids=[current_group_id]` for conversation-scoped retrieval.
5. Use user-only retrieval for broader cross-conversation recall when needed.
