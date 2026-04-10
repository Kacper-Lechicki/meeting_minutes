from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class LLMParams:
    model: str
    temperature: float = 0.3
    max_output_tokens: int = 5000


class Provider(Protocol):
    name: str

    def transcribe(self, audio_file_path: str, *, max_audio_size_mb: int) -> str:
        ...

    def generate_minutes(
        self,
        *,
        system_prompt: str,
        transcript_or_summary: str,
        meeting_context: Optional[str],
        params: LLMParams,
    ) -> str:
        ...

