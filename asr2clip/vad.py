"""Voice Activity Detection (VAD) using Silero VAD via sherpa-onnx.

Requires the ``sherpa-onnx`` package (install with ``pip install asr2clip[vad]``).
The Silero VAD model (~629 KB) is downloaded automatically on first use.
"""

import os
import sys
import threading
from pathlib import Path

import numpy as np

VAD_MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
)
VAD_MODEL_FILENAME = "silero_vad.onnx"

# Default VAD parameters
DEFAULT_THRESHOLD = 0.5  # Silero speech probability threshold
DEFAULT_SILENCE_DURATION = 1.5  # Seconds of silence to trigger transcription
DEFAULT_MIN_SPEECH_DURATION = 0.25  # Minimum speech duration for a valid segment
DEFAULT_MAX_SPEECH_DURATION = 30.0  # Max duration before forced transcription


def _default_data_dir() -> Path:
    """Return XDG_DATA_HOME / asr2clip or ~/.local/share/asr2clip."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "asr2clip"
    return Path.home() / ".local" / "share" / "asr2clip"


def _resolve_vad_model() -> Path:
    """Return path to silero_vad.onnx, downloading if needed."""
    model_path = _default_data_dir() / "models" / VAD_MODEL_FILENAME
    if model_path.is_file():
        return model_path
    return _download_vad_model(model_path)


def _download_vad_model(model_path: Path) -> Path:
    """Download the Silero VAD ONNX model.

    Args:
        model_path: Target path to save the model file.

    Returns:
        Path to the downloaded model.
    """
    from asr2clip._vendor.httpclient import httpclient

    model_path.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading Silero VAD model (~629 KB)...", file=sys.stderr)
    print(f"  From: {VAD_MODEL_URL}", file=sys.stderr)
    print(f"  To:   {model_path}", file=sys.stderr)

    try:
        with httpclient.get(VAD_MODEL_URL, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(model_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
    except httpclient.HTTPError as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        if model_path.exists():
            model_path.unlink()
        raise SystemExit(1) from e

    print("VAD model ready.", file=sys.stderr)
    return model_path


class VoiceActivityDetector:
    """Silero VAD wrapper for real-time speech detection.

    Buffers incoming audio into fixed-size windows required by Silero,
    and emits a trigger when a speech segment (speech followed by silence)
    is detected or a maximum duration is exceeded.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = DEFAULT_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        min_speech_duration: float = DEFAULT_MIN_SPEECH_DURATION,
        max_speech_duration: float = DEFAULT_MAX_SPEECH_DURATION,
    ):
        """Initialize the Silero VAD.

        Args:
            sample_rate: Audio sample rate in Hz.
            threshold: Speech probability threshold (0.0-1.0).
            silence_duration: Seconds of silence after speech to trigger.
            min_speech_duration: Minimum speech duration for a valid segment.
            max_speech_duration: Forced trigger after this many seconds.
        """
        try:
            import sherpa_onnx
        except ImportError as e:
            raise ImportError(
                "sherpa-onnx is required for VAD. "
                "Install with: pip install asr2clip[vad]"
            ) from e

        model_path = _resolve_vad_model()

        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(model_path)
        config.silero_vad.threshold = threshold
        config.silero_vad.min_silence_duration = silence_duration
        config.silero_vad.min_speech_duration = min_speech_duration
        config.sample_rate = sample_rate

        self._vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)
        self._window_size = config.silero_vad.window_size
        self._sample_rate = sample_rate
        self._threshold = threshold
        self._max_speech_duration = max_speech_duration

        self._buffer = np.empty(0, dtype=np.float32)
        self._total_samples = 0
        self._speech_detected = False
        self._lock = threading.Lock()

    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """Process an audio chunk and detect if transcription should trigger.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            True if transcription should be triggered.
        """
        with self._lock:
            chunk = audio_chunk.flatten().astype(np.float32)
            self._buffer = np.concatenate([self._buffer, chunk])
            self._total_samples += len(chunk)

            trigger = False
            while len(self._buffer) >= self._window_size:
                window = self._buffer[: self._window_size]
                self._buffer = self._buffer[self._window_size :]
                self._vad.accept_waveform(window)

                while not self._vad.empty():
                    self._vad.pop()
                    self._speech_detected = True
                    trigger = True

            # Force trigger on max duration
            if (
                not trigger
                and self._speech_detected
                and self._total_samples / self._sample_rate >= self._max_speech_duration
            ):
                trigger = True

            return trigger

    def reset(self):
        """Reset VAD state after transcription.

        Preserves the audio buffer (partial window data belongs to the
        next segment) but resets counters and flushes Silero state.
        """
        with self._lock:
            self._total_samples = 0
            self._speech_detected = False
            self._vad.flush()
            # Drain any segments produced by flush
            while not self._vad.empty():
                self._vad.pop()

    def get_current_threshold(self) -> float:
        """Return the Silero speech probability threshold.

        Returns:
            Probability threshold (0.0-1.0).
        """
        return self._threshold

    def get_speech_duration(self) -> float:
        """Return total accumulated audio duration since last reset.

        Returns:
            Duration in seconds.
        """
        return self._total_samples / self._sample_rate

    def get_silence_duration(self) -> float:
        """Not available with Silero VAD.

        Returns:
            Always returns 0.0.
        """
        return 0.0
