# Usage Guide

asr2clip provides several recording modes to fit different use cases.

## Recording Modes

- **[Basic Usage](basic.md)** — Single recording and file transcription
- **[Continuous Mode](continuous-mode.md)** — Long recordings with automatic segmentation
- **[Voice Activity Detection](vad.md)** — Auto-transcribe when you stop speaking
- **[Local ASR Server](local-asr.md)** — Offline transcription with sherpa-onnx

## CLI Reference

```
usage: asr2clip [-h] [-v] [-c FILE] [-q] [-i FILE] [-o FILE] [--test]
                [--list_devices] [--device DEV] [-e] [--generate_config]
                [--print_config] [--vad] [--interval SEC] [--adaptive]
                [--calibrate] [--silence_threshold RMS]
                [--silence_duration SEC] [--no_adaptive]
                [--serve] [--host HOST] [--port PORT]
                [--model-dir DIR] [--num-threads N] [--download-model]
```

### General Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message |
| `-v, --version` | Show version number |
| `-c FILE` | Path to configuration file |
| `-q, --quiet` | Quiet mode — only output transcription and errors |
| `-i FILE` | Transcribe audio file instead of recording |
| `-o FILE` | Append transcripts to file |
| `--test` | Test API configuration and exit |
| `--list_devices` | List available audio input devices |
| `--device DEV` | Audio input device (name or index) |
| `-e, --edit` | Open configuration file in editor |
| `--generate_config` | Create config file |
| `--print_config` | Print config template to stdout |

### VAD & Continuous Mode Options

| Option | Description |
|--------|-------------|
| `--vad` | Continuous recording with voice activity detection |
| `--interval SEC` | Continuous recording with fixed interval |
| `--adaptive` | Adaptive threshold (default with `--vad`) |
| `--calibrate` | Calibrate silence threshold from ambient noise |
| `--silence_threshold RMS` | Silence threshold |
| `--silence_duration SEC` | Silence duration to trigger transcription |
| `--no_adaptive` | Disable adaptive threshold |

### Local ASR Server Options

| Option | Description |
|--------|-------------|
| `--serve` | Start the local ASR API server |
| `--host HOST` | Server bind address (default: `127.0.0.1`) |
| `--port PORT` | Server bind port (default: `8000`) |
| `--model-dir DIR` | Path to ASR model directory |
| `--num-threads N` | Number of inference threads (default: `4`) |
| `--download-model` | Download the SenseVoice model and exit |

!!! tip
    The local ASR server requires the `local_asr` extra: `pip install "asr2clip[local_asr]"`
