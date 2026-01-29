"""Utility functions for asr2clip."""

import signal
import sys

# Import logging functions from the new logging module
# This provides backward compatibility while using the new structured logging
from .logging import (
    debug,
    error,
    exception,
    get_logger,
    get_verbose,
    info,
    log,
    print_error,
    print_key_value,
    print_recording_status,
    print_separator,
    print_status,
    print_success,
    print_transcribe_status,
    set_verbose,
    setup_logging,
    warning,
)

# Global state for signal handling
stop_recording = False

# Re-export logging functions for backward compatibility
__all__ = [
    "log",
    "set_verbose",
    "get_verbose",
    "setup_logging",
    "get_logger",
    "debug",
    "info",
    "warning",
    "error",
    "exception",
    "print_status",
    "print_recording_status",
    "print_transcribe_status",
    "print_success",
    "print_error",
    "print_separator",
    "print_key_value",
    "setup_signal_handlers",
    "is_stop_requested",
    "request_stop",
]


def signal_handler(sig, frame):
    """Signal handler for normal mode - first Ctrl+C stops recording."""
    global stop_recording
    stop_recording = True
    info("\nReceived interrupt signal...")
    signal.signal(signal.SIGINT, signal_handler_exit)


def signal_handler_exit(sig, frame):
    """Signal handler for second Ctrl+C - exit immediately."""
    info("\nExiting...")
    sys.exit(0)


def signal_handler_daemon(sig, frame):
    """Signal handler for daemon mode - exit immediately on Ctrl+C."""
    global stop_recording
    stop_recording = True
    info("\nStopping continuous recording...")


def setup_signal_handlers(daemon_mode: bool = False):
    """Set up signal handlers for Ctrl+C.

    Args:
        daemon_mode: If True, use single Ctrl+C to stop.
                    If False, use double Ctrl+C (first stops recording, second exits).
    """
    global stop_recording
    stop_recording = False
    if daemon_mode:
        signal.signal(signal.SIGINT, signal_handler_daemon)
    else:
        signal.signal(signal.SIGINT, signal_handler)


def is_stop_requested() -> bool:
    """Check if stop has been requested via signal.

    Returns:
        True if stop was requested, False otherwise.
    """
    return stop_recording


def request_stop():
    """Request to stop recording."""
    global stop_recording
    stop_recording = True
