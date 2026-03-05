# Backend Authentication

VoiceSpirit backend supports optional Bearer-token authentication for write requests under `/api/*`.

## Enable Authentication

You can enable auth by setting either one:

1. Environment variable (recommended for deployment):

```bash
export VOICESPIRIT_API_TOKEN="your-token"
```

2. `config.json`:

```json
{
  "auth_settings": {
    "api_token": "your-token"
  }
}
```

If token is empty, authentication is disabled.

## Optional Admin Token (Settings Write Protection)

If admin token is set, `PUT /api/settings/` requires admin token specifically.

Environment variable:

```bash
export VOICESPIRIT_ADMIN_TOKEN="your-admin-token"
```

`config.json`:

```json
{
  "auth_settings": {
    "api_token": "your-token",
    "admin_token": "your-admin-token"
  }
}
```

## Protected / Unprotected Endpoints

- Protected: `/api/*` with method `POST|PUT|PATCH|DELETE`
- Unprotected:
  - `/api/*` with method `GET|HEAD|OPTIONS`
  - `/` and `/health`

## Request Header

```http
Authorization: Bearer your-token
```

## Error Responses

When token is configured and request targets a protected endpoint:

- Missing token:

```json
{
  "detail": {
    "code": "AUTH_TOKEN_MISSING",
    "message": "Missing Bearer token.",
    "meta": {
      "hint": "Use Authorization: Bearer <token>."
    }
  }
}
```

- Invalid token:

```json
{
  "detail": {
    "code": "AUTH_TOKEN_INVALID",
    "message": "Invalid Bearer token.",
    "meta": {}
  }
}
```

For admin-protected settings write endpoint:

- Missing admin token: `AUTH_ADMIN_TOKEN_MISSING` (401)
- Invalid admin token: `AUTH_ADMIN_TOKEN_INVALID` (403)

## Frontend Integration

Frontend can send token via Vite env:

```bash
VITE_API_TOKEN="your-token"
```

Optional admin token for settings write:

```bash
VITE_API_ADMIN_TOKEN="your-admin-token"
```

`frontend/src/api.ts` will:
- attach `VITE_API_TOKEN` for normal API calls
- prefer `VITE_API_ADMIN_TOKEN` for settings update API
