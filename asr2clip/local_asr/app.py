"""FastAPI application providing an OpenAI-compatible ASR endpoint."""

import argparse
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from .engine import ASREngine
from .model_manager import (
    download_model,
    get_model_paths,
    resolve_model_dir,
    validate_model,
)

logger = logging.getLogger("asr2clip.local_asr")

# Module-level state set during lifespan
_engine: ASREngine | None = None
_model_name: str = "sensevoice-small"

# Configuration passed via module-level setter before app starts
_config: dict = {}


def configure(
    model_dir: str | None = None,
    num_threads: int = 4,
) -> None:
    """Set server configuration before startup.

    Args:
        model_dir: Path to model directory (None for auto-detection).
        num_threads: Number of inference threads.
    """
    _config["model_dir"] = model_dir
    _config["num_threads"] = num_threads


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the ASR engine on startup."""
    global _engine

    model_dir = resolve_model_dir(_config.get("model_dir"))
    num_threads = _config.get("num_threads", 4)

    if not validate_model(model_dir):
        logger.info("Model not found at %s, downloading...", model_dir)
        download_model(model_dir)

    model_path, tokens_path = get_model_paths(model_dir)
    logger.info("Loading model from %s", model_dir)

    t0 = time.perf_counter()
    _engine = ASREngine(
        model_path=str(model_path),
        tokens_path=str(tokens_path),
        num_threads=num_threads,
    )
    load_ms = (time.perf_counter() - t0) * 1000
    logger.info("Model loaded in %.0f ms (threads=%d)", load_ms, num_threads)

    yield

    _engine = None


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


@app.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form(...),
    response_format: str = Form("json"),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    temperature: float = Form(0.0),
):
    """Transcribe audio to text (OpenAI-compatible endpoint).

    Args:
        file: Audio file to transcribe.
        model: Model name (accepted but ignored; SenseVoice is always used).
        response_format: Response format: "json", "text", or "verbose_json".
        language: Language hint (accepted but ignored).
        prompt: Prompt text (accepted but ignored).
        temperature: Temperature (accepted but ignored).

    Returns:
        Transcription result in the requested format.
    """
    if _engine is None:
        return _error_response("ASR engine not initialized", 503, "server_error")

    if response_format not in ("json", "text", "verbose_json"):
        return _error_response(
            f"Unsupported response_format: {response_format}. "
            "Supported values: json, text, verbose_json",
            400,
        )

    audio_data = await file.read()
    if not audio_data:
        return _error_response("Empty audio file", 400)

    filename = file.filename or "audio.wav"

    try:
        t0 = time.perf_counter()
        result = _engine.transcribe(audio_data, filename)
        infer_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Transcribed %.1fs audio in %.0f ms: %s",
            result.duration,
            infer_ms,
            result.text[:80],
        )
    except Exception as e:
        logger.exception("Transcription failed")
        return _error_response(f"Transcription failed: {e}", 500, "server_error")

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
    return JSONResponse(
        {
            "object": "list",
            "data": [
                {
                    "id": _model_name,
                    "object": "model",
                    "owned_by": "local",
                }
            ],
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "ok" if _engine is not None else "loading"})


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    model_dir: str | None = None,
    num_threads: int = 4,
) -> None:
    """Start the ASR server.

    Args:
        host: Bind address.
        port: Bind port.
        model_dir: Path to model directory.
        num_threads: Number of inference threads.
    """
    import uvicorn

    configure(model_dir=model_dir, num_threads=num_threads)
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
        "--download-model",
        action="store_true",
        help="Download the SenseVoice model and exit",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    if args.download_model:
        model_dir = resolve_model_dir(args.model_dir)
        download_model(model_dir)
        return

    run_server(
        host=args.host,
        port=args.port,
        model_dir=args.model_dir,
        num_threads=args.num_threads,
    )
