#!/usr/bin/env python3
"""ASR to Clipboard - Record audio and transcribe to clipboard.

This is the main CLI entry point for asr2clip.
"""

import argparse
import os
import sys

from . import __version__
from .audio import (
    convert_audio_to_wav,
    get_audio_duration,
    list_audio_devices,
    record_audio,
    save_audio,
)
from .config import (
    generate_config,
    get_api_config,
    get_audio_device,
    open_in_editor,
    read_config,
)
from .daemon import continuous_recording
from .output import (
    check_clipboard_support,
    output_transcript,
    print_clipboard_help,
)
from .transcribe import test_transcription, transcribe_audio
from .utils import (
    info,
    log,
    print_key_value,
    print_separator,
    set_verbose,
    setup_logging,
    setup_signal_handlers,
    warning,
)


def test_config(config: dict) -> bool:
    """Test the configuration by checking API connectivity.

    Args:
        config: Configuration dictionary.

    Returns:
        True if configuration is valid and API is accessible.
    """
    api_key, api_base_url, model_name, org_id = get_api_config(config)

    info("Testing configuration...")
    print_key_value("API Base URL", api_base_url)
    print_key_value("Model", model_name)
    masked_key = f"{'*' * 8}...{api_key[-4:] if len(api_key) > 4 else '****'}"
    print_key_value("API Key", masked_key)
    print_separator()

    return test_transcription(api_key, api_base_url, model_name, org_id)


def process_recording(
    config: dict,
    device: str | int | None = None,
    output_file: str | None = None,
):
    """Record audio, transcribe, and output the result.

    Args:
        config: Configuration dictionary.
        device: Audio device name or index.
        output_file: Optional file to append transcript to.
    """
    api_key, api_base_url, model_name, org_id = get_api_config(config)

    # Check clipboard support
    if not check_clipboard_support():
        warning("Clipboard support may not be available.")
        print_clipboard_help()

    setup_signal_handlers(daemon_mode=False)

    log("Recording... Press Ctrl+C to stop (press twice to cancel)")

    # Record audio
    audio_data = record_audio(device=device)

    duration = get_audio_duration(audio_data)
    if duration < 0.1:
        log("Recording too short or empty. Exiting.")
        sys.exit(0)

    log(f"Recorded {duration:.1f} seconds of audio")
    log("Processing...")

    # Save to temp file
    temp_path = save_audio(audio_data)

    try:
        # Transcribe
        text = transcribe_audio(
            temp_path,
            api_key,
            api_base_url,
            model_name,
            org_id,
        )

        if text.strip():
            output_transcript(
                text,
                to_clipboard=True,
                to_stdout=True,
                to_file=output_file,
            )
        else:
            log("No speech detected in the recording.")

    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass


def process_file(
    config: dict,
    input_file: str,
    output_file: str | None = None,
):
    """Transcribe an existing audio file.

    Args:
        config: Configuration dictionary.
        input_file: Path to the audio file.
        output_file: Optional file to append transcript to.
    """
    api_key, api_base_url, model_name, org_id = get_api_config(config)

    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        sys.exit(1)

    log(f"Processing file: {input_file}")

    # Convert to WAV if needed
    if not input_file.lower().endswith(".wav"):
        log("Converting to WAV format...")
        temp_path = convert_audio_to_wav(input_file)
        cleanup_temp = True
    else:
        temp_path = input_file
        cleanup_temp = False

    try:
        # Transcribe
        text = transcribe_audio(
            temp_path,
            api_key,
            api_base_url,
            model_name,
            org_id,
        )

        if text.strip():
            output_transcript(
                text,
                to_clipboard=True,
                to_stdout=True,
                to_file=output_file,
            )
        else:
            log("No speech detected in the audio file.")

    finally:
        # Clean up temp file if we created one
        if cleanup_temp:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for asr2clip.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Record audio and transcribe to clipboard using ASR API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  asr2clip                         # Single recording (Ctrl+C to stop)
  asr2clip --vad                   # Continuous with voice detection
  asr2clip --interval 60           # Continuous with fixed interval
  asr2clip -i audio.mp3            # Transcribe existing file

With output file:
  asr2clip --vad -o meeting.txt    # Save transcripts to file
  asr2clip -i audio.mp3 -o out.txt # Transcribe file and save

Setup:
  asr2clip --edit                  # Create/edit configuration
  asr2clip --generate_config       # Create new config file
  asr2clip --test                  # Test API connection
  asr2clip --list_devices          # List audio devices

Local ASR server:
  asr2clip --serve                 # Start local ASR server on :8000
  asr2clip --serve --port 9000     # Start on custom port
  asr2clip --download-model        # Download SenseVoice model
""",
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"asr2clip {__version__}"
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="FILE",
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode - only output transcription and errors",
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="FILE",
        help="Transcribe audio file instead of recording",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Append transcripts to file",
        default=None,
    )
    parser.add_argument(
        "--test", action="store_true", help="Test API configuration and exit"
    )
    parser.add_argument(
        "--list_devices", action="store_true", help="List available audio input devices"
    )
    parser.add_argument(
        "--device",
        metavar="DEV",
        help="Audio input device (name or index)",
        default=None,
    )
    parser.add_argument(
        "-e", "--edit", action="store_true", help="Open configuration file in editor"
    )
    parser.add_argument(
        "--generate_config",
        action="store_true",
        help="Create config file at ~/.config/asr2clip/config.yaml",
    )
    parser.add_argument(
        "--print_config",
        action="store_true",
        help="Print template configuration to stdout",
    )
    parser.add_argument(
        "--vad",
        action="store_true",
        help="Continuous recording with voice activity detection",
    )
    parser.add_argument(
        "--interval",
        type=float,
        metavar="SEC",
        default=None,
        help="Continuous recording with fixed interval (seconds)",
    )
    parser.add_argument(
        "--silence_threshold",
        type=float,
        metavar="PROB",
        default=None,
        help="VAD speech probability threshold, 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--silence_duration",
        type=float,
        metavar="SEC",
        default=1.5,
        help="Silence duration to trigger transcription (default: 1.5)",
    )

    # Local ASR server
    server_group = parser.add_argument_group("Local ASR server")
    server_group.add_argument(
        "--serve",
        action="store_true",
        help="Start the local ASR API server",
    )
    server_group.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server bind address (default: 127.0.0.1)",
    )
    server_group.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server bind port (default: 8000)",
    )
    server_group.add_argument(
        "--model-dir",
        default=None,
        help="Path to ASR model directory",
    )
    server_group.add_argument(
        "--num-threads",
        type=int,
        default=4,
        help="Inference threads (default: 4)",
    )
    server_group.add_argument(
        "--download-model",
        action="store_true",
        help="Download the SenseVoice model and exit",
    )

    return parser


def _validate_args(args: argparse.Namespace):
    """Validate and resolve argument defaults.

    Args:
        args: Parsed arguments namespace (modified in-place).

    Raises:
        SystemExit: On invalid argument combinations.
    """
    if args.silence_threshold is None:
        args.silence_threshold = 0.5


def main():
    """Main entry point for asr2clip."""
    parser = _build_parser()
    args = parser.parse_args()

    # Handle --serve (local ASR server) — before validation
    if args.serve:
        from .local_asr import check_deps

        check_deps()
        from .local_asr.app import run_server

        run_server(
            host=args.host,
            port=args.port,
            model_dir=args.model_dir,
            num_threads=args.num_threads,
        )
        return

    # Handle --download-model — before validation
    if args.download_model:
        from .local_asr import check_deps

        check_deps()
        from .local_asr.model_registry import create_registry

        registry = create_registry(model_dir=args.model_dir)
        default_cfg = registry.get_default_model()
        registry.download_model(default_cfg)
        return

    _validate_args(args)

    # Handle --generate_config and --print_config
    if args.print_config:
        generate_config(print_only=True)
        return

    if args.generate_config:
        generate_config()
        return

    if args.edit:
        open_in_editor(args.config)
        return

    if args.list_devices:
        list_audio_devices()
        return

    # Read configuration
    config = read_config(args.config)

    # Set up logging
    quiet = args.quiet or config.get("quiet", False)
    setup_logging(verbose=not quiet)
    set_verbose(not quiet)

    if args.test:
        success = test_config(config)
        sys.exit(0 if success else 1)

    device = get_audio_device(config, args.device)

    # File transcription takes priority over continuous modes
    if args.input:
        process_file(config, args.input, args.output)
        return

    if args.vad or args.interval is not None:
        api_key, api_base_url, model_name, org_id = get_api_config(config)
        if args.vad:
            try:
                __import__("sherpa_onnx")
            except ImportError:
                print(
                    "Error: VAD requires sherpa-onnx.\n"
                    "Install with: pip install asr2clip[vad]"
                )
                sys.exit(1)
        interval = args.interval if args.interval is not None else 30.0
        continuous_recording(
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            org_id=org_id,
            device=device,
            interval=interval,
            output_file=args.output,
            vad_enabled=args.vad,
            silence_threshold=args.silence_threshold,
            silence_duration=args.silence_duration,
        )
        return

    process_recording(config, device, args.output)


if __name__ == "__main__":
    main()
