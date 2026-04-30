"""sherpa-onnx ASR engine with multi-model support and per-request parameters."""

import io
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydub import AudioSegment

import sherpa_onnx

from .model_registry import ModelConfig

logger = logging.getLogger("asr2clip.local_asr")

SAMPLE_RATE = 16000

# Model types whose language is set at recognizer creation time
_LANG_AT_INIT_TYPES = frozenset({"sense_voice", "whisper"})

# sherpa-onnx factory method name for each model type
_FACTORY_MAP: dict[str, str] = {
    "sense_voice": "from_sense_voice",
    "whisper": "from_whisper",
    "paraformer": "from_paraformer",
    "transducer": "from_transducer",
}

# Mapping from logical file names to sherpa-onnx factory parameter names.
# Each model type has its own mapping.
_FILE_PARAM_MAP: dict[str, dict[str, str]] = {
    "sense_voice": {"model": "model", "tokens": "tokens"},
    "whisper": {"encoder": "encoder", "decoder": "decoder", "tokens": "tokens"},
    "paraformer": {"paraformer": "paraformer", "tokens": "tokens"},
    "transducer": {
        "encoder": "encoder",
        "decoder": "decoder",
        "joiner": "joiner",
        "tokens": "tokens",
    },
}


@dataclass
class TranscriptionResult:
    """Result from ASR inference."""

    text: str
    duration: float


class ASREngine:
    """Wraps sherpa-onnx OfflineRecognizer with multi-model and per-request support.

    For model types whose ``language`` is fixed at recognizer creation time
    (sense_voice, whisper), the engine maintains an LRU cache of recognizer
    instances keyed by language string.

    Args:
        config: Model configuration from the registry.
        num_threads: Number of inference threads.
        recognizer_cache_size: Max cached recognizers per language (LRU).
    """

    def __init__(
        self,
        config: ModelConfig,
        num_threads: int = 4,
        recognizer_cache_size: int = 3,
    ) -> None:
        self._config = config
        self._num_threads = num_threads
        self._cache_size = recognizer_cache_size

        # Resolve absolute file paths for each logical file name
        # (done once; paths stored for recognizer creation)
        self._file_paths: dict[str, str] = {}

        # LRU cache: language -> recognizer (only for _LANG_AT_INIT_TYPES)
        self._recognizers: OrderedDict[str, sherpa_onnx.OfflineRecognizer] = (
            OrderedDict()
        )

        # For types that don't need language caching, a single recognizer
        self._recognizer: sherpa_onnx.OfflineRecognizer | None = None

    # -- public API ----------------------------------------------------------

    @classmethod
    def from_model_config(
        cls,
        config: ModelConfig,
        model_dir: str | os.PathLike[str],
        num_threads: int = 4,
        recognizer_cache_size: int = 3,
    ) -> "ASREngine":
        """Create an engine from a ModelConfig.

        Args:
            config: Model configuration.
            model_dir: Absolute path to the model directory.
            num_threads: Inference threads.
            recognizer_cache_size: Max language-specific recognizers to cache.

        Returns:
            Initialized ASREngine.
        """
        engine = cls(config, num_threads, recognizer_cache_size)
        md = Path(model_dir)

        # Build file path mapping
        param_map = _FILE_PARAM_MAP.get(config.type, {})
        for logical_name, factory_param in param_map.items():
            filename = config.files.get(logical_name, "")
            if filename:
                engine._file_paths[factory_param] = str(md / filename)

        # Pre-create the default recognizer
        default_lang = str(config.options.get("language", ""))
        engine._get_or_create_recognizer(default_lang)

        return engine

    def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
        prompt: str | None = None,
        temperature: float | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio file bytes (any format supported by pydub).
            filename: Original filename for format detection.
            language: Language hint (used if the model supports it).
            prompt: Prompt text (used if the model supports it).
            temperature: Decoding temperature (used if the model supports it).

        Returns:
            TranscriptionResult with text and duration.
        """
        audio_array, sr = _audio_bytes_to_numpy(audio_data, filename)
        duration = len(audio_array) / sr

        recognizer = self._resolve_recognizer(language)

        stream = recognizer.create_stream()
        stream.accept_waveform(sr, audio_array)
        recognizer.decode_stream(stream)

        text = stream.result.text.strip()
        return TranscriptionResult(text=text, duration=duration)

    # -- internal ------------------------------------------------------------

    def _resolve_recognizer(
        self, language: str | None
    ) -> sherpa_onnx.OfflineRecognizer:
        """Return the appropriate recognizer, creating/caching as needed."""
        if self._config.type not in _LANG_AT_INIT_TYPES:
            # Types without per-language recognizers
            if self._recognizer is None:
                self._recognizer = self._build_recognizer()
            return self._recognizer

        # Determine effective language
        lang = language or str(self._config.options.get("language", ""))
        return self._get_or_create_recognizer(lang)

    def _get_or_create_recognizer(self, language: str) -> sherpa_onnx.OfflineRecognizer:
        """Get a cached recognizer or create a new one for *language*."""
        if language in self._recognizers:
            # Move to end (most recently used)
            self._recognizers.move_to_end(language)
            return self._recognizers[language]

        t0 = time.perf_counter()
        recognizer = self._build_recognizer(language=language)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Created recognizer for language=%r in %.0f ms",
            language or "(auto)",
            elapsed_ms,
        )

        self._recognizers[language] = recognizer
        # Evict oldest if over cache limit
        while len(self._recognizers) > self._cache_size:
            evicted_lang, _ = self._recognizers.popitem(last=False)
            logger.debug("Evicted cached recognizer for language=%r", evicted_lang)

        return recognizer

    def _build_recognizer(
        self, language: str | None = None
    ) -> sherpa_onnx.OfflineRecognizer:
        """Build a sherpa-onnx OfflineRecognizer for this model type."""
        factory_name = _FACTORY_MAP.get(self._config.type)
        if not factory_name:
            raise ValueError(f"Unsupported model type: {self._config.type!r}")

        factory = getattr(sherpa_onnx.OfflineRecognizer, factory_name)

        # Start with file paths
        kwargs: dict[str, object] = dict(self._file_paths)
        kwargs["num_threads"] = self._num_threads

        # Add model-type-specific options from config
        options = dict(self._config.options)

        # Override language if provided
        if language is not None and self._config.type in _LANG_AT_INIT_TYPES:
            options["language"] = language

        # Merge options into kwargs (they are forwarded to the factory)
        kwargs.update(options)

        return factory(**kwargs)


def _audio_bytes_to_numpy(audio_data: bytes, filename: str) -> tuple[np.ndarray, int]:
    """Convert audio bytes to mono float32 numpy array at 16 kHz.

    Args:
        audio_data: Raw audio file bytes.
        filename: Filename for format detection.

    Returns:
        Tuple of (audio_array, sample_rate).
    """
    buf = io.BytesIO(audio_data)

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
    fmt = fmt_map.get(ext)

    if fmt:
        audio = AudioSegment.from_file(buf, format=fmt)
    else:
        audio = AudioSegment.from_file(buf)

    audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE)

    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    samples /= 2 ** (audio.sample_width * 8 - 1)

    return samples, SAMPLE_RATE
