"""Minimal demo server for admin panel development."""

import argparse
import time

from ..config import read_config
from ..engines import create_engine
from .server import AdminServer, TranscriptionStats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8082)
    parser.add_argument("-c", "--config", default=None, help="Path to config file")
    args = parser.parse_args()

    config = read_config(args.config)

    engine = create_engine(config)
    print(f"Engine: {engine.name}")

    stats = TranscriptionStats()
    stats.record_success("Hello world, this is a test transcription.", 3.5)
    stats.record_success("Another transcription example.", 2.1)

    server = AdminServer(
        config=config,
        stats=stats,
        host="127.0.0.1",
        port=args.port,
        mode="demo",
        device="default",
    )

    info = server.start()
    server.set_engine_ref([engine])
    print(f"Admin panel running at: {info.url}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
