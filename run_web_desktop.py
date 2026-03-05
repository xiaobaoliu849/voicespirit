#!/usr/bin/env python3
"""Launch VoiceSpirit Web inside a native desktop window (PyWebView)."""

from __future__ import annotations

import atexit
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIST_INDEX = PROJECT_ROOT / "frontend" / "dist" / "index.html"
HEALTH_URL = "http://127.0.0.1:8000/health"
APP_URL = "http://127.0.0.1:8000/app/"


def is_url_available(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= int(resp.status) < 400
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_for_url(url: str, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_url_available(url):
            return True
        time.sleep(0.2)
    return False


def resolve_backend_python() -> str:
    candidates = [
        BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
        BACKEND_DIR / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def stop_backend(proc: Optional[subprocess.Popen[str]]) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def start_backend() -> Optional[subprocess.Popen[str]]:
    if is_url_available(HEALTH_URL):
        # A backend is already running; reuse it.
        return None

    backend_python = resolve_backend_python()
    command = [
        backend_python,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    proc: subprocess.Popen[str] = subprocess.Popen(command, cwd=str(BACKEND_DIR))
    if not wait_for_url(HEALTH_URL, timeout_seconds=30):
        stop_backend(proc)
        raise RuntimeError(
            "Backend failed to start on http://127.0.0.1:8000 within 30 seconds."
        )
    return proc


def ensure_frontend_dist() -> None:
    if FRONTEND_DIST_INDEX.is_file():
        return
    raise FileNotFoundError(
        "frontend/dist/index.html not found.\n"
        "Please run:\n"
        "  cd frontend && npm install && npm run build"
    )


def main() -> int:
    ensure_frontend_dist()
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "pywebview is not installed.\n"
            "Please run:\n"
            "  pip install pywebview"
        ) from exc

    backend_proc = start_backend()
    atexit.register(stop_backend, backend_proc)

    if not wait_for_url(APP_URL, timeout_seconds=10):
        stop_backend(backend_proc)
        raise RuntimeError(
            "Backend is up, but /app is not reachable.\n"
            "Ensure backend/main.py includes /app static mounting and frontend is built."
        )

    webview.create_window(
        title="VoiceSpirit",
        url=APP_URL,
        width=1280,
        height=860,
        min_size=(980, 680),
    )
    try:
        webview.start(debug=False, http_server=False)
    finally:
        stop_backend(backend_proc)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:  # pragma: no cover - launcher runtime fallback
        print(f"[VoiceSpirit Desktop] {err}")
        raise SystemExit(1)
