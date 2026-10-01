"""Local ASR engine using whisper.cpp.

Transcribes audio by running a locally built ``whisper-cli`` binary with a
GGLM model. No extra Python dependencies beyond the base asr2clip install.

See build instructions at: https://github.com/ggml-org/whisper.cpp
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .audio_input import AudioInput
from .base import BaseEngine, TranscriptionError, TranscriptionResult

_MIN_TIMEOUT = 10.0
_TIMEOUT_MULTIPLIER = 3.0


class WhisperCppEngine(BaseEngine):
    """ASR engine using whisper.cpp ``whisper-cli``.

    Audio is passed with :meth:`~asr2clip.engines.AudioInput.as_file` so
    file-backed input is not re-encoded. Transcription result is taken direct
    from stdout.

    Args:
        binary: Path to ``whisper-cli`` (or a compatible binary).
        model: Path to a GGML model (``.bin``).
        vad_model: Optional Silero VAD model for ``--vad``.
        num_threads: Number of threads (``-t``).
        timeout_multiplier: Scales the timeout with audio duration.
    """

    def __init__(
        self,
        binary: str,
        model: str,
        vad_model: str | None = None,
        num_threads: int = 4,
        timeout_multiplier: float = _TIMEOUT_MULTIPLIER,
    ) -> None:
        self._binary = os.path.expanduser(binary)
        self._model = os.path.expanduser(model)
        self._vad_model = os.path.expanduser(vad_model) if vad_model else None
        self._num_threads = num_threads
        self._timeout_multiplier = timeout_multiplier

    def transcribe(
        self,
        audio: AudioInput,
        language: str | None = None,
    ) -> TranscriptionResult:
        samples, sr = audio.as_numpy()
        duration = len(samples) / sr if sr else 0.0
        cmd = [
            self._binary, "-m", self._model, "-f", audio.as_file(), "-t",
            str(self._num_threads), "-np", "-nt",
        ]
        if language:
            cmd.extend(["-l", language])
        if self._vad_model:
            cmd.extend(["--vad", "-vm", self._vad_model])

        timeout = _MIN_TIMEOUT + duration * self._timeout_multiplier
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired as e:
            raise TranscriptionError(
                f"whisper.cpp timed out after {timeout:.0f}s"
            ) from e
        except OSError as e:
            raise TranscriptionError(f"Failed to run whisper.cpp: {e}") from e

        if proc.returncode != 0:
            raise TranscriptionError(
                f"whisper.cpp exited with code {proc.returncode}: "
                f"{(proc.stderr or proc.stdout or '').strip()}"
            )

        text = proc.stdout.strip()
        if not text:
            raise TranscriptionError("whisper.cpp produced no transcription text")
        return TranscriptionResult(text=text, duration=duration)

    def test(self) -> bool:
        if not os.path.isfile(self._binary) or not os.access(self._binary, os.X_OK):
            return False
        if not os.path.isfile(self._model):
            return False
        if self._vad_model and not os.path.isfile(self._vad_model):
            return False
        return True

    @property
    def name(self) -> str:
        return f"whisper.cpp/{Path(self._model).stem}"
