"""Base engine interface for ASR transcription."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class TranscriptionError(Exception):
    """Raised when transcription fails."""


@dataclass
class TranscriptionResult:
    """Result from ASR transcription.

    Attributes:
        text: Transcribed text.
        duration: Audio duration in seconds.
    """

    text: str
    duration: float


class BaseEngine(ABC):
    """Abstract base class for ASR engines.

    An engine takes raw audio bytes and returns transcribed text.
    Implementations may call a remote API, run local inference,
    or use any other mechanism.
    """

    @abstractmethod
    def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio data to text.

        Args:
            audio_data: Raw audio file bytes (WAV or any pydub-supported format).
            filename: Original filename, used for format detection.
            language: Optional language hint (e.g. "en", "fi", "zh").

        Returns:
            TranscriptionResult with transcribed text and audio duration.

        Raises:
            TranscriptionError: On transcription failure.
        """
        ...

    @abstractmethod
    def test(self) -> bool:
        """Test engine readiness (connectivity, model loaded, etc.).

        Returns:
            True if engine is ready to transcribe.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name for logging.

        Examples: "openai", "groq", "sherpa-onnx/sensevoice-small".
        """
        ...
