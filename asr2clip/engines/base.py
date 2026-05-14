"""Base engine interface for ASR transcription."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audio_input import AudioInput


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

    An engine takes audio input and returns transcribed text.
    Implementations may call a remote API, run local inference,
    or use any other mechanism.

    Audio is provided via :class:`~asr2clip.engines.AudioInput`, which
    supports multiple representations (bytes, file path, numpy array).
    Each engine retrieves whichever format is most natural for it.
    """

    @abstractmethod
    def transcribe(
        self,
        audio: AudioInput,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Audio input (bytes, file, or numpy array).
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
