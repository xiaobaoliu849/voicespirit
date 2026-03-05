# Backend Error Codes Catalog

This document is the consolidated error-code reference for VoiceSpirit backend APIs.
All structured error responses use:

```json
{
  "detail": {
    "code": "...",
    "message": "...",
    "meta": {}
  }
}
```

Observability note:

- All responses include `X-Request-ID` header.
- Auth errors additionally include `detail.meta.request_id`.

## Authentication

| Code | Typical HTTP | Meaning |
| --- | --- | --- |
| `AUTH_TOKEN_MISSING` | `401` | Write request requires bearer token but none was provided. |
| `AUTH_TOKEN_INVALID` | `403` | Bearer token does not match configured API/admin tokens. |
| `AUTH_ADMIN_TOKEN_MISSING` | `401` | Admin-protected endpoint requires admin bearer token. |
| `AUTH_ADMIN_TOKEN_INVALID` | `403` | Provided token is not the configured admin token. |

## Audio Overview

| Code Prefix / Code | Typical HTTP | Meaning |
| --- | --- | --- |
| `AUDIO_OVERVIEW_*` | `400/404/500` | Podcast CRUD/list/read/audio retrieval errors. |
| `AUDIO_SCRIPT_GENERATE_*` | `400/502/500` | Script generation request/provider/internal errors. |
| `AUDIO_SYNTHESIZE_*` | `400/503/500` | Synthesis request/runtime/internal errors. |
| `AUDIO_MERGE_STRATEGY_INVALID` | `400` | Unsupported `merge_strategy`. |
| `AUDIO_MERGE_PYDUB_FAILED` | `503` | `pydub` merge failed. |
| `AUDIO_MERGE_FFMPEG_FAILED` | `503` | `ffmpeg` merge failed. |
| `AUDIO_MERGE_ALL_FAILED` | `503` | `pydub -> ffmpeg -> concat` all failed. |
| `AUDIO_SEGMENT_SYNTHESIS_FAILED` | `503` | Segment-level TTS generation failed. |
| `AUDIO_MERGE_UNKNOWN_ERROR` | `500` | Unexpected merge-layer failure. |

## Chat / Translate

| Code Prefix / Code | Typical HTTP | Meaning |
| --- | --- | --- |
| `CHAT_BAD_REQUEST` | `400` | Invalid chat payload. |
| `CHAT_PROVIDER_ERROR` | `502` | Upstream LLM provider failure. |
| `CHAT_INTERNAL_ERROR` | `500` | Unexpected chat server error. |
| `TRANSLATE_BAD_REQUEST` | `400` | Invalid translate payload. |
| `TRANSLATE_PROVIDER_ERROR` | `502` | Upstream translation provider failure. |
| `TRANSLATE_INTERNAL_ERROR` | `500` | Unexpected translate server error. |

## Settings

| Code | Typical HTTP | Meaning |
| --- | --- | --- |
| `SETTINGS_LOAD_FAILED` | `500` | Settings read failed. |
| `SETTINGS_BAD_REQUEST` | `400` | Settings patch validation failed. |
| `SETTINGS_UPDATE_FAILED` | `500` | Settings write failed. |

## TTS

| Code | Typical HTTP | Meaning |
| --- | --- | --- |
| `TTS_VOICES_BAD_REQUEST` | `400` | Invalid voices query. |
| `TTS_VOICES_INTERNAL_ERROR` | `500` | Voice list failed unexpectedly. |
| `TTS_SPEAK_BAD_REQUEST` | `400` | Invalid speak request. |
| `TTS_SPEAK_DEPENDENCY_ERROR` | `503` | Runtime dependency issue (e.g. edge-tts). |
| `TTS_SPEAK_INTERNAL_ERROR` | `500` | Unexpected TTS server error. |

## Voices

| Code Prefix / Code | Typical HTTP | Meaning |
| --- | --- | --- |
| `VOICE_DESIGN_*` | `400/502/500` | Voice design request/provider/internal errors. |
| `VOICE_CLONE_*` | `400/502/500` | Voice clone request/provider/internal errors. |
| `VOICE_LIST_*` | `400/502/500` | Voice list request/provider/internal errors. |
| `VOICE_DELETE_*` | `400/502/500` | Voice delete request/provider/internal errors. |

## Related Documents

- Audio Overview merge and synthesis details: `backend/docs/audio_overview_error_codes.md`
- Authentication behavior and token sources: `backend/docs/authentication.md`
