@echo off
setlocal

echo Starting VoiceSpirit Web (Phase B start)...

echo [1/2] Starting backend on http://127.0.0.1:8000
start "VoiceSpirit Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting frontend on http://127.0.0.1:5173
start "VoiceSpirit Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Done.
exit /b 0
