# Changelog

All notable changes to asr2clip are documented here.

## 0.4.0 (Unreleased)

### Added

- **Local ASR server** — optional offline transcription powered by [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), with OpenAI-compatible API (`asr2clip-serve` / `asr2clip --serve`)
- **Model registry** — YAML-based model management (`models.yaml`) supporting multiple model types (sense_voice, whisper, paraformer, transducer) with lazy loading and auto-download
- **Multi-model routing** — the `model` API parameter selects which engine to use; models are loaded on first request
- **Per-request parameters** — `language`, `prompt`, and `temperature` are passed through to the engine where the model supports them; unsupported parameters are silently accepted
- **Language-specific recognizer caching** — LRU cache of recognizer instances for per-request language hints (configurable cache size, default 3)
- **SSE streaming** — `stream=true` parameter returns Server-Sent Events (`transcript.text.delta`, `transcript.text.done`, `[DONE]`)
- `--download-model` option to pre-download the default model
- `--host` / `--port` / `--config` options for local ASR server configuration
- CI pipeline with ruff, ty, and complexipy checks

### Changed

- **Zero external dependencies** — replaced PyYAML with a vendored YAML parser and httpx/requests with a vendored HTTP client; core install now pulls only numpy, sounddevice, pydub, and copykitten
- **Clipboard library** — replaced pyperclip with [copykitten](https://github.com/koenvervloesem/copykitten) (Rust-based, no external tools like xclip/wl-clipboard needed)
- **Wayland clipboard** — on Wayland sessions, prefers `wl-copy` for proper clipboard manager integration (e.g. KDE Klipper); falls back to copykitten on X11 or when wl-copy is unavailable
- Minimum Python version raised from 3.8 to **3.10**

### Fixed

- `-i` flag now correctly triggers file transcription instead of entering continuous recording mode

## 0.3.8

### Added

- **Voice Activity Detection (VAD)** with `--vad` flag for automatic transcription on silence
- **Multi-feature VAD** — combines RMS energy, zero-crossing rate, and speech-band frequency ratio for robust detection
- **Adaptive threshold** — real-time adjustment to ambient noise (enabled by default with `--vad`)
- **Ambient noise calibration** — `--calibrate` measures environment noise and suggests threshold
- **Continuous recording mode** — `--vad` and `--interval` for long sessions (meetings, lectures)
- **Async transcription** — transcription runs in background with ordered output
- **Automatic retry on timeout** — configurable retry count and delay for API calls
- **Structured logging** with ANSI color support and colored status indicators
- **Double Ctrl+C** to force exit in continuous mode (single Ctrl+C transcribes remaining audio first)
- **Auto-calibrate** ambient noise level on startup

### Changed

- Modularized codebase into separate modules (audio, config, output, transcribe, vad, utils)
- Simplified CLI and improved config management

### Fixed

- Handle multi-dimensional audio arrays in WAV writing
- Skip silence check when VAD confirms speech

## 0.3.7

### Added

- `--version` / `-v` option to display program version
- `--edit` / `-e` option to open config file in default editor
- `--test` command for comprehensive configuration testing (clipboard, audio, API)
- Audio device selection with `--list_devices` and `--device`

### Changed

- Migrated from `setup.py` to `pyproject.toml` with dynamic versioning
- Simplified dependencies by removing unused packages

## 0.3.6

### Added

- `-o FILE` / `--output` option to append transcripts to a file with timestamps
- Transcript output to stdout

## 0.3.5

### Added

- `--generate_config` and `--print_config` for configuration template management
- `org_id` support for OpenAI Organization ID
- Verbose logging with `-q` / `--quiet` toggle

## 0.3.0

### Added

- Input file transcription (`-i FILE`) with ffmpeg-based format conversion
- Support for MP3, WAV, FLAC, OGG, and other ffmpeg-supported formats

### Changed

- Renamed project from `asr_to_clipboard` to `asr2clip`

## 0.2.0

### Added

- Continuous recording mode
- Recording duration option
- Configurable audio settings

## 0.1.0

### Added

- Initial release
- Real-time speech recording and transcription
- Clipboard integration
- YAML configuration file support
- OpenAI Whisper API support
