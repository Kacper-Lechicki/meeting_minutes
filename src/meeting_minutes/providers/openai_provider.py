from __future__ import annotations

import os

from collections.abc import Iterator
from openai import OpenAI
from .base import LLMParams


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, api_key: str, whisper_model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._whisper_model = whisper_model

    def transcribe(self, audio_file_path: str, *, max_audio_size_mb: int) -> str:
        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)

        if file_size_mb > max_audio_size_mb:
            raise ValueError(
                f"File is too large: {file_size_mb:.1f}MB. "
                f"Maximum size is {max_audio_size_mb}MB."
            )

        with open(audio_file_path, "rb") as audio_file:
            transcription = self._client.audio.transcriptions.create(
                model=self._whisper_model,
                file=audio_file,
                response_format="text",
            )

        return transcription

    def generate_minutes(
        self,
        *,
        system_prompt: str,
        transcript_or_summary: str,
        meeting_context: str | None,
        params: LLMParams,
    ) -> str:
        context_block = ""

        if meeting_context and meeting_context.strip():
            context_block = (
                "\nMEETING CONTEXT:\n---\n" f"{meeting_context.strip()}\n---\n"
            )

        response = self._client.chat.completions.create(
            model=params.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Below is a transcript (or summary) of a meeting.\n"
                        "Generate professional minutes according to the provided format.\n"
                        f"{context_block}\n"
                        "CONTENT:\n---\n"
                        f"{transcript_or_summary}\n"
                        "---\n"
                    ),
                },
            ],
            max_tokens=params.max_output_tokens,
            temperature=params.temperature,
        )

        minutes = response.choices[0].message.content

        return minutes or ""

    def generate_minutes_stream(
        self,
        *,
        system_prompt: str,
        transcript_or_summary: str,
        meeting_context: str | None,
        params: LLMParams,
    ) -> Iterator[str]:
        context_block = ""

        if meeting_context and meeting_context.strip():
            context_block = (
                "\nMEETING CONTEXT:\n---\n" f"{meeting_context.strip()}\n---\n"
            )

        resp = self._client.chat.completions.create(
            model=params.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Below is a transcript (or summary) of a meeting.\n"
                        "Generate professional minutes according to the provided format.\n"
                        f"{context_block}\n"
                        "CONTENT:\n---\n"
                        f"{transcript_or_summary}\n"
                        "---\n"
                    ),
                },
            ],
            max_tokens=params.max_output_tokens,
            temperature=params.temperature,
            stream=True,
        )

        acc = ""

        for chunk in resp:
            piece = None
            try:
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None)
            except (AttributeError, IndexError, TypeError):
                piece = None

            if piece:
                acc += piece
                yield acc
