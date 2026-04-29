# Local ASR Server

asr2clip includes an optional local ASR server powered by [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) for fully offline speech recognition.

## Installation

Install with the `local_asr` extra:

```bash
pip install "asr2clip[local_asr]"
```

## Download Model

Pre-download the SenseVoice model before first use:

```bash
asr2clip --download-model
```

Models are stored in `~/.cache/asr2clip/models/` by default.

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

```bash
# Start on a custom address and port
asr2clip --serve --host 0.0.0.0 --port 9000

# Use a specific model directory
asr2clip --serve --model-dir /path/to/models
```

## Configuration

Point asr2clip to the local server:

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sensevoice-small"
```

## Usage

```bash
# Start the server in one terminal
asr2clip --serve

# Use asr2clip with local server in another terminal
asr2clip -c local_config.yaml

# Or transcribe a file directly
asr2clip -c local_config.yaml -i recording.mp3
```

## Features

- **Fully offline** — no internet connection required
- **OpenAI-compatible API** — works as a drop-in replacement for cloud ASR services
- **Automatic model download** — models are downloaded on first use
- **Multiple model support** — configurable ASR models via sherpa-onnx
- **Integrated CLI** — start the server with `asr2clip --serve` without separate commands
