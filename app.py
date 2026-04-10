from __future__ import annotations

import inspect
import sys

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import gradio as gr
from gradio.themes import Soft

_SRC_DIR = Path(__file__).resolve().parent / "src"

if _SRC_DIR.exists():
    sys.path.insert(0, str(_SRC_DIR))

from meeting_minutes.config import ConfigurationError, Settings, load_settings, validate_settings
from meeting_minutes.pipeline import PipelineOptions, run_pipeline_stream
from meeting_minutes.providers import OpenAIProvider


def _build_provider() -> tuple[OpenAIProvider, Settings]:
    settings = load_settings()
    validate_settings(settings)

    return (
        OpenAIProvider(
            api_key=settings.openai_api_key or "",
            whisper_model=settings.whisper_model,
        ),
        settings,
    )


def _audio_file_info_md(audio_path: str | None) -> str:
    if not audio_path:
        return "**Current audio:** _No file selected._"

    return f"**Current audio:** `{Path(audio_path).name}`"


def _loader_html() -> str:
    return (
        '<div class="mm-loader" aria-label="Loading">'
        '<span class="mm-spinner" aria-hidden="true"></span>'
        "</div>"
    )


_GRADIO_CUSTOM_CSS = """
    .header-text { text-align: center; margin-bottom: 20px; }
    .output-box { font-family: 'Courier New', monospace; }

    .mm-loader {
      display: flex;
      justify-content: center;
      padding: 10px 0 0;
    }

    .mm-spinner {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.25);
      border-top-color: rgba(255, 255, 255, 0.85);
      animation: mmspin 0.9s linear infinite;
    }

    @keyframes mmspin {
      to { transform: rotate(360deg); }
    }

    #mm-minutes-output,
    #mm-minutes-output * {
      border: none !important;
      box-shadow: none !important;
      outline: none !important;
      background: transparent !important;
    }

    #mm-minutes-output::before,
    #mm-minutes-output::after,
    #mm-minutes-output *::before,
    #mm-minutes-output *::after {
      border: none !important;
      box-shadow: none !important;
      background: transparent !important;
    }

    #mm-minutes-output .prose {
      padding-top: 6px;
    }

    #mm-minutes-loader,
    #mm-transcription-loader {
      border: none !important;
      box-shadow: none !important;
      outline: none !important;
      background: transparent !important;
    }
"""


def _reset_outputs() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        gr.update(value=""),
        gr.update(value="*Minutes will appear here after generating...*"),
    )


def on_audio_change(audio_path: str | None):
    current_audio_md = _audio_file_info_md(audio_path)
    transcription_reset, minutes_reset = _reset_outputs()

    if not audio_path:
        return (
            gr.update(value=current_audio_md),
            gr.update(interactive=False),
            transcription_reset,
            minutes_reset,
        )

    return (
        gr.update(value=current_audio_md),
        gr.update(interactive=True),
        gr.update(),
        gr.update(),
    )


def process_meeting_audio_ui(
    audio_file: str | None,
    model: str,
    meeting_context: str,
) -> Iterator[tuple[object, ...]]:
    if audio_file is None:
        transcription_reset, minutes_reset = _reset_outputs()

        yield (
            transcription_reset,
            minutes_reset,
            gr.update(value="", visible=False), 
            gr.update(value="", visible=False), 
            gr.update(interactive=True), 
            gr.update(interactive=True), 
            gr.update(interactive=True),  
            gr.update(interactive=False), 
        )
        return

    try:
        provider, settings = _build_provider()

        options = PipelineOptions(
            llm_model=model or settings.llm_model,
            max_output_tokens=settings.llm_max_output_tokens,
            max_audio_size_mb=settings.max_audio_size_mb,
        )

        yield (
            gr.update(value=""),
            gr.update(),
            gr.update(value=_loader_html(), visible=True),
            gr.update(value=_loader_html(), visible=True),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )

        seen_first = False
        transcription = ""
        minutes = ""

        for transcription, minutes in run_pipeline_stream(
            provider,
            audio_file_path=audio_file,
            meeting_context=meeting_context,
            options=options,
        ):
            if not seen_first:
                yield (
                    gr.update(value=transcription),
                    gr.update(),
                    gr.update(value="", visible=False),
                    gr.update(value=_loader_html(), visible=True),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                )

                seen_first = True
                
                continue

            yield (
                gr.update(value=transcription),
                gr.update(value=minutes),
                gr.update(value="", visible=False),
                gr.update(value=_loader_html(), visible=True),
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(interactive=False),
            )

        yield (
            gr.update(value=transcription),
            gr.update(value=minutes),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )

    except ConfigurationError as e:
        msg = f"Configuration error: {e}"

        yield (
            gr.update(value=msg),
            gr.update(value=msg),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )
    except ValueError as e:
        msg = f"Validation error: {e}"

        yield (
            gr.update(value=msg),
            gr.update(value=msg),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )
    except Exception as e:
        msg = f"Error: {type(e).__name__}: {e}"

        yield (
            gr.update(value=msg),
            gr.update(value=msg),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )


def build_demo() -> gr.Blocks:
    textbox_supports_copy_btn = (
        "show_copy_button" in inspect.signature(gr.Textbox.__init__).parameters
    )

    with gr.Blocks(title="Meeting Minutes AI") as demo:
        gr.Markdown(
            """
            ## Meeting Minutes AI
            Upload meeting recording → receive professional notes automatically.

            **Supported formats:** MP3, WAV, M4A, OGG, FLAC, WEBM.
            **Size limit:** 25MB (OpenAI Whisper API limit).
            """
        )

        _, settings = _build_provider()

        audio_input = gr.Audio(
            label="Upload audio file",
            type="filepath",
            sources=["upload"],
        )

        current_audio_md = gr.Markdown(_audio_file_info_md(None))

        model_input = gr.Textbox(
            label="LLM model",
            value=settings.llm_model,
            placeholder="e.g. gpt-4o-mini",
        )

        meeting_context_input = gr.Textbox(
            label="Meeting context (optional)",
            lines=4,
            placeholder="e.g. Project name, expected attendees, goal of the meeting...",
        )

        submit_btn = gr.Button(
            "Generate minutes", variant="primary", size="lg", interactive=False
        )

        with gr.Tabs():
            with gr.Tab("Minutes"):
                minutes_output = gr.Markdown(
                    value="*Minutes will appear here after generating...*",
                    elem_id="mm-minutes-output",
                )

                minutes_loader = gr.HTML(
                    value="", visible=False, elem_id="mm-minutes-loader"
                )

            with gr.Tab("Transcription"):
                transcription_textbox_kw: dict[str, Any] = {
                    "label": "Raw transcription",
                    "lines": 15,
                    "placeholder": "The raw transcript will appear here...",
                    "elem_id": "mm-transcription-output",
                }

                if textbox_supports_copy_btn:
                    transcription_textbox_kw["show_copy_button"] = True

                transcription_output = gr.Textbox(**transcription_textbox_kw)

                transcription_loader = gr.HTML(
                    value="", visible=False, elem_id="mm-transcription-loader"
                )

        audio_input.change(
            fn=on_audio_change,
            inputs=[audio_input],
            outputs=[
                current_audio_md,
                submit_btn,
                transcription_output,
                minutes_output,
            ],
        )

        submit_btn.click(
            fn=process_meeting_audio_ui,
            inputs=[audio_input, model_input, meeting_context_input],
            outputs=[
                transcription_output,
                minutes_output,
                transcription_loader,
                minutes_loader,
                audio_input,
                model_input,
                meeting_context_input,
                submit_btn,
            ],
        )

    return demo


if __name__ == "__main__":
    demo = build_demo()

    demo.launch(
        share=False,
        debug=False,
        theme=Soft(),
        css=_GRADIO_CUSTOM_CSS,
    )

