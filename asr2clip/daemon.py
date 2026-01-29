"""Continuous recording (daemon) mode for asr2clip."""

import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from .audio import calculate_rms, get_audio_duration, save_audio
from .logging import CYAN, GREEN, RED, RESET, YELLOW
from .output import output_transcript
from .transcribe import TranscriptionError, transcribe_audio
from .utils import (
    info,
    is_stop_requested,
    log,
    print_separator,
    setup_signal_handlers,
    warning,
)
from .vad import VoiceActivityDetector, calibrate_silence_threshold


@dataclass
class TranscriptionTask:
    """A transcription task with sequence number for ordering."""

    sequence: int
    audio_path: str
    duration: float
    timestamp: float


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
    min_transcribe_interval: float = 0.5,
    max_concurrent_transcriptions: int = 3,
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
        min_transcribe_interval: Minimum interval between transcription triggers (seconds).
        max_concurrent_transcriptions: Maximum number of concurrent transcription requests.
    """
    import sounddevice as sd

    setup_signal_handlers(daemon_mode=True)

    # Auto-calibrate threshold if adaptive mode is enabled and no manual threshold set
    if vad_enabled and adaptive_threshold and silence_threshold == 0.01:
        info("Calibrating ambient noise level...")
        calibrated = calibrate_silence_threshold(
            device=device, duration=1.0, sample_rate=sample_rate
        )
        # Use calibrated threshold, but ensure minimum sensitivity
        silence_threshold = max(calibrated, 0.001)

    if vad_enabled:
        info(f"Starting continuous recording with VAD (silence: {silence_duration}s)")
        if adaptive_threshold:
            info(f"Adaptive threshold enabled (base: {silence_threshold:.4f})")
        else:
            info(f"Silence threshold: {silence_threshold:.4f}")
    else:
        info(f"Starting continuous recording mode (interval: {interval}s)")
    info("Press Ctrl+C to stop")
    print_separator()

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

    # Async transcription setup
    task_sequence = 0
    task_sequence_lock = threading.Lock()
    result_queue = queue.PriorityQueue()  # (sequence, result)
    next_output_sequence = 0
    next_output_lock = threading.Lock()
    executor = ThreadPoolExecutor(max_workers=max_concurrent_transcriptions)
    pending_tasks = {}  # sequence -> Future

    def audio_callback(indata, frames, time_info, status):
        if status:
            warning(f"Audio status: {status}")
        with chunks_lock:
            audio_chunks.append(indata.copy())

        # Check VAD if enabled
        if vad is not None:
            if vad.process_chunk(indata):
                should_transcribe.set()

    def process_transcription(
        task: TranscriptionTask,
    ) -> tuple[int, str | None, str | None]:
        """Process a transcription task asynchronously.

        Args:
            task: The transcription task to process.

        Returns:
            Tuple of (sequence, text, error_message).
        """
        try:
            text = transcribe_audio(
                task.audio_path,
                api_key,
                api_base_url,
                model_name,
                org_id,
                raise_on_error=True,
            )
            return (task.sequence, text, None)
        except TranscriptionError as e:
            return (task.sequence, None, str(e))
        finally:
            # Clean up temp file
            try:
                os.unlink(task.audio_path)
            except Exception:
                pass

    def output_worker():
        """Worker thread to output results in order."""
        nonlocal next_output_sequence

        while not is_stop_requested():
            try:
                # Wait for next result with timeout
                sequence, text, error = result_queue.get(timeout=0.1)

                # Wait until it's this sequence's turn
                with next_output_lock:
                    while sequence != next_output_sequence and not is_stop_requested():
                        time.sleep(0.01)

                    if is_stop_requested():
                        break

                    # Output the result
                    if error:
                        print(f"\r{RED}✗{RESET} Failed: {error}" + " " * 20, flush=True)
                    elif text and text.strip():
                        print(f"\r{GREEN}✓{RESET} Transcribed" + " " * 30, flush=True)
                        output_transcript(
                            text,
                            to_clipboard=True,
                            to_stdout=True,
                            to_file=output_file,
                        )
                    else:
                        print(f"\r{YELLOW}○{RESET} (no speech)" + " " * 30, flush=True)

                    next_output_sequence += 1

            except queue.Empty:
                continue

    def transcribe_chunks(reason: str = "interval", skip_silence_check: bool = False):
        """Transcribe accumulated audio chunks asynchronously.

        Args:
            reason: Reason for transcription (for logging).
            skip_silence_check: If True, skip the silence check (used when VAD triggered).
        """
        nonlocal audio_chunks, last_transcribe_time, task_sequence

        # Check minimum interval
        if time.time() - last_transcribe_time < min_transcribe_interval:
            return

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
            return  # Too short, skip silently

        # Check if audio has any sound (skip silent recordings)
        # But skip this check if VAD already confirmed speech
        if not skip_silence_check:
            rms = calculate_rms(audio_data)
            current_threshold = (
                vad.get_current_threshold() if vad else silence_threshold
            )
            if rms < current_threshold:
                # Silent, skip without verbose logging
                last_transcribe_time = time.time()
                return

        # Save to temp file
        temp_path = save_audio(audio_data, sample_rate)

        # Get sequence number
        with task_sequence_lock:
            seq = task_sequence
            task_sequence += 1

        # Show recording complete indicator (with newline to avoid overlap)
        print(
            f"\n{CYAN}●{RESET} Recording {duration:.1f}s → {YELLOW}⟳{RESET} Sending #{seq}...",
            end="",
            flush=True,
        )

        # Create task and submit
        task = TranscriptionTask(
            sequence=seq,
            audio_path=temp_path,
            duration=duration,
            timestamp=time.time(),
        )

        def task_callback(future):
            """Callback when transcription completes."""
            try:
                result = future.result()
                result_queue.put(result)
            except Exception as e:
                result_queue.put((task.sequence, None, str(e)))
            finally:
                # Remove from pending tasks
                with task_sequence_lock:
                    pending_tasks.pop(task.sequence, None)

        future = executor.submit(process_transcription, task)
        future.add_done_callback(task_callback)

        with task_sequence_lock:
            pending_tasks[seq] = future

        last_transcribe_time = time.time()

    # Start output worker thread
    output_thread = threading.Thread(target=output_worker, daemon=True)
    output_thread.start()

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
                        # VAD confirmed speech, skip silence check
                        transcribe_chunks(
                            reason="speech detected", skip_silence_check=True
                        )
                    # Also check max interval (but check for silence)
                    elif time.time() - last_transcribe_time >= interval:
                        transcribe_chunks(
                            reason="max interval", skip_silence_check=False
                        )
                else:
                    sd.sleep(100)
                    # Check if it's time to transcribe
                    if time.time() - last_transcribe_time >= interval:
                        transcribe_chunks(reason="interval", skip_silence_check=False)

    except KeyboardInterrupt:
        pass

    # Transcribe any remaining audio
    log("\nProcessing remaining audio...")
    transcribe_chunks(reason="final", skip_silence_check=False)

    # Wait for all pending tasks to complete
    if pending_tasks:
        log("Waiting for pending transcriptions...")
        executor.shutdown(wait=True, cancel_futures=False)
    else:
        executor.shutdown(wait=False, cancel_futures=True)

    # Wait for output worker to finish
    if output_thread.is_alive():
        output_thread.join(timeout=2.0)

    log("Continuous recording stopped.")
