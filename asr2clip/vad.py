"""Voice Activity Detection (VAD) for asr2clip.

Multi-feature VAD using numpy only (no extra dependencies).
Combines RMS energy, zero-crossing rate, and spectral features for robust detection.
"""

import numpy as np

from .utils import debug

# Default VAD parameters
DEFAULT_SILENCE_THRESHOLD = 0.01  # RMS threshold for silence
DEFAULT_SILENCE_DURATION = 1.5  # Seconds of silence to trigger transcription
DEFAULT_MIN_SPEECH_DURATION = 0.5  # Minimum speech duration to transcribe
DEFAULT_ADAPTIVE_WINDOW = 5.0  # Seconds of audio to use for adaptive threshold
DEFAULT_MAX_SPEECH_DURATION = 30.0  # Max speech duration before forced transcription
DEFAULT_SPEECH_GAP_TOLERANCE = 0.3  # Max gap in speech before resetting (seconds)

# Speech frequency band (Hz)
SPEECH_FREQ_LOW = 300
SPEECH_FREQ_HIGH = 3000

# Zero-crossing rate threshold (speech typically has lower ZCR than noise)
DEFAULT_ZCR_THRESHOLD = 0.3

# Minimum speech band energy ratio
DEFAULT_SPEECH_BAND_RATIO = 0.2


class VoiceActivityDetector:
    """Multi-feature Voice Activity Detector.

    Detects speech using multiple features:
    - RMS energy: Basic volume detection
    - Zero-crossing rate: Distinguishes speech from noise
    - Spectral band energy: Filters non-speech frequencies

    Triggers transcription when speech is followed by silence.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        min_speech_duration: float = DEFAULT_MIN_SPEECH_DURATION,
        adaptive: bool = False,
        adaptive_window: float = DEFAULT_ADAPTIVE_WINDOW,
        use_spectral: bool = True,
        max_speech_duration: float = DEFAULT_MAX_SPEECH_DURATION,
        speech_gap_tolerance: float = DEFAULT_SPEECH_GAP_TOLERANCE,
    ):
        """Initialize the VAD.

        Args:
            sample_rate: Audio sample rate in Hz.
            silence_threshold: RMS threshold below which audio is considered silence.
            silence_duration: Duration of silence (seconds) to trigger transcription.
            min_speech_duration: Minimum speech duration (seconds) to transcribe.
            adaptive: Enable adaptive threshold based on ambient noise.
            adaptive_window: Window size (seconds) for adaptive threshold calculation.
            use_spectral: Enable spectral analysis for better noise rejection.
            max_speech_duration: Maximum speech duration before forced transcription.
            speech_gap_tolerance: Maximum gap in speech before resetting speech state.
        """
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.base_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.adaptive = adaptive
        self.adaptive_window = adaptive_window
        self.use_spectral = use_spectral
        self.max_speech_duration = max_speech_duration
        self.speech_gap_tolerance = speech_gap_tolerance

        # State
        self.silence_samples = 0
        self.speech_samples = 0
        self.is_speaking = False
        self.total_samples = 0  # Total samples since last transcription

        # Adaptive threshold state
        self.rms_history = []
        self.max_history_samples = int(
            adaptive_window * sample_rate / 1024
        )  # ~1024 samples per chunk

        # ZCR adaptive state
        self.zcr_history = []
        self.zcr_threshold = DEFAULT_ZCR_THRESHOLD

    def reset(self):
        """Reset the VAD state (keeps adaptive threshold history)."""
        self.silence_samples = 0
        self.speech_samples = 0
        self.is_speaking = False
        self.total_samples = 0

    def reset_adaptive(self):
        """Reset adaptive threshold history."""
        self.rms_history = []
        self.zcr_history = []
        self.silence_threshold = self.base_threshold
        self.zcr_threshold = DEFAULT_ZCR_THRESHOLD

    def update_adaptive_threshold(self, rms: float, zcr: float):
        """Update adaptive thresholds based on recent values.

        Uses the lower percentile of recent values as the noise floor,
        then sets threshold slightly above it.

        Args:
            rms: Current RMS value.
            zcr: Current zero-crossing rate.
        """
        if not self.adaptive:
            return

        self.rms_history.append(rms)
        self.zcr_history.append(zcr)

        # Keep only recent history
        if len(self.rms_history) > self.max_history_samples:
            self.rms_history = self.rms_history[-self.max_history_samples :]
            self.zcr_history = self.zcr_history[-self.max_history_samples :]

        # Need enough samples for reliable estimate
        if len(self.rms_history) < 10:
            return

        # RMS: Use 20th percentile as noise floor estimate
        sorted_rms = sorted(self.rms_history)
        noise_floor_idx = int(len(sorted_rms) * 0.2)
        noise_floor = sorted_rms[noise_floor_idx]

        # Set threshold at 2x noise floor, with minimum of 0.001
        new_rms_threshold = max(noise_floor * 2.0, 0.001)

        # ZCR: Use 80th percentile as noise ZCR estimate (noise has higher ZCR)
        sorted_zcr = sorted(self.zcr_history)
        noise_zcr_idx = int(len(sorted_zcr) * 0.8)
        noise_zcr = sorted_zcr[noise_zcr_idx]

        # Set ZCR threshold slightly below noise ZCR
        new_zcr_threshold = min(noise_zcr * 0.9, DEFAULT_ZCR_THRESHOLD)

        # Smooth the threshold updates
        self.silence_threshold = 0.9 * self.silence_threshold + 0.1 * new_rms_threshold
        self.zcr_threshold = 0.9 * self.zcr_threshold + 0.1 * new_zcr_threshold

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

    def calculate_zcr(self, audio_chunk: np.ndarray) -> float:
        """Calculate zero-crossing rate of audio chunk.

        Zero-crossing rate is the rate at which the signal changes sign.
        Speech typically has lower ZCR than noise.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            Zero-crossing rate (0.0 to 1.0).
        """
        if len(audio_chunk) < 2:
            return 0.0
        # Flatten if multi-channel
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.flatten()

        # Count sign changes
        signs = np.sign(audio_chunk)
        sign_changes = np.sum(np.abs(np.diff(signs)) > 0)

        # Normalize by length
        return float(sign_changes / (len(audio_chunk) - 1))

    def calculate_speech_band_ratio(self, audio_chunk: np.ndarray) -> float:
        """Calculate the ratio of energy in speech frequency band.

        Speech is primarily in 300-3000 Hz range. This helps filter out
        low-frequency rumble and high-frequency noise.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            Ratio of energy in speech band (0.0 to 1.0).
        """
        if len(audio_chunk) < 256:
            return 1.0  # Too short for reliable FFT, assume speech

        # Flatten if multi-channel
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.flatten()

        # Compute FFT
        fft = np.fft.rfft(audio_chunk)
        freqs = np.fft.rfftfreq(len(audio_chunk), 1.0 / self.sample_rate)
        power = np.abs(fft) ** 2

        # Calculate total energy
        total_energy = np.sum(power)
        if total_energy == 0:
            return 0.0

        # Calculate energy in speech band
        speech_mask = (freqs >= SPEECH_FREQ_LOW) & (freqs <= SPEECH_FREQ_HIGH)
        speech_energy = np.sum(power[speech_mask])

        return float(speech_energy / total_energy)

    def is_speech(self, audio_chunk: np.ndarray) -> tuple[bool, float, float, float]:
        """Determine if audio chunk contains speech.

        Uses multiple features for robust detection:
        1. RMS energy must exceed threshold
        2. ZCR must be below threshold (speech has lower ZCR than noise)
        3. Speech band energy ratio must be significant (if spectral enabled)

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            Tuple of (is_speech, rms, zcr, band_ratio).
        """
        rms = self.calculate_rms(audio_chunk)
        zcr = self.calculate_zcr(audio_chunk)

        # Check RMS threshold
        if rms <= self.silence_threshold:
            return False, rms, zcr, 0.0

        # Check ZCR (speech has lower ZCR than noise)
        if zcr > self.zcr_threshold:
            return False, rms, zcr, 0.0

        # Check spectral features if enabled
        if self.use_spectral:
            band_ratio = self.calculate_speech_band_ratio(audio_chunk)
            if band_ratio < DEFAULT_SPEECH_BAND_RATIO:
                return False, rms, zcr, band_ratio
        else:
            band_ratio = 1.0

        return True, rms, zcr, band_ratio

    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """Process an audio chunk and detect if transcription should be triggered.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            True if transcription should be triggered (speech followed by silence).
        """
        chunk_samples = (
            len(audio_chunk.flatten()) if audio_chunk.ndim > 1 else len(audio_chunk)
        )
        self.total_samples += chunk_samples

        # Multi-feature speech detection
        speech_detected, rms, zcr, _ = self.is_speech(audio_chunk)

        # Update adaptive thresholds
        self.update_adaptive_threshold(rms, zcr)

        if speech_detected:
            # Speech detected
            self.speech_samples += chunk_samples
            self.silence_samples = 0
            self.is_speaking = True
        else:
            # Silence or noise detected
            self.silence_samples += chunk_samples

            # Check for speech gap tolerance - if silence exceeds gap tolerance
            # but we haven't accumulated enough speech, reset speech state
            gap_seconds = self.silence_samples / self.sample_rate
            speech_seconds = self.speech_samples / self.sample_rate

            if (
                self.is_speaking
                and gap_seconds > self.speech_gap_tolerance
                and speech_seconds < self.min_speech_duration
            ):
                # Short noise burst followed by silence - reset speech state
                self.speech_samples = 0
                self.is_speaking = False

        # Check if we should trigger transcription
        silence_seconds = self.silence_samples / self.sample_rate
        speech_seconds = self.speech_samples / self.sample_rate
        total_seconds = self.total_samples / self.sample_rate

        # Trigger conditions:
        # 1. Normal: speech followed by sufficient silence
        # 2. Forced: max speech duration exceeded
        should_trigger = False

        if self.is_speaking and speech_seconds >= self.min_speech_duration:
            if silence_seconds >= self.silence_duration:
                # Normal trigger: speech followed by silence
                should_trigger = True
            elif total_seconds >= self.max_speech_duration:
                # Forced trigger: max duration exceeded
                should_trigger = True

        if should_trigger:
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
    silence threshold using multiple features.

    Args:
        device: Audio device name or index.
        duration: Duration to record for calibration (seconds).
        sample_rate: Sample rate in Hz.

    Returns:
        Recommended silence threshold (RMS value).
    """
    import sounddevice as sd

    debug(f"Calibrating silence threshold ({duration}s)...")

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

    # Calculate ZCR of ambient noise
    audio_flat = audio.flatten()
    signs = np.sign(audio_flat)
    zcr = float(np.sum(np.abs(np.diff(signs)) > 0) / (len(audio_flat) - 1))

    # Set threshold slightly above ambient noise
    threshold = rms * 2.0

    debug(f"Ambient noise RMS: {rms:.4f}, ZCR: {zcr:.4f}")
    debug(f"Recommended threshold: {threshold:.4f}")

    return threshold
