@echo off
echo Starting Voice Spirit 2.0 (Debug Mode)...
echo.

REM Use the Python interpreter from the whisperx environment directly
set PYTHON_PATH=D:\conda\envs\whisperx\python.exe

if not exist "%PYTHON_PATH%" (
    echo ERROR: Python interpreter not found at %PYTHON_PATH%
    pause
    exit /b 1
)

echo Found Python interpreter: %PYTHON_PATH%
echo.

echo Launching Voice Spirit in debug mode...
echo Log output will be displayed here.
echo.

REM Run with unbuffered output so we see logs immediately
call "%PYTHON_PATH%" -u main_new.py

echo.
echo Application exited.
pause
