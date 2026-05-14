"""Transcription API calls for asr2clip (deprecated shim).

.. deprecated::
    This module is retained for backward compatibility.  New code should
    use :mod:`asr2clip.engines` directly::

        from asr2clip.engines import AudioInput, create_engine
        engine = create_engine(config)
        result = engine.transcribe(AudioInput.from_file("audio.wav"))
"""

from __future__ import annotations

import warnings

from .engines.base import TranscriptionError
from .engines.audio_input import AudioInput
from .engines.openai_compat import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    OpenAICompatEngine,
)

__all__ = [
    "TranscriptionError",
    "transcribe_audio",
    "test_transcription",
]


def transcribe_audio(
    audio_file_path: str,
    api_key: str,
    api_base_url: str,
    model_name: str,
    org_id: str | None = None,
    raise_on_error: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Transcribe audio using the ASR API with automatic retry on timeout.

    .. deprecated::
        Use :class:`~asr2clip.engines.OpenAICompatEngine` instead.

    Args:
        audio_file_path: Path to the audio file to transcribe.
        api_key: API key for authentication.
        api_base_url: Base URL of the API.
        model_name: Name of the model to use.
        org_id: Optional organization ID.
        raise_on_error: If True, raise exception on error instead of sys.exit().
        max_retries: Maximum number of retry attempts for timeout errors.
        retry_delay: Delay between retries in seconds.
        timeout: Request timeout in seconds.

    Returns:
        Transcribed text.

    Raises:
        TranscriptionError: If transcription fails and raise_on_error is True.
        SystemExit: If transcription fails and raise_on_error is False.
    """
    warnings.warn(
        "transcribe_audio() is deprecated. Use asr2clip.engines.OpenAICompatEngine instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    engine = OpenAICompatEngine(
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        org_id=org_id,
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout,
    )

    with open(audio_file_path, "rb") as f:
        audio_data = f.read()

    import os
    import sys

    try:
        audio_input = AudioInput.from_bytes(
            audio_data, filename=os.path.basename(audio_file_path)
        )
        result = engine.transcribe(audio_input)
        return result.text
    except TranscriptionError:
        if raise_on_error:
            raise
        from .utils import error

        error(str(sys.exc_info()[1]))
        sys.exit(1)


def test_transcription(
    api_key: str,
    api_base_url: str,
    model_name: str,
    org_id: str | None = None,
) -> bool:
    """Test the transcription API connection.

    .. deprecated::
        Use :class:`~asr2clip.engines.OpenAICompatEngine.test` instead.

    Args:
        api_key: API key for authentication.
        api_base_url: Base URL of the API.
        model_name: Name of the model to use.
        org_id: Optional organization ID.

    Returns:
        True if the API is accessible, False otherwise.
    """
    warnings.warn(
        "test_transcription() is deprecated. Use asr2clip.engines.OpenAICompatEngine.test() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    engine = OpenAICompatEngine(
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        org_id=org_id,
    )

    success = engine.test()

    from .utils import print_error, print_key_value, print_success

    if success:
        print_success("API connection successful")
        print_key_value("Base URL", api_base_url)
        print_key_value("Model", model_name)
    else:
        print_error("API connection failed")

    return success
