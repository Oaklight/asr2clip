"""Local ASR engine using sherpa-onnx.

Supports SenseVoice, Whisper, Paraformer, and Transducer model types
through the sherpa-onnx OfflineRecognizer API.
"""

from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from pathlib import Path

import sherpa_onnx

from asr2clip.local_asr.model_registry import ModelConfig

from .audio_input import AudioInput
from .base import BaseEngine, TranscriptionError, TranscriptionResult

logger = logging.getLogger("asr2clip.engines.sherpa_onnx")

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


class SherpaOnnxEngine(BaseEngine):
    """ASR engine using sherpa-onnx OfflineRecognizer.

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
    ) -> SherpaOnnxEngine:
        """Create an engine from a ModelConfig.

        Args:
            config: Model configuration.
            model_dir: Absolute path to the model directory.
            num_threads: Inference threads.
            recognizer_cache_size: Max language-specific recognizers to cache.

        Returns:
            Initialized SherpaOnnxEngine.
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

    @classmethod
    def from_registry(
        cls,
        model_name: str | None = None,
        config_path: str | None = None,
        model_dir: str | None = None,
        num_threads: int = 4,
    ) -> SherpaOnnxEngine:
        """Create an engine by loading a model from the ModelRegistry.

        Auto-downloads the model if it is not present locally.

        Args:
            model_name: Model name in the registry. Uses default if None.
            config_path: Path to models.yaml. Uses default if None.
            model_dir: Legacy model directory override.
            num_threads: Inference threads.

        Returns:
            Initialized SherpaOnnxEngine.

        Raises:
            TranscriptionError: If the model is not found or cannot be loaded.
        """
        from asr2clip.local_asr.model_registry import create_registry

        try:
            registry = create_registry(config_path=config_path, model_dir=model_dir)

            if model_name:
                model_cfg = registry.get_model(model_name)
                if model_cfg is None:
                    raise TranscriptionError(
                        f"Model {model_name!r} not found in registry"
                    )
            else:
                model_cfg = registry.get_default_model()

            # Auto-download if needed
            if not registry.validate_model(model_cfg):
                logger.info("Downloading model %r...", model_cfg.name)
                registry.download_model(model_cfg)

            resolved_dir = registry.model_dir(model_cfg)
            return cls.from_model_config(
                model_cfg,
                resolved_dir,
                num_threads=num_threads,
            )
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Failed to load model from registry: {e}") from e

    def transcribe(
        self,
        audio: AudioInput,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Audio input (bytes, file, or numpy array).
            language: Language hint (used if the model supports it).

        Returns:
            TranscriptionResult with text and duration.

        Raises:
            TranscriptionError: On transcription failure.
        """
        try:
            audio_array, sr = audio.as_numpy()
            duration = len(audio_array) / sr

            recognizer = self._resolve_recognizer(language)

            stream = recognizer.create_stream()
            stream.accept_waveform(sr, audio_array)
            recognizer.decode_stream(stream)

            text = stream.result.text.strip()
            return TranscriptionResult(text=text, duration=duration)
        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

    def test(self) -> bool:
        """Test engine by verifying the recognizer is loaded.

        Returns:
            True if the engine has at least one recognizer ready.
        """
        return bool(self._recognizers) or self._recognizer is not None

    @property
    def name(self) -> str:
        """Engine name including model identifier."""
        return f"sherpa-onnx/{self._config.name}"

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
