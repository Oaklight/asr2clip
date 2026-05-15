"""HTTP server for admin panel.

This module provides the AdminServer class for running the admin panel
as an async HTTP server in a background thread, along with a lightweight
TranscriptionStats collector.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import threading
import time
from dataclasses import dataclass

from .._vendor.httpserver import App

logger = logging.getLogger(__name__)


@dataclass
class AdminInfo:
    """Information about the running admin server.

    Attributes:
        host: The host address the server is bound to.
        port: The port number the server is listening on.
        url: The full URL to access the admin panel.
    """

    host: str
    port: int
    url: str


class TranscriptionStats:
    """Thread-safe transcription statistics collector.

    Attributes:
        transcription_count: Total number of successful transcriptions.
        error_count: Total number of failed transcriptions.
        total_duration: Cumulative audio duration in seconds.
        last_text: Text from the most recent transcription.
        last_timestamp: Timestamp of the most recent transcription.
        start_time: Epoch time when stats collection started.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.transcription_count: int = 0
        self.error_count: int = 0
        self.total_duration: float = 0.0
        self.last_text: str = ""
        self.last_timestamp: float = 0.0
        self.start_time: float = time.time()

    def record_success(self, text: str, duration: float) -> None:
        """Record a successful transcription.

        Args:
            text: The transcribed text.
            duration: Audio duration in seconds.
        """
        with self._lock:
            self.transcription_count += 1
            self.total_duration += duration
            self.last_text = text
            self.last_timestamp = time.time()

    def record_error(self) -> None:
        """Record a failed transcription."""
        with self._lock:
            self.error_count += 1

    def snapshot(self) -> dict:
        """Return a snapshot of current statistics.

        Returns:
            Dictionary containing all stats fields.
        """
        with self._lock:
            return {
                "transcription_count": self.transcription_count,
                "error_count": self.error_count,
                "total_duration": round(self.total_duration, 1),
                "last_text": self.last_text,
                "last_timestamp": self.last_timestamp,
                "uptime": round(time.time() - self.start_time, 1),
            }


class AdminApp(App):
    """App subclass with typed admin-specific attributes.

    Attributes:
        config: The asr2clip configuration dictionary.
        stats: Transcription statistics collector.
        mode: The current operating mode (e.g. "vad", "interval", "serve").
        device: The audio device in use.
        engine_ref: Mutable list holding the current engine instance.
            Shared with the daemon so that hot-reloading is possible
            by replacing ``engine_ref[0]``.
    """

    config: dict
    stats: TranscriptionStats
    mode: str
    device: str | int | None
    engine_ref: list | None


class AdminServer:
    """Admin panel HTTP server.

    Runs an async HTTP server in a background daemon thread, providing
    a REST API and web UI for monitoring asr2clip.

    Example:
        >>> server = AdminServer(config={}, stats=TranscriptionStats())
        >>> info = server.start()
        >>> print(f"Admin panel at: {info.url}")
        >>> server.stop()
    """

    def __init__(
        self,
        config: dict,
        stats: TranscriptionStats,
        host: str = "127.0.0.1",
        port: int = 8081,
        mode: str = "unknown",
        device: str | int | None = None,
    ) -> None:
        """Initialize admin server.

        Args:
            config: The asr2clip configuration dictionary.
            stats: Transcription statistics collector.
            host: The host address to bind to. Defaults to "127.0.0.1".
            port: The port number to listen on. Defaults to 8081.
            mode: The current operating mode. Defaults to "unknown".
            device: The audio device in use. Defaults to None.
        """
        self._config = config
        self._stats = stats
        self._host = host
        self._port = port
        self._mode = mode
        self._device = device
        self._app: AdminApp | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def start(self) -> AdminInfo:
        """Start the server in a background daemon thread.

        Returns:
            AdminInfo containing server details including URL.

        Raises:
            RuntimeError: If the server is already running.
        """
        if self._app is not None:
            raise RuntimeError("Server is already running")

        actual_port = self._find_available_port(self._host, self._port)
        self._port = actual_port

        # Create app and attach context
        self._app = AdminApp()
        self._app.config = self._config
        self._app.stats = self._stats
        self._app.mode = self._mode
        self._app.device = self._device
        self._app.engine_ref = None

        # Register routes
        from .handlers import setup_routes

        setup_routes(self._app)

        # Start server in background thread
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

        # Wait for server to start
        self._started.wait(timeout=5.0)

        display_host = (
            "localhost" if self._host in ("0.0.0.0", "127.0.0.1") else self._host
        )
        url = f"http://{display_host}:{self._port}"

        info = AdminInfo(host=self._host, port=self._port, url=url)
        logger.info("Admin server started at %s", url)
        return info

    def _run_server(self) -> None:
        """Run the async server in a background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_serve())
        finally:
            self._loop.close()
            self._loop = None

    async def _async_serve(self) -> None:
        """Async server coroutine.

        Replicates App._serve() logic but omits signal handler
        registration, which would fail in a non-main thread.
        """
        assert self._app is not None
        app = self._app
        app._shutdown_event = asyncio.Event()

        server = await asyncio.start_server(
            app._handle_connection,
            self._host,
            self._port,
        )

        app._server = server
        addrs = (
            server.sockets[0].getsockname()
            if server.sockets
            else (self._host, self._port)
        )
        app.host = addrs[0]
        app.port = addrs[1]

        # Signal that the server is ready
        self._started.set()

        async with server:
            await app._shutdown_event.wait()

    def stop(self) -> None:
        """Stop the server.

        This method is safe to call even if the server is not running.
        """
        if self._app is not None and self._loop is not None:
            if self._app._shutdown_event is not None:
                self._loop.call_soon_threadsafe(self._app._shutdown_event.set)

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

        self._app = None
        self._started.clear()
        logger.info("Admin server stopped")

    def set_engine_ref(self, engine_ref: list) -> None:
        """Set the shared engine reference.

        Args:
            engine_ref: Mutable list where ``engine_ref[0]`` is the
                current engine instance. Shared with the daemon loop.
        """
        if self._app is not None:
            self._app.engine_ref = engine_ref

    def is_running(self) -> bool:
        """Check if server is running.

        Returns:
            True if the server is running, False otherwise.
        """
        return self._app is not None and self._started.is_set()

    def get_info(self) -> AdminInfo | None:
        """Get server info if running.

        Returns:
            AdminInfo if server is running, None otherwise.
        """
        if not self.is_running():
            return None

        display_host = (
            "localhost" if self._host in ("0.0.0.0", "127.0.0.1") else self._host
        )
        return AdminInfo(
            host=self._host,
            port=self._port,
            url=f"http://{display_host}:{self._port}",
        )

    @staticmethod
    def _find_available_port(host: str, start_port: int) -> int:
        """Find an available port starting from start_port.

        Args:
            host: The host address to check.
            start_port: The port number to start searching from.

        Returns:
            An available port number.

        Raises:
            RuntimeError: If no available port is found after 100 attempts.
        """
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((host, port))
                    return port
            except OSError:
                continue

        raise RuntimeError(
            f"Could not find available port in range {start_port}-{start_port + 99}"
        )
