"""sherpa-onnx ASR engine (backward-compatibility shim).

This module re-exports :class:`~asr2clip.engines.sherpa_onnx.SherpaOnnxEngine`
as ``ASREngine`` for backward compatibility.  New code should import from
:mod:`asr2clip.engines` directly.

.. deprecated::
    Use :class:`asr2clip.engines.SherpaOnnxEngine` instead of
    ``asr2clip.local_asr.engine.ASREngine``.
"""

from __future__ import annotations

# Re-export the canonical implementation under the legacy name
from asr2clip.engines.base import TranscriptionResult
from asr2clip.engines.sherpa_onnx import (
    SAMPLE_RATE,
    SherpaOnnxEngine as ASREngine,
    _audio_bytes_to_numpy,
)

__all__ = [
    "ASREngine",
    "TranscriptionResult",
    "SAMPLE_RATE",
    "_audio_bytes_to_numpy",
]
