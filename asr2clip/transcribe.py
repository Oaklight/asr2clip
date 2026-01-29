"""Transcription API calls for asr2clip."""

import os
import sys

import httpx

from .utils import error, info, print_error, print_key_value, print_success


class TranscriptionError(Exception):
    """Exception raised when transcription fails."""

    pass


def transcribe_audio(
    audio_file_path: str,
    api_key: str,
    api_base_url: str,
    model_name: str,
    org_id: str | None = None,
    raise_on_error: bool = False,
) -> str:
    """Transcribe audio using the ASR API.

    Args:
        audio_file_path: Path to the audio file to transcribe.
        api_key: API key for authentication.
        api_base_url: Base URL of the API.
        model_name: Name of the model to use.
        org_id: Optional organization ID.
        raise_on_error: If True, raise exception on error instead of sys.exit().

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

    try:
        with open(audio_file_path, "rb") as audio_file:
            files = {
                "file": (os.path.basename(audio_file_path), audio_file, "audio/wav")
            }
            data = {"model": model_name}

            info(f"Sending request to {url}...")

            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, files=files, data=data)

            if response.status_code != 200:
                error_msg = f"API error {response.status_code}: {response.text}"
                if raise_on_error:
                    raise TranscriptionError(error_msg)
                error(error_msg)
                sys.exit(1)

            result = response.json()
            return result.get("text", "")

    except httpx.TimeoutException:
        error_msg = "Request timed out. Please try again."
        if raise_on_error:
            raise TranscriptionError(error_msg)
        error(error_msg)
        sys.exit(1)

    except httpx.RequestError as e:
        error_msg = f"Request failed: {e}"
        if raise_on_error:
            raise TranscriptionError(error_msg)
        error(error_msg)
        sys.exit(1)

    except Exception as e:
        error_msg = f"Transcription error: {e}"
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
