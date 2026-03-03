@echo off
echo Starting Voice Spirit 2.0...
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

echo Launching Voice Spirit...
call "%PYTHON_PATH%" main_new.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Application failed to start with code %errorlevel%
    echo.
    pause
) else (
    echo.
    echo SUCCESS: Application started successfully
    echo.
    pause
)