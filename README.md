# asr2clip -- Speech-to-Text Clipboard Tool

[![PyPI version](https://badge.fury.io/py/asr2clip.svg?icon=si%3Apython)](https://badge.fury.io/py/asr2clip)
[![GitHub version](https://badge.fury.io/gh/oaklight%2Fasr2clip.svg?icon=si%3Agithub)](https://badge.fury.io/gh/oaklight%2Fasr2clip)
[![License](https://img.shields.io/github/license/Oaklight/asr2clip)](https://github.com/Oaklight/asr2clip/blob/master/LICENSE)

[中文](README_zh.md)

This tool is designed to recognize speech in real-time, convert it to text, and automatically copy the text to the system clipboard. The tool leverages API services for speech recognition and uses Python libraries for audio capture and clipboard management.

## TL;DR

```bash
pip install asr2clip       # Install the package
asr2clip --edit            # Create/edit config file
asr2clip --test            # Test your configuration
asr2clip                   # Start recording and transcribing
```

## Prerequisites

Before you begin, ensure you have the following ready:

- **Python 3.8 or higher**: The tool is written in Python, so you'll need Python installed on your system.
- **API Key**: You will need an API key from a speech recognition service (e.g., **OpenAI/Whisper** API or a compatible ASR API, such as **FunAudioLLM/SenseVoiceSmall** at [siliconflow](https://siliconflow.cn/) or [xinference](https://inference.readthedocs.io/en/latest/)).

### System Dependencies

| Dependency | Purpose | Linux | macOS | Windows |
|------------|---------|-------|-------|---------|
| **ffmpeg** | Audio format conversion | `apt install ffmpeg` | `brew install ffmpeg` | [Download](https://ffmpeg.org/download.html) |
| **PortAudio** | Audio recording | `apt install libportaudio2` | `brew install portaudio` | Included with sounddevice |
| **Clipboard** | Copy to clipboard | `apt install xclip` (X11) or `wl-clipboard` (Wayland) | Built-in | Built-in |

## Installation

### Option 1: Install via pip or pipx (Recommended)

```bash
# Install using pip
pip install asr2clip

# Or install using pipx (recommended for isolated environments)
pipx install asr2clip

# Upgrade to latest version
pip install --upgrade asr2clip
```

### Option 2: Install from source

```bash
git clone https://github.com/Oaklight/asr2clip.git
cd asr2clip
pip install -e .
```

## Configuration

### Quick Setup

The easiest way to configure asr2clip is using the built-in editor:

```bash
asr2clip --edit  # Opens config file in your default editor
```

This will create a config file at `~/.config/asr2clip/config.yaml` if it doesn't exist.

### Configuration File

The configuration file uses YAML format:

```yaml
api_base_url: "https://api.openai.com/v1/"  # or other compatible API base URL
api_key: "YOUR_API_KEY"                     # api key for the platform
model_name: "whisper-1"                     # or other compatible model
# quiet: false                              # optional, disable logging
# audio_device: "pulse"                     # optional, audio input device
```

Config file locations (searched in order):
1. `./asr2clip.conf` (current directory)
2. `~/.config/asr2clip/config.yaml`
3. `~/.config/asr2clip.conf` (legacy)
4. `~/.asr2clip.conf` (legacy)

### Test Your Configuration

Before using the tool, verify your setup:

```bash
asr2clip --test
```

This will check:
- ✓ Clipboard support
- ✓ Audio device functionality
- ✓ API connection

### Audio Device Selection

If the default audio device doesn't work, list available devices and select one:

```bash
asr2clip --list_devices    # List all audio input devices
asr2clip --device pulse    # Use specific device
```

Or add to your config file:
```yaml
audio_device: "pulse"  # or device index like 12
```

## Usage

### Basic Usage

```bash
asr2clip                   # Record until Ctrl+C, transcribe, copy to clipboard
asr2clip --vad             # Continuous recording with voice detection
asr2clip -i audio.mp3      # Transcribe an audio file
```

### CLI Options

```
usage: asr2clip [-h] [-v] [-c FILE] [-q] [-i FILE] [-o FILE] [--test]
                [--list_devices] [--device DEV] [-e] [--generate_config]
                [--print_config] [--vad] [--interval SEC] [--adaptive]
                [--calibrate] [--silence_threshold RMS]
                [--silence_duration SEC] [--no_adaptive]

Record audio and transcribe to clipboard using ASR API

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -c FILE, --config FILE
                        Path to configuration file
  -q, --quiet           Quiet mode - only output transcription and errors
  -i FILE, --input FILE
                        Transcribe audio file instead of recording
  -o FILE, --output FILE
                        Append transcripts to file
  --test                Test API configuration and exit
  --list_devices        List available audio input devices
  --device DEV          Audio input device (name or index)
  -e, --edit            Open configuration file in editor
  --generate_config     Create config file at ~/.config/asr2clip/config.yaml
  --print_config        Print template configuration to stdout
  --vad                 Continuous recording with voice activity detection
  --interval SEC        Continuous recording with fixed interval (seconds)
  --adaptive            Adaptive threshold (default when --vad is used)
  --calibrate           Calibrate silence threshold from ambient noise
  --silence_threshold RMS
                        Silence threshold (default: auto with adaptive)
  --silence_duration SEC
                        Silence duration to trigger transcription (default: 1.5)
  --no_adaptive         Disable adaptive threshold (use fixed threshold)
```

### Examples

```bash
# Single recording (press Ctrl+C to stop)
asr2clip

# Transcribe an audio file
asr2clip -i recording.mp3

# Save transcript to file
asr2clip -o transcript.txt

# Use specific audio device
asr2clip --device pulse
```

### Continuous Recording Mode

For long recordings like meetings or lectures, use `--vad` or `--interval`:

```bash
# Continuous with voice activity detection (auto-transcribe on silence)
asr2clip --vad -o ~/meeting.txt

# Continuous with fixed interval (transcribe every 60 seconds)
asr2clip --interval 60 -o ~/meeting.txt

# Combine VAD with max interval
asr2clip --vad --interval 120 -o ~/meeting.txt
```

In continuous mode:
- Audio is recorded continuously
- Transcription happens automatically (on silence or at interval)
- Press Ctrl+C once to stop (transcribes remaining audio before exit)
- Transcripts are appended to the output file with timestamps

### Voice Activity Detection (VAD)

Enable automatic transcription when you stop speaking:

```bash
# Auto-transcribe when silence is detected
asr2clip --daemon --vad

# Calibrate silence threshold for your environment
asr2clip --calibrate

# Use custom silence settings
asr2clip --daemon --vad --silence_threshold 0.005 --silence_duration 2.0
```

VAD options:
- `--vad`: Enable voice activity detection
- `--adaptive`: Enable adaptive threshold that adjusts to ambient noise on-the-fly
- `--calibrate`: Measure ambient noise and suggest threshold
- `--silence_threshold`: RMS threshold for silence (default: 0.01)
- `--silence_duration`: Seconds of silence to trigger transcription (default: 1.5)

With VAD enabled, transcription is triggered when:
1. Speech is detected (audio above threshold)
2. Followed by silence (audio below threshold for the specified duration)

Tip: Use `--adaptive` for automatic threshold adjustment during recording:
```bash
asr2clip --daemon --vad --adaptive
```
This continuously monitors ambient noise and adjusts the threshold accordingly.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Audio not captured | Run `asr2clip --list_devices` and select a working device |
| Clipboard not working | Install `xclip` (X11) or `wl-clipboard` (Wayland) |
| API errors | Check your API key and endpoint in config |
| Silent audio | Try a different audio device with `--device` |

Run `asr2clip --test` to diagnose issues.

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request. We welcome any improvements or new features!

## License

This project is licensed under the GNU Affero General Public License v3.0. See the [LICENSE](LICENSE) file for details.