"""Capture microphone audio, with optional Windows speaker loopback."""
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
        self._system_frames = []
        self._system_thread = None
        self._capture_system_audio = False
        self._recording = False
        self._lock = threading.Lock()
        self.start_time = None
        self.elapsed_seconds = 0.0
        self.input_level = 0.0

    def _callback(self, indata, frames, time_info, status):
        if status:
            # Non-fatal audio warnings (e.g. buffer overflow) - just log them.
            print(f"[audio warning] {status}")
        with self._lock:
            self.input_level = float(np.max(np.abs(indata))) if indata.size else 0.0
        self._queue.put(indata.copy())

    def _drain_queue(self):
        while self._recording:
            try:
                chunk = self._queue.get(timeout=0.2)
                with self._lock:
                    self._frames.append(chunk)
            except queue.Empty:
                continue

    def _capture_loopback(self):
        try:
            import soundcard as sc

            speaker = sc.default_speaker()
            loopbacks = sc.all_microphones(include_loopback=True)
            loopback = next(
                (device for device in loopbacks if speaker.name in device.name),
                next((device for device in loopbacks if "loopback" in device.name.lower()), None),
            )
            if loopback is None:
                raise RuntimeError("No Windows loopback device is available.")
            with loopback.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS) as recorder:
                while self._recording:
                    chunk = recorder.record(numframes=1024)
                    with self._lock:
                        self._system_frames.append(np.asarray(chunk, dtype="float32"))
        except Exception as exc:  # noqa: BLE001 - report through stop status
            print(f"[system audio warning] {exc}")

    def start(self, capture_system_audio: bool = False, device_index=None):
        with self._lock:
            if not self._recording:
                self._frames = []
                self._system_frames = []
                self.input_level = 0.0
                self._capture_system_audio = capture_system_audio
                self._recording = True
                self.start_time = time.time()
                self._stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="float32",
                    device=device_index,
                    callback=self._callback,
                )
                self._stream.start()
                threading.Thread(target=self._drain_queue, daemon=True).start()
                if capture_system_audio:
                    self._system_thread = threading.Thread(target=self._capture_loopback, daemon=True)
                    self._system_thread.start()

    def snapshot_to_wav(self, out_path: Path) -> Path:
        """Write a stable copy of audio captured so far for live transcription."""
        with self._lock:
            mic_frames = list(self._frames)
            system_frames = list(self._system_frames)
        mic_audio = np.concatenate(mic_frames, axis=0) if mic_frames else np.zeros((1, CHANNELS), dtype="float32")
        system_audio = np.concatenate(system_frames, axis=0) if system_frames else None
        if system_audio is not None and len(system_audio):
            sample_count = min(len(mic_audio), len(system_audio))
            audio = np.clip((mic_audio[:sample_count] + system_audio[:sample_count]) / 2, -1, 1)
        else:
            audio = mic_audio
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), audio, SAMPLE_RATE)
        return out_path

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

        with self._lock:
            mic_audio = np.concatenate(self._frames, axis=0) if self._frames else np.zeros((1, CHANNELS), dtype="float32")
            system_audio = np.concatenate(self._system_frames, axis=0) if self._system_frames else None

        if system_audio is not None and len(system_audio):
            sample_count = min(len(mic_audio), len(system_audio))
            audio = np.clip((mic_audio[:sample_count] + system_audio[:sample_count]) / 2, -1, 1)
        else:
            audio = mic_audio

        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), audio, SAMPLE_RATE)
        return out_path

    @property
    def is_recording(self) -> bool:
        return self._recording

    @staticmethod
    def list_input_devices():
        """Return available input devices, including virtual meeting devices."""
        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"], "channels": d.get("max_input_channels", 0)}
            for i, d in enumerate(devices)
            if d.get("max_input_channels", 0) > 0
        ]

    @staticmethod
    def input_level(device_index=None) -> float:
        """Capture a short sample and return its peak level for diagnostics."""
        recording = sd.rec(int(SAMPLE_RATE * 0.25), samplerate=SAMPLE_RATE,
                           channels=CHANNELS, dtype="float32", device=device_index)
        sd.wait()
        return float(np.max(np.abs(recording))) if recording.size else 0.0
