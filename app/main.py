"""
Mock Interview Trainer - main desktop application (Windows-friendly, but
runs anywhere Python + Tk run).

Flow: configure a practice session, capture permitted audio, see a live local
transcript, then receive post-session coaching.

Nothing here listens to a live call, hides itself from screen-sharing, or
feeds answers to you while you're being asked a real question by someone
else. It's an offline-first solo practice loop.
"""
import threading
import time
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.config import SESSIONS_DIR, LLM_PROVIDER, has_api_key
from app.audio_recorder import AudioRecorder
from app.transcriber import transcribe
from app.llm_client import generate_question, get_feedback, get_direct_answer
from app.session_store import save_round, load_history
from app.resume_context import load_text_from_file, SUPPORTED_EXTENSIONS
from app.dashboard import DashboardWindow

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ROLE_OPTIONS = [
    "Software Engineer", "Data Scientist", "Product Manager",
    "DevOps Engineer", "Frontend Engineer", "Backend Engineer",
    "ML Engineer", "QA Engineer", "Other (type topic)",
]
LEVEL_OPTIONS = ["Intern", "Junior", "Mid-level", "Senior", "Staff+"]


class MockInterviewApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mock Interview Trainer")
        self.geometry("820x640")
        self.minsize(700, 560)

        self.recorder = AudioRecorder()
        self.current_question = ""
        self.current_audio_path: Path | None = None
        self.timer_running = False
        self.live_transcript_running = False
        self.live_transcription_in_progress = False
        self.input_devices = []
        self.input_device_map = {}

        self._build_layout()

        if not has_api_key():
            provider = "Anthropic" if LLM_PROVIDER == "anthropic" else "OpenAI"
            self._set_status(
                f"⚠ No {provider} API key found. Copy .env.example to .env and add your key.",
                warn=True,
            )

    # ---------- UI construction ----------

    def _build_layout(self):
        pad = {"padx": 16, "pady": 8}

        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", **pad)

        header = ctk.CTkLabel(
            header_row, text="🎤 Mock Interview Trainer",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        header.pack(side="left")

        ctk.CTkButton(
            header_row, text="📊 Progress Dashboard", width=170,
            command=self._on_open_dashboard,
        ).pack(side="right")

        # --- Setup row: role / level / topic ---
        setup_frame = ctk.CTkFrame(self)
        setup_frame.pack(fill="x", **pad)

        ctk.CTkLabel(setup_frame, text="Role").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        self.role_var = ctk.StringVar(value=ROLE_OPTIONS[0])
        ctk.CTkOptionMenu(setup_frame, values=ROLE_OPTIONS, variable=self.role_var,
                           width=180).grid(row=0, column=1, padx=8, pady=8)

        ctk.CTkLabel(setup_frame, text="Level").grid(row=0, column=2, padx=8, pady=8, sticky="w")
        self.level_var = ctk.StringVar(value=LEVEL_OPTIONS[2])
        ctk.CTkOptionMenu(setup_frame, values=LEVEL_OPTIONS, variable=self.level_var,
                           width=140).grid(row=0, column=3, padx=8, pady=8)

        ctk.CTkLabel(setup_frame, text="Topic (optional)").grid(row=0, column=4, padx=8, pady=8, sticky="w")
        self.topic_entry = ctk.CTkEntry(setup_frame, placeholder_text="e.g. system design, SQL, leadership")
        self.topic_entry.grid(row=0, column=5, padx=8, pady=8, sticky="ew")
        setup_frame.grid_columnconfigure(5, weight=1)

        # --- Optional resume / job description tailoring ---
        tailor_frame = ctk.CTkFrame(self)
        tailor_frame.pack(fill="x", **pad)

        tailor_header = ctk.CTkFrame(tailor_frame, fg_color="transparent")
        tailor_header.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(
            tailor_header, text="Tailor to a role (optional)",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            tailor_header, text="Load resume file…", width=140,
            command=lambda: self._on_load_context_file(self.resume_box),
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            tailor_header, text="Load job description file…", width=170,
            command=lambda: self._on_load_context_file(self.jd_box),
        ).pack(side="right")

        boxes_row = ctk.CTkFrame(tailor_frame, fg_color="transparent")
        boxes_row.pack(fill="x", padx=8, pady=8)
        boxes_row.grid_columnconfigure(0, weight=1)
        boxes_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(boxes_row, text="Resume text").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(boxes_row, text="Job description text").grid(row=0, column=1, sticky="w")

        self.resume_box = ctk.CTkTextbox(boxes_row, height=60, wrap="word")
        self.resume_box.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.jd_box = ctk.CTkTextbox(boxes_row, height=60, wrap="word")
        self.jd_box.grid(row=1, column=1, sticky="ew", padx=(6, 0))

        self.get_question_btn = ctk.CTkButton(
            self, text="🎯 Get a Question", command=self._on_get_question
        )
        self.get_question_btn.pack(**pad)

        # --- Question display ---
        self.question_box = ctk.CTkTextbox(self, height=80, wrap="word")
        self.question_box.pack(fill="x", **pad)
        self.question_box.insert("1.0", "Click \"Get a Question\" to begin.")
        self.question_box.configure(state="disabled")

        # --- Recording controls ---
        rec_frame = ctk.CTkFrame(self)
        rec_frame.pack(fill="x", **pad)

        self.record_btn = ctk.CTkButton(
            rec_frame, text="▶ Start Listening", fg_color="#c0392b",
            hover_color="#922b21", command=self._on_toggle_record,
        )
        self.record_btn.pack(side="left", padx=8, pady=8)

        self.input_device_var = ctk.StringVar(value="Default microphone")
        self.input_device_menu = ctk.CTkOptionMenu(
            rec_frame, variable=self.input_device_var, values=["Default microphone"], width=230,
        )
        self.input_device_menu.pack(side="left", padx=8)
        ctk.CTkButton(
            rec_frame, text="Test microphone", width=120, command=self._on_test_microphone,
        ).pack(side="left", padx=8)

        self.system_audio_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            rec_frame,
            text="Capture system audio (consent required)",
            variable=self.system_audio_var,
        ).pack(side="left", padx=8)

        self.timer_label = ctk.CTkLabel(rec_frame, text="00:00")
        self.timer_label.pack(side="left", padx=8)
        self.level_label = ctk.CTkLabel(rec_frame, text="Input level: --")
        self.level_label.pack(side="left", padx=8)

        # --- Transcript + feedback ---
        ctk.CTkLabel(self, text="Transcript").pack(anchor="w", padx=16)
        self.transcript_box = ctk.CTkTextbox(self, height=80, wrap="word")
        self.transcript_box.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Suggested Answer").pack(anchor="w", padx=16)
        self.answer_box = ctk.CTkTextbox(self, height=110, wrap="word")
        self.answer_box.pack(fill="x", **pad)
        self._set_textbox(self.answer_box, "Stop listening to generate a suggested answer.")

        ctk.CTkLabel(self, text="Feedback").pack(anchor="w", padx=16)
        self.feedback_box = ctk.CTkTextbox(self, height=150, wrap="word")
        self.feedback_box.pack(fill="both", expand=True, **pad)

        # --- Status bar ---
        self.status_label = ctk.CTkLabel(self, text="Ready.", anchor="w")
        self.status_label.pack(fill="x", padx=16, pady=(0, 10))
        self._refresh_input_devices()

    # ---------- helpers ----------

    def _set_status(self, text: str, warn: bool = False):
        self.status_label.configure(text=text, text_color="#e67e22" if warn else "#bdc3c7")

    def _set_textbox(self, box: ctk.CTkTextbox, text: str):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _refresh_input_devices(self):
        try:
            self.input_devices = AudioRecorder.list_input_devices()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Could not list audio devices: {exc}", warn=True)
            return
        self.input_device_map = {
            f"{device['index']}: {device['name']}": device["index"]
            for device in self.input_devices
        }
        values = ["Default microphone", *self.input_device_map]
        self.input_device_menu.configure(values=values)
        self.input_device_var.set(values[0])

    def _selected_device_index(self):
        return self.input_device_map.get(self.input_device_var.get())

    def _on_test_microphone(self):
        self._set_status("Testing microphone for 1/4 second…")
        threading.Thread(target=self._test_microphone_worker, daemon=True).start()

    def _test_microphone_worker(self):
        try:
            level = AudioRecorder.input_level(self._selected_device_index())
            message = f"Microphone level: {level:.4f}. " + (
                "Voice detected." if level > 0.01 else "No voice detected; select another input device."
            )
            self.after(0, lambda: self._set_status(message, warn=level <= 0.01))
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            self.after(0, lambda: self._set_status(f"Microphone test failed: {error_message}", warn=True))

    # ---------- actions ----------

    def _on_get_question(self):
        self.get_question_btn.configure(state="disabled")
        self._set_status("Generating question…")
        threading.Thread(target=self._get_question_worker, daemon=True).start()

    def _get_question_worker(self):
        role = self.role_var.get()
        level = self.level_var.get()
        topic = self.topic_entry.get().strip()
        resume_text = self.resume_box.get("1.0", "end").strip()
        jd_text = self.jd_box.get("1.0", "end").strip()
        try:
            question = generate_question(role, level, topic, resume_text, jd_text)
            self.current_question = question
            self.after(0, lambda: self._set_textbox(self.question_box, question))
            self.after(0, lambda: self.record_btn.configure(state="normal"))
            self.after(0, lambda: self._set_status("Question ready. Start recording when you're ready to answer."))
        except Exception as exc:  # noqa: BLE001 - surface any API/config error to the user
            error_message = str(exc)
            self.after(0, lambda: self._set_status(f"Error generating question: {error_message}", warn=True))
        finally:
            self.after(0, lambda: self.get_question_btn.configure(state="normal"))

    def _on_load_context_file(self, target_box: ctk.CTkTextbox):
        filetypes = [("Supported files", " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)),
                     ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Select a file", filetypes=filetypes)
        if not path:
            return
        try:
            text = load_text_from_file(Path(path))
        except Exception as exc:  # noqa: BLE001 - surface bad file/format to the user
            self._set_status(f"Couldn't load file: {exc}", warn=True)
            return
        target_box.delete("1.0", "end")
        target_box.insert("1.0", text)
        self._set_status(f"Loaded {Path(path).name} ({len(text)} chars).")

    def _on_open_dashboard(self):
        DashboardWindow(self)

    def _on_toggle_record(self):
        if not self.recorder.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        try:
            self.recorder.start(
                capture_system_audio=self.system_audio_var.get(),
                device_index=self._selected_device_index(),
            )
        except Exception as exc:  # noqa: BLE001 - surface device errors in the UI
            self._set_status(f"Could not start audio: {exc}", warn=True)
            return
        self.record_btn.configure(text="■ Stop Listening", fg_color="#7f8c8d")
        self._set_textbox(self.transcript_box, "Listening… live transcript will appear here.")
        self._set_status("Recording permitted audio; transcribing locally…")
        self.timer_running = True
        self.live_transcript_running = True
        self._tick_timer()
        self._live_transcribe_tick()

    def _live_transcribe_tick(self):
        if not self.live_transcript_running or self.live_transcription_in_progress:
            return
        snapshot_path = SESSIONS_DIR / "live_snapshot.wav"
        self.recorder.snapshot_to_wav(snapshot_path)
        self.live_transcription_in_progress = True
        threading.Thread(target=self._live_transcribe_worker, args=(snapshot_path,), daemon=True).start()
        self.after(5000, self._live_transcribe_tick)

    def _live_transcribe_worker(self, audio_path: Path):
        try:
            transcript = transcribe(audio_path)
            if self.live_transcript_running and transcript:
                self.after(0, lambda: self._set_textbox(self.transcript_box, transcript))
        except Exception as exc:  # noqa: BLE001 - surface local transcription errors
            error_message = str(exc)
            self.after(0, lambda: self._set_status(f"Live transcription error: {error_message}", warn=True))
        finally:
            self.live_transcription_in_progress = False
            if self.live_transcript_running:
                self.after(100, self._live_transcribe_tick)

    def _tick_timer(self):
        if not self.timer_running:
            return
        elapsed = int(time.time() - self.recorder.start_time) if self.recorder.start_time else 0
        mins, secs = divmod(elapsed, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        level = self.recorder.input_level
        self.level_label.configure(text=f"Input level: {level:.4f}")
        self.after(500, self._tick_timer)

    def _stop_recording(self):
        self.timer_running = False
        self.live_transcript_running = False
        self.record_btn.configure(state="disabled", text="▶ Start Listening", fg_color="#c0392b")
        self._set_status("Transcribing your answer…")

        out_path = SESSIONS_DIR / f"answer_{int(time.time())}.wav"
        self.recorder.stop_and_save(out_path)
        self.current_audio_path = out_path

        threading.Thread(target=self._transcribe_and_feedback_worker, args=(out_path,), daemon=True).start()

    def _transcribe_and_feedback_worker(self, audio_path: Path):
        try:
            transcript = transcribe(audio_path)
            self.after(0, lambda: self._set_textbox(self.transcript_box, transcript or "(No speech detected)"))
            self.after(0, lambda: self._set_status("Generating suggested answer and feedback…"))

            answer = get_direct_answer(self.current_question, transcript)
            self.after(0, lambda: self._set_textbox(self.answer_box, answer))
            feedback = get_feedback(self.current_question, transcript)
            self.after(0, lambda: self._set_textbox(self.feedback_box, feedback))

            save_round(
                role=self.role_var.get(),
                level=self.level_var.get(),
                question=self.current_question,
                transcript=transcript,
                feedback=feedback,
                audio_path=str(audio_path),
            )
            self.after(0, lambda: self._set_status("Done. Saved to your session history."))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._set_status(f"Error: {exc}", warn=True))
        finally:
            self.after(0, lambda: self.record_btn.configure(state="normal"))


def main():
    app = MockInterviewApp()
    app.mainloop()


if __name__ == "__main__":
    main()
