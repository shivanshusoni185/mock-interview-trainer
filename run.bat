@echo off
REM Mock Interview Trainer launcher for Windows.
REM Run this after following the setup steps in README.md.

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing/checking dependencies...
pip install -r requirements.txt --quiet

if not exist ".env" (
    echo.
    echo No .env file found. Copying .env.example to .env -
    echo please open .env and add your OpenAI API key before continuing.
    copy .env.example .env
    notepad .env
)

echo Starting Mock Interview Trainer...
python -m app.main

pause
