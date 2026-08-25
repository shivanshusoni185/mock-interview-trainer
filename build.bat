@echo off
setlocal
REM Packages Mock Interview Trainer as a standalone Windows .exe using
REM PyInstaller. Must be run ON WINDOWS -- PyInstaller builds for the OS
REM it runs on, so this cannot produce a Windows .exe from Linux/macOS.
REM
REM Usage:
REM   build.bat
REM Output:
REM   dist\MockInterviewTrainer\MockInterviewTrainer.exe

if not exist ".venv" (
    echo No .venv found. Run run.bat first to set up the environment.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Installing build dependencies...
pip install -r requirements.txt -r requirements-build.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install build dependencies.
    pause
    exit /b 1
)

echo.
echo Building standalone .exe (this can take several minutes)...
pyinstaller --noconfirm --clean --windowed --onedir ^
    --name "MockInterviewTrainer" ^
    --collect-all customtkinter ^
    --collect-all sounddevice ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    --collect-all tokenizers ^
    --add-data ".env.example;." ^
    app\main.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. See the output above.
    pause
    exit /b 1
)

echo.
echo Done. Your app is at dist\MockInterviewTrainer\MockInterviewTrainer.exe
echo Copy a .env file (with your API key) into dist\MockInterviewTrainer\ before
echo running it -- see README.md for details.
pause
