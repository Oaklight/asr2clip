"""Output handling for asr2clip (clipboard, file, stdout)."""

import os
import shutil
import subprocess
from datetime import datetime

from .utils import log, print_success, warning


def _is_wayland() -> bool:
    """Check if the current session is running on Wayland."""
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _has_wl_copy() -> bool:
    """Check if wl-copy is available."""
    return shutil.which("wl-copy") is not None


def _wl_copy(text: str) -> bool:
    """Copy text using wl-copy (Wayland native, persists after exit).

    Args:
        text: Text to copy.

    Returns:
        True if successful, False otherwise.
    """
    try:
        subprocess.run(
            ["wl-copy"],
            input=text,
            text=True,
            check=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def check_clipboard_support() -> bool:
    """Check if clipboard support is available on the system.

    Returns:
        True if clipboard is supported, False otherwise.
    """
    if _is_wayland() and _has_wl_copy():
        return True
    try:
        import copykitten

        copykitten.copy("")
        return True
    except Exception:
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard.

    On Wayland, prefers wl-copy for clipboard manager integration.
    Falls back to copykitten on X11 or when wl-copy is unavailable.

    Args:
        text: Text to copy to clipboard.

    Returns:
        True if successful, False otherwise.
    """
    # Wayland: prefer wl-copy for proper clipboard manager integration
    if _is_wayland() and _has_wl_copy():
        if _wl_copy(text):
            return True
        # Fall through to copykitten on failure

    try:
        import copykitten

        copykitten.copy(text, detach=True)
        return True
    except Exception as e:
        warning(f"Clipboard error: {e}")
        return False


def generate_timestamp_filename(
    prefix: str = "transcript", extension: str = "txt"
) -> str:
    """Generate a filename with timestamp.

    Args:
        prefix: Prefix for the filename.
        extension: File extension.

    Returns:
        Filename with timestamp.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def append_transcript_to_file(text: str, filepath: str):
    """Append transcript text to a file with timestamp.

    Args:
        text: Transcript text to append.
        filepath: Path to the output file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create directory if it doesn't exist
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}]\n{text}\n")

    log(f"Appended transcript to {filepath}")


def output_transcript(
    text: str,
    to_clipboard: bool = True,
    to_stdout: bool = True,
    to_file: str | None = None,
):
    """Output transcript to various destinations.

    Args:
        text: Transcript text to output.
        to_clipboard: Whether to copy to clipboard.
        to_stdout: Whether to print to stdout.
        to_file: Optional file path to append transcript to.
    """
    if to_clipboard:
        if copy_to_clipboard(text):
            print_success("Copied to clipboard")
        else:
            warning("Failed to copy to clipboard")

    if to_stdout:
        print(text)

    if to_file:
        append_transcript_to_file(text, to_file)


def print_clipboard_help():
    """Print help message for clipboard setup."""
    print("\nClipboard is handled by copykitten (no external tools needed).")
    print("If clipboard is unavailable, use --output to save transcripts to a file.")
