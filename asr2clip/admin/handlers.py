"""HTTP request handlers for admin panel.

This module provides route registration for the admin panel using
the zerodep httpserver, implementing REST API endpoints for status
monitoring and configuration inspection.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, cast

from asr2clip import __version__

from .._vendor.httpserver import Request, Response
from .static import ADMIN_HTML

if TYPE_CHECKING:
    from .server import AdminApp


# ============== CORS Constants ==============

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ============== Request Helpers ==============


def _app(request: Request) -> AdminApp:
    """Get the typed AdminApp from a request."""
    from .server import AdminApp

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
        return "(not set)"
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


def _handle_config(request: Request) -> Response:
    """Return current configuration (with masked API key)."""
    app = _app(request)
    config = app.config

    safe_config = {
        "api_base_url": config.get("api_base_url", "(not set)"),
        "model_name": config.get("model_name", "(not set)"),
        "api_key": _mask_api_key(config.get("api_key")),
        "quiet": config.get("quiet", False),
        "audio_device": _format_device(config.get("audio_device", app.device)),
    }
    return _json_response(safe_config)


def _handle_devices(request: Request) -> Response:
    """Return available audio input devices."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                input_devices.append(
                    {
                        "index": i,
                        "name": dev["name"],
                        "channels": dev["max_input_channels"],
                        "sample_rate": dev["default_samplerate"],
                        "is_default": i == sd.default.device[0],
                    }
                )
        return _json_response({"devices": input_devices})
    except Exception as e:
        return _json_response({"devices": [], "error": str(e)})


def _handle_stats(request: Request) -> Response:
    """Return transcription statistics."""
    app = _app(request)
    return _json_response(app.stats.snapshot())


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
    app.get("/api/config")(_handle_config)
    app.get("/api/devices")(_handle_devices)
    app.get("/api/stats")(_handle_stats)
