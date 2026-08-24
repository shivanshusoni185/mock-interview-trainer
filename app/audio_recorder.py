"""
Records audio from the user's own microphone only (not system/loopback audio,
not the other side of a call). This app never captures another person's voice
or a live meeting -- it's you, alone, practicing an answer out loud.
"""
import threading
import queue
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from app.config import SAMPLE_RATE, CHANNELS


class AudioRecorder:
    def __init__(self):
        self._stream = None
        self._queue: queue.Queue = queue.Queue()
        self._frames = []
        self._recording = False
        self._lock = threading.Lock()
        self.start_time = None
        self.elapsed_seconds = 0.0

    def _callback(self, indata, frames, time_info, status):
        if status:
            # Non-fatal audio warnings (e.g. buffer overflow) - just log them.
            print(f"[audio warning] {status}")
        self._queue.put(indata.copy())

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self.start_time = time.time()
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
            threading.Thread(target=self._drain_queue, daemon=True).start()

    def _drain_queue(self):
        while self._recording:
            try:
                chunk = self._queue.get(timeout=0.2)
                self._frames.append(chunk)
            except queue.Empty:
                continue

    def stop_and_save(self, out_path: Path) -> Path:
        with self._lock:
            if not self._recording:
                raise RuntimeError("Recorder was not running.")
            self._recording = False
            self.elapsed_seconds = time.time() - (self.start_time or time.time())
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        # Drain anything left in the queue
        while not self._queue.empty():
            self._frames.append(self._queue.get())

        if not self._frames:
            audio = np.zeros((1, CHANNELS), dtype="float32")
        else:
            audio = np.concatenate(self._frames, axis=0)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), audio, SAMPLE_RATE)
        return out_path

    @property
    def is_recording(self) -> bool:
        return self._recording

    @staticmethod
    def list_input_devices():
        """Return available microphone devices, for a settings dropdown."""
        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"]}
            for i, d in enumerate(devices)
            if d.get("max_input_channels", 0) > 0
        ]
