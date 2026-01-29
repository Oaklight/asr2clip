"""Output handling for asr2clip (clipboard, file, stdout)."""

import os
import shutil
import sys
from datetime import datetime

from .utils import log


def check_clipboard_support() -> bool:
    """Check if clipboard support is available on the system.

    Returns:
        True if clipboard is supported, False otherwise.
    """
    # Check for xclip (X11)
    if shutil.which("xclip"):
        return True

    # Check for wl-copy (Wayland)
    if shutil.which("wl-copy"):
        return True

    # Check for xsel (X11 alternative)
    if shutil.which("xsel"):
        return True

    # On macOS, pbcopy is always available
    if sys.platform == "darwin":
        return True

    # On Windows, clipboard is always available
    if sys.platform == "win32":
        return True

    return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard.

    Args:
        text: Text to copy to clipboard.

    Returns:
        True if successful, False otherwise.
    """
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception as e:
        log(f"Clipboard error: {e}")
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
            log("Copied to clipboard")
        else:
            log("Failed to copy to clipboard")

    if to_stdout:
        print(text)

    if to_file:
        append_transcript_to_file(text, to_file)


def print_clipboard_help():
    """Print help message for clipboard setup."""
    print("\nClipboard support requires one of the following:")
    print("  - xclip (X11): sudo apt install xclip")
    print("  - wl-clipboard (Wayland): sudo apt install wl-clipboard")
    print("  - xsel (X11): sudo apt install xsel")
    print("\nAlternatively, use --output to save transcripts to a file.")
