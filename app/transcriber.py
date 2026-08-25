"""
Transcribes recorded audio locally with faster-whisper.
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
    segments, _info = model.transcribe(
        str(audio_path),
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
