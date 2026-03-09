from __future__ import annotations

import base64
import json
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .config_loader import BackendConfig
from .evermem_config import EverMemConfig
from .transcription_publish_adapter import build_transcription_publisher

QWEN_ASR_SYNC_MODEL = "qwen-asr-flash"
QWEN_ASR_ASYNC_MODEL = "qwen-asr-flash-filetrans"
QWEN_MULTIMODAL_GENERATION_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
)
SUPPORTED_AUDIO_SUFFIXES = {
    ".wav",
    ".mp3",
    ".flac",
    ".m4a",
    ".aac",
    ".mp4",
    ".ogg",
    ".opus",
    ".webm",
}


@dataclass(slots=True)
class TranscriptionJob:
    file_path: str
    mode: str
    status: str = "queued"
    job_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    transcript_path: str | None = None
    error: str | None = None
    remote_job_id: str | None = None
    source_url: str | None = None
    memory_saved: bool = False


class TranscriptionService:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()
        self.jobs_dir = Path(__file__).resolve().parents[1] / "temp_audio" / "transcription_jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def published_dir(self) -> Path:
        path = self.jobs_dir / "published"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _dashscope_key(self) -> str:
        self.config.reload()
        api_keys = self.config.get_all().get("api_keys", {})
        return str(api_keys.get("dashscope_api_key", "")).strip()

    def _dashscope_async_base_url(self) -> str:
        base_url = self.config.get_provider_settings("DashScope").get("base_url", "").strip()
        if not base_url:
            return "https://dashscope.aliyuncs.com/api/v1"
        if base_url.endswith("/compatible-mode/v1"):
            return base_url[: -len("/compatible-mode/v1")] + "/api/v1"
        return base_url.rstrip("/")

    @staticmethod
    def _guess_mime_type(file_path: Path) -> str:
        guessed, _ = mimetypes.guess_type(str(file_path))
        return guessed or "audio/wav"

    @staticmethod
    def _validate_file(path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {path}")
        if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            raise ValueError(
                "Unsupported audio format. Supported formats: "
                + ", ".join(sorted(SUPPORTED_AUDIO_SUFFIXES))
            )
        if path.stat().st_size <= 0:
            raise ValueError("Audio file is empty.")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _job_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def _write_job(self, job: TranscriptionJob) -> TranscriptionJob:
        if not job.job_id:
            raise ValueError("job_id is required to persist transcription job.")
        payload = {
            "job_id": job.job_id,
            "file_path": job.file_path,
            "mode": job.mode,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "transcript_path": job.transcript_path,
            "error": job.error,
            "remote_job_id": job.remote_job_id,
            "source_url": job.source_url,
            "memory_saved": job.memory_saved,
        }
        self._job_path(job.job_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return job

    def get_job(self, job_id: str) -> TranscriptionJob | None:
        path = self._job_path(job_id)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TranscriptionJob(**payload)

    def list_jobs(
        self,
        *,
        statuses: set[str] | None = None,
        limit: int = 50,
    ) -> list[TranscriptionJob]:
        normalized_statuses = {status.strip().lower() for status in (statuses or set()) if status.strip()}
        jobs: list[TranscriptionJob] = []
        for path in self.jobs_dir.glob("tx_*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                job = TranscriptionJob(**payload)
            except Exception:
                continue
            if normalized_statuses and job.status.lower() not in normalized_statuses:
                continue
            jobs.append(job)

        jobs.sort(
            key=lambda item: (
                item.updated_at or "",
                item.created_at or "",
                item.job_id or "",
            ),
            reverse=True,
        )
        return jobs[: max(0, limit)]

    def can_publish_local_async(self) -> bool:
        return build_transcription_publisher(
            self.config,
            published_dir=self.published_dir,
        ).is_enabled()

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        transcript_path: str | None = None,
        error: str | None = None,
        remote_job_id: str | None = None,
        source_url: str | None = None,
        memory_saved: bool | None = None,
    ) -> TranscriptionJob:
        job = self.get_job(job_id)
        if job is None:
            raise FileNotFoundError(f"Transcription job not found: {job_id}")
        if status is not None:
            job.status = status
        if transcript_path is not None:
            job.transcript_path = transcript_path
        if error is not None:
            job.error = error
        if remote_job_id is not None:
            job.remote_job_id = remote_job_id
        if source_url is not None:
            job.source_url = source_url
        if memory_saved is not None:
            job.memory_saved = memory_saved
        job.updated_at = self._now_iso()
        return self._write_job(job)

    async def transcribe_file(self, file_path: str | Path) -> str:
        path = Path(file_path).expanduser().resolve()
        self._validate_file(path)

        api_key = self._dashscope_key()
        if not api_key:
            raise ValueError("DashScope API Key missing.")

        audio_bytes = path.read_bytes()
        mime_type = self._guess_mime_type(path)
        payload = {
            "model": QWEN_ASR_SYNC_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "audio": (
                                    f"data:{mime_type};base64,"
                                    f"{base64.b64encode(audio_bytes).decode('ascii')}"
                                )
                            }
                        ],
                    }
                ]
            },
            "parameters": {
                "language_hints": ["zh", "en"],
            },
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                QWEN_MULTIMODAL_GENERATION_URL,
                headers=headers,
                json=payload,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RuntimeError(f"Qwen ASR request failed: {detail}") from exc

        text = self._extract_text(response.json())
        if not text:
            raise RuntimeError("Qwen ASR returned empty transcript.")
        return text

    async def prepare_long_transcription_job(self, file_path: str | Path) -> TranscriptionJob:
        path = Path(file_path).expanduser().resolve()
        self._validate_file(path)
        timestamp = self._now_iso()
        job = TranscriptionJob(
            job_id=f"tx_{uuid.uuid4().hex[:16]}",
            file_path=str(path),
            mode="async",
            status="queued",
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self._write_job(job)

    async def prepare_long_transcription_url_job(self, file_url: str) -> TranscriptionJob:
        normalized_url = self._validate_remote_file_url(file_url)
        timestamp = self._now_iso()
        job = TranscriptionJob(
            job_id=f"tx_{uuid.uuid4().hex[:16]}",
            file_path=normalized_url,
            mode="async",
            status="queued",
            created_at=timestamp,
            updated_at=timestamp,
            source_url=normalized_url,
        )
        return self._write_job(job)

    async def submit_long_transcription_job(self, job_id: str) -> TranscriptionJob:
        job = self.get_job(job_id)
        if job is None:
            raise FileNotFoundError(f"Transcription job not found: {job_id}")
        if job.mode != "async":
            raise ValueError("Only async transcription jobs can be submitted.")

        if job.source_url:
            remote_job_id = await self._submit_remote_job_from_url(job.source_url)
        else:
            raise ValueError(
                "DashScope async transcription requires a public file_url. "
                "Use the from-url endpoint or sync transcription for local uploads."
            )
        return self.update_job(
            job_id,
            status="submitted",
            remote_job_id=remote_job_id,
            error="",
        )

    def publish_local_job_for_async(self, job_id: str) -> TranscriptionJob:
        job = self.get_job(job_id)
        if job is None:
            raise FileNotFoundError(f"Transcription job not found: {job_id}")

        source_path = Path(job.file_path).expanduser().resolve()
        self._validate_file(source_path)
        publisher = build_transcription_publisher(
            self.config,
            published_dir=self.published_dir,
        )
        published_asset = publisher.publish(
            job_id=job.job_id or uuid.uuid4().hex,
            source_path=source_path,
        )
        return self.update_job(
            job_id,
            source_url=published_asset.source_url,
            error="",
        )

    async def retry_long_transcription_job(self, job_id: str) -> TranscriptionJob:
        job = self.get_job(job_id)
        if job is None:
            raise FileNotFoundError(f"Transcription job not found: {job_id}")
        if job.mode != "async":
            raise ValueError("Only async transcription jobs can be retried.")
        if not job.source_url:
            raise ValueError(
                "Only URL-based async transcription jobs can be retried. "
                "Local uploads still require a public file_url."
            )

        if job.transcript_path:
            transcript_path = Path(job.transcript_path)
            try:
                transcript_path.unlink(missing_ok=True)
            except Exception:
                pass

        self.update_job(
            job_id,
            status="queued",
            transcript_path="",
            error="",
            remote_job_id="",
            memory_saved=False,
        )
        return await self.submit_long_transcription_job(job_id)

    async def refresh_long_transcription_job(self, job_id: str) -> TranscriptionJob:
        job = self.get_job(job_id)
        if job is None:
            raise FileNotFoundError(f"Transcription job not found: {job_id}")
        if not job.remote_job_id:
            raise ValueError("Transcription job has not been submitted yet.")

        remote_status = await self._fetch_remote_job_status(job.remote_job_id)
        mapped_status = self._map_remote_status(remote_status)
        transcript_path = job.transcript_path
        error = job.error or ""

        if mapped_status == "completed":
            transcript_text = await self._resolve_remote_transcript(remote_status)
            transcript_path = self._persist_transcript(job.job_id or "", transcript_text)
            error = ""
        elif mapped_status == "failed":
            error = self._extract_remote_error(remote_status) or "Remote transcription failed."

        return self.update_job(
            job_id,
            status=mapped_status,
            transcript_path=transcript_path,
            error=error,
        )

    async def maybe_save_memory(
        self,
        *,
        transcript_text: str,
        headers: dict[str, Any],
        source: str,
    ) -> bool:
        evermem_config = EverMemConfig()
        evermem_config.update_from_headers(headers)
        evermem_service = evermem_config.get_service()
        if not evermem_service:
            return False

        memory_text = self._build_transcript_memory_entry(transcript_text)
        if not memory_text:
            return False

        saved = await evermem_service.add_memory(
            content=memory_text,
            user_id=evermem_config.memory_scope,
            sender=f"{evermem_config.memory_scope}_{source}",
            sender_name="VoiceSpirit Transcription",
        )
        return saved is not None

    async def _submit_remote_job_from_url(self, file_url: str) -> str:
        normalized_url = self._validate_remote_file_url(file_url)
        api_key = self._dashscope_key()
        if not api_key:
            raise ValueError("DashScope API Key missing.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": QWEN_ASR_ASYNC_MODEL,
            "input": {"file_url": normalized_url},
            "parameters": {
                "channel_id": [0],
                "enable_itn": False,
                "enable_words": True,
            },
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self._dashscope_async_base_url()}/services/audio/asr/transcription",
                headers=headers,
                json=payload,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RuntimeError(f"Qwen async ASR submission failed: {detail}") from exc

        output = response.json().get("output", {})
        task_id = output.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise RuntimeError("Qwen async ASR submission returned no task_id.")
        return task_id.strip()

    async def _fetch_remote_job_status(self, remote_job_id: str) -> dict[str, Any]:
        api_key = self._dashscope_key()
        if not api_key:
            raise ValueError("DashScope API Key missing.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.get(
                f"{self._dashscope_async_base_url()}/tasks/{remote_job_id}",
                headers=headers,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RuntimeError(f"Qwen async ASR status query failed: {detail}") from exc
        return response.json()

    async def _resolve_remote_transcript(self, payload: dict[str, Any]) -> str:
        direct_text = self._extract_remote_transcript(payload)
        if direct_text:
            return direct_text

        result = payload.get("result")
        if isinstance(result, dict):
            transcription_url = result.get("transcription_url")
            if isinstance(transcription_url, str) and transcription_url.strip():
                return await self._download_remote_transcript(transcription_url.strip())

        raise RuntimeError("Remote transcription completed without transcript text.")

    async def _download_remote_transcript(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RuntimeError(f"Failed to download transcription result: {detail}") from exc

        data = response.json()
        if isinstance(data, dict):
            text = self._extract_remote_transcript(data)
            if text:
                return text
            results = data.get("results")
            if isinstance(results, list):
                pieces: list[str] = []
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    sentence = item.get("text")
                    if isinstance(sentence, str) and sentence.strip():
                        pieces.append(sentence.strip())
                if pieces:
                    return "\n".join(pieces)
        raise RuntimeError("Downloaded transcription result did not contain transcript text.")

    def _persist_transcript(self, job_id: str, transcript_text: str) -> str:
        transcript_path = self.jobs_dir / f"{job_id}.txt"
        transcript_path.write_text(transcript_text.strip(), encoding="utf-8")
        return str(transcript_path)

    @staticmethod
    def _build_transcript_memory_entry(transcript_text: str) -> str:
        compact = " ".join(str(transcript_text or "").split()).strip()
        if len(compact) < 12:
            return ""
        snippet = compact[:320]
        return f"VoiceSpirit 转写完成。关键信息摘要：{snippet}"

    @staticmethod
    def _map_remote_status(payload: dict[str, Any]) -> str:
        raw = str(
            payload.get("task_status")
            or payload.get("status")
            or payload.get("state")
            or ""
        ).strip().upper()
        if raw in {"RUNNING", "PENDING", "QUEUED", "SUBMITTED"}:
            return "running"
        if raw in {"SUCCEEDED", "SUCCESS", "COMPLETED", "FINISHED"}:
            return "completed"
        if raw in {"FAILED", "ERROR", "CANCELLED"}:
            return "failed"
        return "running"

    @staticmethod
    def _extract_remote_transcript(payload: dict[str, Any]) -> str:
        transcript = payload.get("transcript")
        if isinstance(transcript, str) and transcript.strip():
            return transcript.strip()

        output = payload.get("output")
        if isinstance(output, dict):
            text = output.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

        result = payload.get("result")
        if isinstance(result, dict):
            text = result.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
            sentences = result.get("sentences")
            if isinstance(sentences, list):
                pieces = [
                    str(item.get("text", "")).strip()
                    for item in sentences
                    if isinstance(item, dict) and str(item.get("text", "")).strip()
                ]
                if pieces:
                    return "\n".join(pieces)

        return ""

    @staticmethod
    def _extract_remote_error(payload: dict[str, Any]) -> str:
        for key in ("message", "error", "error_message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        output = payload.get("output")
        if isinstance(output, dict):
            message = output.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        return ""

    @staticmethod
    def _validate_remote_file_url(file_url: str) -> str:
        normalized = str(file_url or "").strip()
        if not normalized:
            raise ValueError("file_url is required.")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https", "oss"}:
            raise ValueError("file_url must use http, https, or oss scheme.")
        return normalized

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        output = data.get("output")
        if not isinstance(output, dict):
            return ""

        direct_text = output.get("text")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()

        choices = output.get("choices")
        if not isinstance(choices, list):
            return ""

        texts: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                texts.append(content.strip())
                continue
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

        return "\n".join(part for part in texts if part).strip()
