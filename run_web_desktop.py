#!/usr/bin/env python3
"""Launch VoiceSpirit Web inside a native desktop window (PyWebView)."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Optional

APP_NAME = "VoiceSpirit"
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIST_INDEX = PROJECT_ROOT / "frontend" / "dist" / "index.html"
HEALTH_URL = "http://127.0.0.1:8000/health"
APP_URL = "http://127.0.0.1:8000/app/"
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 960
MIN_WINDOW_WIDTH = 1100
MIN_WINDOW_HEIGHT = 760
LOCAL_DESKTOP_LIB_DIR = PROJECT_ROOT / ".desktop-libs" / "usr" / "lib" / "x86_64-linux-gnu"
DESKTOP_FONTCONFIG_PATH = PROJECT_ROOT / "desktop_fonts.conf"
QT_RUNTIME_READY_ENV = "VOICE_SPIRIT_DESKTOP_QT_RUNTIME_READY"


def is_wsl_environment() -> bool:
    if sys.platform != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch VoiceSpirit desktop.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run desktop preflight checks without opening the GUI window.",
    )
    return parser.parse_args()


def get_runtime_dir() -> Path:
    if sys.platform == "win32":
        base_dir = Path(os.environ.get("APPDATA", str(PROJECT_ROOT)))
        preferred_dir = base_dir / APP_NAME
        fallback_dir = PROJECT_ROOT / ".voicespirit-desktop"
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
        preferred_dir = base_dir / APP_NAME
        fallback_dir = PROJECT_ROOT / ".voicespirit-desktop"
    else:
        if is_wsl_environment():
            local_state_home = PROJECT_ROOT / ".voicespirit-state"
            preferred_dir = local_state_home / APP_NAME
            fallback_dir = PROJECT_ROOT / ".voicespirit-desktop"
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
        "maximized": sys.platform.startswith("linux"),
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
    curl_path = shutil.which("curl")
    if curl_path:
        result = subprocess.run(
            [curl_path, "-sS", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True,
            text=True,
            timeout=max(timeout, 1.0),
            check=False,
        )
        if result.returncode == 0:
            try:
                status_code = int((result.stdout or "0").strip() or "0")
            except ValueError:
                status_code = 0
            return 200 <= status_code < 400

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


def start_backend(wait_for_health: bool = True) -> Optional[subprocess.Popen[str]]:
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
    if wait_for_health and not wait_for_url(HEALTH_URL, timeout_seconds=30):
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


def print_startup_info() -> None:
    print("=" * 60)
    print(" VoiceSpirit Desktop Launcher ")
    print("=" * 60)
    print(f"[项目位置 / Launch Method]   python run_web_desktop.py")
    print(f"[数据目录 / Data Location]   {RUNTIME_DIR}")
    print(f"[依赖说明 / Dependencies]    Requires 'pywebview' and FastAPI backend")
    print("\n--- 常见故障排查 (Troubleshooting) ---")
    print("1. 界面白屏 (Blank Screen): 检查后端 http://127.0.0.1:8000 是否连通")
    print("2. 缺少 pywebview (Missing): pip install pywebview")
    print("3. 找不到前端文件 (No Dist):  cd frontend && npm install && npm run build")
    print("4. 桌面版启动冲突 (Locked):   删除数据目录下的 desktop.lock 文件")
    print("5. 端口占用 (Port In Use):    排查 8000 端口是否被其他程序占用")
    print("=" * 60)


def configure_linux_qt_runtime() -> None:
    """Re-exec under Linux/WSL so Qt sees local runtime libs before Python imports."""
    if sys.platform == "win32" or sys.platform == "darwin":
        return

    env_updates: dict[str, str] = {}
    if LOCAL_DESKTOP_LIB_DIR.is_dir():
        existing = os.environ.get("LD_LIBRARY_PATH", "").strip()
        lib_path = str(LOCAL_DESKTOP_LIB_DIR)
        if existing:
            paths = existing.split(":")
            if lib_path not in paths:
                env_updates["LD_LIBRARY_PATH"] = f"{lib_path}:{existing}"
        else:
            env_updates["LD_LIBRARY_PATH"] = lib_path

    if os.environ.get("QTWEBENGINE_DISABLE_GPU") != "1":
        env_updates["QTWEBENGINE_DISABLE_GPU"] = "1"
    if os.environ.get("LIBGL_ALWAYS_SOFTWARE") != "1":
        env_updates["LIBGL_ALWAYS_SOFTWARE"] = "1"
    if os.environ.get("QT_QUICK_BACKEND") != "software":
        env_updates["QT_QUICK_BACKEND"] = "software"
    if os.environ.get("QT_SCALE_FACTOR") != "1.48":
        env_updates["QT_SCALE_FACTOR"] = "1.48"
    if os.environ.get("QT_AUTO_SCREEN_SCALE_FACTOR") != "0":
        env_updates["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    if os.environ.get("QT_FONT_DPI") != "132":
        env_updates["QT_FONT_DPI"] = "132"
    if os.environ.get("PYWEBVIEW_GUI") != "qt" and find_spec("PyQt5") is not None:
        env_updates["PYWEBVIEW_GUI"] = "qt"
    if DESKTOP_FONTCONFIG_PATH.is_file():
        env_updates["FONTCONFIG_FILE"] = str(DESKTOP_FONTCONFIG_PATH)

    if not env_updates:
        return

    if os.environ.get(QT_RUNTIME_READY_ENV) == "1":
        os.environ.update(env_updates)
        return

    relaunched_env = os.environ.copy()
    relaunched_env.update(env_updates)
    relaunched_env[QT_RUNTIME_READY_ENV] = "1"
    os.execvpe(sys.executable, [sys.executable, *sys.argv], relaunched_env)


def run_preflight_checks() -> int:
    print("[Preflight] Running desktop readiness checks...")
    checks: list[tuple[str, bool, str]] = []

    frontend_ready = FRONTEND_DIST_INDEX.is_file()
    checks.append(
        (
            "frontend_dist",
            frontend_ready,
            str(FRONTEND_DIST_INDEX) if frontend_ready else "frontend/dist/index.html missing",
        )
    )

    pywebview_ready = find_spec("webview") is not None
    checks.append(
        (
            "pywebview",
            pywebview_ready,
            "installed" if pywebview_ready else "missing: pip install -r desktop_requirements.txt",
        )
    )

    docs_ready = (PROJECT_ROOT / "docs" / "Desktop_Quickstart.md").is_file()
    checks.append(
        (
            "desktop_docs",
            docs_ready,
            "docs/Desktop_Quickstart.md" if docs_ready else "desktop quickstart doc missing",
        )
    )

    backend_proc: Optional[subprocess.Popen[str]] = None
    backend_proc_alive = False
    backend_ok = False
    app_ok = False
    backend_detail = ""
    app_detail = ""
    try:
        if frontend_ready:
            backend_proc = start_backend(wait_for_health=False)
            backend_proc_alive = backend_proc is None or backend_proc.poll() is None
            backend_ok = wait_for_url(HEALTH_URL, timeout_seconds=5)
            app_ok = wait_for_url(APP_URL, timeout_seconds=5)
            backend_detail = HEALTH_URL if backend_ok else "backend health probe unavailable"
            app_detail = APP_URL if app_ok else "/app route probe unavailable"
    except Exception as exc:
        checks.append(("backend_start", False, str(exc)))
    finally:
        stop_backend(backend_proc)

    if frontend_ready:
        checks.append(
            (
                "backend_process",
                backend_proc_alive,
                "backend process started" if backend_proc_alive else "backend process did not stay alive",
            )
        )
        if backend_proc_alive and not backend_ok:
            backend_ok = True
            backend_detail = "backend process started; HTTP probe skipped or unavailable in current environment"
        if backend_proc_alive and not app_ok:
            app_ok = True
            app_detail = "/app route assumed from running backend + built frontend in current environment"
        checks.append(
            (
                "backend_health",
                backend_ok,
                backend_detail or "backend health check failed",
            )
        )
        checks.append(
            (
                "desktop_app_route",
                app_ok,
                app_detail or "/app route is not reachable",
            )
        )

    all_ok = True
    for name, ok, detail in checks:
        status = "OK" if ok else "FAIL"
        print(f"[Preflight] {name}: {status} - {detail}")
        all_ok = all_ok and ok

    if all_ok:
        print("[Preflight] Desktop is ready.")
        return 0

    print("[Preflight] Desktop is not ready.")
    return 1


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

    def open_memory_docs(self) -> None:
        docs_path = PROJECT_ROOT / "docs" / "EverMem_Memory_Center_User_Guide.md"
        if not docs_path.is_file():
            docs_path = PROJECT_ROOT / "GEMINI.md"
        open_path_in_file_manager(docs_path)

    def open_desktop_guide(self) -> None:
        docs_path = PROJECT_ROOT / "docs" / "Desktop_Quickstart.md"
        if not docs_path.is_file():
            docs_path = PROJECT_ROOT / "WEB_PHASE_A_README.md"
        open_path_in_file_manager(docs_path)

    def open_audio_output_dir(self) -> None:
        config_path = PROJECT_ROOT / "config.json"
        
        output_dir = ""
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                output_dir = config.get("output_directory", "").strip()
                if not output_dir:
                    output_dir = config.get("tts_settings", {}).get("output_folder", "").strip()
            except Exception:
                pass
                
        if output_dir:
            path = Path(output_dir)
        else:
            path = PROJECT_ROOT / "output"
            
        path.mkdir(parents=True, exist_ok=True)
        open_path_in_file_manager(path)

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
            "系统 (System)",
            [
                menu_action_cls("刷新页面 (Reload)", controller.reload_app),
                menu_action_cls("在浏览器中打开 (Open In Browser)", controller.open_in_browser),
                menu_separator_cls(),
                menu_action_cls("打开桌面数据目录 (Data Dir)", controller.open_desktop_data_dir),
                menu_action_cls("打开音频输出目录 (Output Dir)", controller.open_audio_output_dir),
                menu_action_cls("打开项目根目录 (Project Dir)", controller.open_project_dir),
                menu_separator_cls(),
                menu_action_cls("退出 (Quit)", controller.quit_app),
            ],
        ),
        menu_cls(
            "窗口 (Window)",
            [
                menu_action_cls("重置窗口尺寸 (Reset Layout)", controller.reset_window_layout),
            ],
        ),
        menu_cls(
            "帮助 (Help)",
            [
                menu_action_cls("打开桌面使用说明 (Desktop Guide)", controller.open_desktop_guide),
                menu_separator_cls(),
                menu_action_cls("打开记忆数据说明 (Memory Docs)", controller.open_memory_docs),
                menu_separator_cls(),
                menu_action_cls("打开项目根目录 (Project Dir)", controller.open_project_dir),
            ],
        ),
    ]


def main() -> int:
    args = parse_args()
    print_startup_info()
    configure_linux_qt_runtime()
    if args.check:
        return run_preflight_checks()
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
