"""ASR engine abstraction for asr2clip.

Provides a unified interface for different ASR backends:

- :class:`OpenAICompatEngine` — any OpenAI-compatible API (cloud or local server)
- :class:`SherpaOnnxEngine` — local inference via sherpa-onnx (lazy import)

Use :func:`create_engine` to create an engine from a configuration dict.
"""

from __future__ import annotations

from .audio_input import AudioInput
from .base import BaseEngine, TranscriptionError, TranscriptionResult
from .openai_compat import OpenAICompatEngine

__all__ = [
    "AudioInput",
    "BaseEngine",
    "TranscriptionError",
    "TranscriptionResult",
    "OpenAICompatEngine",
    "create_engine",
]


def create_engine(config: dict, **kwargs) -> BaseEngine:
    """Create an engine from a configuration dictionary.

    The engine type is determined by the ``engine`` field in config:
    - Not set or ``"openai_compat"``: :class:`OpenAICompatEngine`
    - ``"sherpa_onnx"``: :class:`SherpaOnnxEngine` (lazy-imported)

    Supports both the new multi-engine config layout (with ``engines``
    sub-dict) and the legacy flat layout.

    Args:
        config: Configuration dictionary.
        **kwargs: Additional arguments passed to the engine constructor.

    Returns:
        Initialized engine instance.

    Raises:
        ValueError: If the engine type is unknown.
        KeyError: If required config fields are missing.
    """
    from ..config import get_engine_config

    engine_name = config.get("engine", "openai_compat")
    ecfg = get_engine_config(config, engine_name)
    engine_type = ecfg.get("type", engine_name)

    if engine_type == "openai_compat":
        return OpenAICompatEngine(
            api_base_url=ecfg["api_base_url"],
            api_key=ecfg["api_key"],
            model_name=ecfg["model_name"],
            org_id=ecfg.get("org_id"),
            **kwargs,
        )
    elif engine_type == "sherpa_onnx":
        # Lazy import to avoid mandatory sherpa-onnx dependency
        from .sherpa_onnx import SherpaOnnxEngine

        return SherpaOnnxEngine.from_registry(
            model_name=ecfg.get("model_name"),
            config_path=ecfg.get("model_config_path"),
            model_dir=ecfg.get("model_dir"),
            num_threads=ecfg.get("num_threads", 4),
        )
    else:
        raise ValueError(
            f"Unknown engine type: {engine_type!r}. "
            f"Supported: 'openai_compat', 'sherpa_onnx'"
        )
