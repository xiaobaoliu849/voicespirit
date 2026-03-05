# VoiceSpirit Web (Phase A done, Phase B started)

This is the first migration step from PySide6 UI to FastAPI + React.

## Included now

- FastAPI backend skeleton
- TTS API:
  - `GET /api/tts/voices`
  - `GET /api/tts/speak?text=...&voice=...&rate=...`
- Chat API (OpenAI-compatible providers):
  - `POST /api/chat/completions`
  - `POST /api/chat/completions/stream` (SSE)
- Translate API:
  - `POST /api/translate/`
- Voice API (Qwen custom voices):
  - `POST /api/voices/design`
  - `POST /api/voices/clone`
  - `GET /api/voices/?voice_type=voice_design|voice_clone`
  - `DELETE /api/voices/{voice_name}?voice_type=...`
- Settings API:
  - `GET /api/settings/`
  - `PUT /api/settings/`
- Audio Overview API (baseline CRUD):
  - `GET /api/audio-overview/podcasts`
  - `GET /api/audio-overview/podcasts/latest`
  - `GET /api/audio-overview/podcasts/{podcast_id}`
  - `POST /api/audio-overview/podcasts`
  - `PUT /api/audio-overview/podcasts/{podcast_id}`
  - `PUT /api/audio-overview/podcasts/{podcast_id}/script`
  - `DELETE /api/audio-overview/podcasts/{podcast_id}`
- Audio Overview API (generation + synthesis):
  - `POST /api/audio-overview/scripts/generate`
  - `POST /api/audio-overview/podcasts/{podcast_id}/synthesize`
  - `GET /api/audio-overview/podcasts/{podcast_id}/audio`
  - Synthesis body supports:
    - `gap_ms` (0-3000)
    - `merge_strategy`: `auto|pydub|ffmpeg|concat`
  - Synthesis error detail uses structured format:
    - `{"code": "...", "message": "...", "meta": {...}}`
- React + Vite frontend page with 7 tabs:
  - `TTS`
  - `Chat`
  - `Translate`
  - `Voice Design`
  - `Voice Clone`
  - `Audio Overview`
  - `Settings`
  - Chat tab supports streaming render from SSE chunks
  - Voice tabs support create/list/delete
  - Settings tab supports provider config read/write
  - Audio Overview tab supports script generation/edit/save/synthesis/playback/history load

## Project paths

- Backend: `backend/`
- Frontend: `frontend/`

## Local run

### 1) Browser mode (existing)

#### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`

### 2) Desktop mode (PyWebView wrapper)

Build frontend first (required for `/app` static hosting):

```bash
cd frontend
npm install
npm run build
```

Install desktop dependencies:

```bash
pip install -r desktop_requirements.txt
```

Launch desktop window:

```bash
python run_web_desktop.py
```

Windows one-click launcher:

```bash
run_web_desktop.bat
```

Notes:
- The launcher starts backend automatically on `127.0.0.1:8000` if not already running.
- Desktop UI opens `http://127.0.0.1:8000/app/` (FastAPI serves `frontend/dist`).

### 3) Optional auth token

Backend auth is enabled automatically when a token is configured:

```bash
export VOICESPIRIT_API_TOKEN="your-token"
```

Frontend can pass the token automatically:

```bash
export VITE_API_TOKEN="your-token"
```

Optional admin token (settings write):

```bash
export VOICESPIRIT_ADMIN_TOKEN="your-admin-token"
export VITE_API_ADMIN_TOKEN="your-admin-token"
```

Optional log search link for `request_id` (frontend):

```bash
export VITE_LOG_SEARCH_BASE_URL="https://your-log-system/search"
```

If set, frontend will render `request_id` as clickable link and append `request_id` query param automatically.
Error panel also supports one-click `Copy issue template` (Markdown) for bug reports.
Issue template and diagnostics include `frontend_version` and `user_agent` for faster environment triage.
If backend root API (`GET /`) is reachable, diagnostics also include `backend_phase/backend_auth_mode/backend_auth_enabled/backend_version/backend_status`.
The header now also provides `Show backend runtime` and `Copy backend runtime` for full root JSON export.

Current auth scope:

- write endpoints only (`POST/PUT/PATCH/DELETE` under `/api/*`)
- read endpoints (`GET`) remain open for local/dev convenience
- when admin token is configured, `PUT /api/settings/` requires admin token

## Notes

- If backend returns `edge-tts is not installed`, run:
  - `pip install edge-tts`
- Chat/Translate/Voice/Settings read-write root `config.json`.
- Optional auth docs:
  - `backend/docs/authentication.md`
- Request tracing docs:
  - `backend/docs/request_tracing.md`
- Diagnostic export template:
  - `backend/docs/diagnostic_export_template.md`
- Global error code catalog:
  - `backend/docs/error_codes_catalog.md`
- Audio Overview merge now supports `pydub/ffmpeg/concat` with auto fallback and configurable sentence gap.
- Audio Overview structured error codes:
  - `backend/docs/audio_overview_error_codes.md`
  - Frontend maps common `detail.code` values to actionable recovery hints via shared `ErrorNotice`.
