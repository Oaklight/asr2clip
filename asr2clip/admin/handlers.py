"""HTTP request handlers for admin panel.

This module provides route registration for the admin panel using
the zerodep httpserver, implementing REST API endpoints for status
monitoring, configuration management, and device control.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

from asr2clip import __version__

from .._vendor.httpserver import Request, Response
from .static import ADMIN_HTML

from .server import AdminApp


# ============== CORS Constants ==============

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

# Allowed config keys for POST /api/config
_WRITABLE_CONFIG_KEYS = {
    "engine",
    "api_base_url",
    "api_key",
    "model_name",
    "quiet",
    "model_config_path",
    "model_dir",
    "num_threads",
}


# ============== Request Helpers ==============


def _app(request: Request) -> AdminApp:
    """Get the typed AdminApp from a request."""
    return cast(AdminApp, request.app)


# ============== Response Helpers ==============


def _json_response(data: Any, status_code: int = 200) -> Response:
    """Create a JSON response.

    Args:
        data: The data to serialize as JSON.
        status_code: HTTP status code.

    Returns:
        Response with JSON content type.
    """
    body = json.dumps(data)
    return Response(
        body=body,
        status_code=status_code,
        content_type="application/json; charset=utf-8",
    )


def _error_response(status: int, error: str, message: str) -> Response:
    """Create an error JSON response.

    Args:
        status: HTTP status code.
        error: Error type/name.
        message: Detailed error message.

    Returns:
        Response with error details.
    """
    return _json_response({"error": error, "message": message}, status)


def _add_cors(response: Response) -> Response:
    """Add CORS headers to a response.

    Args:
        response: The response to add headers to.

    Returns:
        The response with CORS headers added.
    """
    response.headers.update(_CORS_HEADERS)
    return response


def _mask_api_key(key: str | None) -> str:
    """Mask an API key for display.

    Args:
        key: The API key to mask.

    Returns:
        Masked key string.
    """
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{'*' * 8}...{key[-4:]}"


# ============== Middleware Handlers ==============


def _cors_preflight(request: Request) -> Response | None:
    """Handle CORS preflight requests."""
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=dict(_CORS_HEADERS))
    return None


def _after_cors(request: Request, response: Response) -> None:
    """Add CORS headers to all routed responses."""
    _add_cors(response)


def _handle_404(request: Request, exc: Any) -> Response:
    """Handle 404 errors with CORS headers."""
    return _add_cors(
        _error_response(404, "Not Found", f"Path not found: {request.path}")
    )


def _handle_405(request: Request, exc: Any) -> Response:
    """Handle 405 errors with CORS headers."""
    return _add_cors(_error_response(405, "Method Not Allowed", "Method Not Allowed"))


# ============== Route Handlers ==============


def _handle_root(request: Request) -> Response:
    """Serve the admin HTML page."""
    return Response(
        body=ADMIN_HTML,
        status_code=200,
        content_type="text/html; charset=utf-8",
    )


def _handle_status(request: Request) -> Response:
    """Return overall status."""
    app = _app(request)
    stats = app.stats.snapshot()
    return _json_response(
        {
            "version": __version__,
            "mode": app.mode,
            "uptime": stats["uptime"],
            "pid": os.getpid(),
            "device": _format_device(app.device),
        }
    )


def _handle_get_config(request: Request) -> Response:
    """Return current configuration (with masked API key)."""
    app = _app(request)
    config = app.config

    safe_config = {
        "engine": config.get("engine", "openai_compat"),
        "api_base_url": config.get("api_base_url", ""),
        "model_name": config.get("model_name", ""),
        "api_key": _mask_api_key(config.get("api_key")),
        "quiet": config.get("quiet", False),
        "audio_device": _format_device(config.get("audio_device", app.device)),
        "model_config_path": config.get("model_config_path", ""),
        "model_dir": config.get("model_dir", ""),
        "num_threads": config.get("num_threads", 4),
    }
    return _json_response(safe_config)


def _handle_update_config(request: Request) -> Response:
    """Update configuration fields.

    Accepts a JSON body with fields to update. Only whitelisted keys
    are accepted. Changes are applied to the running config and
    persisted to disk.
    """
    if not request.body:
        return _error_response(400, "Bad Request", "Request body is required")

    try:
        data = request.json()
    except (json.JSONDecodeError, ValueError) as e:
        return _error_response(400, "Bad Request", f"Invalid JSON: {e}")

    if not isinstance(data, dict) or not data:
        return _error_response(
            400, "Bad Request", "Body must be a non-empty JSON object"
        )

    # Filter to allowed keys only
    updates = {k: v for k, v in data.items() if k in _WRITABLE_CONFIG_KEYS}
    if not updates:
        return _error_response(
            400,
            "Bad Request",
            f"No valid fields. Allowed: {sorted(_WRITABLE_CONFIG_KEYS)}",
        )

    app = _app(request)
    app.config.update(updates)

    # Persist to disk
    try:
        from ..config import write_config

        write_config(app.config)
    except Exception as e:
        return _json_response(
            {
                "success": True,
                "message": "Config updated in memory but failed to save to disk",
                "error": str(e),
                "updated": list(updates.keys()),
            }
        )

    return _json_response(
        {
            "success": True,
            "message": "Configuration updated",
            "updated": list(updates.keys()),
        }
    )


def _handle_devices(request: Request) -> Response:
    """Return available audio input devices."""
    app = _app(request)
    current_device = app.config.get("audio_device", app.device)

    try:
        import sounddevice as sd

        devices = sd.query_devices()
        default_input = sd.default.device[0]
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                is_active = False
                if current_device is not None:
                    is_active = str(current_device) == str(i) or str(
                        current_device
                    ) == str(dev["name"])
                elif i == default_input:
                    is_active = True

                input_devices.append(
                    {
                        "index": i,
                        "name": dev["name"],
                        "channels": dev["max_input_channels"],
                        "sample_rate": dev["default_samplerate"],
                        "is_default": i == default_input,
                        "is_active": is_active,
                    }
                )
        return _json_response({"devices": input_devices})
    except Exception as e:
        return _json_response({"devices": [], "error": str(e)})


def _handle_set_device(request: Request) -> Response:
    """Set the active audio input device.

    Accepts JSON body with ``index`` (int) or ``name`` (str) field.
    """
    if not request.body:
        return _error_response(400, "Bad Request", "Request body is required")

    try:
        data = request.json()
    except (json.JSONDecodeError, ValueError) as e:
        return _error_response(400, "Bad Request", f"Invalid JSON: {e}")

    device = data.get("index", data.get("name"))
    if device is None:
        return _error_response(400, "Bad Request", "'index' or 'name' is required")

    app = _app(request)
    app.device = device
    app.config["audio_device"] = device

    # Persist
    try:
        from ..config import write_config

        write_config(app.config)
    except Exception:
        pass

    return _json_response(
        {
            "success": True,
            "message": f"Device set to {device}",
            "device": _format_device(device),
        }
    )


def _handle_restart_engine(request: Request) -> Response:
    """Restart the ASR engine with current configuration.

    Hot-reloads the engine by creating a new instance from the current
    config and replacing the shared engine reference used by the daemon.
    """
    app = _app(request)

    if app.engine_ref is None:
        return _error_response(
            503,
            "Unavailable",
            "Engine hot-reload is not available (no engine reference)",
        )

    try:
        from ..engines import create_engine

        new_engine = create_engine(app.config)
    except Exception as e:
        return _error_response(500, "Engine Error", f"Failed to create engine: {e}")

    # Test the new engine
    try:
        new_engine.test()
    except Exception as e:
        return _error_response(500, "Engine Error", f"Engine test failed: {e}")

    # Swap the engine
    old_name = app.engine_ref[0].name if app.engine_ref[0] else "none"
    app.engine_ref[0] = new_engine

    return _json_response(
        {
            "success": True,
            "message": "Engine restarted",
            "old_engine": old_name,
            "new_engine": new_engine.name,
        }
    )


def _handle_stats(request: Request) -> Response:
    """Return transcription statistics."""
    app = _app(request)
    return _json_response(app.stats.snapshot())


def _handle_history(request: Request) -> Response:
    """Return transcription history (newest first, max 50 entries)."""
    app = _app(request)
    return _json_response({"history": app.stats.get_history()})


def _handle_test_record(request: Request) -> Response:
    """Record audio for a short duration and transcribe it.

    Accepts POST with optional JSON body ``{"duration": 3}``.
    Duration defaults to 3 seconds and is capped at 10.

    Args:
        request: The incoming HTTP request.

    Returns:
        JSON response with transcription text and duration, or an
        error response on failure.
    """
    app = _app(request)

    if app.engine_ref is None or app.engine_ref[0] is None:
        return _error_response(
            503,
            "Unavailable",
            "No ASR engine available. Start the daemon first.",
        )

    # Parse optional duration from request body
    duration = 3
    if request.body:
        try:
            data = request.json()
            raw = data.get("duration", 3)
            duration = max(1, min(int(raw), 10))
        except (json.JSONDecodeError, ValueError, TypeError):
            duration = 3

    sample_rate = 16000
    channels = 1
    device = app.device

    # Record audio
    try:
        import sounddevice as sd

        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            device=device,
        )
        sd.wait()
    except Exception as e:
        return _error_response(500, "Recording Error", f"Failed to record audio: {e}")

    # Save to temp file and build AudioInput
    temp_path: str | None = None
    try:
        from ..audio import save_audio
        from ..engines.audio_input import AudioInput

        temp_path = save_audio(audio_data, sample_rate)
        audio_input = AudioInput.from_file(temp_path)

        engine = app.engine_ref[0]
        result = engine.transcribe(audio_input)

        return _json_response(
            {
                "success": True,
                "text": result.text,
                "duration": round(result.duration, 2),
            }
        )
    except Exception as e:
        return _error_response(
            500, "Transcription Error", f"Failed to transcribe audio: {e}"
        )
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _format_device(device: str | int | None) -> str:
    """Format device value for display.

    Args:
        device: Audio device name, index, or None.

    Returns:
        Human-readable device string.
    """
    if device is None:
        return "system default"
    return str(device)


# ============== Route Setup ==============


def setup_routes(app: AdminApp) -> None:
    """Register all middleware and routes on the app.

    Args:
        app: The AdminApp instance with config and stats attributes.
    """
    # Middleware
    app.before_request(_cors_preflight)
    app.after_request(_after_cors)
    app.errorhandler(404)(_handle_404)
    app.errorhandler(405)(_handle_405)

    # Routes
    app.get("/")(_handle_root)
    app.get("/api/status")(_handle_status)
    app.get("/api/config")(_handle_get_config)
    app.post("/api/config")(_handle_update_config)
    app.get("/api/devices")(_handle_devices)
    app.post("/api/device")(_handle_set_device)
    app.post("/api/restart-engine")(_handle_restart_engine)
    app.get("/api/stats")(_handle_stats)
    app.get("/api/history")(_handle_history)
    app.post("/api/test-record")(_handle_test_record)
