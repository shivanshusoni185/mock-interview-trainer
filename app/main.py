"""
Mock Interview Trainer - main desktop application (Windows-friendly, but
runs anywhere Python + Tk run).

Flow:
  1. Pick a role / level / optional topic.
  2. Click "Get Question" -> LLM generates one practice question.
  3. Click "Start Recording" -> speak your answer into your own mic.
  4. Click "Stop & Get Feedback" -> local Whisper transcribes your answer,
     then the LLM gives you structured feedback.
  5. Everything is saved to sessions/history.json so you can track progress.

Nothing here listens to a live call, hides itself from screen-sharing, or
feeds answers to you while you're being asked a real question by someone
else. It's an offline-first solo practice loop.
"""
import threading
import time
from pathlib import Path

import customtkinter as ctk

from app.config import SESSIONS_DIR, has_api_key
from app.audio_recorder import AudioRecorder
from app.transcriber import transcribe
from app.llm_client import generate_question, get_feedback
from app.session_store import save_round, load_history

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

        self._build_layout()

        if not has_api_key():
            self._set_status(
                "⚠ No OpenAI API key found. Copy .env.example to .env and add your key.",
                warn=True,
            )

    # ---------- UI construction ----------

    def _build_layout(self):
        pad = {"padx": 16, "pady": 8}

        header = ctk.CTkLabel(
            self, text="🎤 Mock Interview Trainer",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        header.pack(anchor="w", **pad)

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
            rec_frame, text="⏺ Start Recording", fg_color="#c0392b",
            hover_color="#922b21", command=self._on_toggle_record, state="disabled",
        )
        self.record_btn.pack(side="left", padx=8, pady=8)

        self.timer_label = ctk.CTkLabel(rec_frame, text="00:00")
        self.timer_label.pack(side="left", padx=8)

        # --- Transcript + feedback ---
        ctk.CTkLabel(self, text="Transcript").pack(anchor="w", padx=16)
        self.transcript_box = ctk.CTkTextbox(self, height=80, wrap="word")
        self.transcript_box.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Feedback").pack(anchor="w", padx=16)
        self.feedback_box = ctk.CTkTextbox(self, height=150, wrap="word")
        self.feedback_box.pack(fill="both", expand=True, **pad)

        # --- Status bar ---
        self.status_label = ctk.CTkLabel(self, text="Ready.", anchor="w")
        self.status_label.pack(fill="x", padx=16, pady=(0, 10))

    # ---------- helpers ----------

    def _set_status(self, text: str, warn: bool = False):
        self.status_label.configure(text=text, text_color="#e67e22" if warn else "#bdc3c7")

    def _set_textbox(self, box: ctk.CTkTextbox, text: str):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    # ---------- actions ----------

    def _on_get_question(self):
        self.get_question_btn.configure(state="disabled")
        self._set_status("Generating question…")
        threading.Thread(target=self._get_question_worker, daemon=True).start()

    def _get_question_worker(self):
        role = self.role_var.get()
        level = self.level_var.get()
        topic = self.topic_entry.get().strip()
        try:
            question = generate_question(role, level, topic)
            self.current_question = question
            self.after(0, lambda: self._set_textbox(self.question_box, question))
            self.after(0, lambda: self.record_btn.configure(state="normal"))
            self.after(0, lambda: self._set_status("Question ready. Start recording when you're ready to answer."))
        except Exception as exc:  # noqa: BLE001 - surface any API/config error to the user
            self.after(0, lambda: self._set_status(f"Error generating question: {exc}", warn=True))
        finally:
            self.after(0, lambda: self.get_question_btn.configure(state="normal"))

    def _on_toggle_record(self):
        if not self.recorder.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.recorder.start()
        self.record_btn.configure(text="⏹ Stop && Get Feedback", fg_color="#7f8c8d")
        self._set_status("Recording your answer…")
        self.timer_running = True
        self._tick_timer()

    def _tick_timer(self):
        if not self.timer_running:
            return
        elapsed = int(time.time() - self.recorder.start_time) if self.recorder.start_time else 0
        mins, secs = divmod(elapsed, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        self.after(500, self._tick_timer)

    def _stop_recording(self):
        self.timer_running = False
        self.record_btn.configure(state="disabled", text="⏺ Start Recording", fg_color="#c0392b")
        self._set_status("Transcribing your answer…")

        out_path = SESSIONS_DIR / f"answer_{int(time.time())}.wav"
        self.recorder.stop_and_save(out_path)
        self.current_audio_path = out_path

        threading.Thread(target=self._transcribe_and_feedback_worker, args=(out_path,), daemon=True).start()

    def _transcribe_and_feedback_worker(self, audio_path: Path):
        try:
            transcript = transcribe(audio_path)
            self.after(0, lambda: self._set_textbox(self.transcript_box, transcript or "(No speech detected)"))
            self.after(0, lambda: self._set_status("Getting feedback…"))

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
