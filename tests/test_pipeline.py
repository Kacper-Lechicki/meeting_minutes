from __future__ import annotations

from collections.abc import Iterator

import pytest

from meeting_minutes.pipeline import PipelineOptions, _chunk_text, run_pipeline, run_pipeline_stream
from meeting_minutes.providers.base import LLMParams


class StubProvider:
    name = "stub"

    def __init__(self, transcription: str) -> None:
        self._transcription = transcription

    def transcribe(self, audio_file_path: str, *, max_audio_size_mb: int) -> str:
        return self._transcription

    def generate_minutes(
        self,
        *,
        system_prompt: str,
        transcript_or_summary: str,
        meeting_context: str | None,
        params: LLMParams,
    ) -> str:
        return "minutes-result"

    def generate_minutes_stream(
        self,
        *,
        system_prompt: str,
        transcript_or_summary: str,
        meeting_context: str | None,
        params: LLMParams,
    ) -> Iterator[str]:
        yield "stream-"


def test_chunk_text_nonpositive_max_chars_returns_whole_text() -> None:
    assert _chunk_text("hello", max_chars=0, overlap=0) == ["hello"]


def test_chunk_text_empty_string() -> None:
    assert _chunk_text("", max_chars=10, overlap=2) == []


def test_chunk_text_overlap_and_windows() -> None:
    chunks = _chunk_text("abcdefghij", max_chars=4, overlap=2)
    assert chunks == ["abcd", "cdef", "efgh", "ghij"]


def test_run_pipeline_rejects_empty_transcription() -> None:
    provider = StubProvider("")

    with pytest.raises(ValueError, match="empty"):
        run_pipeline(
            provider,
            audio_file_path="unused",
            meeting_context=None,
            options=PipelineOptions(),
        )


def test_run_pipeline_stream_rejects_empty_transcription() -> None:
    provider = StubProvider("")

    gen = run_pipeline_stream(
        provider,
        audio_file_path="unused",
        meeting_context=None,
        options=PipelineOptions(),
    )

    with pytest.raises(ValueError, match="empty"):
        next(gen)


def test_run_pipeline_accepts_whitespace_only_as_empty() -> None:
    provider = StubProvider("   \n\t ")

    with pytest.raises(ValueError, match="empty"):
        run_pipeline(
            provider,
            audio_file_path="unused",
            meeting_context=None,
            options=PipelineOptions(),
        )


def test_run_pipeline_short_transcript_calls_generate_once() -> None:
    provider = StubProvider("Short meeting notes.")

    trans, minutes = run_pipeline(
        provider,
        audio_file_path="unused",
        meeting_context=None,
        options=PipelineOptions(),
    )
    
    assert trans == "Short meeting notes."
    assert minutes == "minutes-result"
