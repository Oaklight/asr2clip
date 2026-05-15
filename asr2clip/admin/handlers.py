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

# Top-level writable config keys
_WRITABLE_TOP_KEYS = {"engine", "quiet", "audio_device"}

# Allowed fields per engine *type* (type itself is always allowed)
_TYPE_FIELDS: dict[str, set[str]] = {
    "openai_compat": {"api_base_url", "api_key", "model_name", "org_id"},
    "sherpa_onnx": {"model_name", "model_config_path", "model_dir", "num_threads"},
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


def _safe_engine_fields(ecfg: dict) -> dict:
    """Return engine config fields safe for the API response.

    Strips internal keys (like ``type``) and returns only the fields
    that belong to the engine's type-specific configuration.

    Args:
        ecfg: Engine instance config dict (must contain ``type``).

    Returns:
        Filtered dict with ``type`` and type-specific fields.
    """
    etype = ecfg.get("type", "openai_compat")
    allowed = _TYPE_FIELDS.get(etype, set())
    result: dict = {"type": etype}
    for k in allowed:
        if k in ecfg:
            result[k] = ecfg[k]
    return result


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
    """Return current configuration with all engine instances."""
    app = _app(request)
    config = app.config

    from ..config import get_engine_config

    # Build engines dict from config
    engines_out: dict[str, dict] = {}
    engines_raw = config.get("engines", {})
    for inst_name in engines_raw:
        ecfg = get_engine_config(config, inst_name)
        engines_out[inst_name] = _safe_engine_fields(ecfg)

    return _json_response(
        {
            "engine": config.get("engine", ""),
            "quiet": config.get("quiet", False),
            "audio_device": _format_device(config.get("audio_device", app.device)),
            "engines": engines_out,
        }
    )


def _parse_json_body(request: Request) -> dict | Response:
    """Parse and validate a JSON request body.

    Args:
        request: The incoming HTTP request.

    Returns:
        Parsed dict on success, or an error Response on failure.
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
    return data


def _merge_engine_configs(engines_data: dict, config: dict) -> list[str]:
    """Merge per-engine instance fields into config.

    Each instance sub-dict must contain a ``type`` field. Fields are
    validated against ``_TYPE_FIELDS`` for that type.

    Args:
        engines_data: Incoming ``engines`` dict from the request body,
            keyed by instance name.
        config: The live application config dict (mutated in place).

    Returns:
        List of dotted key names that were updated.
    """
    if not engines_data or not isinstance(engines_data, dict):
        return []

    updated: list[str] = []
    config.setdefault("engines", {})

    for inst_name, inst_fields in engines_data.items():
        if not isinstance(inst_fields, dict):
            continue
        etype = inst_fields.get(
            "type", config.get("engines", {}).get(inst_name, {}).get("type")
        )
        allowed = _TYPE_FIELDS.get(etype or "", set())
        filtered = {k: v for k, v in inst_fields.items() if k in allowed}
        if etype:
            filtered["type"] = etype
        if not filtered:
            continue
        config["engines"].setdefault(inst_name, {}).update(filtered)
        updated.append(f"engines.{inst_name}")

    return updated


def _persist_config(config: dict, updated: list[str]) -> Response:
    """Write config to disk and return an appropriate JSON response.

    Args:
        config: The configuration dict to persist.
        updated: List of keys that were updated.

    Returns:
        JSON response indicating success or partial failure.
    """
    try:
        from ..config import write_config

        write_config(config)
    except Exception as e:
        return _json_response(
            {
                "success": True,
                "message": "Config updated in memory but failed to save to disk",
                "error": str(e),
                "updated": updated,
            }
        )

    return _json_response(
        {
            "success": True,
            "message": "Configuration updated",
            "updated": updated,
        }
    )


def _handle_update_config(request: Request) -> Response:
    """Update configuration fields.

    Accepts JSON body with ``engine``, ``quiet``, and an ``engines``
    sub-dict keyed by engine name. Each engine sub-dict is validated
    against its allowed keys and merged into the stored config.
    """
    data = _parse_json_body(request)
    if isinstance(data, Response):
        return data

    app = _app(request)
    updated: list[str] = []

    # Top-level keys
    for key in _WRITABLE_TOP_KEYS:
        if key in data:
            app.config[key] = data[key]
            updated.append(key)

    # Per-engine sub-dicts
    updated.extend(_merge_engine_configs(data.get("engines", {}), app.config))

    if not updated:
        return _error_response(400, "Bad Request", "No valid fields provided")

    return _persist_config(app.config, updated)


def _create_engine_instance(data: dict, config: dict) -> Response:
    """Create a new engine instance in the config.

    Args:
        data: Request data with ``name``, ``type``, and optional fields.
        config: The live config dict (mutated in place).

    Returns:
        JSON response indicating success or error.
    """
    name = data["name"]
    etype = data.get("type", "")
    if etype not in _TYPE_FIELDS:
        return _error_response(400, "Bad Request", f"Unknown engine type: {etype!r}")
    if name in config.get("engines", {}):
        return _error_response(409, "Conflict", f"Engine '{name}' already exists")

    allowed = _TYPE_FIELDS[etype]
    inst = {"type": etype}
    inst.update({k: v for k, v in data.items() if k in allowed})
    config.setdefault("engines", {})[name] = inst
    return _persist_config(config, [f"engines.{name}"])


def _delete_engine_instance(name: str, config: dict) -> Response:
    """Delete an engine instance from the config.

    Args:
        name: Instance name to delete.
        config: The live config dict (mutated in place).

    Returns:
        JSON response indicating success or error.
    """
    if name not in config.get("engines", {}):
        return _error_response(404, "Not Found", f"Engine '{name}' not found")
    if config.get("engine") == name:
        return _error_response(400, "Bad Request", "Cannot delete the active engine")
    del config["engines"][name]
    return _persist_config(config, [f"engines.{name}(deleted)"])


def _handle_manage_engine(request: Request) -> Response:
    """Create or delete an engine instance.

    Accepts JSON body with ``action`` ("create" or "delete") and ``name``.
    For "create", ``type`` is also required.
    """
    data = _parse_json_body(request)
    if isinstance(data, Response):
        return data

    name = data.get("name", "").strip()
    if not name:
        return _error_response(400, "Bad Request", "'name' is required")
    data["name"] = name

    action = data.get("action")
    app = _app(request)

    if action == "create":
        return _create_engine_instance(data, app.config)
    if action == "delete":
        return _delete_engine_instance(name, app.config)
    return _error_response(400, "Bad Request", "action must be 'create' or 'delete'")


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


def _handle_models(request: Request) -> Response:
    """Return registered sherpa-onnx models and their availability."""
    try:
        from ..local_asr.model_registry import create_registry

        registry = create_registry()
        models = []
        default_name = ""
        default_cfg = registry.get_default_model()
        if default_cfg:
            default_name = default_cfg.name
        for cfg in registry.list_models():
            models.append(
                {
                    "name": cfg.name,
                    "type": cfg.type,
                    "available": registry.validate_model(cfg),
                    "is_default": cfg.name == default_name,
                }
            )
        return _json_response({"models": models})
    except Exception as e:
        return _json_response({"models": [], "error": str(e)})


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

    target_rate = 16000
    channels = 1
    # sounddevice expects None for system default, not the string "default"
    device = (
        app.device if app.device not in (None, "default", "system default") else None
    )

    # Record audio at device's native sample rate, then resample to 16kHz
    try:
        import sounddevice as sd

        dev_info = sd.query_devices(device or sd.default.device[0])
        native_rate = int(dev_info["default_samplerate"])

        audio_data = sd.rec(
            int(duration * native_rate),
            samplerate=native_rate,
            channels=channels,
            dtype="float32",
            device=device,
        )
        sd.wait()

        # Resample to 16kHz if needed
        if native_rate != target_rate:
            import numpy as np

            # Simple linear interpolation resample
            n_target = int(len(audio_data) * target_rate / native_rate)
            indices = np.linspace(0, len(audio_data) - 1, n_target)
            audio_data = np.interp(
                indices, np.arange(len(audio_data)), audio_data[:, 0]
            )
            audio_data = audio_data.astype(np.float32).reshape(-1, 1)

        sample_rate = target_rate
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
    app.post("/api/engines")(_handle_manage_engine)
    app.get("/api/devices")(_handle_devices)
    app.post("/api/device")(_handle_set_device)
    app.post("/api/restart-engine")(_handle_restart_engine)
    app.get("/api/stats")(_handle_stats)
    app.get("/api/history")(_handle_history)
    app.get("/api/models")(_handle_models)
    app.post("/api/test-record")(_handle_test_record)
