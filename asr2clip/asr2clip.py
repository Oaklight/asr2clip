#!/usr/bin/env python3

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import wave
from datetime import datetime

import numpy as np
import pyperclip
import sounddevice as sd
import yaml
from openai import OpenAI
from pydub import AudioSegment

from . import __version__

verbose = True


def log(message, **kwargs):
    global verbose
    if verbose:
        if kwargs:
            print(message, **kwargs)
        else:
            print(message)


# Default paths to search for config file
CONFIG_PATHS = [
    "asr2clip.conf",
    os.path.expanduser("~/.config/asr2clip.conf"),
]


def find_config_path(config_file=None):
    """Find the configuration file path."""
    if config_file and os.path.exists(config_file):
        return config_file

    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path

    return None


def read_config(config_file):
    """Read and parse the configuration file."""
    config_path = find_config_path(config_file)

    if config_path is None:
        user_config_path = os.path.expanduser("~/.config/asr2clip.conf")
        print(f"Configuration file not found: {config_file} or {user_config_path}")
        print("\nTo generate a template configuration file, run:")
        print("    asr2clip --generate_config > ~/.config/asr2clip.conf")
        print("\nOr edit the config file directly:")
        print("    asr2clip --edit")
        sys.exit(1)

    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            if "asr_model" in config and len(config) == 1:
                return config["asr_model"]
            return config
    except Exception as e:
        print(f"Could not read configuration file {config_path}: {e}")
        sys.exit(1)


def open_in_editor(config_file=None):
    """Open the configuration file in the system's default editor."""
    config_path = find_config_path(config_file)

    # If no config exists, create a default one
    if config_path is None:
        config_path = os.path.expanduser("~/.config/asr2clip.conf")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Write default config template
        config_template = """api_base_url: "https://api.openai.com/v1/"  # or other compatible API base URL
api_key: "YOUR_API_KEY"                     # api key for the platform
model_name: "whisper-1"                     # or other compatible model
# quiet: false                              # optional, `true` only allow errors and transcriptions
# org_id: none                              # optional, only required if you are using OpenAI organization id
# audio_device: null                        # optional, audio input device (name or index)
                                            # use `asr2clip --list_devices` to see available devices
                                            # common values: "pulse", "pipewire", or device index like 12
"""
        with open(config_path, "w") as f:
            f.write(config_template)
        print(f"Created new config file: {config_path}")

    # Determine which editor to use
    editors_to_try = []
    if os.getenv("EDITOR"):
        editors_to_try.append(os.getenv("EDITOR"))

    if os.name == "nt":  # Windows
        editors_to_try.append("notepad")
    else:  # Unix-like
        editors_to_try.extend(["nano", "vi", "vim"])

    for editor in editors_to_try:
        try:
            subprocess.run([editor, config_path], check=True)
            return
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Failed to open editor '{editor}': {e}")
            sys.exit(1)

    print(f"No suitable editor found. Please edit manually: {config_path}")
    sys.exit(1)


def generate_config():
    """Prints the template configuration for asr2clip.conf."""
    config_template = """
api_base_url: "https://api.openai.com/v1/"  # or other compatible API base URL
api_key: "YOUR_API_KEY"                     # api key for the platform
model_name: "whisper-1"                     # or other compatible model
# quiet: false                              # optional, `true` only allow errors and transcriptions
# org_id: none                              # optional, only required if you are using OpenAI organization id
# audio_device: null                        # optional, audio input device (name or index). Use --list_devices to see available devices

# xinference or other selfhosted platform
# api_base_url: "https://localhost:9997/v1" # or other compatible API base URL
# api_key: "none-or-random"
# model_name: "SenseVoiceSmall"             # or other compatible model

# SiliconFlow or other compatible platform
# api_base_url: "https://api.siliconflow.com/v1/"  # or other compatible API base URL
# api_key: "YOUR_API_KEY"                          # api key for the platform
# model_name: "FunAudioLLM/SenseVoiceSmall"
"""
    print(config_template.strip())


def list_audio_devices():
    """List all available audio input devices."""
    print("Available audio input devices:")
    print("-" * 60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        # Only show devices with input channels
        if device["max_input_channels"] > 0:
            default_marker = "*" if i == sd.default.device[0] else " "
            print(f"{default_marker} [{i}] {device['name']}")
            print(
                f"       Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']}"
            )
    print("-" * 60)
    print("* = default device")
    print("\nTo use a specific device, add to config file:")
    print('  audio_device: "pulse"  # or device index like 12')


def write_wav(filename, fs, audio_data):
    """Write audio data to a WAV file using stdlib wave module."""
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(fs)
        # Convert numpy array to bytes
        wav_file.writeframes(audio_data.tobytes())


def generate_test_audio(filename, fs=44100, duration=1.0, frequency=440):
    """Generate a simple test audio file with a sine wave tone."""
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    # Generate a sine wave
    audio = np.sin(2 * np.pi * frequency * t)
    # Normalize and convert to 16-bit
    audio = np.int16(audio * 32767 * 0.5)  # 50% volume
    write_wav(filename, fs, audio)
    return filename


def check_clipboard_support():
    """Check if clipboard functionality is available."""
    try:
        # Try to determine the paste mechanism
        pyperclip.paste()
        return True, None
    except pyperclip.PyperclipException as e:
        return False, str(e)


def check_audio_device(device=None):
    """Check if the audio device is working properly."""
    try:
        fs = 44100
        # Try to record a very short sample
        recording = sd.rec(
            int(fs * 0.1), samplerate=fs, channels=1, device=device, blocking=True
        )
        max_val = np.max(np.abs(recording))
        if max_val == 0:
            return (
                False,
                "Audio device returns silent/zero data. Try a different device with --list_devices",
            )
        return True, None
    except Exception as e:
        return False, str(e)


def test_config(api_key, api_base_url, model_name, org_id=None, audio_device=None):
    """Test the full configuration including API, audio device, and clipboard."""
    all_passed = True

    print("=" * 60)
    print("asr2clip Configuration Test")
    print("=" * 60)

    # Test 1: Clipboard support
    print("\n[1/3] Testing clipboard support...")
    clipboard_ok, clipboard_err = check_clipboard_support()
    if clipboard_ok:
        print("  ✓ Clipboard support: OK")
    else:
        print("  ✗ Clipboard support: FAILED")
        print(f"    Error: {clipboard_err}")
        print("    Hint: Install xclip (X11) or wl-clipboard (Wayland)")
        print("    You can still use -o FILE or -o - to output to file/stdout")
        all_passed = False

    # Test 2: Audio device
    print("\n[2/3] Testing audio device...")
    device_display = audio_device if audio_device is not None else "default"
    print(f"  Device: {device_display}")
    audio_ok, audio_err = check_audio_device(audio_device)
    if audio_ok:
        print("  ✓ Audio device: OK")
    else:
        print("  ✗ Audio device: FAILED")
        print(f"    Error: {audio_err}")
        print("    Hint: Use --list_devices to see available devices")
        print("    Then set audio_device in config or use --device")
        all_passed = False

    # Test 3: API connection
    print("\n[3/3] Testing API connection...")
    print(f"  API Base URL: {api_base_url}")
    print(f"  Model: {model_name}")

    # Create a temporary test audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        filename = tmpfile.name

    try:
        # Generate test audio (1 second of 440Hz tone)
        generate_test_audio(filename, fs=44100, duration=1.0, frequency=440)

        # Try to transcribe
        transcript = transcribe_audio(
            filename,
            api_key,
            api_base_url,
            model_name,
            org_id=org_id,
        )

        print("  ✓ API connection: OK")
        print(f"    Transcription result: '{transcript.text}'")
        print("    (Note: A simple tone may produce empty or unexpected transcription)")
    except Exception as e:
        print("  ✗ API connection: FAILED")
        print(f"    Error: {e}")
        all_passed = False
    finally:
        # Clean up
        if os.path.exists(filename):
            os.remove(filename)

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed. Please fix the issues above.")
    print("=" * 60)

    return all_passed


def record_audio(fs, duration=None, device=None):
    if duration:
        log(f"Recording for {duration} seconds...")
    else:
        log("Recording indefinitely...")

    if device is not None:
        log(f"Using audio device: {device}")

    try:
        # Initialize an empty list to store audio chunks
        audio_chunks = []

        # Start recording in a loop until stop_recording is True or duration is reached
        with sd.InputStream(
            samplerate=fs,
            channels=1,
            device=device,
            callback=lambda indata, frames, time, status: audio_chunks.append(
                indata.copy()
            ),
        ):
            if duration is None:
                while not stop_recording:
                    sd.sleep(100)  # Sleep for 100ms to avoid busy-waiting
            else:
                # Record for the specified duration
                sd.sleep(int(duration * 1000))  # Convert duration to milliseconds

        # Concatenate all recorded chunks into a single numpy array
        recording = np.concatenate(audio_chunks)
        log("Recording stopped.")
        return recording
    except Exception as e:
        print(f"An error occurred while recording audio: {e}")
        sys.exit(1)


def save_audio(recording, fs, filename):
    # Check if the recording is empty or contains invalid values
    if recording.size == 0:
        print("Error: The recorded audio data is empty.")
        sys.exit(1)

    # Check for all-zero or all-NaN recordings
    max_val = np.max(np.abs(recording))
    if max_val == 0 or np.isnan(max_val):
        print(
            "Error: The recorded audio contains no valid audio data (silent or invalid)."
        )
        sys.exit(1)

    # Normalize and convert to 16-bit data
    recording = recording / max_val
    recording = np.int16(recording * 32767)
    write_wav(filename, fs, recording)


def transcribe_audio(
    filename, api_key, api_base_url, model_name, org_id=None, raise_on_error=False
):
    """Transcribe audio file using the API.

    Args:
        filename: Path to the audio file
        api_key: API key for authentication
        api_base_url: Base URL for the API
        model_name: Name of the transcription model
        org_id: Optional organization ID
        raise_on_error: If True, raise exception instead of sys.exit()

    Returns:
        Transcription result object

    Raises:
        Exception: If raise_on_error is True and transcription fails
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key, base_url=api_base_url, organization=org_id)

        # Open the audio file
        with open(filename, "rb") as audio_file:
            log("Transcribing audio...")
            transcript = client.audio.transcriptions.create(
                model=model_name,
                file=audio_file,
            )
            return transcript
    except Exception as e:
        if raise_on_error:
            raise
        print(f"An error occurred during transcription: {e}")
        sys.exit(1)


def signal_handler(sig, frame):
    global stop_recording
    stop_recording = True
    log("\nReceived interrupt signal...", end=" ")
    signal.signal(signal.SIGINT, signal_handler_exit)


def signal_handler_exit(sig, frame):
    log("\nExiting...")
    sys.exit(0)


def signal_handler_daemon(sig, frame):
    """Signal handler for daemon mode - exit immediately on Ctrl+C."""
    global stop_recording
    stop_recording = True
    log("\nStopping continuous recording...")


def setup_signal_handlers(daemon_mode=False):
    global stop_recording
    stop_recording = False
    if daemon_mode:
        signal.signal(signal.SIGINT, signal_handler_daemon)
    else:
        signal.signal(signal.SIGINT, signal_handler)


def convert_audio_to_wav(input_source):
    """Convert an audio file or raw audio data to WAV format."""
    if isinstance(input_source, str) and os.path.isfile(input_source):
        # Input is a file path
        log(f"Reading audio file: {input_source}")
        audio = AudioSegment.from_file(input_source)
    else:
        # Input is raw audio data (e.g., a temporary file or stdin data)
        log("Converting raw audio data to WAV format...")
        audio = AudioSegment.from_file(input_source, format="wav")

    # Create a temporary file manually (without using the context manager)
    tmpfile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    filename = tmpfile.name
    tmpfile.close()  # Close the file so it can be used by other processes

    # Export the audio to the temporary WAV file
    audio.export(filename, format="wav")
    return filename


def generate_timestamp_filename(output_path, extension=".txt"):
    """Generate a timestamped filename for continuous mode output."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.isdir(output_path):
        return os.path.join(output_path, f"transcript_{timestamp}{extension}")
    return output_path


def append_transcript_to_file(output_file, text, timestamp=None):
    """Append transcribed text to a file with optional timestamp."""
    with open(output_file, "a", encoding="utf-8") as f:
        if timestamp:
            f.write(f"\n[{timestamp}]\n")
        f.write(text)
        f.write("\n")


def continuous_recording(
    fs,
    interval,
    api_key,
    api_base_url,
    model_name,
    org_id=None,
    output_path=None,
    audio_device=None,
):
    """Continuously record and transcribe audio at specified intervals."""
    global stop_recording

    log(f"Starting continuous recording mode (interval: {interval}s)...")
    log("Press Ctrl+C to stop.")

    # Determine output mode
    output_is_dir = output_path and os.path.isdir(output_path)
    if output_path and not output_is_dir:
        # Create parent directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        # Clear the file at start
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Continuous transcription started at {datetime.now().isoformat()}\n"
            )

    segment_count = 0
    audio_chunks = []
    chunk_lock = threading.Lock()

    def audio_callback(indata, frames, time_info, status):
        with chunk_lock:
            audio_chunks.append(indata.copy())

    try:
        with sd.InputStream(
            samplerate=fs,
            channels=1,
            device=audio_device,
            callback=audio_callback,
        ):
            last_transcribe_time = time.time()

            while not stop_recording:
                sd.sleep(100)  # Sleep for 100ms

                current_time = time.time()
                elapsed = current_time - last_transcribe_time

                if elapsed >= interval:
                    # Time to transcribe
                    with chunk_lock:
                        if audio_chunks:
                            recording = np.concatenate(audio_chunks)
                            audio_chunks.clear()
                        else:
                            recording = None

                    if recording is not None and recording.size > 0:
                        segment_count += 1
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log(f"\n[Segment {segment_count}] Transcribing...")

                        # Save to temporary file
                        with tempfile.NamedTemporaryFile(
                            suffix=".wav", delete=False
                        ) as tmpfile:
                            temp_filename = tmpfile.name

                        try:
                            # Check for valid audio
                            max_val = np.max(np.abs(recording))
                            if max_val > 0 and not np.isnan(max_val):
                                # Normalize and save
                                normalized = recording / max_val
                                audio_int16 = np.int16(normalized * 32767)
                                write_wav(temp_filename, fs, audio_int16)

                                # Transcribe (don't exit on error in daemon mode)
                                try:
                                    transcript = transcribe_audio(
                                        temp_filename,
                                        api_key,
                                        api_base_url,
                                        model_name,
                                        org_id=org_id,
                                        raise_on_error=True,
                                    )
                                    text = transcript.text.strip()
                                except Exception as e:
                                    log(f"  Transcription error: {e}")
                                    text = None

                                if text:
                                    log(
                                        f"  Text: {text[:100]}{'...' if len(text) > 100 else ''}"
                                    )

                                    # Output handling
                                    if output_path:
                                        if output_is_dir:
                                            # Each segment to a new file
                                            segment_file = generate_timestamp_filename(
                                                output_path
                                            )
                                            with open(
                                                segment_file, "w", encoding="utf-8"
                                            ) as f:
                                                f.write(text)
                                            log(f"  Saved to: {segment_file}")
                                        else:
                                            # Append to single file
                                            append_transcript_to_file(
                                                output_path, text, timestamp
                                            )
                                            log(f"  Appended to: {output_path}")
                                    else:
                                        # Print to stdout
                                        print(f"[{timestamp}] {text}")
                                else:
                                    log("  (No speech detected)")
                            else:
                                log("  (Silent audio, skipping)")
                        finally:
                            if os.path.exists(temp_filename):
                                os.remove(temp_filename)

                    last_transcribe_time = current_time

            # Handle remaining audio after stop signal
            with chunk_lock:
                if audio_chunks:
                    recording = np.concatenate(audio_chunks)
                    audio_chunks.clear()
                else:
                    recording = None

            if recording is not None and recording.size > 0:
                segment_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log(
                    f"\n[Final Segment {segment_count}] Transcribing remaining audio..."
                )

                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmpfile:
                    temp_filename = tmpfile.name

                try:
                    max_val = np.max(np.abs(recording))
                    if max_val > 0 and not np.isnan(max_val):
                        normalized = recording / max_val
                        audio_int16 = np.int16(normalized * 32767)
                        write_wav(temp_filename, fs, audio_int16)

                        try:
                            transcript = transcribe_audio(
                                temp_filename,
                                api_key,
                                api_base_url,
                                model_name,
                                org_id=org_id,
                                raise_on_error=True,
                            )
                            text = transcript.text.strip()
                        except Exception as e:
                            log(f"  Transcription error: {e}")
                            text = None

                        if text:
                            log(
                                f"  Text: {text[:100]}{'...' if len(text) > 100 else ''}"
                            )
                            if output_path:
                                if output_is_dir:
                                    segment_file = generate_timestamp_filename(
                                        output_path
                                    )
                                    with open(segment_file, "w", encoding="utf-8") as f:
                                        f.write(text)
                                    log(f"  Saved to: {segment_file}")
                                else:
                                    append_transcript_to_file(
                                        output_path, text, timestamp
                                    )
                                    log(f"  Appended to: {output_path}")
                            else:
                                print(f"[{timestamp}] {text}")
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

    except Exception as e:
        print(f"An error occurred during continuous recording: {e}")
        sys.exit(1)

    log(f"\nContinuous recording stopped. Total segments: {segment_count}")


def process_recording(
    fs,
    duration,
    api_key,
    api_base_url,
    model_name,
    org_id=None,
    use_stdin=False,
    input_file=None,
    output_file=None,
    audio_device=None,
):
    if use_stdin:
        # Read audio data from stdin
        log("Reading audio data from stdin...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            filename = tmpfile.name
            # Assuming the input is raw audio data, you may need to adjust this depending on the format
            audio_data = sys.stdin.buffer.read()
            with open(filename, "wb") as f:
                f.write(audio_data)

            # Convert to WAV format
            wav_filename = convert_audio_to_wav(filename)
            # Transcribe audio
            transcript = transcribe_audio(
                wav_filename,
                api_key,
                api_base_url,
                model_name,
                org_id=org_id,
            )
            # Clean up the temporary file
            os.remove(wav_filename)
    elif input_file:
        # Convert input file to WAV format
        wav_filename = convert_audio_to_wav(input_file)
        # Transcribe audio
        transcript = transcribe_audio(
            wav_filename,
            api_key,
            api_base_url,
            model_name,
            org_id=org_id,
        )
        # Clean up the temporary file
        os.remove(wav_filename)
    else:
        # Record audio based on the specified duration or continuously
        recording = record_audio(fs, duration, device=audio_device)

        # Save to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            filename = tmpfile.name
            save_audio(recording, fs, filename)

            # Transcribe audio
            transcript = transcribe_audio(
                filename,
                api_key,
                api_base_url,
                model_name,
                org_id=org_id,
            )
            # Clean up the temporary file
            os.remove(filename)

    # Get the transcribed text
    text = transcript.text

    # Handle output redirection
    if output_file == "-":
        # Output to stdout
        print(text)
    elif output_file:
        # Create the directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Output to a file
        with open(output_file, "w") as f:
            f.write(text)
        log(f"\nTranscribed text saved to {output_file}")
    else:
        # Copy to clipboard
        pyperclip.copy(text)
        log("\nTranscribed Text:")
        log("-----------------")
        print(text)
        log("\nCopied to the clipboard!")


def main():
    parser = argparse.ArgumentParser(
        description="Real-time speech recognizer that copies transcribed text to the clipboard."
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="asr2clip.conf",
        help="Path to the configuration file. Default is 'asr2clip.conf'.",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=None,
        help="Duration to record (seconds). If not specified, recording continues until Ctrl+C.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read audio data from stdin instead of recording.",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default=None,
        help="Path to the input audio file to transcribe.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Disable logging.",
    )
    parser.add_argument(
        "--generate_config",
        action="store_true",
        help="Print the template configuration file and exit.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path to the output file. If not specified, output will be copied to the clipboard. Use '-' for stdout.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test the full configuration (API, audio device, clipboard) and exit.",
    )
    parser.add_argument(
        "--list_devices",
        action="store_true",
        help="List available audio input devices and exit.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Audio input device (name or index). Overrides config file setting.",
    )
    parser.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="Open the configuration file in the system's default editor.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in continuous recording mode with automatic transcription.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Transcription interval in seconds for daemon mode. Default is 30.",
    )

    args = parser.parse_args()

    # If --edit is provided, open editor and exit
    if args.edit:
        open_in_editor(args.config)
        sys.exit(0)

    # If --list_devices is provided, list devices and exit
    if args.list_devices:
        list_audio_devices()
        sys.exit(0)

    # If --generate_config is provided, print the template and exit
    if args.generate_config:
        generate_config()
        sys.exit(0)

    # If --test is provided, test the full configuration and exit
    if args.test:
        asr_config = read_config(args.config)
        api_key = asr_config.get("api_key", os.environ.get("OPENAI_API_KEY"))
        api_base_url = asr_config.get("api_base_url", "https://api.openai.com/v1")
        org_id = asr_config.get("org_id", os.environ.get("OPENAI_ORG_ID"))
        model_name = asr_config.get("model_name", "whisper-1")

        # Get audio device from command line or config
        test_audio_device = args.device
        if test_audio_device is None:
            test_audio_device = asr_config.get("audio_device", None)
        if (
            test_audio_device is not None
            and isinstance(test_audio_device, str)
            and test_audio_device.isdigit()
        ):
            test_audio_device = int(test_audio_device)

        if not api_key:
            print("Error: API key not found in the configuration file.")
            sys.exit(1)

        success = test_config(
            api_key, api_base_url, model_name, org_id, test_audio_device
        )
        sys.exit(0 if success else 1)

    # Read configuration
    asr_config = read_config(args.config)
    api_key = asr_config.get("api_key", os.environ.get("OPENAI_API_KEY"))
    api_base_url = asr_config.get("api_base_url", "https://api.openai.com/v1")
    org_id = asr_config.get("org_id", os.environ.get("OPENAI_ORG_ID"))
    model_name = asr_config.get("model_name", "whisper-1")
    quiet = asr_config.get("quiet", False)

    # Get audio device from command line or config
    audio_device = args.device
    if audio_device is None:
        audio_device = asr_config.get("audio_device", None)

    # Convert device to int if it's a numeric string
    if (
        audio_device is not None
        and isinstance(audio_device, str)
        and audio_device.isdigit()
    ):
        audio_device = int(audio_device)

    global verbose
    if quiet:  # config file has lower priority
        verbose = False
    if args.quiet:  # command line argument can override
        verbose = False

    # Check API key
    if not api_key:
        print("Error: API key not found in the configuration file.")
        sys.exit(1)

    fs = 44100  # Sample rate

    # Check for daemon mode
    if args.daemon:
        # Set up signal handlers for daemon mode (single Ctrl+C to exit)
        setup_signal_handlers(daemon_mode=True)

        if not args.output:
            log(
                "Warning: No output file specified. Transcriptions will be printed to stdout."
            )

        continuous_recording(
            fs=fs,
            interval=args.interval,
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            org_id=org_id,
            output_path=args.output,
            audio_device=audio_device,
        )
    else:
        # Set up signal handlers for normal mode (double Ctrl+C to exit)
        setup_signal_handlers(daemon_mode=False)

        log(
            "Press Ctrl+C\n   - once, to stop recording and transcribe\n   - twice, to exit the program"
        )

        # Process the recording
        process_recording(
            fs=fs,
            duration=args.duration,
            api_key=api_key,
            api_base_url=api_base_url,
            org_id=org_id,
            model_name=model_name,
            use_stdin=args.stdin,
            input_file=args.input,
            output_file=args.output,
            audio_device=audio_device,
        )


if __name__ == "__main__":
    main()
