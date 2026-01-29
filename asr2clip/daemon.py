"""Continuous recording (daemon) mode for asr2clip."""

import os
import threading
import time

import numpy as np

from .audio import calculate_rms, get_audio_duration, save_audio
from .output import output_transcript
from .transcribe import TranscriptionError, transcribe_audio
from .utils import is_stop_requested, log, setup_signal_handlers
from .vad import VoiceActivityDetector


def continuous_recording(
    api_key: str,
    api_base_url: str,
    model_name: str,
    org_id: str | None = None,
    device: str | int | None = None,
    interval: float = 30.0,
    output_file: str | None = None,
    sample_rate: int = 16000,
    vad_enabled: bool = False,
    silence_threshold: float = 0.01,
    silence_duration: float = 1.5,
    adaptive_threshold: bool = False,
):
    """Run continuous recording mode with periodic transcription.

    Records audio continuously and transcribes at regular intervals or
    when silence is detected (if VAD is enabled).
    Press Ctrl+C once to stop.

    Args:
        api_key: API key for authentication.
        api_base_url: Base URL of the API.
        model_name: Name of the model to use.
        org_id: Optional organization ID.
        device: Audio device name or index.
        interval: Transcription interval in seconds (used as max interval with VAD).
        output_file: Optional file to append transcripts to.
        sample_rate: Sample rate in Hz.
        vad_enabled: Enable voice activity detection.
        silence_threshold: RMS threshold for silence detection.
        silence_duration: Duration of silence to trigger transcription.
        adaptive_threshold: Enable adaptive threshold based on ambient noise.
    """
    import sounddevice as sd

    setup_signal_handlers(daemon_mode=True)

    if vad_enabled:
        log(f"Starting continuous recording with VAD (silence: {silence_duration}s)")
        if adaptive_threshold:
            log(f"Adaptive threshold enabled (base: {silence_threshold:.4f})")
        else:
            log(f"Silence threshold: {silence_threshold:.4f}")
    else:
        log(f"Starting continuous recording mode (interval: {interval}s)")
    log("Press Ctrl+C to stop")
    log("-" * 40)

    audio_chunks = []
    chunks_lock = threading.Lock()
    last_transcribe_time = time.time()

    # Initialize VAD if enabled
    vad = None
    if vad_enabled:
        vad = VoiceActivityDetector(
            sample_rate=sample_rate,
            silence_threshold=silence_threshold,
            silence_duration=silence_duration,
            adaptive=adaptive_threshold,
        )

    should_transcribe = threading.Event()

    def audio_callback(indata, frames, time_info, status):
        if status:
            log(f"Audio status: {status}")
        with chunks_lock:
            audio_chunks.append(indata.copy())

        # Check VAD if enabled
        if vad is not None:
            if vad.process_chunk(indata):
                should_transcribe.set()

    def transcribe_chunks(reason: str = "interval"):
        """Transcribe accumulated audio chunks."""
        nonlocal audio_chunks, last_transcribe_time

        with chunks_lock:
            if not audio_chunks:
                return
            audio_data = np.concatenate(audio_chunks, axis=0)
            audio_chunks = []

        # Reset VAD state
        if vad is not None:
            vad.reset()

        duration = get_audio_duration(audio_data, sample_rate)
        if duration < 0.5:
            log("Audio too short, skipping...")
            return

        # Check if audio has any sound (skip silent recordings)
        rms = calculate_rms(audio_data)
        current_threshold = vad.get_current_threshold() if vad else silence_threshold
        if rms < current_threshold:
            log(
                f"Audio is silent (RMS: {rms:.4f} < {current_threshold:.4f}), skipping API call..."
            )
            last_transcribe_time = time.time()
            return

        log(f"Transcribing {duration:.1f}s of audio ({reason})...")

        # Save to temp file
        temp_path = save_audio(audio_data, sample_rate)

        try:
            text = transcribe_audio(
                temp_path,
                api_key,
                api_base_url,
                model_name,
                org_id,
                raise_on_error=True,
            )

            if text.strip():
                output_transcript(
                    text,
                    to_clipboard=True,
                    to_stdout=True,
                    to_file=output_file,
                )
            else:
                log("(No speech detected)")

        except TranscriptionError as e:
            log(f"Transcription failed: {e}")

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        last_transcribe_time = time.time()

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            device=device,
            callback=audio_callback,
        ):
            while not is_stop_requested():
                # Wait for either VAD trigger or timeout
                if vad_enabled:
                    triggered = should_transcribe.wait(timeout=0.1)
                    if triggered:
                        should_transcribe.clear()
                        transcribe_chunks(reason="silence detected")
                    # Also check max interval
                    elif time.time() - last_transcribe_time >= interval:
                        transcribe_chunks(reason="max interval")
                else:
                    sd.sleep(100)
                    # Check if it's time to transcribe
                    if time.time() - last_transcribe_time >= interval:
                        transcribe_chunks(reason="interval")

    except KeyboardInterrupt:
        pass

    # Transcribe any remaining audio
    log("\nProcessing remaining audio...")
    transcribe_chunks(reason="final")

    log("Continuous recording stopped.")
