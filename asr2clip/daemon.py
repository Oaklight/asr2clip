"""Continuous recording (daemon) mode for asr2clip."""

import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

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
from .vad import VoiceActivityDetector

# RMS threshold for silence filtering in interval-only mode (no VAD)
_INTERVAL_SILENCE_RMS = 0.005


@dataclass
class TranscriptionTask:
    """A transcription task with sequence number for ordering."""

    sequence: int
    audio_path: str
    duration: float
    timestamp: float


@dataclass
class RecorderConfig:
    """Configuration for the continuous recorder."""

    api_key: str
    api_base_url: str
    model_name: str
    org_id: str | None = None
    device: str | int | None = None
    interval: float = 30.0
    output_file: str | None = None
    sample_rate: int = 16000
    vad_enabled: bool = False
    silence_threshold: float = 0.5
    silence_duration: float = 1.5
    min_transcribe_interval: float = 0.5
    max_concurrent_transcriptions: int = 3


@dataclass
class RecorderState:
    """Mutable state for the continuous recorder."""

    audio_chunks: list = field(default_factory=list)
    chunks_lock: threading.Lock = field(default_factory=threading.Lock)
    last_transcribe_time: float = field(default_factory=time.time)
    task_sequence: int = 0
    task_sequence_lock: threading.Lock = field(default_factory=threading.Lock)
    result_queue: queue.PriorityQueue = field(default_factory=queue.PriorityQueue)
    next_output_sequence: int = 0
    next_output_lock: threading.Lock = field(default_factory=threading.Lock)
    pending_tasks: dict = field(default_factory=dict)
    should_transcribe: threading.Event = field(default_factory=threading.Event)
    vad: VoiceActivityDetector | None = None


def _log_startup(cfg: RecorderConfig):
    """Log startup information.

    Args:
        cfg: Recorder configuration.
    """
    if cfg.vad_enabled:
        info(
            f"Starting continuous recording with VAD "
            f"(threshold: {cfg.silence_threshold}, silence: {cfg.silence_duration}s)"
        )
    else:
        info(f"Starting continuous recording mode (interval: {cfg.interval}s)")
    info("Press Ctrl+C to stop")
    print_separator()


def _make_audio_callback(state: RecorderState):
    """Create the audio input stream callback.

    Args:
        state: Recorder state.

    Returns:
        Callback function for sounddevice.InputStream.
    """

    def audio_callback(indata, frames, time_info, status):
        if status:
            warning(f"Audio status: {status}")
        with state.chunks_lock:
            state.audio_chunks.append(indata.copy())
        if state.vad is not None and state.vad.process_chunk(indata):
            state.should_transcribe.set()

    return audio_callback


def _process_transcription(
    task: TranscriptionTask,
    cfg: RecorderConfig,
) -> tuple[int, str | None, str | None]:
    """Process a transcription task.

    Args:
        task: The transcription task to process.
        cfg: Recorder configuration.

    Returns:
        Tuple of (sequence, text, error_message).
    """
    try:
        text = transcribe_audio(
            task.audio_path,
            cfg.api_key,
            cfg.api_base_url,
            cfg.model_name,
            cfg.org_id,
            raise_on_error=True,
        )
        return (task.sequence, text, None)
    except TranscriptionError as e:
        return (task.sequence, None, str(e))
    finally:
        try:
            os.unlink(task.audio_path)
        except Exception:
            pass


def _run_output_worker(state: RecorderState, output_file: str | None):
    """Output transcription results in order.

    Args:
        state: Recorder state.
        output_file: Optional file to append transcripts to.
    """
    while not is_stop_requested():
        try:
            sequence, text, error = state.result_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        with state.next_output_lock:
            while sequence != state.next_output_sequence and not is_stop_requested():
                time.sleep(0.01)

            if is_stop_requested():
                break

            _output_single_result(text, error, output_file)
            state.next_output_sequence += 1


def _output_single_result(text: str | None, error: str | None, output_file: str | None):
    """Output a single transcription result.

    Args:
        text: Transcribed text (if successful).
        error: Error message (if failed).
        output_file: Optional file to append transcripts to.
    """
    if error:
        print(f"\r{RED}✗{RESET} Failed: {error}" + " " * 20, flush=True)
    elif text and text.strip():
        print(f"\r{GREEN}✓{RESET} Transcribed" + " " * 30, flush=True)
        output_transcript(text, to_clipboard=True, to_stdout=True, to_file=output_file)
    else:
        print(f"\r{YELLOW}○{RESET} (no speech)" + " " * 30, flush=True)


def _transcribe_chunks(
    cfg: RecorderConfig,
    state: RecorderState,
    executor: ThreadPoolExecutor,
    skip_silence_check: bool = False,
):
    """Transcribe accumulated audio chunks asynchronously.

    Args:
        cfg: Recorder configuration.
        state: Recorder state.
        executor: Thread pool executor for async transcription.
        skip_silence_check: If True, skip the silence check.
    """
    if time.time() - state.last_transcribe_time < cfg.min_transcribe_interval:
        return

    with state.chunks_lock:
        if not state.audio_chunks:
            return
        audio_data = np.concatenate(state.audio_chunks, axis=0)
        state.audio_chunks = []

    if state.vad is not None:
        state.vad.reset()

    duration = get_audio_duration(audio_data, cfg.sample_rate)
    if duration < 0.5:
        return

    if not skip_silence_check and state.vad is None:
        rms = calculate_rms(audio_data)
        if rms < _INTERVAL_SILENCE_RMS:
            state.last_transcribe_time = time.time()
            return

    temp_path = save_audio(audio_data, cfg.sample_rate)

    with state.task_sequence_lock:
        seq = state.task_sequence
        state.task_sequence += 1

    print(
        f"\n{CYAN}●{RESET} Recording {duration:.1f}s → {YELLOW}⟳{RESET} Sending #{seq}...",
        end="",
        flush=True,
    )

    task = TranscriptionTask(
        sequence=seq, audio_path=temp_path, duration=duration, timestamp=time.time()
    )

    def task_callback(future):
        try:
            result = future.result()
            state.result_queue.put(result)
        except Exception as e:
            state.result_queue.put((task.sequence, None, str(e)))
        finally:
            with state.task_sequence_lock:
                state.pending_tasks.pop(task.sequence, None)

    future = executor.submit(_process_transcription, task, cfg)
    future.add_done_callback(task_callback)

    with state.task_sequence_lock:
        state.pending_tasks[seq] = future

    state.last_transcribe_time = time.time()


def _run_recording_loop(cfg: RecorderConfig, state: RecorderState, executor):
    """Run the main recording loop.

    Args:
        cfg: Recorder configuration.
        state: Recorder state.
        executor: Thread pool executor.
    """
    import sounddevice as sd

    audio_callback = _make_audio_callback(state)

    try:
        with sd.InputStream(
            samplerate=cfg.sample_rate,
            channels=1,
            dtype="float32",
            device=cfg.device,
            callback=audio_callback,
        ):
            while not is_stop_requested():
                if cfg.vad_enabled:
                    _handle_vad_iteration(cfg, state, executor)
                else:
                    sd.sleep(100)
                    if time.time() - state.last_transcribe_time >= cfg.interval:
                        _transcribe_chunks(
                            cfg, state, executor, skip_silence_check=False
                        )
    except KeyboardInterrupt:
        pass


def _handle_vad_iteration(
    cfg: RecorderConfig, state: RecorderState, executor: ThreadPoolExecutor
):
    """Handle a single VAD-mode iteration.

    Args:
        cfg: Recorder configuration.
        state: Recorder state.
        executor: Thread pool executor.
    """
    triggered = state.should_transcribe.wait(timeout=0.1)
    if triggered:
        state.should_transcribe.clear()
        _transcribe_chunks(cfg, state, executor, skip_silence_check=True)
    elif time.time() - state.last_transcribe_time >= cfg.interval:
        _transcribe_chunks(cfg, state, executor, skip_silence_check=False)


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
    silence_threshold: float = 0.5,
    silence_duration: float = 1.5,
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
        silence_threshold: Silero speech probability threshold (0.0-1.0).
        silence_duration: Duration of silence to trigger transcription.
        min_transcribe_interval: Minimum interval between transcription triggers (seconds).
        max_concurrent_transcriptions: Maximum number of concurrent transcription requests.
    """
    setup_signal_handlers(daemon_mode=True)

    cfg = RecorderConfig(
        api_key=api_key,
        api_base_url=api_base_url,
        model_name=model_name,
        org_id=org_id,
        device=device,
        interval=interval,
        output_file=output_file,
        sample_rate=sample_rate,
        vad_enabled=vad_enabled,
        silence_threshold=silence_threshold,
        silence_duration=silence_duration,
        min_transcribe_interval=min_transcribe_interval,
        max_concurrent_transcriptions=max_concurrent_transcriptions,
    )

    _log_startup(cfg)

    state = RecorderState()
    if vad_enabled:
        state.vad = VoiceActivityDetector(
            sample_rate=sample_rate,
            threshold=cfg.silence_threshold,
            silence_duration=silence_duration,
        )

    executor = ThreadPoolExecutor(max_workers=max_concurrent_transcriptions)

    output_thread = threading.Thread(
        target=_run_output_worker, args=(state, output_file), daemon=True
    )
    output_thread.start()

    _run_recording_loop(cfg, state, executor)

    log("\nProcessing remaining audio...")
    _transcribe_chunks(cfg, state, executor, skip_silence_check=False)

    if state.pending_tasks:
        log("Waiting for pending transcriptions...")
        executor.shutdown(wait=True, cancel_futures=False)
    else:
        executor.shutdown(wait=False, cancel_futures=True)

    if output_thread.is_alive():
        output_thread.join(timeout=2.0)

    log("Continuous recording stopped.")
