@echo off
setlocal
REM Mock Interview Trainer launcher for Windows.
REM Run this after following the setup steps in README.md.

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: "python" was not found on your PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo and make sure "Add Python to PATH" is checked during install.
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create the virtual environment. See README.md Troubleshooting.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip --quiet

echo Installing/checking dependencies (this can take a few minutes the first time)...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Dependency install failed. Common causes:
    echo   - No internet connection
    echo   - sounddevice/PortAudio issue - see README.md Troubleshooting
    echo   - Very old Python version - use Python 3.10, 3.11, or 3.12
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo.
    echo No .env file found. Copying .env.example to .env -
    echo please open .env and add your API key before continuing.
    copy .env.example .env
    notepad .env
)

echo Starting Mock Interview Trainer...
python -m app.main
if errorlevel 1 (
    echo.
    echo The app exited with an error. See README.md Troubleshooting for common fixes.
)

pause
