from __future__ import annotations

import mimetypes
import shutil
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import urlparse

from .config_loader import BackendConfig


@dataclass(slots=True)
class PublishedTranscriptionAsset:
    source_url: str
    published_path: Path


def _is_boto3_available() -> bool:
    return find_spec("boto3") is not None


def _create_s3_client(
    *,
    endpoint_url: str,
    region_name: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
):
    import boto3  # type: ignore

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        region_name=region_name or None,
        aws_access_key_id=aws_access_key_id or None,
        aws_secret_access_key=aws_secret_access_key or None,
    )


class TranscriptionPublisher:
    def is_enabled(self) -> bool:
        raise NotImplementedError

    def publish(self, *, job_id: str, source_path: Path) -> PublishedTranscriptionAsset:
        raise NotImplementedError


class DisabledTranscriptionPublisher(TranscriptionPublisher):
    def __init__(self, reason: str = ""):
        self.reason = reason.strip()

    def is_enabled(self) -> bool:
        return False

    def publish(self, *, job_id: str, source_path: Path) -> PublishedTranscriptionAsset:
        _ = (job_id, source_path)
        detail = self.reason or "Transcription upload publishing is disabled."
        raise ValueError(detail)


class StaticTranscriptionPublisher(TranscriptionPublisher):
    def __init__(self, *, public_base_url: str, published_dir: Path):
        normalized_url = str(public_base_url or "").strip().rstrip("/")
        if not normalized_url:
            raise ValueError("transcription_settings.public_base_url is not configured.")
        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("transcription_settings.public_base_url must use http or https.")
        self.public_base_url = normalized_url
        self.published_dir = published_dir
        self.published_dir.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        return True

    def publish(self, *, job_id: str, source_path: Path) -> PublishedTranscriptionAsset:
        published_name = f"{job_id}{source_path.suffix.lower()}"
        published_path = self.published_dir / published_name
        shutil.copy2(source_path, published_path)
        source_url = f"{self.public_base_url}/public/transcription/{published_name}"
        return PublishedTranscriptionAsset(
            source_url=source_url,
            published_path=published_path,
        )


class S3TranscriptionPublisher(TranscriptionPublisher):
    def __init__(
        self,
        *,
        bucket: str,
        key_prefix: str,
        public_base_url: str,
        endpoint_url: str,
        region_name: str,
        access_key_id: str,
        secret_access_key: str,
    ):
        self.bucket = bucket.strip()
        self.key_prefix = key_prefix.strip().strip("/")
        self.public_base_url = public_base_url.strip().rstrip("/")
        self.endpoint_url = endpoint_url.strip()
        self.region_name = region_name.strip()
        self.access_key_id = access_key_id.strip()
        self.secret_access_key = secret_access_key.strip()

        if not self.bucket:
            raise ValueError("transcription_settings.s3_bucket is required for s3 upload mode.")
        if not self.public_base_url:
            raise ValueError(
                "transcription_settings.public_base_url is required for s3 upload mode."
            )
        parsed = urlparse(self.public_base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("transcription_settings.public_base_url must use http or https.")

    def is_enabled(self) -> bool:
        return True

    def publish(self, *, job_id: str, source_path: Path) -> PublishedTranscriptionAsset:
        key = f"{self.key_prefix}/{job_id}{source_path.suffix.lower()}" if self.key_prefix else f"{job_id}{source_path.suffix.lower()}"
        client = _create_s3_client(
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        content_type, _ = mimetypes.guess_type(str(source_path))
        extra_args = {"ContentType": content_type or "application/octet-stream"}
        client.upload_file(str(source_path), self.bucket, key, ExtraArgs=extra_args)
        source_url = f"{self.public_base_url}/{key}"
        return PublishedTranscriptionAsset(
            source_url=source_url,
            published_path=source_path,
        )


def build_transcription_publisher(
    config: BackendConfig,
    *,
    published_dir: Path,
) -> TranscriptionPublisher:
    config.reload()
    settings = config.get_all().get("transcription_settings", {})
    if not isinstance(settings, dict):
        return DisabledTranscriptionPublisher("transcription_settings is missing.")

    upload_mode = str(settings.get("upload_mode", "static")).strip().lower() or "static"
    public_base_url = str(settings.get("public_base_url", "")).strip()

    if upload_mode in {"disabled", "off", "none"}:
        return DisabledTranscriptionPublisher("transcription upload publishing is disabled.")
    if upload_mode == "static":
        if not public_base_url:
            return DisabledTranscriptionPublisher(
                "transcription_settings.public_base_url is not configured."
            )
        return StaticTranscriptionPublisher(
            public_base_url=public_base_url,
            published_dir=published_dir,
        )
    if upload_mode == "s3":
        if not _is_boto3_available():
            return DisabledTranscriptionPublisher(
                "boto3 is not installed for transcription s3 upload mode."
            )
        return S3TranscriptionPublisher(
            bucket=str(settings.get("s3_bucket", "")).strip(),
            key_prefix=str(settings.get("s3_key_prefix", "transcription")).strip(),
            public_base_url=public_base_url,
            endpoint_url=str(settings.get("s3_endpoint_url", "")).strip(),
            region_name=str(settings.get("s3_region", "")).strip(),
            access_key_id=str(settings.get("s3_access_key_id", "")).strip(),
            secret_access_key=str(settings.get("s3_secret_access_key", "")).strip(),
        )
    return DisabledTranscriptionPublisher(
        f"Unsupported transcription upload mode: {upload_mode}"
    )
