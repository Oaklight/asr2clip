#!/usr/bin/env python3

import argparse
import sys
import tempfile

import numpy as np
from openai import OpenAI  # Updated import for OpenAI client
import pyperclip
import sounddevice as sd
import yaml
from scipy.io.wavfile import write


def read_config(config_file):
    try:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        print(f"Could not read configuration file {config_file}: {e}")
        sys.exit(1)


def record_audio(duration, fs):
    print(f"Recording for {duration} seconds...")
    try:
        myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
        sd.wait()
        print("Recording complete.")
        return myrecording
    except Exception as e:
        print(f"An error occurred while recording audio: {e}")
        sys.exit(1)


def save_audio(recording, fs, filename):
    # Normalize and convert to 16-bit data
    recording = recording / np.max(np.abs(recording))
    recording = np.int16(recording * 32767)
    write(filename, fs, recording)


def transcribe_audio(filename, api_key, api_base_url, model_name):
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key, base_url=api_base_url)

        # Open the audio file
        with open(filename, "rb") as audio_file:
            print("Transcribing audio...")
            transcript = client.audio.transcriptions.create(
                model=model_name,
                file=audio_file,
            )
            return transcript
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Real-time speech recognizer that copies transcribed text to the clipboard."
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Duration to record (seconds). Default is 5 seconds.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to the configuration file. Default is 'config.yaml'.",
    )

    args = parser.parse_args()

    # Read configuration
    config = read_config(args.config)
    asr_config = config.get("asr_model", {})
    api_key = asr_config.get("api_key")
    api_base_url = asr_config.get("api_base_url")
    model_name = asr_config.get("model_name", "whisper-1")

    # Check API key
    if not api_key:
        print("Error: API key not found in the configuration file.")
        sys.exit(1)

    fs = 44100  # Sample rate
    duration = args.duration

    # Record audio
    recording = record_audio(duration, fs)

    # Save to a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
        filename = tmpfile.name
        save_audio(recording, fs, filename)

        # Transcribe audio
        transcript = transcribe_audio(filename, api_key, api_base_url, model_name)

    # Copy to clipboard
    text = transcript.text

    pyperclip.copy(text)
    print("\nTranscribed Text:")
    print("-----------------")
    print(text)
    print("\nThe transcribed text has been copied to the clipboard.")


if __name__ == "__main__":
    main()
