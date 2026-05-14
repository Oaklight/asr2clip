"""Lazy-converting audio input container for ASR engines.

AudioInput holds audio in its original representation (bytes, file path,
or numpy array) and converts to other formats on demand.  Conversions are
cached so each target format is computed at most once.
"""

from __future__ import annotations

import io
import os
import tempfile

import numpy as np
from pydub import AudioSegment

SAMPLE_RATE = 16000

# Extension → pydub format name
_FMT_MAP: dict[str, str] = {
    "wav": "wav",
    "mp3": "mp3",
    "flac": "flac",
    "ogg": "ogg",
    "m4a": "m4a",
    "mp4": "mp4",
    "mpeg": "mp3",
    "mpga": "mp3",
    "webm": "webm",
}


class AudioInput:
    """Lazy-converting audio input container.

    Holds audio in its original representation and converts on demand.
    Conversions are cached — each format is computed at most once.

    Create instances via the ``from_*`` classmethods::

        audio = AudioInput.from_file("recording.wav")
        audio = AudioInput.from_bytes(raw_bytes)
        audio = AudioInput.from_numpy(samples, sample_rate=16000)

    Then let the engine retrieve whichever format it needs::

        samples, sr = audio.as_numpy()   # zero-copy if created from numpy
        path = audio.as_file()           # zero-copy if created from file
        data = audio.as_bytes()          # zero-copy if created from bytes
    """

    __slots__ = (
        "_bytes",
        "_file_path",
        "_owns_file",
        "_samples",
        "_sample_rate",
        "_filename",
        "_cached_bytes",
        "_cached_file",
        "_cached_numpy",
    )

    def __init__(self) -> None:
        # Original data (exactly one will be set by from_* methods)
        self._bytes: bytes | None = None
        self._file_path: str | None = None
        self._owns_file: bool = False
        self._samples: np.ndarray | None = None
        self._sample_rate: int = SAMPLE_RATE
        self._filename: str = "audio.wav"

        # Cached conversions
        self._cached_bytes: bytes | None = None
        self._cached_file: str | None = None
        self._cached_numpy: tuple[np.ndarray, int] | None = None

    # -- constructors ----------------------------------------------------------

    @classmethod
    def from_bytes(cls, data: bytes, filename: str = "audio.wav") -> AudioInput:
        """Create from raw audio file bytes.

        Args:
            data: Raw audio file content (WAV, MP3, etc.).
            filename: Original filename, used for format detection.

        Returns:
            AudioInput backed by bytes.
        """
        ai = cls()
        ai._bytes = data
        ai._filename = filename
        return ai

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> AudioInput:
        """Create from a file path on disk.

        The file is **not** read eagerly — it will be read only when a
        conversion to bytes or numpy is requested.

        Args:
            path: Path to an audio file.

        Returns:
            AudioInput backed by a file path.
        """
        ai = cls()
        p = str(path)
        ai._file_path = p
        ai._filename = os.path.basename(p)
        return ai

    @classmethod
    def from_numpy(
        cls,
        samples: np.ndarray,
        sample_rate: int = SAMPLE_RATE,
    ) -> AudioInput:
        """Create from a numpy array of audio samples.

        Args:
            samples: Float32 audio samples, mono, range [-1.0, 1.0].
            sample_rate: Sample rate in Hz.

        Returns:
            AudioInput backed by a numpy array.
        """
        ai = cls()
        ai._samples = samples
        ai._sample_rate = sample_rate
        ai._filename = "audio.wav"
        return ai

    # -- accessors -------------------------------------------------------------

    @property
    def filename(self) -> str:
        """Original filename (for format detection and HTTP uploads)."""
        return self._filename

    # -- converters ------------------------------------------------------------

    def as_bytes(self) -> bytes:
        """Return audio as raw file bytes (WAV format if converted).

        Returns:
            Audio file content as bytes.
        """
        # Already bytes
        if self._bytes is not None:
            return self._bytes

        # Check cache
        if self._cached_bytes is not None:
            return self._cached_bytes

        if self._file_path is not None:
            # Read from file
            with open(self._file_path, "rb") as f:
                self._cached_bytes = f.read()
            return self._cached_bytes

        if self._samples is not None:
            # Convert numpy → WAV bytes
            self._cached_bytes = _numpy_to_wav_bytes(self._samples, self._sample_rate)
            return self._cached_bytes

        raise ValueError("AudioInput has no audio data")

    def as_file(self) -> str:
        """Return audio as a file path.

        If the audio was not created from a file, a temporary file is
        written and its path is returned.  Temporary files are cleaned
        up when :meth:`cleanup` is called or the object is garbage-collected.

        Returns:
            Path to an audio file on disk.
        """
        # Already a file
        if self._file_path is not None:
            return self._file_path

        # Check cache
        if self._cached_file is not None:
            return self._cached_file

        # Write bytes to temp file
        data = self.as_bytes()
        ext = _ext_from_filename(self._filename)
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tmp.write(data)
            tmp.close()
        except Exception:
            tmp.close()
            os.unlink(tmp.name)
            raise

        self._cached_file = tmp.name
        self._owns_file = True
        return self._cached_file

    def as_numpy(self) -> tuple[np.ndarray, int]:
        """Return audio as a mono float32 numpy array at 16 kHz.

        Returns:
            Tuple of (samples, sample_rate).
        """
        # Already numpy
        if self._samples is not None:
            return self._samples, self._sample_rate

        # Check cache
        if self._cached_numpy is not None:
            return self._cached_numpy

        # Convert from bytes (or read file first)
        data = self.as_bytes()
        samples, sr = _bytes_to_numpy(data, self._filename)
        self._cached_numpy = (samples, sr)
        return samples, sr

    # -- cleanup ---------------------------------------------------------------

    def cleanup(self) -> None:
        """Remove any temporary files created by :meth:`as_file`."""
        if self._cached_file is not None and self._owns_file:
            try:
                os.unlink(self._cached_file)
            except OSError:
                pass
            self._cached_file = None

    def __del__(self) -> None:
        self.cleanup()


# -- internal conversion helpers ----------------------------------------------


def _ext_from_filename(filename: str) -> str:
    """Extract file extension including the dot."""
    _, ext = os.path.splitext(filename)
    return ext or ".wav"


def _numpy_to_wav_bytes(
    samples: np.ndarray, sample_rate: int, channels: int = 1
) -> bytes:
    """Convert float32 numpy array to WAV bytes.

    Args:
        samples: Float32 audio samples.
        sample_rate: Sample rate in Hz.
        channels: Number of channels.

    Returns:
        WAV file content as bytes.
    """
    import wave

    if samples.ndim > 1:
        samples = samples.flatten()

    audio_int16 = np.clip(samples * 32767, -32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())

    return buf.getvalue()


def _bytes_to_numpy(audio_data: bytes, filename: str) -> tuple[np.ndarray, int]:
    """Convert audio bytes to mono float32 numpy array at 16 kHz.

    Args:
        audio_data: Raw audio file bytes.
        filename: Filename for format detection.

    Returns:
        Tuple of (samples_float32, sample_rate).
    """
    buf = io.BytesIO(audio_data)

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    fmt = _FMT_MAP.get(ext)

    if fmt:
        audio = AudioSegment.from_file(buf, format=fmt)
    else:
        audio = AudioSegment.from_file(buf)

    audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE)

    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    samples /= 2 ** (audio.sample_width * 8 - 1)

    return samples, SAMPLE_RATE
