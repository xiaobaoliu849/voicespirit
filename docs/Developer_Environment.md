# Developer Environment

Use one Python environment per workspace and keep the editor, terminal, and type checker on that same environment.

## Recommended setup

This repository works best in one of these two modes:

1. Windows-first desktop workflow
2. WSL-first backend/frontend workflow

Do not mix them inside the same VS Code window.

## Windows-first

Use this when working on desktop behavior, `run_web_desktop.bat`, or Windows packaging.

- Open `D:\voicespirit` in Windows VS Code
- Select interpreter `D:\voicespirit\backend\.venv\Scripts\python.exe`
- Install backend packages into that same environment

## WSL-first

Use this when working mainly on backend or frontend code from WSL.

- Open `/mnt/d/voicespirit` with VS Code Remote - WSL
- Select interpreter `/mnt/d/voicespirit/backend/.venv/bin/python`
- Install backend packages into that same environment

## Why the Problems panel explodes

If the editor opens the project from one side but analyzes it with the other side's interpreter, the checker may see:

- empty search roots
- empty site-package paths
- many false import errors

Typical examples are `websockets`, `PySide6`, `openai`, or project imports under `app` and `backend`.

## Project default

Workspace settings add these source roots for analysis:

- repository root
- `backend`

Select the interpreter manually based on where VS Code is running.

Note: the current `backend/.venv` in this repository was created from WSL and contains `bin/python`, not `Scripts/python.exe`. Windows VS Code cannot use that environment directly.
