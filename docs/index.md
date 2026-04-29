---
title: Home
author: Oaklight
hide:
  - navigation
---

<div style="display: flex; align-items: center; gap: 1.5em; margin-bottom: 0.5em;">
  <div>
    <h1 style="margin: 0 0 0.2em 0;">asr2clip</h1>
    <p style="margin: 0; font-size: 1.1em; opacity: 0.85;">A real-time speech-to-text clipboard tool.</p>
    <p style="margin: 0.4em 0 0 0;">
      <a href="https://pypi.org/project/asr2clip/"><img src="https://img.shields.io/pypi/v/asr2clip?color=green" alt="PyPI"></a>
      <a href="https://github.com/Oaklight/asr2clip/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/asr2clip?color=green" alt="Release"></a>
      <a href="https://github.com/Oaklight/asr2clip/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="AGPL-3.0"></a>
    </p>
  </div>
</div>

asr2clip recognizes speech in real-time, converts it to text, and automatically copies the result to your system clipboard. It leverages ASR API services for speech recognition and provides flexible recording modes for different use cases.

---

## Quick Start

```bash
pip install asr2clip       # Install the package
asr2clip --edit            # Create/edit config file
asr2clip --test            # Test your configuration
asr2clip                   # Start recording and transcribing
```

---

## Key Features

| | |
|---|---|
| **Real-time Transcription** | Record and transcribe speech with a single command |
| **Clipboard Integration** | Automatically copy results to clipboard (no external tools needed) |
| **Voice Activity Detection** | Multi-feature VAD with adaptive threshold for auto-transcription |
| **Continuous Mode** | Long recording for meetings and lectures |
| **Multiple Backends** | OpenAI Whisper, SiliconFlow, Xinference, and more |
| **Local ASR Server** | Optional offline transcription with sherpa-onnx |
| **File Transcription** | Transcribe existing audio files |
| **Minimal Dependencies** | Core functionality with vendored YAML and HTTP modules |
| **Cross-platform** | Works on Linux, macOS, and Windows |

---

## Use Cases

**Meeting transcription** — Record meetings with continuous mode and VAD, automatically transcribing speech segments to a file with timestamps.

**Quick voice notes** — Press a key, speak, and have the text instantly in your clipboard ready to paste anywhere.

**Lecture notes** — Capture lecture audio with automatic segmentation and transcription.

**Audio file processing** — Transcribe existing audio files from the command line.

---

## Documentation

- **[Installation](getting-started/installation.md)** — System dependencies and installation methods
- **[Quick Start](getting-started/quickstart.md)** — Get up and running in minutes
- **[Configuration](getting-started/configuration.md)** — Config file format and options
- **[Usage Guide](usage/)** — Recording modes, VAD, and advanced features
- **[API Reference](api/)** — Module documentation
- **[Changelog](changelog.md)** — Version history

## License

GNU Affero General Public License v3.0
