"""
Transcribes a recorded answer file to text using faster-whisper, running
locally on your machine. This happens AFTER you finish recording an answer
(not a live streaming transcript during a real interview) -- the practice
flow is: record -> stop -> transcribe -> get feedback.
"""
from pathlib import Path
from functools import lru_cache

from faster_whisper import WhisperModel

from app.config import WHISPER_MODEL_SIZE


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    # compute_type "int8" keeps this usable on a CPU-only Windows laptop.
    # If the user has a CUDA GPU, they can change device="cuda" for speed.
    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(audio_path: Path) -> str:
    model = _get_model()
    segments, _info = model.transcribe(str(audio_path), beam_size=5)
    return " ".join(segment.text.strip() for segment in segments).strip()
