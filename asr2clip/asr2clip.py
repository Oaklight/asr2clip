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
from .utils import log, set_verbose, setup_signal_handlers


def test_config(config: dict) -> bool:
    """Test the configuration by checking API connectivity.

    Args:
        config: Configuration dictionary.

    Returns:
        True if configuration is valid and API is accessible.
    """
    api_key, api_base_url, model_name, org_id = get_api_config(config)

    print("Testing configuration...")
    print(f"  API Base URL: {api_base_url}")
    print(f"  Model: {model_name}")
    print(f"  API Key: {'*' * 8}...{api_key[-4:] if len(api_key) > 4 else '****'}")
    print()

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
        log("Warning: Clipboard support may not be available.")
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


def main():
    """Main entry point for asr2clip."""
    parser = argparse.ArgumentParser(
        description="Record audio and transcribe to clipboard using ASR API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  asr2clip                      # Record and transcribe
  asr2clip --test               # Test API configuration
  asr2clip --list_devices       # List audio devices
  asr2clip --device pulse       # Use specific audio device
  asr2clip --daemon             # Continuous recording mode
  asr2clip --daemon --interval 60  # Transcribe every 60 seconds
  asr2clip --daemon --vad       # Auto-transcribe on silence
  asr2clip -i audio.mp3         # Transcribe existing file
  asr2clip --edit               # Edit configuration file
""",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"asr2clip {__version__}",
    )

    parser.add_argument(
        "-c",
        "--config",
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
        help="Input audio file to transcribe (instead of recording)",
        default=None,
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file to append transcripts to",
        default=None,
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test API configuration and exit",
    )

    parser.add_argument(
        "--list_devices",
        action="store_true",
        help="List available audio input devices",
    )

    parser.add_argument(
        "--device",
        help="Audio input device (name or index)",
        default=None,
    )

    parser.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="Open configuration file in editor",
    )

    parser.add_argument(
        "--generate_config",
        action="store_true",
        help="Print template configuration to stdout",
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in continuous recording mode",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Transcription interval in seconds for daemon mode (default: 30)",
    )

    parser.add_argument(
        "--vad",
        action="store_true",
        help="Enable voice activity detection (auto-transcribe on silence)",
    )

    parser.add_argument(
        "--silence_threshold",
        type=float,
        default=0.01,
        help="RMS threshold for silence detection (default: 0.01)",
    )

    parser.add_argument(
        "--silence_duration",
        type=float,
        default=1.5,
        help="Silence duration in seconds to trigger transcription (default: 1.5)",
    )

    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Calibrate silence threshold from ambient noise",
    )

    parser.add_argument(
        "--auto_calibrate",
        action="store_true",
        help="Auto-calibrate silence threshold before starting daemon mode",
    )

    args = parser.parse_args()

    # Handle --generate_config
    if args.generate_config:
        generate_config()
        return

    # Handle --edit
    if args.edit:
        open_in_editor(args.config)
        return

    # Handle --list_devices
    if args.list_devices:
        list_audio_devices()
        return

    # Read configuration
    config = read_config(args.config)

    # Set verbose mode
    quiet = args.quiet or config.get("quiet", False)
    set_verbose(not quiet)

    # Handle --test
    if args.test:
        success = test_config(config)
        sys.exit(0 if success else 1)

    # Get audio device
    device = get_audio_device(config, args.device)

    # Handle --calibrate
    if args.calibrate:
        from .vad import calibrate_silence_threshold

        threshold = calibrate_silence_threshold(device=device)
        print(f"\nUse this threshold with: --silence_threshold {threshold:.4f}")
        return

    # Handle --daemon mode
    if args.daemon:
        api_key, api_base_url, model_name, org_id = get_api_config(config)

        # Auto-calibrate if requested
        silence_threshold = args.silence_threshold
        if args.auto_calibrate and args.vad:
            from .vad import calibrate_silence_threshold

            silence_threshold = calibrate_silence_threshold(device=device)
            log(f"Using calibrated threshold: {silence_threshold:.4f}")

        continuous_recording(
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            org_id=org_id,
            device=device,
            interval=args.interval,
            output_file=args.output,
            vad_enabled=args.vad,
            silence_threshold=silence_threshold,
            silence_duration=args.silence_duration,
        )
        return

    # Handle --input (file transcription)
    if args.input:
        process_file(config, args.input, args.output)
        return

    # Default: record and transcribe
    process_recording(config, device, args.output)


if __name__ == "__main__":
    main()
