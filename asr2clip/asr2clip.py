#!/usr/bin/env python3

import argparse
import os
import signal
import sys
import tempfile

import numpy as np
import pyperclip
import sounddevice as sd
import yaml
from openai import OpenAI
from pydub import AudioSegment
from scipy.io.wavfile import write

verbose = True


def log(message, **kwargs):
    global verbose
    if verbose:
        if kwargs:
            print(message, **kwargs)
        else:
            print(message)


def read_config(config_file):
    # Check if the config file exists in the repository root directory
    if os.path.exists(config_file):
        config_path = config_file
    else:
        # If not found, check the user's ~/.config/ directory
        user_config_path = os.path.expanduser("~/.config/asr2clip.conf")
        if os.path.exists(user_config_path):
            config_path = user_config_path
        else:
            print(f"Configuration file not found: {config_file} or {user_config_path}")
            print("\nTo generate a template configuration file, run:")
            print("    asr2clip.py --generate_config")
            print(
                f"\nCopy the output to a file (e.g., {user_config_path}) and customize it."
            )
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


def generate_config():
    """Prints the template configuration for asr2clip.conf."""
    config_template = """
api_base_url: "https://api.openai.com/v1/"  # or other compatible API base URL
api_key: "YOUR_API_KEY"                     # api key for the platform
model_name: "whisper-1"                     # or other compatible model
# quiet: false                              # optional, `true` only allow errors and transcriptions
# org_id: none                              # optional, only required if you are using OpenAI organization id

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


def record_audio(fs, duration=None):
    if duration:
        log(f"Recording for {duration} seconds...")
    else:
        log("Recording indefinitely...")
    try:
        # Initialize an empty list to store audio chunks
        audio_chunks = []

        # Start recording in a loop until stop_recording is True or duration is reached
        with sd.InputStream(
            samplerate=fs,
            channels=1,
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
    # Normalize and convert to 16-bit data
    recording = recording / np.max(np.abs(recording))
    recording = np.int16(recording * 32767)
    write(filename, fs, recording)


def transcribe_audio(filename, api_key, api_base_url, model_name, org_id=None):
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


def setup_signal_handlers():
    global stop_recording
    stop_recording = False
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


def process_recording(
    fs,
    duration,
    api_key,
    api_base_url,
    model_name,
    org_id=None,
    use_stdin=False,
    input_file=None,
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
        recording = record_audio(fs, duration)

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

    # Copy to clipboard
    text = transcript.text
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

    args = parser.parse_args()

    # If --generate_config is provided, print the template and exit
    if args.generate_config:
        generate_config()
        sys.exit(0)

    # Read configuration
    asr_config = read_config(args.config)
    api_key = asr_config.get("api_key", os.environ.get("OPENAI_API_KEY"))
    api_base_url = asr_config.get("api_base_url", "https://api.openai.com/v1")
    org_id = asr_config.get("org_id", os.environ.get("OPENAI_ORG_ID"))
    model_name = asr_config.get("model_name", "whisper-1")
    quiet = asr_config.get("quiet", False)

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

    # Set up signal handlers
    setup_signal_handlers()

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
    )


if __name__ == "__main__":
    main()
