# Mock Interview Trainer

A desktop app for **practicing interview answers on your own** — pick a role,
get an AI-generated question, record yourself answering it out loud, and get
structured feedback afterward (content, structure, delivery).

This is a solo practice tool, not a live-assist tool: it never listens to a
real interview, never hides itself from screen-sharing, and never suggests
answers while someone is actually asking you a question. The feedback loop
only happens *after* you finish recording your own answer.

## How it works

1. **Pick a role, level, and optional topic** in the app.
2. **Get a Question** — an LLM (OpenAI) generates one realistic practice
   question for that role/level.
3. **Start Recording** — speak your answer into your own microphone.
4. **Stop & Get Feedback** — your answer is transcribed locally with
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (runs on your
   machine, no audio is uploaded for transcription), then the transcript is
   sent to the LLM for feedback on content, structure, and delivery.
5. Every round is saved to `sessions/history.json` so you can track your
   progress over time.

## Requirements

- Windows 10/11
- [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to
  PATH" during install)
- An [OpenAI API key](https://platform.openai.com/api-keys) (used only for
  question generation and feedback text — a few cents per practice session)
- A working microphone

## Setup (Windows)

```bat
:: 1. Clone the repo
git clone https://github.com/<your-username>/mock-interview-trainer.git
cd mock-interview-trainer

:: 2. Run the launcher — it creates a virtual environment, installs
::    dependencies, and prompts you for your API key on first run.
run.bat
```

That's it — `run.bat` handles the virtual environment, dependency install,
and `.env` setup for you on first launch. On later runs it just starts the
app.

### Manual setup (if you prefer not to use run.bat)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
:: edit .env and add your OPENAI_API_KEY
python -m app.main
```

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | Model used for questions/feedback (default `gpt-4o-mini`) |
| `WHISPER_MODEL_SIZE` | Local transcription model size: `tiny`, `base`, `small`, `medium`, `large-v3`. Bigger = more accurate, slower, more RAM. `base` is a good default on a CPU-only laptop. |

## Project structure

```
mock-interview-trainer/
├── app/
│   ├── main.py            # Desktop GUI (CustomTkinter) — app entry point
│   ├── audio_recorder.py  # Records from your own microphone only
│   ├── transcriber.py     # Local speech-to-text via faster-whisper
│   ├── llm_client.py      # Question generation + post-answer feedback
│   ├── session_store.py   # Saves practice history to sessions/history.json
│   └── config.py          # Loads settings from .env
├── sessions/               # Your local recordings + history (gitignored)
├── requirements.txt
├── run.bat                 # One-click Windows launcher
└── .env.example
```

## Why it's built this way (for anyone extending this)

The pipeline — mic capture → streaming/batch speech-to-text → LLM call →
UI — is the same core architecture used by real-time "interview copilot"
tools. The difference here is deliberate:

- Audio comes from **your own mic**, never system/call audio or the other
  participant's voice.
- Feedback is generated **after** you stop recording, never live while
  someone is asking you a real question.
- Nothing about the UI tries to be invisible to screen-sharing or hidden
  from a meeting platform — there's no "stealth overlay" here.

If you want to extend this into a live meeting note-taker (transcribing
your own calls, with the other participants' knowledge/consent) the same
`audio_recorder.py` → `transcriber.py` pipeline is a reasonable starting
point — you'd swap the mic-only input for a loopback/system-audio source
and add a summarization pass instead of the feedback prompt.

## License

MIT — do whatever you like with this, just don't use the underlying
transcription/LLM pipeline to build a tool that deceives another person
about who (or what) is actually answering.
