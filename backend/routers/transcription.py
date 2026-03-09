from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services.transcription_service import SUPPORTED_AUDIO_SUFFIXES, TranscriptionJob, TranscriptionService

router = APIRouter()
transcription_service = TranscriptionService()


class StructuredErrorDetail(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail


class TranscriptionSyncResponse(BaseModel):
    transcript: str
    memory_saved: bool = False


class TranscriptionJobResponse(BaseModel):
    job_id: str
    remote_job_id: str | None = None
    mode: str
    status: str
    file_name: str
    created_at: str | None = None
    updated_at: str | None = None
    transcript: str | None = None
    has_transcript: bool = False
    transcript_download_url: str | None = None
    source_url: str | None = None
    error: str | None = None
    memory_saved: bool = False


class TranscriptionJobListResponse(BaseModel):
    count: int
    jobs: list[TranscriptionJobResponse]


class TranscriptionUrlJobRequest(BaseModel):
    file_url: str = Field(..., min_length=1, max_length=4000)


def _error(code: str, message: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "meta": meta or {}}


def _validate_upload(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_FILE_MISSING", "No file uploaded."),
        )
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "TRANSCRIPTION_UNSUPPORTED_FORMAT",
                "Unsupported audio format.",
                {"supported_suffixes": sorted(SUPPORTED_AUDIO_SUFFIXES)},
            ),
        )
    return suffix


def _job_to_response(job: TranscriptionJob) -> TranscriptionJobResponse:
    transcript = None
    has_transcript = False
    transcript_download_url = None
    if job.transcript_path:
        path = Path(job.transcript_path)
        if path.is_file():
            transcript = path.read_text(encoding="utf-8")
            has_transcript = True
            transcript_download_url = f"/api/transcription/jobs/{job.job_id}/transcript.txt"
    return TranscriptionJobResponse(
        job_id=job.job_id or "",
        remote_job_id=job.remote_job_id,
        mode=job.mode,
        status=job.status,
        file_name=Path(job.file_path).name,
        created_at=job.created_at,
        updated_at=job.updated_at,
        transcript=transcript,
        has_transcript=has_transcript,
        transcript_download_url=transcript_download_url,
        source_url=job.source_url,
        error=job.error,
        memory_saved=job.memory_saved,
    )


async def _persist_upload(file: UploadFile, target_dir: Path, suffix: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"upload_{uuid.uuid4().hex[:12]}{suffix}"
    content = await file.read()
    target_path.write_bytes(content)
    return target_path


@router.post(
    "/",
    response_model=TranscriptionSyncResponse,
    responses={
        400: {"description": "Invalid transcription upload.", "model": StructuredErrorResponse},
        500: {"description": "Transcription failed.", "model": StructuredErrorResponse},
    },
)
async def transcribe_audio(request: Request, file: UploadFile = File(...)) -> TranscriptionSyncResponse:
    suffix = _validate_upload(file)

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        transcript = await transcription_service.transcribe_file(tmp_path)
        memory_saved = await transcription_service.maybe_save_memory(
            transcript_text=transcript,
            headers=dict(request.headers),
            source="transcription_sync",
        )
        return TranscriptionSyncResponse(transcript=transcript, memory_saved=memory_saved)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_VALIDATION_ERROR", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("TRANSCRIPTION_ERROR", str(exc)),
        ) from exc
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


@router.post(
    "/jobs",
    response_model=TranscriptionJobResponse,
    responses={
        400: {"description": "Invalid transcription job upload.", "model": StructuredErrorResponse},
        500: {"description": "Failed to create transcription job.", "model": StructuredErrorResponse},
    },
)
async def create_transcription_job(file: UploadFile = File(...)) -> TranscriptionJobResponse:
    suffix = _validate_upload(file)

    try:
        upload_path = await _persist_upload(file, transcription_service.jobs_dir / "uploads", suffix)
        job = await transcription_service.prepare_long_transcription_job(upload_path)
        if transcription_service.can_publish_local_async():
            job = transcription_service.publish_local_job_for_async(job.job_id or "")
            job = await transcription_service.submit_long_transcription_job(job.job_id or "")
        else:
            job = transcription_service.update_job(
                job.job_id or "",
                status="uploaded",
                error=(
                    "Local async uploads are staged only. "
                    "Configure transcription_settings.public_base_url or use "
                    "/api/transcription/jobs/from-url for true DashScope async transcription."
                ),
            )
        return _job_to_response(job)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_JOB_BAD_REQUEST", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("TRANSCRIPTION_JOB_CREATE_FAILED", str(exc)),
        ) from exc


@router.post(
    "/jobs/from-url",
    response_model=TranscriptionJobResponse,
    responses={
        400: {"description": "Invalid transcription job URL.", "model": StructuredErrorResponse},
        500: {"description": "Failed to create URL transcription job.", "model": StructuredErrorResponse},
    },
)
async def create_transcription_job_from_url(payload: TranscriptionUrlJobRequest) -> TranscriptionJobResponse:
    try:
        job = await transcription_service.prepare_long_transcription_url_job(payload.file_url)
        job = await transcription_service.submit_long_transcription_job(job.job_id or "")
        return _job_to_response(job)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_JOB_BAD_REQUEST", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("TRANSCRIPTION_JOB_CREATE_FAILED", str(exc)),
        ) from exc


@router.get(
    "/jobs",
    response_model=TranscriptionJobListResponse,
    responses={
        400: {"description": "Invalid transcription job query.", "model": StructuredErrorResponse},
        500: {"description": "Failed to list transcription jobs.", "model": StructuredErrorResponse},
    },
)
async def list_transcription_jobs(
    status: str | None = Query(
        default=None,
        description="Comma-separated status filter, e.g. completed,running,failed",
    ),
    limit: int = Query(default=20, ge=1, le=200),
) -> TranscriptionJobListResponse:
    try:
        statuses = {
            item.strip().lower()
            for item in str(status or "").split(",")
            if item.strip()
        }
        jobs = transcription_service.list_jobs(statuses=statuses, limit=limit)
        return TranscriptionJobListResponse(
            count=len(jobs),
            jobs=[_job_to_response(job) for job in jobs],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_JOB_BAD_REQUEST", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("TRANSCRIPTION_JOB_LIST_FAILED", str(exc)),
        ) from exc


@router.get(
    "/jobs/{job_id}",
    response_model=TranscriptionJobResponse,
    responses={
        404: {"description": "Transcription job not found.", "model": StructuredErrorResponse},
        400: {"description": "Invalid job request.", "model": StructuredErrorResponse},
        500: {"description": "Failed to fetch transcription job.", "model": StructuredErrorResponse},
    },
)
async def get_transcription_job(
    request: Request,
    job_id: str,
    refresh: bool = Query(default=True, description="Refresh remote status before returning."),
) -> TranscriptionJobResponse:
    job = transcription_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=_error("TRANSCRIPTION_JOB_NOT_FOUND", f"Transcription job not found: {job_id}"),
        )

    try:
        if refresh and job.remote_job_id and job.status not in {"completed", "failed"}:
            job = await transcription_service.refresh_long_transcription_job(job_id)
        else:
            job = transcription_service.get_job(job_id) or job

        if (
            job.status == "completed"
            and not job.memory_saved
            and job.transcript_path
            and Path(job.transcript_path).is_file()
        ):
            transcript_text = Path(job.transcript_path).read_text(encoding="utf-8")
            memory_saved = await transcription_service.maybe_save_memory(
                transcript_text=transcript_text,
                headers=dict(request.headers),
                source="transcription_async",
            )
            if memory_saved:
                job = transcription_service.update_job(job_id, memory_saved=True)
        return _job_to_response(job)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_JOB_BAD_REQUEST", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("TRANSCRIPTION_JOB_GET_FAILED", str(exc)),
        ) from exc


@router.post(
    "/jobs/{job_id}/retry",
    response_model=TranscriptionJobResponse,
    responses={
        404: {"description": "Transcription job not found.", "model": StructuredErrorResponse},
        400: {"description": "Invalid retry request.", "model": StructuredErrorResponse},
        500: {"description": "Failed to retry transcription job.", "model": StructuredErrorResponse},
    },
)
async def retry_transcription_job(job_id: str) -> TranscriptionJobResponse:
    try:
        job = await transcription_service.retry_long_transcription_job(job_id)
        return _job_to_response(job)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error("TRANSCRIPTION_JOB_NOT_FOUND", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error("TRANSCRIPTION_JOB_BAD_REQUEST", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("TRANSCRIPTION_JOB_RETRY_FAILED", str(exc)),
        ) from exc


@router.get(
    "/jobs/{job_id}/transcript.txt",
    responses={
        404: {"description": "Transcript file not found.", "model": StructuredErrorResponse},
    },
)
async def download_transcription_job_transcript(job_id: str) -> Response:
    job = transcription_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=_error("TRANSCRIPTION_JOB_NOT_FOUND", f"Transcription job not found: {job_id}"),
        )

    transcript_path = Path(job.transcript_path or "")
    if not transcript_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=_error("TRANSCRIPTION_TRANSCRIPT_NOT_FOUND", f"Transcript not found for job: {job_id}"),
        )

    response = Response(
        content=transcript_path.read_bytes(),
        media_type="text/plain; charset=utf-8",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{job_id}.txt"'
    return response
