"""Voice Activity Detection (VAD) for asr2clip.

Simple energy-based VAD using numpy only (no extra dependencies).
"""

import numpy as np

from .utils import info

# Default VAD parameters
DEFAULT_SILENCE_THRESHOLD = 0.01  # RMS threshold for silence
DEFAULT_SILENCE_DURATION = 1.5  # Seconds of silence to trigger transcription
DEFAULT_MIN_SPEECH_DURATION = 0.5  # Minimum speech duration to transcribe
DEFAULT_ADAPTIVE_WINDOW = 5.0  # Seconds of audio to use for adaptive threshold


class VoiceActivityDetector:
    """Energy-based Voice Activity Detector.

    Detects silence in audio stream and triggers transcription when
    speech is followed by a period of silence.

    Supports adaptive threshold that adjusts based on ambient noise levels.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        min_speech_duration: float = DEFAULT_MIN_SPEECH_DURATION,
        adaptive: bool = False,
        adaptive_window: float = DEFAULT_ADAPTIVE_WINDOW,
    ):
        """Initialize the VAD.

        Args:
            sample_rate: Audio sample rate in Hz.
            silence_threshold: RMS threshold below which audio is considered silence.
            silence_duration: Duration of silence (seconds) to trigger transcription.
            min_speech_duration: Minimum speech duration (seconds) to transcribe.
            adaptive: Enable adaptive threshold based on ambient noise.
            adaptive_window: Window size (seconds) for adaptive threshold calculation.
        """
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.base_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.adaptive = adaptive
        self.adaptive_window = adaptive_window

        # State
        self.silence_samples = 0
        self.speech_samples = 0
        self.is_speaking = False

        # Adaptive threshold state
        self.rms_history = []
        self.max_history_samples = int(
            adaptive_window * sample_rate / 1024
        )  # ~1024 samples per chunk

    def reset(self):
        """Reset the VAD state (keeps adaptive threshold history)."""
        self.silence_samples = 0
        self.speech_samples = 0
        self.is_speaking = False

    def reset_adaptive(self):
        """Reset adaptive threshold history."""
        self.rms_history = []
        self.silence_threshold = self.base_threshold

    def update_adaptive_threshold(self, rms: float):
        """Update adaptive threshold based on recent RMS values.

        Uses the lower percentile of recent RMS values as the noise floor,
        then sets threshold slightly above it.

        Args:
            rms: Current RMS value.
        """
        if not self.adaptive:
            return

        self.rms_history.append(rms)

        # Keep only recent history
        if len(self.rms_history) > self.max_history_samples:
            self.rms_history = self.rms_history[-self.max_history_samples :]

        # Need enough samples for reliable estimate
        if len(self.rms_history) < 10:
            return

        # Use 20th percentile as noise floor estimate
        sorted_rms = sorted(self.rms_history)
        noise_floor_idx = int(len(sorted_rms) * 0.2)
        noise_floor = sorted_rms[noise_floor_idx]

        # Set threshold at 2x noise floor, but not below base threshold
        new_threshold = max(noise_floor * 2.0, self.base_threshold * 0.5)

        # Smooth the threshold update
        self.silence_threshold = 0.9 * self.silence_threshold + 0.1 * new_threshold

    def calculate_rms(self, audio_chunk: np.ndarray) -> float:
        """Calculate RMS of audio chunk.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            RMS value.
        """
        if len(audio_chunk) == 0:
            return 0.0
        # Flatten if multi-channel
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.flatten()
        return float(np.sqrt(np.mean(audio_chunk**2)))

    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """Process an audio chunk and detect if transcription should be triggered.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            True if transcription should be triggered (speech followed by silence).
        """
        rms = self.calculate_rms(audio_chunk)
        chunk_samples = (
            len(audio_chunk.flatten()) if audio_chunk.ndim > 1 else len(audio_chunk)
        )

        # Update adaptive threshold
        self.update_adaptive_threshold(rms)

        if rms > self.silence_threshold:
            # Speech detected
            self.speech_samples += chunk_samples
            self.silence_samples = 0
            self.is_speaking = True
        else:
            # Silence detected
            self.silence_samples += chunk_samples

        # Check if we should trigger transcription
        silence_seconds = self.silence_samples / self.sample_rate
        speech_seconds = self.speech_samples / self.sample_rate

        if (
            self.is_speaking
            and silence_seconds >= self.silence_duration
            and speech_seconds >= self.min_speech_duration
        ):
            # Reset state and trigger transcription
            self.reset()
            return True

        return False

    def get_speech_duration(self) -> float:
        """Get the current accumulated speech duration in seconds.

        Returns:
            Speech duration in seconds.
        """
        return self.speech_samples / self.sample_rate

    def get_silence_duration(self) -> float:
        """Get the current accumulated silence duration in seconds.

        Returns:
            Silence duration in seconds.
        """
        return self.silence_samples / self.sample_rate

    def get_current_threshold(self) -> float:
        """Get the current silence threshold.

        Returns:
            Current silence threshold (may differ from initial if adaptive).
        """
        return self.silence_threshold


def calibrate_silence_threshold(
    device: str | int | None = None,
    duration: float = 2.0,
    sample_rate: int = 16000,
) -> float:
    """Calibrate silence threshold by measuring ambient noise.

    Records a short sample of ambient noise and calculates an appropriate
    silence threshold.

    Args:
        device: Audio device name or index.
        duration: Duration to record for calibration (seconds).
        sample_rate: Sample rate in Hz.

    Returns:
        Recommended silence threshold (RMS value).
    """
    import sounddevice as sd

    info(f"Calibrating silence threshold ({duration}s)... Please be quiet.")

    # Record ambient noise
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=device,
    )
    sd.wait()

    # Calculate RMS of ambient noise
    rms = float(np.sqrt(np.mean(audio**2)))

    # Set threshold slightly above ambient noise
    threshold = rms * 2.0

    info(f"Ambient noise RMS: {rms:.4f}")
    info(f"Recommended threshold: {threshold:.4f}")

    return threshold
