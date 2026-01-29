"""Utility functions for asr2clip."""

import signal
import sys

# Global state
verbose = True
stop_recording = False


def log(message, **kwargs):
    """Log a message if verbose mode is enabled.

    Args:
        message: The message to log.
        **kwargs: Additional keyword arguments passed to print().
    """
    global verbose
    if verbose:
        if kwargs:
            print(message, **kwargs)
        else:
            print(message)


def set_verbose(value: bool):
    """Set the verbose mode.

    Args:
        value: True to enable verbose logging, False to disable.
    """
    global verbose
    verbose = value


def get_verbose() -> bool:
    """Get the current verbose mode setting.

    Returns:
        True if verbose mode is enabled, False otherwise.
    """
    return verbose


def signal_handler(sig, frame):
    """Signal handler for normal mode - first Ctrl+C stops recording."""
    global stop_recording
    stop_recording = True
    log("\nReceived interrupt signal...", end=" ")
    signal.signal(signal.SIGINT, signal_handler_exit)


def signal_handler_exit(sig, frame):
    """Signal handler for second Ctrl+C - exit immediately."""
    log("\nExiting...")
    sys.exit(0)


def signal_handler_daemon(sig, frame):
    """Signal handler for daemon mode - exit immediately on Ctrl+C."""
    global stop_recording
    stop_recording = True
    log("\nStopping continuous recording...")


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
