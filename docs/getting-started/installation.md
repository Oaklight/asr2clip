# Installation

## System Dependencies

Before installing asr2clip, ensure the following system dependencies are available:

| Dependency | Purpose | Linux | macOS | Windows |
|------------|---------|-------|-------|---------|
| **ffmpeg** | Audio format conversion | `apt install ffmpeg` | `brew install ffmpeg` | [Download](https://ffmpeg.org/download.html) |
| **PortAudio** | Audio recording | `apt install libportaudio2` | `brew install portaudio` | Included with sounddevice |
| **Clipboard** | Copy to clipboard | `apt install xclip` (X11) or `wl-clipboard` (Wayland) | Built-in | Built-in |

## Install via pip or pipx (Recommended)

```bash
# Install using pip
pip install asr2clip

# Or install using pipx (recommended for isolated environments)
pipx install asr2clip

# Upgrade to latest version
pip install --upgrade asr2clip
```

## Install from source

```bash
git clone https://github.com/Oaklight/asr2clip.git
cd asr2clip
pip install -e .
```

## Optional: Local ASR Server

To use the local ASR server (offline transcription with sherpa-onnx):

```bash
pip install "asr2clip[local_asr]"
```
