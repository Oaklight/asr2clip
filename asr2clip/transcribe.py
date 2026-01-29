"""Transcription API calls for asr2clip."""

import os
import sys
import time

import httpx

from .utils import error, print_error, print_key_value, print_success, warning


class TranscriptionError(Exception):
    """Exception raised when transcription fails."""

    pass


# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0  # seconds
DEFAULT_TIMEOUT = 60.0  # seconds


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
    # Normalize API base URL
    if not api_base_url.endswith("/"):
        api_base_url += "/"

    url = f"{api_base_url}audio/transcriptions"

    headers = {"Authorization": f"Bearer {api_key}"}
    if org_id:
        headers["OpenAI-Organization"] = org_id

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            with open(audio_file_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(audio_file_path), audio_file, "audio/wav")
                }
                data = {"model": model_name}

                # Logging is now handled by daemon.py with colored indicators
                pass

                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, headers=headers, files=files, data=data)

                if response.status_code != 200:
                    error_msg = f"API error {response.status_code}: {response.text}"
                    if raise_on_error:
                        raise TranscriptionError(error_msg)
                    error(error_msg)
                    sys.exit(1)

                result = response.json()
                return result.get("text", "")

        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries:
                warning(
                    f"Request timed out (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                continue
            else:
                error_msg = f"Request timed out after {max_retries + 1} attempts."
                if raise_on_error:
                    raise TranscriptionError(error_msg) from last_error
                error(error_msg)
                sys.exit(1)

        except httpx.RequestError as e:
            last_error = e
            # Retry on connection errors as well
            if attempt < max_retries:
                warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                continue
            else:
                error_msg = f"Request failed after {max_retries + 1} attempts: {e}"
                if raise_on_error:
                    raise TranscriptionError(error_msg) from last_error
                error(error_msg)
                sys.exit(1)

        except Exception as e:
            error_msg = f"Transcription error: {e}"
            if raise_on_error:
                raise TranscriptionError(error_msg) from e
            error(error_msg)
            sys.exit(1)

    # Should not reach here, but just in case
    error_msg = "Unexpected error in transcription retry loop"
    if raise_on_error:
        raise TranscriptionError(error_msg)
    error(error_msg)
    sys.exit(1)


def test_transcription(
    api_key: str,
    api_base_url: str,
    model_name: str,
    org_id: str | None = None,
) -> bool:
    """Test the transcription API connection.

    Args:
        api_key: API key for authentication.
        api_base_url: Base URL of the API.
        model_name: Name of the model to use.
        org_id: Optional organization ID.

    Returns:
        True if the API is accessible, False otherwise.
    """
    # Normalize API base URL
    if not api_base_url.endswith("/"):
        api_base_url += "/"

    # Try to access the models endpoint to verify connectivity
    url = f"{api_base_url}models"

    headers = {"Authorization": f"Bearer {api_key}"}
    if org_id:
        headers["OpenAI-Organization"] = org_id

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)

        if response.status_code == 200:
            print_success("API connection successful")
            print_key_value("Base URL", api_base_url)
            print_key_value("Model", model_name)
            return True
        else:
            print_error(f"API returned status {response.status_code}")
            print_key_value("Response", response.text[:200])
            return False

    except httpx.TimeoutException:
        print_error("Connection timed out")
        return False

    except httpx.RequestError as e:
        print_error(f"Connection failed: {e}")
        return False
