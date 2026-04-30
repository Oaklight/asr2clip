# Local ASR Server

asr2clip includes an optional local ASR server powered by [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) for fully offline speech recognition.

## Installation

Install with the `local_asr` extra:

```bash
pip install "asr2clip[local_asr]"
```

## Download Model

Pre-download the default SenseVoice model before first use:

```bash
asr2clip --download-model
```

Models are stored in `~/.local/share/asr2clip/models/` by default. You can override this with `--model-dir` or the `ASR2CLIP_MODEL_DIR` environment variable.

## Starting the Server

You can start the server in two ways:

```bash
# Using the dedicated command
asr2clip-serve

# Or using the --serve flag
asr2clip --serve
```

The server starts on `http://localhost:8000` by default and provides an OpenAI-compatible `/v1/audio/transcriptions` endpoint.

### Server Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Server bind address |
| `--port` | `8000` | Server bind port |
| `--model-dir` | auto | Path to ASR model directory |
| `--num-threads` | `4` | Number of inference threads |
| `--config` | auto | Path to `models.yaml` config file |

```bash
# Start on a custom address and port
asr2clip --serve --host 0.0.0.0 --port 9000

# Use a specific model directory
asr2clip --serve --model-dir /path/to/models

# Use a custom models.yaml config
asr2clip-serve --config /path/to/models.yaml
```

## Model Registry

The server uses a YAML-based model registry (`models.yaml`) to manage available models. The registry is automatically created at `~/.local/share/asr2clip/models.yaml` on first run with a default SenseVoice entry.

### Registry Format

```yaml
default_model: sensevoice-small
num_threads: 4

models:
  sensevoice-small:
    type: sense_voice
    dir: sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17
    files:
      model: model.int8.onnx
      tokens: tokens.txt
    options:
      use_itn: true
      language: ""          # empty = auto-detect
    download:
      url: "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
      archive_subdir: sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17
```

### Supported Model Types

| Type | sherpa-onnx Factory | Required Files |
|------|-------------------|----------------|
| `sense_voice` | `from_sense_voice` | `model`, `tokens` |
| `whisper` | `from_whisper` | `encoder`, `decoder`, `tokens` |
| `paraformer` | `from_paraformer` | `paraformer`, `tokens` |
| `transducer` | `from_transducer` | `encoder`, `decoder`, `joiner`, `tokens` |

### Adding a Model

To add a new model, download the sherpa-onnx model files into `~/.local/share/asr2clip/models/<model-dir>/` and add an entry to `models.yaml`:

```yaml
models:
  # ... existing models ...
  whisper-large-v3:
    type: whisper
    dir: sherpa-onnx-whisper-large-v3
    files:
      encoder: encoder.int8.onnx
      decoder: decoder.int8.onnx
      tokens: tokens.txt
    options:
      language: en
```

Models are loaded lazily on first request — only the default model is loaded at startup.

## Configuration

Point asr2clip to the local server:

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sensevoice-small"
```

## API Endpoints

### POST `/v1/audio/transcriptions`

OpenAI-compatible transcription endpoint.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | file | required | Audio file to transcribe |
| `model` | string | required | Model name (must be registered in the model registry) |
| `response_format` | string | `"json"` | `"json"`, `"text"`, or `"verbose_json"` |
| `language` | string | `null` | Language hint (ISO-639-1, e.g. `"en"`, `"zh"`) |
| `prompt` | string | `null` | Prompt text (model-dependent) |
| `temperature` | float | `0.0` | Decoding temperature (model-dependent) |
| `stream` | bool | `false` | Enable SSE streaming response |

**Response formats:**

=== "json (default)"

    ```json
    {"text": "transcribed text"}
    ```

=== "text"

    ```
    transcribed text
    ```

=== "verbose_json"

    ```json
    {
      "task": "transcribe",
      "language": "auto",
      "duration": 2.5,
      "text": "transcribed text",
      "segments": [{"id": 0, "start": 0.0, "end": 2.5, "text": "transcribed text"}]
    }
    ```

**Streaming (SSE):**

When `stream=true`, the response is a `text/event-stream` with the following events:

```
data: {"type": "transcript.text.delta", "delta": "transcribed text"}

data: {"type": "transcript.text.done", "text": "transcribed text", "duration": 2.5, "language": "auto"}

data: [DONE]
```

### GET `/v1/models`

List all registered models.

### GET `/health`

Health check — returns `{"status": "ok"}` or `{"status": "loading"}`.

## Usage

```bash
# Start the server in one terminal
asr2clip --serve

# Use asr2clip with local server in another terminal
asr2clip -c local_config.yaml

# Or transcribe a file directly
asr2clip -c local_config.yaml -i recording.mp3

# Test with curl
curl http://localhost:8000/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=sensevoice-small

# Streaming response
curl http://localhost:8000/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=sensevoice-small \
  -F stream=true
```

## Features

- **Fully offline** — no internet connection required
- **OpenAI-compatible API** — works as a drop-in replacement for cloud ASR services
- **Multi-model support** — register and switch between models via `models.yaml`
- **Model parameter routing** — the `model` field selects which engine to use
- **Language support** — per-request language hints with LRU-cached recognizers
- **SSE streaming** — streaming transcription responses for real-time clients
- **Lazy model loading** — non-default models are loaded on first request
- **Automatic model download** — models with configured download URLs are fetched on first use
- **Integrated CLI** — start the server with `asr2clip --serve` without separate commands
