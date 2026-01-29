"""Audio recording and processing for asr2clip."""

import io
import tempfile
import wave
from typing import Callable

import numpy as np
import sounddevice as sd
from pydub import AudioSegment

from .utils import is_stop_requested, log, warning


def list_audio_devices():
    """List all available audio input devices."""
    print("Available audio input devices:")
    print("-" * 60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            default_marker = ""
            try:
                default_input = sd.query_devices(kind="input")
                if device["name"] == default_input["name"]:
                    default_marker = " [DEFAULT]"
            except Exception:
                pass
            print(f"  {i}: {device['name']}{default_marker}")
            print(
                f"      Channels: {device['max_input_channels']}, "
                f"Sample Rate: {device['default_samplerate']}"
            )
    print("-" * 60)
    print("\nUse --device <name_or_index> to select a device")
    print("Example: asr2clip --device pulse")
    print("         asr2clip --device 12")


def write_wav(audio_data: np.ndarray, sample_rate: int, channels: int = 1) -> bytes:
    """Write audio data to WAV format bytes using stdlib wave module.

    Args:
        audio_data: Audio data as numpy array (float32, range -1.0 to 1.0).
        sample_rate: Sample rate in Hz.
        channels: Number of audio channels.

    Returns:
        WAV file content as bytes.
    """
    # Flatten if multi-dimensional (e.g., from stereo recording)
    if audio_data.ndim > 1:
        audio_data = audio_data.flatten()

    # Convert float32 to int16
    audio_int16 = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)

    # Convert to bytes using numpy's tobytes (more efficient than struct.pack)
    audio_bytes = audio_int16.tobytes()

    # Write WAV using stdlib wave module
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)

    return buffer.getvalue()


def record_audio(
    sample_rate: int = 16000,
    channels: int = 1,
    device: str | int | None = None,
    callback: Callable[[np.ndarray], None] | None = None,
) -> np.ndarray:
    """Record audio from the microphone until stop is requested.

    Args:
        sample_rate: Sample rate in Hz.
        channels: Number of audio channels.
        device: Audio device name or index, or None for default.
        callback: Optional callback function called with each audio chunk.

    Returns:
        Recorded audio as numpy array.
    """
    audio_chunks = []

    def audio_callback(indata, frames, time, status):
        if status:
            warning(f"Audio status: {status}")
        chunk = indata.copy()
        audio_chunks.append(chunk)
        if callback:
            callback(chunk)

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            device=device,
            callback=audio_callback,
        ):
            while not is_stop_requested():
                sd.sleep(100)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"Recording error: {e}")
        raise

    if audio_chunks:
        return np.concatenate(audio_chunks, axis=0)
    return np.array([], dtype=np.float32)


def save_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> str:
    """Save audio data to a temporary WAV file.

    Args:
        audio_data: Audio data as numpy array.
        sample_rate: Sample rate in Hz.

    Returns:
        Path to the temporary WAV file.
    """
    wav_bytes = write_wav(audio_data, sample_rate)

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.write(wav_bytes)
    temp_file.close()

    return temp_file.name


def convert_audio_to_wav(input_path: str, output_path: str = None) -> str:
    """Convert an audio file to WAV format.

    Args:
        input_path: Path to the input audio file.
        output_path: Optional path for the output WAV file.

    Returns:
        Path to the converted WAV file.
    """
    if output_path is None:
        output_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format="wav")

    return output_path


def get_audio_duration(audio_data: np.ndarray, sample_rate: int = 16000) -> float:
    """Calculate the duration of audio data in seconds.

    Args:
        audio_data: Audio data as numpy array.
        sample_rate: Sample rate in Hz.

    Returns:
        Duration in seconds.
    """
    if len(audio_data) == 0:
        return 0.0
    return len(audio_data) / sample_rate


def calculate_rms(audio_data: np.ndarray) -> float:
    """Calculate the RMS (root mean square) of audio data.

    Args:
        audio_data: Audio data as numpy array.

    Returns:
        RMS value.
    """
    if len(audio_data) == 0:
        return 0.0
    return float(np.sqrt(np.mean(audio_data**2)))
