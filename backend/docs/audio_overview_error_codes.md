# Audio Overview Error Codes

This document defines the structured error codes returned by:

- `POST /api/audio-overview/podcasts/{podcast_id}/synthesize`

Error payload format:

```json
{
  "detail": {
    "code": "AUDIO_MERGE_FFMPEG_FAILED",
    "message": "ffmpeg merge failed.",
    "meta": {
      "returncode": 1,
      "stderr_tail": "..."
    }
  }
}
```

## Code Reference

| Code | HTTP Status | Meaning | Typical `meta` fields | Suggested Fix |
| --- | --- | --- | --- | --- |
| `AUDIO_MERGE_STRATEGY_INVALID` | `400` | Requested `merge_strategy` is unsupported. | `strategy` | Use one of: `auto`, `pydub`, `ffmpeg`, `concat`. |
| `AUDIO_MERGE_PYDUB_FAILED` | `503` | Merge using `pydub` failed. | `gap_ms`, `reason` | Install `pydub`, verify ffmpeg availability, or switch strategy to `auto`/`concat`. |
| `AUDIO_MERGE_FFMPEG_FAILED` | `503` | Merge using `ffmpeg` failed. | `returncode`, `stderr_tail` | Install/repair ffmpeg and ensure it is in PATH, or switch strategy. |
| `AUDIO_MERGE_ALL_FAILED` | `503` | All fallback strategies failed (`pydub -> ffmpeg -> concat`). | `failures` | Use `concat` directly for immediate recovery, then repair dependencies. |
| `AUDIO_SEGMENT_SYNTHESIS_FAILED` | `503` | TTS synthesis failed on one script segment. | `podcast_id`, `line_index`, `line_role`, `voice`, `reason` | Check provider key/model/network; verify selected voices and retry. |
| `AUDIO_MERGE_UNKNOWN_ERROR` | `503` | Unexpected merge-layer failure. | `reason` | Retry with `concat`, inspect backend logs for traceback. |

## Non-Code Errors

Some failures return plain string messages (for example, resource not found):

- `404`: `podcast not found: {podcast_id}`
- `400`: validation or script-content related errors

These are not returned in `code/message/meta` shape.

## Notes

- `merge_strategy=auto` tries: `pydub` -> `ffmpeg` -> `concat`.
- `gap_ms` is applied only when merge result is `pydub`.
- Frontend should prefer `detail.code` as the machine key and treat `detail.message` as display text.
