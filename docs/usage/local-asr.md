# Local ASR Server

asr2clip includes an optional local ASR server powered by [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) for fully offline speech recognition.

## Installation

Install with the `local_asr` extra:

```bash
pip install "asr2clip[local_asr]"
```

## Starting the Server

```bash
asr2clip-serve
```

The server starts on `http://localhost:8000` by default and provides an OpenAI-compatible `/v1/audio/transcriptions` endpoint.

## Configuration

Point asr2clip to the local server:

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sherpa-onnx"
```

## Usage

```bash
# Start the server in one terminal
asr2clip-serve

# Use asr2clip with local server in another terminal
asr2clip -c local_config.yaml
```

## Features

- **Fully offline** — no internet connection required
- **OpenAI-compatible API** — works as a drop-in replacement
- **Automatic model download** — models are downloaded on first use
- **Multiple model support** — configurable ASR models via sherpa-onnx
