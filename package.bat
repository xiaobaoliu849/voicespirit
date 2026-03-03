@echo off
echo Starting packaging...

REM Copy necessary files to root directory
copy /Y resources\donation\donate_qr.png .
copy /Y resources\logo.png .

REM Clean old builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Set UTF-8 encoding
chcp 65001 >nul

REM Execute packaging
pyinstaller --clean --noconfirm --name VoiceWizard --windowed --icon=logo.ico --add-data="logo.ico;." --add-data="logo.png;." --add-data="donate_qr.png;." --add-data="resources;resources" --hidden-import=PySide6.QtSvgWidgets --hidden-import=PySide6.QtMultimedia --hidden-import=PySide6.QtMultimediaWidgets --hidden-import=pydub --hidden-import=tempfile --hidden-import=edge_tts --hidden-import=aiohttp --hidden-import=asyncio --hidden-import=resources_rc --hidden-import=miniaudio main.py

if %errorlevel% neq 0 (
    echo Packaging failed, error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo Packaging successful!
echo Test method:
echo 1. Go to dist\VoiceWizard directory
echo 2. Run VoiceWizard.exe

pause
