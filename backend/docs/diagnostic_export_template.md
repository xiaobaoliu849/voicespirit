# Diagnostic Export Template

Use this template when reporting backend/frontend issues.

## 1) Basic Context

- Date/time:
- Environment: local / staging / production
- Backend commit/version:
- Frontend commit/version:

## 2) Request Trace

- Request ID (`X-Request-ID`):
- Endpoint:
- Method:
- HTTP status:
- Error code (`detail.code` if available):

## 3) Reproduction Steps

1. 
2. 
3. 

## 4) Inputs (sanitized)

- Request payload (remove secrets):
- Query params:
- Auth mode used: api token / admin token / none

## 5) Logs

Attach matching records from:

- `voicespirit.request` (by `request_id`)
- `voicespirit.error` (by `request_id`)

Suggested minimal fields:

- `request_id`
- `path`
- `status`
- `code`
- `message`
- `duration_ms`

## 6) Current vs Expected

- Current behavior:
- Expected behavior:

## 7) Additional Attachments

- Screenshots / screen recording
- Browser console errors
- Related config section (sanitized)
