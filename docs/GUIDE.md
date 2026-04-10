# Meeting Minutes AI — guide

This document explains **what the project does**, **how you use it day to day**, and **how the pieces fit together technically** — enough detail to navigate the codebase without reading every line.

For installation, environment variables, and quick start, see [README.md](../README.md).

---

## 1. What is it for?

**Meeting Minutes AI** is a small Python application that:

1. Accepts a **meeting audio file** (upload in the Gradio UI or the same flow from a notebook).
2. Sends the audio to **OpenAI Whisper** for transcription.
3. Sends the transcript (or a chunked summary for very long text) to a **chat model** (default `gpt-4o-mini`) to produce **structured meeting minutes** in Markdown.

In one line: **audio file → Whisper → GPT-style model → minutes**.

---

## 2. High-level architecture

```
.env / environment
    -> load_settings + validate_settings (config.py)
    -> OpenAIProvider (Whisper + chat completions)
    -> pipeline: transcribe -> (optional chunk summaries) -> final minutes
    -> Gradio UI (app.py) or notebook calling the same primitives
```

The library code under `src/meeting_minutes/` is kept separate from the Gradio **shell** in `app.py`, so you can reuse the pipeline from scripts or notebooks.

| Module | Responsibility |
| ------ | -------------- |
| [`src/meeting_minutes/config.py`](../src/meeting_minutes/config.py) | `Settings`, `load_settings`, `validate_settings`, `ConfigurationError` |
| [`src/meeting_minutes/prompts.py`](../src/meeting_minutes/prompts.py) | Default system prompt; optional override via `SYSTEM_PROMPT` |
| [`src/meeting_minutes/pipeline.py`](../src/meeting_minutes/pipeline.py) | `PipelineOptions`, chunking, `run_pipeline`, `run_pipeline_stream` |
| [`src/meeting_minutes/providers/base.py`](../src/meeting_minutes/providers/base.py) | `LLMParams`, `Provider` protocol |
| [`src/meeting_minutes/providers/openai_provider.py`](../src/meeting_minutes/providers/openai_provider.py) | Whisper transcription + chat (non-stream and stream) |
| [`app.py`](../app.py) | `sys.path` bootstrap, Gradio layout, loaders, error surfacing |
| [`notebooks/meeting_minutes.ipynb`](../notebooks/meeting_minutes.ipynb) | Alternate entry: same ideas in notebook form |

Entry points:

- **Web UI:** `python app.py` (from repo root, after installing deps and setting `OPENAI_API_KEY`).
- **Notebook:** open `notebooks/meeting_minutes.ipynb` in Jupyter / VS Code.

---

## 3. User flow (Gradio)

1. **Startup:** `build_demo()` calls `_build_provider()` to load settings and confirm `OPENAI_API_KEY` is present (via `validate_settings`). Default LLM model is shown in a textbox.
2. **Upload:** User selects an audio file. `on_audio_change` enables **Generate minutes** when a path exists.
3. **Submit:** `process_meeting_audio_ui` locks inputs, shows lightweight HTML loaders, and consumes `run_pipeline_stream`.
4. **Streaming:** First yield exposes the full transcription (Whisper is not token-streamed here); subsequent yields append streamed minutes when `generate_minutes_stream` is used.
5. **Errors:** `ConfigurationError` → configuration message; `ValueError` → validation (e.g. file size, empty transcript); other exceptions → generic error line in the UI.

---

## 4. Configuration (`config.py`)

- **`load_dotenv()`** runs when settings are loaded; values come from the process environment and optional `.env` in the working directory.
- **`OPENAI_API_KEY`** is required for real runs; missing key raises **`ConfigurationError`** (subclass of `ValueError`).
- Optional knobs: `WHISPER_MODEL`, `LLM_MODEL`, `LLM_MAX_OUTPUT_TOKENS`, `MAX_AUDIO_SIZE_MB`, `DEBUG`. See [`.env.example`](../.env.example).
- **`SYSTEM_PROMPT`** is read in `prompts.py` (not the `Settings` dataclass) so long prompts stay out of the main config object.

Secrets are not printed by `load_settings`.

---

## 5. Pipeline (`pipeline.py`)

### 5.1 Transcription and guard

- `provider.transcribe(path, max_audio_size_mb=...)` uploads audio to Whisper (via `OpenAIProvider`).
- If the returned text is empty or whitespace-only, **`_require_non_empty_transcription`** raises `ValueError` so the LLM is not called pointlessly.

### 5.2 Long transcripts

- If transcript length **≥ `long_transcript_threshold_chars`** (default 18_000), the text is split with **`_chunk_text`** (window + overlap).
- Each chunk is summarized with a **fixed analyst-style system prompt** in **`_summarize_chunks`**, using `generate_minutes` with lower temperature and a capped `max_output_tokens` per chunk.
- Concatenated summaries become the **input** to the final minutes pass.

### 5.3 Final minutes

- **`system_prompt()`** from `prompts.py` defines the Markdown structure (executive summary, participants, action items, etc.).
- **`run_pipeline`** returns `(transcription, minutes)` in one shot.
- **`run_pipeline_stream`** yields `(transcription, "")` first, then incremental minutes strings if the provider implements **`generate_minutes_stream`**; otherwise it falls back to a single `generate_minutes` call and one final yield.

---

## 6. OpenAI provider (`openai_provider.py`)

- **`transcribe`:** checks file size against `max_audio_size_mb`, opens the file in binary mode, calls `audio.transcriptions.create` with `response_format="text"`.
- **`generate_minutes`:** builds system + user messages (optional **meeting context** block), `chat.completions.create` without streaming.
- **`generate_minutes_stream`:** same message shape with `stream=True`; walks chunks and accumulates text. Narrow handling around `chunk.choices[0].delta` avoids swallowing unrelated errors inside a bare `except`.

---

## 7. Gradio shell (`app.py`)

- Prepends **`src/`** to `sys.path` so `meeting_minutes` imports work when running from repo root without an installed package.
- Duplicates loader HTML/CSS with the notebook for a consistent look.
- Maps exceptions to Gradio updates so the user sees a single error string in both transcript and minutes panels when something fails early.

---

## 8. Security and privacy (summary)

- Keep **`OPENAI_API_KEY`** in `.env` or the environment; `.env` should stay git-ignored.
- Audio and derived text are sent to **OpenAI’s APIs**; retention and processing are governed by OpenAI’s terms and policies — see [README.md](../README.md) for the policy link.
- The app is intended for **local** use (`share=False` in `demo.launch`); exposing it on a network would require your own threat model (no built-in authentication).

---

## 9. Limits and trade-offs

- **Whisper file size:** API limit is **25 MB** per request; the app enforces a configurable cap (`MAX_AUDIO_SIZE_MB`).
- **Chunked path:** long meetings cost more API calls (per-chunk summaries + final pass).
- **Single provider:** `OpenAIProvider` is the concrete implementation; swapping providers would mean a new class matching the `Provider` protocol.
- **Formats:** some containers (e.g. certain `m4a` paths) may need **ffmpeg** locally depending on how Gradio/your OS decodes before upload.

---

## 10. Tests and quality gates

- **`pytest`** and **`pytest.ini`** (`pythonpath = src`) cover config validation, chunking, empty transcript behavior, and a short non-stream pipeline path with a stub provider.
- CI (if enabled in the repo) typically runs `compileall` and `pytest`; see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

---

## 11. Where to look in the code

| Topic | Location |
| ----- | -------- |
| Env vars and `ConfigurationError` | `src/meeting_minutes/config.py` |
| Chunking, long-transcript strategy, guards | `src/meeting_minutes/pipeline.py` |
| Default / custom system prompt | `src/meeting_minutes/prompts.py` |
| Whisper + chat API calls | `src/meeting_minutes/providers/openai_provider.py` |
| Gradio UX and error mapping | `app.py` |
| Notebook parity | `notebooks/meeting_minutes.ipynb` |

Together with [README.md](../README.md), this should be enough to follow data from **file upload → transcript → minutes** and to know **where to change behavior** safely.
