"""OpenAI-compatible ASR engine.

Works with any service implementing the OpenAI audio transcription API,
including cloud providers (OpenAI, Groq, SiliconFlow, etc.) and local
servers (asr2clip --serve, faster-whisper-server, etc.).
"""

from __future__ import annotations

import os
import tempfile
import time

from asr2clip._vendor.httpclient import httpclient

from .base import BaseEngine, TranscriptionError, TranscriptionResult

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0  # seconds
DEFAULT_TIMEOUT = 60.0  # seconds


class OpenAICompatEngine(BaseEngine):
    """Engine that calls any OpenAI-compatible ASR API.

    Args:
        api_base_url: Base URL of the API (e.g. "https://api.groq.com/openai/v1/").
        api_key: API key for authentication.
        model_name: Name of the model to use (e.g. "whisper-large-v3").
        org_id: Optional OpenAI organization ID.
        max_retries: Maximum retry attempts on timeout/connection errors.
        retry_delay: Delay between retries in seconds.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model_name: str,
        org_id: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_base_url.endswith("/"):
            api_base_url += "/"
        self._api_base_url = api_base_url
        self._api_key = api_key
        self._model_name = model_name
        self._org_id = org_id
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._timeout = timeout

    def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio data via OpenAI-compatible API.

        Args:
            audio_data: Raw audio file bytes.
            filename: Original filename for content-type detection.
            language: Optional language hint (currently unused by most APIs).

        Returns:
            TranscriptionResult with transcribed text and audio duration.

        Raises:
            TranscriptionError: On transcription failure after retries.
        """
        # Estimate duration from audio data (WAV header or fallback)
        duration = _estimate_duration(audio_data)

        # Write to temp file for the HTTP upload
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(audio_data)
            tmp.close()

            text = self._transcribe_with_retries(tmp.name, filename)
            return TranscriptionResult(text=text, duration=duration)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def test(self) -> bool:
        """Test API connectivity by querying the /models endpoint.

        Returns:
            True if the API is accessible.
        """
        url = f"{self._api_base_url}models"
        headers = self._build_headers()

        try:
            with httpclient.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                assert isinstance(response, httpclient.Response)
            return response.status_code == 200
        except (httpclient.HttpTimeoutError, httpclient.HttpClientError):
            return False

    @property
    def name(self) -> str:
        """Derive a human-readable name from the API base URL."""
        return _extract_name_from_url(self._api_base_url)

    # -- internal helpers ------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for API requests."""
        headers = {"Authorization": f"Bearer {self._api_key}"}
        if self._org_id:
            headers["OpenAI-Organization"] = self._org_id
        return headers

    def _attempt_transcription(self, audio_file_path: str, filename: str) -> str:
        """Make a single transcription API request.

        Args:
            audio_file_path: Path to the temporary audio file on disk.
            filename: Original filename for the multipart upload.

        Returns:
            Transcribed text.

        Raises:
            httpclient.HttpTimeoutError: On request timeout.
            httpclient.HttpClientError: On request failure.
            TranscriptionError: On API error response.
        """
        url = f"{self._api_base_url}audio/transcriptions"
        headers = self._build_headers()

        with open(audio_file_path, "rb") as audio_file:
            files = {"file": (filename, audio_file, "audio/wav")}
            data = {"model": self._model_name}

            with httpclient.Client(timeout=self._timeout) as client:
                response = client.post(url, headers=headers, files=files, data=data)
                assert isinstance(response, httpclient.Response)

        if response.status_code != 200:
            raise TranscriptionError(
                f"API error {response.status_code}: {response.text}"
            )

        result = response.json()
        return result.get("text", "")

    def _transcribe_with_retries(self, audio_file_path: str, filename: str) -> str:
        """Transcribe with automatic retry on transient failures.

        Args:
            audio_file_path: Path to the temporary audio file.
            filename: Original filename.

        Returns:
            Transcribed text.

        Raises:
            TranscriptionError: On failure after all retries.
        """
        import logging

        logger = logging.getLogger("asr2clip.engines.openai_compat")

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return self._attempt_transcription(audio_file_path, filename)
            except (httpclient.HttpTimeoutError, httpclient.HttpClientError) as e:
                last_error = e
                if attempt < self._max_retries:
                    logger.warning(
                        "Request failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt + 1,
                        self._max_retries + 1,
                        e,
                        self._retry_delay,
                    )
                    time.sleep(self._retry_delay)
                    continue
                raise TranscriptionError(
                    f"Request failed after {self._max_retries + 1} attempts: {e}"
                ) from last_error
            except TranscriptionError:
                raise
            except Exception as e:
                raise TranscriptionError(f"Transcription error: {e}") from e

        raise TranscriptionError(  # pragma: no cover
            "Unexpected error in transcription retry loop"
        )


def _extract_name_from_url(url: str) -> str:
    """Extract a short engine name from an API base URL.

    Args:
        url: API base URL.

    Returns:
        Short name like "groq", "openai", "localhost:8000".
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or ""

    # Well-known providers
    if "groq.com" in host:
        return "groq"
    if "openai.com" in host:
        return "openai"
    if "siliconflow" in host:
        return "siliconflow"
    if host in ("localhost", "127.0.0.1", "::1"):
        port = parsed.port or 80
        return f"localhost:{port}"

    # Fallback: use hostname
    return host or "unknown"


def _estimate_duration(audio_data: bytes) -> float:
    """Estimate audio duration from WAV data.

    For WAV files, parses the header. For other formats, returns 0.0.

    Args:
        audio_data: Raw audio file bytes.

    Returns:
        Estimated duration in seconds, or 0.0 if unknown.
    """
    # Check for WAV RIFF header
    if len(audio_data) < 44 or audio_data[:4] != b"RIFF":
        return 0.0

    try:
        import struct

        # WAV header fields
        _channels = struct.unpack_from("<H", audio_data, 22)[0]
        sample_rate = struct.unpack_from("<I", audio_data, 24)[0]
        _bits_per_sample = struct.unpack_from("<H", audio_data, 34)[0]
        bytes_per_second = struct.unpack_from("<I", audio_data, 28)[0]

        if bytes_per_second == 0 or sample_rate == 0:
            return 0.0

        # Data size is total minus header (approximate for simple WAV)
        data_size = len(audio_data) - 44
        return data_size / bytes_per_second
    except Exception:
        return 0.0
