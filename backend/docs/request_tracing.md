# Request Tracing (X-Request-ID)

VoiceSpirit backend now returns `X-Request-ID` on every response.

## Behavior

- If client sends `X-Request-ID`, backend reuses it.
- If missing, backend generates one automatically.
- Header is always returned in response.

## Auth Error Body

For auth failures, response body also includes `request_id`:

```json
{
  "detail": {
    "code": "AUTH_TOKEN_MISSING",
    "message": "Missing Bearer token.",
    "meta": {
      "hint": "Use Authorization: Bearer <token>.",
      "request_id": "..."
    }
  }
}
```

## Usage Recommendation

- Frontend should log/display `X-Request-ID` on failures.
- Backend log records should include the same request id for fast correlation.

## Backend Request Log Format

Backend emits one JSON line per request with logger `voicespirit.request`:

```json
{
  "event": "http_request",
  "request_id": "a1b2c3...",
  "method": "POST",
  "path": "/api/chat/completions",
  "status": 200,
  "duration_ms": 123.45,
  "auth_result": "passed"
}
```

`auth_result` values:

- `not_required`: route/method does not require auth.
- `passed`: auth required and validated.
- `denied`: auth required but rejected.

Backend also emits one JSON line for each error response (`status >= 400`)
with logger `voicespirit.error`:

```json
{
  "event": "http_error",
  "request_id": "a1b2c3...",
  "method": "GET",
  "path": "/api/tts/speak",
  "status": 400,
  "code": "TTS_SPEAK_BAD_REQUEST",
  "message": "Text is empty after cleanup."
}
```
