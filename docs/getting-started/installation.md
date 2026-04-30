# Installation

## Prerequisites

- **Python 3.10 or higher**

## System Dependencies

Before installing asr2clip, ensure the following system dependencies are available:

| Dependency | Purpose | Linux | macOS | Windows |
|------------|---------|-------|-------|---------|
| **ffmpeg** | Audio format conversion | `apt install ffmpeg` | `brew install ffmpeg` | [Download](https://ffmpeg.org/download.html) |
| **PortAudio** | Audio recording | `apt install libportaudio2` | `brew install portaudio` | Included with sounddevice |
| **Clipboard** | Copy to clipboard | Built-in (copykitten) | Built-in | Built-in |

!!! note
    Clipboard access is handled by [copykitten](https://github.com/koenvervloesem/copykitten), which uses native platform APIs directly. On **Wayland** sessions, asr2clip prefers `wl-copy` (from `wl-clipboard`) for proper clipboard manager integration (e.g. KDE Klipper). Install it with `apt install wl-clipboard` if not already present. On X11, macOS, and Windows, no external tools are needed.

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

See [Local ASR Server](../usage/local-asr.md) for details.
