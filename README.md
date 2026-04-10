# Meeting Minutes AI

> Automatic transcription and meeting notes generation using OpenAI

[Python](https://www.python.org/)
[OpenAI](https://openai.com/)
[Gradio](https://gradio.app/)

## Description

An AI tool that transforms meeting recordings into professional minutes in two steps:

1. Transcription — OpenAI Whisper converts speech to text
2. Analysis — GPT-4o-mini extracts key information and formats the minutes

## Features

- Audio file upload (MP3, WAV, M4A, OGG, FLAC)
- Automatic transcription in any language
- Minutes generation including: summary, participants, discussion points, and action items
- Simple web interface (Gradio)
- Runs locally (Gradio / Jupyter)

For architecture, pipeline behavior, and a code map, see [docs/GUIDE.md](docs/GUIDE.md).

## How to Run

### Local

```bash
git clone https://github.com/YOUR_USERNAME/meeting-minutes-ai
cd meeting-minutes-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Optional (notebooks/type-checking):
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Fill in OPENAI_API_KEY in the .env file
python app.py
```

## Virtual environments (venv) and pip

Python projects should usually be run inside a **virtual environment** (venv). A venv is an isolated folder containing:

- a dedicated Python interpreter
- its own `pip` and installed packages

This prevents conflicts between projects and keeps your system Python clean.

### Create and activate a venv (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Optional (notebooks/type-checking):
python -m pip install -r requirements-dev.txt
```

To deactivate:

```bash
deactivate
```

### Create and activate a venv (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Optional (notebooks/type-checking):
python -m pip install -r requirements-dev.txt
```

If activation is blocked, you may need (one-time) PowerShell policy change:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### How to tell you are “inside” the venv

- Your shell prompt often shows `(.venv)`
- `which python` (macOS/Linux) or `where python` (Windows) points to the `.venv` directory

### Why use `python -m pip ...`

It ensures the `pip` you run matches the currently active `python` (especially important when you have multiple Python versions installed).

## Backend

The app uses **OpenAI** (Whisper + GPT):

- Set `OPENAI_API_KEY`
- Optional: `WHISPER_MODEL`, `LLM_MODEL`, `LLM_MAX_OUTPUT_TOKENS`, `MAX_AUDIO_SIZE_MB`, `SYSTEM_PROMPT`, `DEBUG`

Python package (for `app.py`): code lives under `src/meeting_minutes/`.

See `.env.example` for all variables.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

## Privacy and data

Uploading audio runs transcription and analysis through **OpenAI** (see [OpenAI’s policies](https://openai.com/policies/) for how they handle API data). Do not commit `.env` or real recordings; keep secrets local.

## Limits

- **Audio size**: Whisper API limit is **25MB** per file (configurable via `MAX_AUDIO_SIZE_MB`).
- **Long meetings**: for long transcripts, the app summarizes in chunks first and then generates final minutes.

## Optional system dependency (local)

Some audio formats (notably `m4a`) may require `ffmpeg` installed on your system for decoding/conversion, depending on your local environment.
