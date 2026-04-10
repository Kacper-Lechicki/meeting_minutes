from __future__ import annotations
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Optional, cast
from .prompts import system_prompt
from .providers.base import LLMParams, Provider


@dataclass(frozen=True)
class PipelineOptions:
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_output_tokens: int = 5000
    max_audio_size_mb: int = 25
    max_chars_per_chunk: int = 12_000
    chunk_overlap_chars: int = 800
    long_transcript_threshold_chars: int = 18_000


def _chunk_text(text: str, *, max_chars: int, overlap: int) -> list[str]:
    if max_chars <= 0:
        return [text]

    if overlap < 0:
        overlap = 0

    if overlap >= max_chars:
        overlap = max(0, max_chars // 10)

    chunks: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(n, start + max_chars)
        chunk = text[start:end]
        chunks.append(chunk)

        if end == n:
            break

        start = max(0, end - overlap)

    return chunks


def _summarize_chunks(
    provider: Provider,
    *,
    chunks: list[str],
    meeting_context: Optional[str],
    params: LLMParams,
) -> str:
    sys = (
        "You are a meeting analyst. You will receive a transcript chunk. "
        "Produce a concise factual summary. "
        "Extract decisions and action items (if present). "
        "Do not invent facts."
    )

    user_prefix = "Transcript chunk:\n---\n"

    summaries: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        chunk_text = f"{user_prefix}{chunk}\n---\n"

        summary = provider.generate_minutes(
            system_prompt=sys,
            transcript_or_summary=f"[CHUNK {i}/{len(chunks)}]\n{chunk_text}",
            meeting_context=meeting_context,
            params=LLMParams(
                model=params.model,
                temperature=0.2,
                max_output_tokens=min(900, params.max_output_tokens),
            ),
        )

        summaries.append(summary.strip())

    return "\n\n".join(s for s in summaries if s)


def _require_non_empty_transcription(transcription: str) -> None:
    if not transcription.strip():
        raise ValueError(
            "Transcription is empty — nothing to summarize. "
            "Check the audio file or try another recording."
        )


def run_pipeline(
    provider: Provider,
    *,
    audio_file_path: str,
    meeting_context: Optional[str],
    options: PipelineOptions,
) -> tuple[str, str]:
    transcription = provider.transcribe(
        audio_file_path, max_audio_size_mb=options.max_audio_size_mb
    )

    transcription = transcription or ""

    _require_non_empty_transcription(transcription)

    params = LLMParams(
        model=options.llm_model,
        temperature=options.temperature,
        max_output_tokens=options.max_output_tokens,
    )

    content_for_minutes = transcription

    if len(transcription) >= options.long_transcript_threshold_chars:
        chunks = _chunk_text(
            transcription,
            max_chars=options.max_chars_per_chunk,
            overlap=options.chunk_overlap_chars,
        )

        content_for_minutes = _summarize_chunks(
            provider,
            chunks=chunks,
            meeting_context=meeting_context,
            params=params,
        )

    minutes = provider.generate_minutes(
        system_prompt=system_prompt(),
        transcript_or_summary=content_for_minutes,
        meeting_context=meeting_context,
        params=params,
    )

    return transcription, minutes or ""


def run_pipeline_stream(
    provider: Provider,
    *,
    audio_file_path: str,
    meeting_context: Optional[str],
    options: PipelineOptions,
) -> Iterator[tuple[str, str]]:
    """
    Streaming variant: yields (transcription_so_far, minutes_so_far).

    Notes:
    - Transcription is produced upfront (non-stream) since Whisper API is not streaming here.
    - Minutes are streamed when provider implements `generate_minutes_stream`.
      Otherwise falls back to a single non-stream result.
    """

    transcription = provider.transcribe(
        audio_file_path, max_audio_size_mb=options.max_audio_size_mb
    )

    transcription = transcription or ""

    _require_non_empty_transcription(transcription)

    params = LLMParams(
        model=options.llm_model,
        temperature=options.temperature,
        max_output_tokens=options.max_output_tokens,
    )

    content_for_minutes = transcription

    if len(transcription) >= options.long_transcript_threshold_chars:
        chunks = _chunk_text(
            transcription,
            max_chars=options.max_chars_per_chunk,
            overlap=options.chunk_overlap_chars,
        )

        content_for_minutes = _summarize_chunks(
            provider,
            chunks=chunks,
            meeting_context=meeting_context,
            params=params,
        )

    yield (transcription, "")

    stream_fn = getattr(provider, "generate_minutes_stream", None)

    if callable(stream_fn):
        stream = cast(Callable[..., Iterator[str]], stream_fn)(
            system_prompt=system_prompt(),
            transcript_or_summary=content_for_minutes,
            meeting_context=meeting_context,
            params=params,
        )
        
        for minutes_so_far in stream:
            yield (transcription, minutes_so_far or "")

        return

    minutes = provider.generate_minutes(
        system_prompt=system_prompt(),
        transcript_or_summary=content_for_minutes,
        meeting_context=meeting_context,
        params=params,
    )

    yield (transcription, minutes or "")
