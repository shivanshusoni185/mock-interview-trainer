"""
Central place for loading settings from .env.
Nothing here talks to a live interviewer or hides anything from anyone --
this app is a solo practice tool: you record your own answer, on your own
machine, and get feedback back.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# Audio recording settings
SAMPLE_RATE = 16000  # Hz, what Whisper expects
CHANNELS = 1


def has_api_key() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-key-here")
