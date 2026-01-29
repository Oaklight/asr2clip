"""Voice Activity Detection (VAD) for asr2clip.

Simple energy-based VAD using numpy only (no extra dependencies).
"""

import numpy as np

from .utils import log

# Default VAD parameters
DEFAULT_SILENCE_THRESHOLD = 0.01  # RMS threshold for silence
DEFAULT_SILENCE_DURATION = 1.5  # Seconds of silence to trigger transcription
DEFAULT_MIN_SPEECH_DURATION = 0.5  # Minimum speech duration to transcribe


class VoiceActivityDetector:
    """Energy-based Voice Activity Detector.

    Detects silence in audio stream and triggers transcription when
    speech is followed by a period of silence.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        min_speech_duration: float = DEFAULT_MIN_SPEECH_DURATION,
    ):
        """Initialize the VAD.

        Args:
            sample_rate: Audio sample rate in Hz.
            silence_threshold: RMS threshold below which audio is considered silence.
            silence_duration: Duration of silence (seconds) to trigger transcription.
            min_speech_duration: Minimum speech duration (seconds) to transcribe.
        """
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration

        # State
        self.silence_samples = 0
        self.speech_samples = 0
        self.is_speaking = False

    def reset(self):
        """Reset the VAD state."""
        self.silence_samples = 0
        self.speech_samples = 0
        self.is_speaking = False

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

    log(f"Calibrating silence threshold ({duration}s)... Please be quiet.")

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

    log(f"Ambient noise RMS: {rms:.4f}")
    log(f"Recommended threshold: {threshold:.4f}")

    return threshold
