"""FastAPI application providing an OpenAI-compatible ASR endpoint."""

import argparse
import json
import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from .engine import ASREngine, TranscriptionResult
from .model_registry import ModelRegistry, create_registry

logger = logging.getLogger("asr2clip.local_asr")

# Module-level state set during lifespan
_registry: ModelRegistry | None = None
_engines: dict[str, ASREngine] = {}

# Configuration passed via module-level setter before app starts
_config: dict = {}


def configure(
    model_dir: str | None = None,
    num_threads: int = 4,
    config_path: str | None = None,
) -> None:
    """Set server configuration before startup.

    Args:
        model_dir: Legacy path to model directory (overrides default model dir).
        num_threads: Number of inference threads.
        config_path: Path to ``models.yaml`` config file.
    """
    _config["model_dir"] = model_dir
    _config["num_threads"] = num_threads
    _config["config_path"] = config_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the model registry and default engine on startup."""
    global _registry

    registry = create_registry(
        config_path=_config.get("config_path"),
        model_dir=_config.get("model_dir"),
    )
    _registry = registry

    num_threads = _config.get("num_threads") or registry.num_threads

    # Pre-load the default model engine
    default_cfg = registry.get_default_model()

    if not registry.validate_model(default_cfg):
        logger.info("Default model '%s' not found, downloading...", default_cfg.name)
        registry.download_model(default_cfg)

    model_dir = registry.model_dir(default_cfg)
    logger.info("Loading default model '%s' from %s", default_cfg.name, model_dir)

    t0 = time.perf_counter()
    engine = ASREngine.from_model_config(
        default_cfg, model_dir, num_threads=num_threads
    )
    load_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "Model '%s' loaded in %.0f ms (threads=%d)",
        default_cfg.name,
        load_ms,
        num_threads,
    )
    _engines[default_cfg.name] = engine

    yield

    _engines.clear()
    _registry = None


app = FastAPI(title="asr2clip local ASR", lifespan=lifespan)


def _error_response(
    message: str, status_code: int, error_type: str = "invalid_request_error"
):
    """Return an OpenAI-style error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": None,
            }
        },
    )


def _get_engine(model_name: str) -> ASREngine | JSONResponse:
    """Resolve an engine for *model_name*, lazy-loading if needed.

    Returns the engine on success, or an error JSONResponse on failure.
    """
    if _registry is None:
        return _error_response("ASR engine not initialized", 503, "server_error")

    # Return cached engine
    if model_name in _engines:
        return _engines[model_name]

    # Try to lazy-load from registry
    cfg = _registry.get_model(model_name)
    if cfg is None:
        available = [m.name for m in _registry.list_models()]
        return _error_response(
            f"Model '{model_name}' not found. Available models: {available}",
            404,
            "model_not_found",
        )

    if not _registry.validate_model(cfg):
        return _error_response(
            f"Model '{model_name}' is registered but model files are missing. "
            f"Expected files in: {_registry.model_dir(cfg)}",
            503,
            "server_error",
        )

    num_threads = _config.get("num_threads") or _registry.num_threads
    model_dir = _registry.model_dir(cfg)
    logger.info("Lazy-loading model '%s' from %s", cfg.name, model_dir)

    t0 = time.perf_counter()
    engine = ASREngine.from_model_config(cfg, model_dir, num_threads=num_threads)
    load_ms = (time.perf_counter() - t0) * 1000
    logger.info("Model '%s' loaded in %.0f ms", cfg.name, load_ms)

    _engines[model_name] = engine
    return engine


async def _stream_transcription(
    result: TranscriptionResult, language: str | None
) -> AsyncIterator[str]:
    """Yield SSE events for a transcription result (OpenAI-compatible)."""
    delta_event = {
        "type": "transcript.text.delta",
        "delta": result.text,
    }
    yield f"data: {json.dumps(delta_event)}\n\n"

    done_event = {
        "type": "transcript.text.done",
        "text": result.text,
        "duration": round(result.duration, 2),
        "language": language or "auto",
    }
    yield f"data: {json.dumps(done_event)}\n\n"

    yield "data: [DONE]\n\n"


@app.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form(...),
    response_format: str = Form("json"),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    temperature: float = Form(0.0),
    stream: bool = Form(False),
):
    """Transcribe audio to text (OpenAI-compatible endpoint).

    Args:
        file: Audio file to transcribe.
        model: Model name to use for transcription.
        response_format: Response format: "json", "text", or "verbose_json".
        language: Language hint (applied if the model supports it).
        prompt: Prompt text (applied if the model supports it).
        temperature: Temperature (applied if the model supports it).
        stream: If true, return Server-Sent Events stream.

    Returns:
        Transcription result in the requested format.
    """
    engine_or_err = _get_engine(model)
    if isinstance(engine_or_err, JSONResponse):
        return engine_or_err
    engine = engine_or_err

    valid_formats = ("json", "text", "verbose_json")
    if response_format not in valid_formats:
        return _error_response(
            f"Unsupported response_format: {response_format}. "
            f"Supported values: {', '.join(valid_formats)}",
            400,
        )

    audio_data = await file.read()
    if not audio_data:
        return _error_response("Empty audio file", 400)

    filename = file.filename or "audio.wav"

    try:
        t0 = time.perf_counter()
        result = engine.transcribe(
            audio_data,
            filename,
            language=language,
            prompt=prompt,
            temperature=temperature,
        )
        infer_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Transcribed %.1fs audio in %.0f ms (model=%s): %s",
            result.duration,
            infer_ms,
            model,
            result.text[:80],
        )
    except Exception as e:
        logger.exception("Transcription failed")
        return _error_response(f"Transcription failed: {e}", 500, "server_error")

    # Streaming response
    if stream:
        return StreamingResponse(
            _stream_transcription(result, language),
            media_type="text/event-stream",
        )

    if response_format == "text":
        return PlainTextResponse(result.text)

    if response_format == "verbose_json":
        return JSONResponse(
            {
                "task": "transcribe",
                "language": language or "auto",
                "duration": round(result.duration, 2),
                "text": result.text,
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": round(result.duration, 2),
                        "text": result.text,
                    }
                ],
            }
        )

    # Default: json
    return JSONResponse({"text": result.text})


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    if _registry is None:
        return _error_response("Registry not initialized", 503, "server_error")

    data = [
        {
            "id": m.name,
            "object": "model",
            "owned_by": "local",
        }
        for m in _registry.list_models()
    ]
    return JSONResponse({"object": "list", "data": data})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "ok" if _engines else "loading"})


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    model_dir: str | None = None,
    num_threads: int = 4,
    config_path: str | None = None,
) -> None:
    """Start the ASR server.

    Args:
        host: Bind address.
        port: Bind port.
        model_dir: Legacy path to model directory.
        num_threads: Number of inference threads.
        config_path: Path to ``models.yaml`` config file.
    """
    import uvicorn

    configure(model_dir=model_dir, num_threads=num_threads, config_path=config_path)
    logger.info("Starting asr2clip local ASR server on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_server_cli() -> None:
    """CLI entry point for ``asr2clip-serve`` command."""
    parser = argparse.ArgumentParser(
        description="Start the asr2clip local ASR server (OpenAI-compatible)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Bind port (default: 8000)"
    )
    parser.add_argument("--model-dir", default=None, help="Path to model directory")
    parser.add_argument(
        "--num-threads", type=int, default=4, help="Inference threads (default: 4)"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to models.yaml config file",
    )
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="Download the default model and exit",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    if args.download_model:
        registry = create_registry(config_path=args.config, model_dir=args.model_dir)
        default_cfg = registry.get_default_model()
        registry.download_model(default_cfg)
        return

    run_server(
        host=args.host,
        port=args.port,
        model_dir=args.model_dir,
        num_threads=args.num_threads,
        config_path=args.config,
    )
