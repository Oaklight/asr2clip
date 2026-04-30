"""Model registry: configuration, path resolution, validation, and download."""

import os
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

from asr2clip._vendor.httpclient import httpclient
from asr2clip._vendor.yaml import yaml

# Default SenseVoice model metadata
_SENSEVOICE_DIR = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
_SENSEVOICE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    f"{_SENSEVOICE_DIR}.tar.bz2"
)

_DEFAULT_CONFIG_YAML = f"""\
default_model: sensevoice-small
num_threads: 4

models:
  sensevoice-small:
    type: sense_voice
    dir: {_SENSEVOICE_DIR}
    files:
      model: model.int8.onnx
      tokens: tokens.txt
    options:
      use_itn: true
      language: ""
    download:
      url: "{_SENSEVOICE_URL}"
      archive_subdir: {_SENSEVOICE_DIR}
"""


@dataclass
class ModelConfig:
    """Configuration for a single ASR model.

    Attributes:
        name: Registry name (e.g. "sensevoice-small").
        type: Model type matching sherpa-onnx factory (e.g. "sense_voice").
        dir: Directory name relative to models root.
        files: Mapping of logical names to filenames (e.g. model, tokens).
        options: Extra kwargs forwarded to the sherpa-onnx factory.
        download_url: URL to download the model archive.
        archive_subdir: Subdirectory inside the archive that contains model files.
    """

    name: str
    type: str
    dir: str
    files: dict[str, str]
    options: dict[str, object] = field(default_factory=dict)
    download_url: str | None = None
    archive_subdir: str | None = None


class ModelRegistry:
    """Manages ASR model configuration, discovery, and download.

    Args:
        config_path: Path to ``models.yaml``. Created with defaults if missing.
        models_root: Root directory containing model subdirectories.
    """

    def __init__(self, config_path: Path, models_root: Path) -> None:
        self._config_path = config_path
        self._models_root = models_root
        self._models: dict[str, ModelConfig] = {}
        self._default_model: str = ""
        self._num_threads: int = 4
        self._load()

    # -- public API ----------------------------------------------------------

    @property
    def num_threads(self) -> int:
        return self._num_threads

    def get_model(self, name: str) -> ModelConfig | None:
        """Return a model config by name, or ``None`` if not registered."""
        return self._models.get(name)

    def get_default_model(self) -> ModelConfig:
        """Return the default model config.

        Raises:
            RuntimeError: If no models are registered.
        """
        if not self._models:
            raise RuntimeError("No models registered in the model registry")
        cfg = self._models.get(self._default_model)
        if cfg is None:
            # Fall back to first registered model
            cfg = next(iter(self._models.values()))
        return cfg

    def list_models(self) -> list[ModelConfig]:
        """Return all registered model configs."""
        return list(self._models.values())

    def model_dir(self, config: ModelConfig) -> Path:
        """Resolve the absolute model directory for *config*."""
        p = Path(config.dir)
        if p.is_absolute():
            return p
        return self._models_root / config.dir

    def validate_model(self, config: ModelConfig) -> bool:
        """Check that all required files exist for *config*."""
        d = self.model_dir(config)
        return all((d / fname).is_file() for fname in config.files.values())

    def download_model(self, config: ModelConfig, *, force: bool = False) -> Path:
        """Download and extract the model archive for *config*.

        Args:
            config: Model config with ``download_url`` set.
            force: Re-download even if files already exist.

        Returns:
            Path to the extracted model directory.

        Raises:
            SystemExit: On download or extraction failure.
            ValueError: If no download URL is configured.
        """
        model_dir = self.model_dir(config)

        if not force and self.validate_model(config):
            print(f"Model already exists at {model_dir}", file=sys.stderr)
            return model_dir

        if not config.download_url:
            raise ValueError(
                f"No download URL configured for model '{config.name}'. "
                "Please download the model manually and place files in: "
                f"{model_dir}"
            )

        model_dir.mkdir(parents=True, exist_ok=True)
        archive_name = config.download_url.rsplit("/", 1)[-1]
        archive_path = self._models_root / archive_name

        print(f"Downloading model '{config.name}' ...", file=sys.stderr)
        print(f"  From: {config.download_url}", file=sys.stderr)
        print(f"  To:   {archive_path}", file=sys.stderr)

        try:
            with httpclient.get(config.download_url, stream=True, timeout=300) as resp:
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
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=self._models_root)

        archive_path.unlink()

        # If archive extracts to a subdir different from config.dir, handle it
        if config.archive_subdir and config.archive_subdir != config.dir:
            extracted = self._models_root / config.archive_subdir
            if extracted.is_dir() and not model_dir.exists():
                extracted.rename(model_dir)

        if not self.validate_model(config):
            print(
                f"Error: Model files not found after extraction in {model_dir}",
                file=sys.stderr,
            )
            raise SystemExit(1)

        print(f"Model ready at {model_dir}", file=sys.stderr)
        return model_dir

    def get_file_path(self, config: ModelConfig, logical_name: str) -> Path:
        """Return the absolute path for a logical file name.

        Args:
            config: Model config.
            logical_name: Logical name (e.g. "model", "tokens", "encoder").

        Raises:
            KeyError: If *logical_name* is not defined in config.files.
        """
        fname = config.files[logical_name]
        return self.model_dir(config) / fname

    # -- internal ------------------------------------------------------------

    def _load(self) -> None:
        """Load or create the registry config file."""
        if not self._config_path.is_file():
            self._create_default_config()

        text = self._config_path.read_text(encoding="utf-8")
        data = yaml.load(text) or {}

        self._default_model = data.get("default_model", "")
        self._num_threads = data.get("num_threads", 4)

        models_data: dict = data.get("models", {})
        for name, raw in models_data.items():
            download = raw.get("download", {}) or {}
            self._models[name] = ModelConfig(
                name=name,
                type=raw["type"],
                dir=raw["dir"],
                files=raw.get("files", {}),
                options=raw.get("options", {}),
                download_url=download.get("url"),
                archive_subdir=download.get("archive_subdir"),
            )

    def _create_default_config(self) -> None:
        """Write the default ``models.yaml`` with SenseVoice entry."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(_DEFAULT_CONFIG_YAML, encoding="utf-8")
        print(
            f"Created default model registry at {self._config_path}",
            file=sys.stderr,
        )


# -- convenience helpers for CLI / backward compat ---------------------------


def _default_data_dir() -> Path:
    """Return XDG_DATA_HOME / asr2clip or ~/.local/share/asr2clip."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "asr2clip"
    return Path.home() / ".local" / "share" / "asr2clip"


def create_registry(
    config_path: str | None = None,
    model_dir: str | None = None,
) -> ModelRegistry:
    """Create a :class:`ModelRegistry` with sensible defaults.

    Args:
        config_path: Explicit path to ``models.yaml``.
        model_dir: Legacy ``--model-dir`` override. When set, the default
            model's directory is overridden to this path.

    Returns:
        Configured ModelRegistry instance.
    """
    data_dir = _default_data_dir()
    cfg_path = Path(config_path) if config_path else data_dir / "models.yaml"
    models_root = data_dir / "models"
    models_root.mkdir(parents=True, exist_ok=True)

    registry = ModelRegistry(cfg_path, models_root)

    # Legacy --model-dir override: patch the default model's dir to absolute
    if model_dir:
        default = registry.get_default_model()
        default.dir = str(Path(model_dir).resolve())

    return registry
