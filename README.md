# Mock Interview Trainer

A desktop app for **interview practice and transparent meeting notes** — pick a
role, get an AI-generated question, see a live local transcript while you
record, and get structured feedback afterward (content, structure, delivery).

The app is transparent by design: it shows when recording is active, keeps the
system-audio option off by default, and does not generate hidden real-time
answers. Only capture audio when everyone involved has been informed and has
given permission.

## How it works

1. **Pick a role, level, and optional topic** in the app. Optionally paste
   (or load from a `.txt`/`.pdf` file) your **resume and/or a target job
   description** to tailor the question to that specific opportunity instead
   of a generic one for the role.
2. **Get a Question** — an LLM (OpenAI or Anthropic — your choice, see
   Configuration) generates one realistic practice question.
3. **Start Recording** — speak into your microphone. The transcript updates
  live every few seconds using local faster-whisper transcription. On
  Windows, you can optionally enable system-audio loopback when permitted.
4. **Stop & Get Feedback** — the complete recording is transcribed locally with
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (runs on your
   machine, no audio is uploaded for transcription), then the transcript is
   sent to the LLM for feedback on content, structure, and delivery.
5. Every round is saved to `sessions/history.json` so you can track your
   progress over time — open **📊 Progress Dashboard** in the app to see
   trends (answer length over time, rounds practiced per role).

## Requirements

- Windows 10/11
- [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to
  PATH" during install)
- An API key for **either** [OpenAI](https://platform.openai.com/api-keys)
  or [Anthropic](https://console.anthropic.com/settings/keys) (used only for
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
| `LLM_PROVIDER` | `openai` (default) or `anthropic` — which backend generates questions and feedback |
| `OPENAI_API_KEY` | Your OpenAI API key (required if `LLM_PROVIDER=openai`) |
| `OPENAI_MODEL` | Model used for questions/feedback (default `gpt-4o-mini`) |
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required if `LLM_PROVIDER=anthropic`) |
| `ANTHROPIC_MODEL` | Model used for questions/feedback (default `claude-sonnet-5`) |
| `WHISPER_MODEL_SIZE` | Local transcription model size: `tiny`, `base`, `small`, `medium`, `large-v3`. Bigger = more accurate, slower, more RAM. `base` is a good default on a CPU-only laptop. |

You only need to set the API key for whichever `LLM_PROVIDER` you choose.

### Capturing your voice and meeting audio

Click **Start Listening** directly; generating a question is optional. Use the
input dropdown to choose your physical microphone. To hear audio from Meet,
Teams, or Zoom, select a Windows device such as **Stereo Mix** (if enabled),
or enable the system-audio checkbox to capture the default speaker output.
Windows may require microphone permission under Settings > Privacy & security
> Microphone. Use **Test microphone** before starting and speak during the
quarter-second test; a near-zero level means the selected device is muted or
not the device used by your meeting.

## Project structure

```
mock-interview-trainer/
├── app/
│   ├── main.py             # Desktop GUI (CustomTkinter) — app entry point
│   ├── audio_recorder.py   # Mic capture + optional Windows speaker loopback
│   ├── transcriber.py      # Local speech-to-text via faster-whisper
│   ├── llm_client.py       # Question generation + post-answer feedback (OpenAI or Anthropic)
│   ├── resume_context.py   # Loads resume/job-description text (paste or .txt/.pdf) for tailoring
│   ├── dashboard.py        # Progress dashboard window (trends over sessions/history.json)
│   ├── session_store.py    # Saves practice history to sessions/history.json
│   └── config.py           # Loads settings from .env
├── sessions/                # Your local recordings + history (gitignored)
├── requirements.txt
├── requirements-build.txt   # Extra dependency (PyInstaller) for packaging only
├── run.bat                  # One-click Windows launcher
├── build.bat                 # Packages the app as a standalone Windows .exe
└── .env.example
```

## Packaging as a standalone .exe

If you'd rather hand someone a `.exe` than ask them to install Python, run
`build.bat` **on Windows** (PyInstaller builds for whatever OS it runs on, so
this step can't be done from Linux/macOS/CI):

```bat
run.bat        :: first, so .venv and dependencies exist
build.bat
```

This produces `dist\MockInterviewTrainer\MockInterviewTrainer.exe`. Copy a
`.env` file (with your API key) into that same `dist\MockInterviewTrainer\`
folder before running it — the packaged app reads `.env` and stores
`sessions\` next to the `.exe`, not inside the source tree. The first launch
still needs internet access once, to download the faster-whisper model.

## Troubleshooting (Windows)

**`'python' is not recognized as an internal or external command`**
Python isn't on your PATH. Reinstall from python.org and check "Add Python to
PATH", or use the `py` launcher (`py -m venv .venv`) instead.

**`pip install` fails on `sounddevice` / mentions PortAudio**
The Windows wheel for `sounddevice` bundles PortAudio, so this is rare, but
if it happens: make sure you're on Python 3.10–3.12 (older/newer versions may
not have a prebuilt wheel yet), and that pip itself is up to date
(`python -m pip install --upgrade pip`), then retry `pip install -r requirements.txt`.

**No sound is recorded / "no default input device"**
Check Windows Settings → Privacy & security → Microphone → allow desktop
apps to access your microphone, and confirm the right mic is set as your
default recording device in Windows Sound settings.

**First "Get a Question" or first recording is slow**
`faster-whisper` downloads its model (a few hundred MB, size depends on
`WHISPER_MODEL_SIZE`) from Hugging Face the first time it's used, and caches
it locally afterward. This needs an internet connection once; later runs are
fast and fully offline for transcription. If it hangs, check your internet
connection or try a smaller `WHISPER_MODEL_SIZE` (e.g. `tiny` or `base`).

**Do I need a GPU / CUDA / PyTorch installed?**
No. `faster-whisper` uses CTranslate2, not PyTorch, and this app runs it with
`device="cpu", compute_type="int8"` specifically so it works on a normal
laptop with no GPU. If you do have an NVIDIA GPU and want it faster, you can
change `device="cpu"` to `device="cuda"` in `app/transcriber.py`, but it's
not required.

**"Error generating question" / "Error: ..." mentioning an API key**
Your `.env` is missing or has the wrong key for the `LLM_PROVIDER` you set —
see the Configuration table above. `OPENAI_API_KEY` is only used when
`LLM_PROVIDER=openai`; `ANTHROPIC_API_KEY` only when `LLM_PROVIDER=anthropic`.

**Dependency install is slow / a lot of disk space**
`faster-whisper`, `matplotlib`, and their dependencies add up to a few
hundred MB in `.venv`. That's expected and only happens once.

## Why it's built this way (for anyone extending this)

The pipeline — permitted audio capture → local live transcription → LLM
feedback — is suitable for interview practice and consent-based meeting
notes. System-audio loopback uses the default Windows speaker and may not be
available on every audio driver; microphone-only capture remains the default.

## License

MIT — do whatever you like with this, just don't use the underlying
transcription/LLM pipeline to build a tool that deceives another person
about who (or what) is actually answering.
