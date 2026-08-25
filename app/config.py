"""
Central place for loading settings from .env.
Nothing here talks to a live interviewer or hides anything from anyone --
this app is a solo practice tool: you record your own answer, on your own
machine, and get feedback back.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built .exe: keep .env and sessions/ next to the
    # executable, not inside the bundle's internal (temporary) unpack folder.
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT_DIR / ".env")

# Which LLM backend to use for question generation + feedback: "openai" or "anthropic".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# Audio recording settings
SAMPLE_RATE = 16000  # Hz, what Whisper expects
CHANNELS = 1

# Max characters of pasted/loaded resume or job-description text to send to the
# LLM when tailoring a question, to keep prompts (and cost) bounded.
MAX_CONTEXT_CHARS = 6000


def has_api_key() -> bool:
    if LLM_PROVIDER == "anthropic":
        return bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "sk-ant-your-key-here")
    return bool(OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-key-here")
