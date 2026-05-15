"""Minimal demo server for admin panel development."""

import argparse
import time

from .server import AdminServer, TranscriptionStats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8082)
    args = parser.parse_args()

    config = {
        "engine": "openai_compat",
        "api_base_url": "https://api.openai.com/v1/audio/transcriptions",
        "model_name": "whisper-1",
        "api_key": "sk-demo-1234567890abcdef",
        "quiet": False,
    }

    stats = TranscriptionStats()
    stats.record_success("Hello world, this is a test transcription.", 3.5)
    stats.record_success("Another transcription example.", 2.1)

    server = AdminServer(
        config=config,
        stats=stats,
        host="127.0.0.1",
        port=args.port,
        mode="vad",
        device="default",
    )

    info = server.start()
    print(f"Admin panel running at: {info.url}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
