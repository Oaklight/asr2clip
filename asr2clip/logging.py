"""Structured logging for asr2clip.

Provides a beautiful, structured logging system using Python's standard logging module
with ANSI color codes for terminal output.
"""

import logging
import os
import sys
from typing import Optional


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal styling."""

    # Reset
    RESET = "\033[0m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bold colors
    BOLD = "\033[1m"
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_MAGENTA = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"

    # Dim
    DIM = "\033[2m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def supports_color() -> bool:
    """Check if the terminal supports color output.

    Returns:
        True if color is supported, False otherwise.
    """
    # Check for NO_COLOR environment variable (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False

    # Check for FORCE_COLOR environment variable
    if os.environ.get("FORCE_COLOR"):
        return True

    # Check if stdout is a TTY
    if not hasattr(sys.stderr, "isatty"):
        return False

    if not sys.stderr.isatty():
        return False

    # Check for dumb terminal
    if os.environ.get("TERM") == "dumb":
        return False

    return True


# Global color support flag
_color_enabled = supports_color()

# Convenience color constants for direct use
RESET = Colors.RESET if _color_enabled else ""
RED = Colors.RED if _color_enabled else ""
GREEN = Colors.GREEN if _color_enabled else ""
YELLOW = Colors.YELLOW if _color_enabled else ""
BLUE = Colors.BLUE if _color_enabled else ""
CYAN = Colors.CYAN if _color_enabled else ""
MAGENTA = Colors.MAGENTA if _color_enabled else ""
DIM = Colors.DIM if _color_enabled else ""
BOLD = Colors.BOLD if _color_enabled else ""


def set_color_enabled(enabled: bool):
    """Enable or disable color output.

    Args:
        enabled: True to enable colors, False to disable.
    """
    global _color_enabled
    _color_enabled = enabled


def colorize(text: str, color: str) -> str:
    """Apply color to text if color is enabled.

    Args:
        text: The text to colorize.
        color: The ANSI color code to apply.

    Returns:
        Colorized text if color is enabled, otherwise plain text.
    """
    if _color_enabled:
        return f"{color}{text}{Colors.RESET}"
    return text


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""

    # Color mapping for log levels
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.BOLD_RED,
        logging.CRITICAL: Colors.BG_RED + Colors.WHITE,
    }

    # Level name formatting (fixed width for alignment)
    LEVEL_NAMES = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARN",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRIT",
    }

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """Initialize the formatter.

        Args:
            fmt: Format string for the log message.
            datefmt: Format string for the date/time.
        """
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors.

        Args:
            record: The log record to format.

        Returns:
            Formatted log message with colors.
        """
        # Get the color for this level
        color = self.LEVEL_COLORS.get(record.levelno, "")
        level_name = self.LEVEL_NAMES.get(record.levelno, record.levelname)

        # Format timestamp
        timestamp = self.formatTime(record, self.datefmt)
        timestamp_colored = colorize(timestamp, Colors.DIM)

        # Format level name with color
        level_colored = colorize(f"{level_name:>5}", color)

        # Format the message
        message = record.getMessage()

        # Build the final formatted string
        # Format: HH:MM:SS │ LEVEL │ message
        separator = colorize("│", Colors.DIM)
        formatted = (
            f"{timestamp_colored} {separator} {level_colored} {separator} {message}"
        )

        # Handle exceptions
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            formatted = f"{formatted}\n{colorize(exc_text, Colors.RED)}"

        return formatted


# Module-level logger
_logger: Optional[logging.Logger] = None
_verbose: bool = True


def setup_logging(
    verbose: bool = True,
    debug: bool = False,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Set up the logging system.

    Args:
        verbose: Enable verbose output (INFO level).
        debug: Enable debug output (DEBUG level).
        log_file: Optional file path to write logs to.

    Returns:
        Configured logger instance.
    """
    global _logger, _verbose
    _verbose = verbose

    # Create logger
    logger = logging.getLogger("asr2clip")
    logger.handlers.clear()

    # Set level based on verbosity
    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    # Create console handler with colored formatting
    handler = logging.StreamHandler(sys.stderr)
    formatter = ColoredFormatter(datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the asr2clip logger instance.

    Returns:
        Logger instance, creating one if necessary.
    """
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def set_verbose(value: bool):
    """Set the verbose mode.

    Args:
        value: True to enable verbose logging, False to disable.
    """
    global _verbose
    _verbose = value
    logger = get_logger()
    if value:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


def get_verbose() -> bool:
    """Get the current verbose mode setting.

    Returns:
        True if verbose mode is enabled, False otherwise.
    """
    return _verbose


# Convenience logging functions
def debug(message: str, *args, **kwargs):
    """Log a debug message.

    Args:
        message: The message to log.
        *args: Additional positional arguments for string formatting.
        **kwargs: Additional keyword arguments passed to logger.
    """
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """Log an info message.

    Args:
        message: The message to log.
        *args: Additional positional arguments for string formatting.
        **kwargs: Additional keyword arguments passed to logger.
    """
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """Log a warning message.

    Args:
        message: The message to log.
        *args: Additional positional arguments for string formatting.
        **kwargs: Additional keyword arguments passed to logger.
    """
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """Log an error message.

    Args:
        message: The message to log.
        *args: Additional positional arguments for string formatting.
        **kwargs: Additional keyword arguments passed to logger.
    """
    get_logger().error(message, *args, **kwargs)


def exception(message: str, *args, **kwargs):
    """Log an exception with traceback.

    Args:
        message: The message to log.
        *args: Additional positional arguments for string formatting.
        **kwargs: Additional keyword arguments passed to logger.
    """
    get_logger().exception(message, *args, **kwargs)


# Styled output functions for special messages
def print_status(message: str, style: str = "info"):
    """Print a styled status message.

    Args:
        message: The message to print.
        style: Style name (info, warning, error, success, recording, transcribe).
    """
    style_colors = {
        "info": Colors.CYAN,
        "warning": Colors.YELLOW,
        "error": Colors.BOLD_RED,
        "success": Colors.BOLD_GREEN,
        "recording": Colors.BOLD_MAGENTA,
        "transcribe": Colors.BOLD_BLUE,
    }
    color = style_colors.get(style, "")
    print(colorize(message, color), file=sys.stderr)


def print_recording_status(message: str):
    """Print a recording status message.

    Args:
        message: The message to print.
    """
    print_status(message, "recording")


def print_transcribe_status(message: str):
    """Print a transcription status message.

    Args:
        message: The message to print.
    """
    print_status(message, "transcribe")


def print_success(message: str):
    """Print a success message.

    Args:
        message: The message to print.
    """
    print_status(f"✓ {message}", "success")


def print_error(message: str):
    """Print an error message.

    Args:
        message: The message to print.
    """
    print_status(f"✗ {message}", "error")


def print_separator(char: str = "─", width: int = 40):
    """Print a separator line.

    Args:
        char: Character to use for the separator.
        width: Width of the separator line.
    """
    print(colorize(char * width, Colors.DIM), file=sys.stderr)


def print_key_value(key: str, value: str):
    """Print a key-value pair.

    Args:
        key: The key/label.
        value: The value.
    """
    key_formatted = colorize(f"  {key}:", Colors.DIM)
    print(f"{key_formatted} {value}", file=sys.stderr)


# Backward compatibility: log function that respects verbose setting
def log(message: str, **kwargs):
    """Log a message if verbose mode is enabled.

    This function provides backward compatibility with the old log() function.

    Args:
        message: The message to log.
        **kwargs: Additional keyword arguments (ignored for compatibility).
    """
    if _verbose:
        info(message)
