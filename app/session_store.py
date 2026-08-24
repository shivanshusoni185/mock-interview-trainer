"""
Saves each practice Q&A round (question, transcript, feedback) to a local
JSON file so the user can review progress over time. Everything stays on
the user's own machine -- nothing is uploaded anywhere except the OpenAI
API calls for question generation / feedback text.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from app.config import SESSIONS_DIR

HISTORY_FILE = SESSIONS_DIR / "history.json"


def _load_all() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []


def save_round(role: str, level: str, question: str, transcript: str,
               feedback: str, audio_path: str = "") -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "level": level,
        "question": question,
        "transcript": transcript,
        "feedback": feedback,
        "audio_path": audio_path,
    }
    history = _load_all()
    history.append(entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return entry


def load_history() -> list:
    return list(reversed(_load_all()))
