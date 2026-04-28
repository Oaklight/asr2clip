"""sherpa-onnx ASR engine wrapper for SenseVoice inference."""

import io
from dataclasses import dataclass

import numpy as np
from pydub import AudioSegment

import sherpa_onnx

SAMPLE_RATE = 16000


@dataclass
class TranscriptionResult:
    """Result from ASR inference."""

    text: str
    duration: float


class ASREngine:
    """Wraps sherpa-onnx OfflineRecognizer for SenseVoice inference.

    Args:
        model_path: Path to the ONNX model file.
        tokens_path: Path to the tokens.txt file.
        num_threads: Number of inference threads.
    """

    def __init__(self, model_path: str, tokens_path: str, num_threads: int = 4):
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=model_path,
            tokens=tokens_path,
            use_itn=True,
            num_threads=num_threads,
        )

    def transcribe(
        self, audio_data: bytes, filename: str = "audio.wav"
    ) -> TranscriptionResult:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio file bytes (any format supported by pydub/ffmpeg).
            filename: Original filename, used to determine audio format.

        Returns:
            TranscriptionResult with text and duration.
        """
        audio_array, sr = self._audio_bytes_to_numpy(audio_data, filename)
        duration = len(audio_array) / sr

        stream = self.recognizer.create_stream()
        stream.accept_waveform(sr, audio_array)
        self.recognizer.decode_stream(stream)

        text = stream.result.text.strip()
        return TranscriptionResult(text=text, duration=duration)

    @staticmethod
    def _audio_bytes_to_numpy(
        audio_data: bytes, filename: str
    ) -> tuple[np.ndarray, int]:
        """Convert audio bytes to mono float32 numpy array.

        Args:
            audio_data: Raw audio file bytes.
            filename: Filename for format detection.

        Returns:
            Tuple of (audio_array, sample_rate).
        """
        buf = io.BytesIO(audio_data)

        # Determine format from extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        fmt_map = {
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
        fmt = fmt_map.get(ext, None)

        if fmt:
            audio = AudioSegment.from_file(buf, format=fmt)
        else:
            audio = AudioSegment.from_file(buf)

        # Convert to mono 16kHz
        audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE)

        # Extract raw samples as float32 normalized to [-1, 1]
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        samples /= 2 ** (audio.sample_width * 8 - 1)

        return samples, SAMPLE_RATE
