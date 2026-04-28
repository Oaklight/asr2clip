"""Model download, path resolution, and validation for SenseVoice."""

import os
import sys
import tarfile
from pathlib import Path

from asr2clip._vendor.httpclient import httpclient

MODEL_ARCHIVE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
)
MODEL_SUBDIR = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
MODEL_FILENAME = "model.int8.onnx"
TOKENS_FILENAME = "tokens.txt"


def _default_data_dir() -> Path:
    """Return XDG_DATA_HOME / asr2clip or ~/.local/share/asr2clip."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "asr2clip"
    return Path.home() / ".local" / "share" / "asr2clip"


def resolve_model_dir(model_dir: str | None = None) -> Path:
    """Resolve the model directory from explicit path, env var, or default.

    Args:
        model_dir: Explicit path override (highest priority).

    Returns:
        Resolved model directory path.
    """
    if model_dir:
        return Path(model_dir)

    env = os.environ.get("ASR2CLIP_MODEL_DIR")
    if env:
        return Path(env)

    return _default_data_dir() / "models" / MODEL_SUBDIR


def get_model_paths(model_dir: Path) -> tuple[Path, Path]:
    """Return (model_onnx_path, tokens_path) within the model directory.

    Args:
        model_dir: Path to the model directory.

    Returns:
        Tuple of (model_path, tokens_path).
    """
    return model_dir / MODEL_FILENAME, model_dir / TOKENS_FILENAME


def validate_model(model_dir: Path) -> bool:
    """Check that required model files exist.

    Args:
        model_dir: Path to the model directory.

    Returns:
        True if all required files are present.
    """
    model_path, tokens_path = get_model_paths(model_dir)
    return model_path.is_file() and tokens_path.is_file()


def download_model(model_dir: Path, force: bool = False) -> Path:
    """Download and extract the SenseVoice model.

    Args:
        model_dir: Target directory for the model files.
        force: If True, re-download even if files exist.

    Returns:
        Path to the extracted model directory.
    """
    if not force and validate_model(model_dir):
        print(f"Model already exists at {model_dir}", file=sys.stderr)
        return model_dir

    # Ensure parent directory exists
    model_dir.mkdir(parents=True, exist_ok=True)
    archive_path = model_dir.parent / f"{MODEL_SUBDIR}.tar.bz2"

    print("Downloading SenseVoice model (~230 MB)...", file=sys.stderr)
    print(f"  From: {MODEL_ARCHIVE_URL}", file=sys.stderr)
    print(f"  To:   {archive_path}", file=sys.stderr)

    try:
        with httpclient.get(MODEL_ARCHIVE_URL, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(archive_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        mb = downloaded / (1024 * 1024)
                        print(
                            f"\r  Progress: {mb:.0f} MB ({pct}%)",
                            end="",
                            flush=True,
                            file=sys.stderr,
                        )

        print(file=sys.stderr)  # newline after progress
    except httpclient.HTTPError as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        if archive_path.exists():
            archive_path.unlink()
        raise SystemExit(1) from e

    print("Extracting...", file=sys.stderr)
    with tarfile.open(archive_path, "r:bz2") as tar:
        tar.extractall(path=model_dir.parent)

    archive_path.unlink()

    if not validate_model(model_dir):
        print(
            f"Error: Model files not found after extraction in {model_dir}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"Model ready at {model_dir}", file=sys.stderr)
    return model_dir
