# VoiceSpirit Desktop Quickstart

## Recommended desktop entry

VoiceSpirit desktop should be launched through the Web desktop wrapper:

```bash
python run_web_desktop.py
```

This starts:
- local FastAPI backend on `127.0.0.1:8000`
- packaged React frontend at `/app/`
- native desktop window through `pywebview`

Do not treat the old `app/ui/...` PySide6 page stack as the main product surface.

## First-time setup

### 1. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Build frontend

```bash
cd frontend
npm install
npm run build
```

### 3. Install desktop wrapper dependencies

```bash
pip install -r desktop_requirements.txt
```

### 4. Launch desktop

```bash
python run_web_desktop.py
```

### Optional: run desktop preflight first

```bash
python run_web_desktop.py --check
```

This verifies:
- frontend build exists
- desktop docs exist
- backend process can start
- desktop prerequisites are roughly ready

## What is already usable

- Chat
- Translate
- TTS
- Podcast
- Transcription Center
- Settings
- EverMem memory integration

## Transcription modes

### Short local audio

- Use local file upload in `Transcription Center`
- This goes through sync transcription

### Long local audio

- If `transcription_settings.public_base_url` is empty:
  - local upload stays in `uploaded/staged`
- If `public_base_url` is configured:
  - local upload can be published and submitted as async transcription

### Remote long audio

- Use public `http/https/oss` file URL
- This goes through true async transcription job flow

## Upload mode settings

Open `Settings -> Transcription Async Upload`.

### `static`

- Local files are exposed under `/public/transcription/*`
- Good for local testing and internal desktop use

### `s3`

- Local files are uploaded to object storage
- Requires:
  - `public_base_url`
  - `s3_bucket`
  - `s3_region`
  - `s3_endpoint_url` if needed
  - `s3_access_key_id`
  - `s3_secret_access_key`
  - `s3_key_prefix`

### `disabled`

- Local long audio stays staged only
- No automatic async submission

## Optional S3 dependency

`s3` upload mode requires `boto3`.

Install it manually when needed:

```bash
cd backend
pip install boto3
```

If `boto3` is not installed, VoiceSpirit will safely disable `s3` upload mode instead of crashing.

## Common desktop paths

- Runtime dir: system state dir or project `.voicespirit-desktop/`
- Window state: `desktop_window.json`
- Lock file: `desktop.lock`
- WebView storage: runtime `webview/`
- Published transcription files: `backend/temp_audio/transcription_jobs/published/`

## Troubleshooting

### Blank window

- Check `http://127.0.0.1:8000/health`
- Check `http://127.0.0.1:8000/app/`
- Rebuild frontend if `frontend/dist` is missing

### Desktop refuses to start

- Check whether another instance is already running
- Remove stale `desktop.lock` only if no desktop instance is active
- Run `python run_web_desktop.py --check`

### Transcription async upload stays staged

- Check `Settings -> Transcription Async Upload`
- Ensure `public_base_url` is configured
- For `s3` mode, ensure `boto3` is installed and credentials are valid

### No transcript download

- Async task must first reach `completed`
- Then the task exposes `transcript_download_url`

## Recommended current workflow

1. Launch `run_web_desktop.py`
2. Open `Settings`
3. Configure provider API keys
4. Configure EverMem if needed
5. Configure `Transcription Async Upload` if you want long local audio async flow
6. Use `Transcription Center` for short sync or long async transcription
