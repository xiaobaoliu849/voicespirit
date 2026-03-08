#!/usr/bin/env python3
"""Launch VoiceSpirit Web inside a native desktop window (PyWebView)."""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Optional

APP_NAME = "VoiceSpirit"
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIST_INDEX = PROJECT_ROOT / "frontend" / "dist" / "index.html"
HEALTH_URL = "http://127.0.0.1:8000/health"
APP_URL = "http://127.0.0.1:8000/app/"
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 860
MIN_WINDOW_WIDTH = 980
MIN_WINDOW_HEIGHT = 680


def get_runtime_dir() -> Path:
    if sys.platform == "win32":
        base_dir = Path(os.environ.get("APPDATA", str(PROJECT_ROOT)))
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        base_dir = Path(xdg_state_home) if xdg_state_home else Path.home() / ".local" / "state"

    preferred_dir = base_dir / APP_NAME
    fallback_dir = PROJECT_ROOT / ".voicespirit-desktop"

    for candidate in (preferred_dir, fallback_dir):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue

    raise RuntimeError("Unable to create a writable runtime directory for VoiceSpirit Desktop.")


RUNTIME_DIR = get_runtime_dir()
WINDOW_STATE_PATH = RUNTIME_DIR / "desktop_window.json"
WEBVIEW_STORAGE_DIR = RUNTIME_DIR / "webview"
LOCK_PATH = RUNTIME_DIR / "desktop.lock"


class SingleInstanceLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle = None

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("a+", encoding="utf-8")
        self._handle.seek(0)

        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.release()
            raise RuntimeError(f"{APP_NAME} Desktop is already running.") from exc

        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(str(os.getpid()))
        self._handle.flush()

    def release(self) -> None:
        if self._handle is None:
            return

        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self._handle.close()
            self._handle = None


def default_window_state() -> dict[str, Any]:
    return {
        "width": DEFAULT_WINDOW_WIDTH,
        "height": DEFAULT_WINDOW_HEIGHT,
        "x": None,
        "y": None,
        "maximized": False,
    }


def load_window_state() -> dict[str, Any]:
    state = default_window_state()
    if not WINDOW_STATE_PATH.is_file():
        return state

    try:
        raw_state = json.loads(WINDOW_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return state

    if not isinstance(raw_state, dict):
        return state

    if isinstance(raw_state.get("width"), int) and raw_state["width"] >= MIN_WINDOW_WIDTH:
        state["width"] = raw_state["width"]
    if isinstance(raw_state.get("height"), int) and raw_state["height"] >= MIN_WINDOW_HEIGHT:
        state["height"] = raw_state["height"]
    if isinstance(raw_state.get("x"), int):
        state["x"] = raw_state["x"]
    if isinstance(raw_state.get("y"), int):
        state["y"] = raw_state["y"]
    if isinstance(raw_state.get("maximized"), bool):
        state["maximized"] = raw_state["maximized"]

    return state


def save_window_state(state: dict[str, Any]) -> None:
    WINDOW_STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def attach_window_state_tracking(window: Any, state: dict[str, Any]) -> None:
    def on_resized(width: int, height: int) -> None:
        if state["maximized"]:
            return
        state["width"] = max(int(width), MIN_WINDOW_WIDTH)
        state["height"] = max(int(height), MIN_WINDOW_HEIGHT)

    def on_moved(x: int, y: int) -> None:
        if state["maximized"]:
            return
        state["x"] = int(x)
        state["y"] = int(y)

    def on_maximized() -> None:
        state["maximized"] = True

    def on_restored() -> None:
        state["maximized"] = False

    def on_closed() -> None:
        save_window_state(state)

    window.events.resized += on_resized
    window.events.moved += on_moved
    window.events.maximized += on_maximized
    window.events.restored += on_restored
    window.events.closed += on_closed


def open_path_in_file_manager(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
        return
    subprocess.Popen(["xdg-open", str(path)])


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


class DesktopController:
    def __init__(self, window_state: dict[str, Any]) -> None:
        self.window_state = window_state
        self.window: Any | None = None
        self.webview_module: Any | None = None

    def attach_window(self, window: Any, webview_module: Any) -> None:
        self.window = window
        self.webview_module = webview_module

    def reload_app(self) -> None:
        if self.window is None:
            return
        self.window.load_url(APP_URL)

    def reset_window_layout(self) -> None:
        self.window_state.clear()
        self.window_state.update(default_window_state())

        if self.window is None:
            save_window_state(self.window_state)
            return

        self.window.restore()
        self.window.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        if self.webview_module is not None:
            screens = self.webview_module.screens()
            if screens:
                screen = screens[0]
                x = screen.x + max((screen.width - DEFAULT_WINDOW_WIDTH) // 2, 0)
                y = screen.y + max((screen.height - DEFAULT_WINDOW_HEIGHT) // 2, 0)
                self.window.move(x, y)
                self.window_state["x"] = x
                self.window_state["y"] = y

        save_window_state(self.window_state)

    def open_in_browser(self) -> None:
        webbrowser.open(APP_URL)

    def open_desktop_data_dir(self) -> None:
        open_path_in_file_manager(RUNTIME_DIR)

    def open_project_dir(self) -> None:
        open_path_in_file_manager(PROJECT_ROOT)

    def quit_app(self) -> None:
        if self.window is None:
            return
        self.window.destroy()


def build_application_menu(
    controller: DesktopController,
    menu_cls: Any,
    menu_action_cls: Any,
    menu_separator_cls: Any,
) -> list[Any]:
    return [
        menu_cls(
            "VoiceSpirit",
            [
                menu_action_cls("Reload App", controller.reload_app),
                menu_action_cls("Open In Browser", controller.open_in_browser),
                menu_separator_cls(),
                menu_action_cls("Open Desktop Data Folder", controller.open_desktop_data_dir),
                menu_action_cls("Open Project Folder", controller.open_project_dir),
                menu_separator_cls(),
                menu_action_cls("Quit", controller.quit_app),
            ],
        ),
        menu_cls(
            "Window",
            [
                menu_action_cls("Reset Window Layout", controller.reset_window_layout),
            ],
        ),
        menu_cls(
            "Help",
            [
                menu_action_cls("Open Project Folder", controller.open_project_dir),
            ],
        ),
    ]


def main() -> int:
    ensure_frontend_dist()
    instance_lock = SingleInstanceLock(LOCK_PATH)
    instance_lock.acquire()
    atexit.register(instance_lock.release)

    try:
        import webview
        from webview.menu import Menu, MenuAction, MenuSeparator
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

    WEBVIEW_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    window_state = load_window_state()
    controller = DesktopController(window_state)
    window = webview.create_window(
        title="VoiceSpirit",
        url=APP_URL,
        width=window_state["width"],
        height=window_state["height"],
        x=window_state["x"],
        y=window_state["y"],
        maximized=window_state["maximized"],
        min_size=(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT),
        menu=build_application_menu(controller, Menu, MenuAction, MenuSeparator),
    )
    controller.attach_window(window, webview)
    attach_window_state_tracking(window, window_state)
    try:
        webview.start(
            debug=False,
            http_server=False,
            private_mode=False,
            storage_path=str(WEBVIEW_STORAGE_DIR),
        )
    finally:
        stop_backend(backend_proc)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:  # pragma: no cover - launcher runtime fallback
        print(f"[VoiceSpirit Desktop] {err}")
        raise SystemExit(1)
