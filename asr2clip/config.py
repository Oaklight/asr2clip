"""Configuration management for asr2clip."""

import os
import subprocess
import sys

import yaml

# Default paths to search for config file (in order of priority)
CONFIG_PATHS = [
    "asr2clip.conf",  # Current directory
    os.path.expanduser("~/.config/asr2clip/config.yaml"),  # XDG style
    os.path.expanduser("~/.config/asr2clip.conf"),  # Legacy
    os.path.expanduser("~/.asr2clip.conf"),  # Home directory
]

# Default config location for new configs
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/asr2clip/config.yaml")

# Default config template
CONFIG_TEMPLATE = """api_base_url: "https://api.openai.com/v1/"  # or other compatible API base URL
api_key: "YOUR_API_KEY"                     # api key for the platform
model_name: "whisper-1"                     # or other compatible model
# quiet: false                              # optional, `true` only allow errors and transcriptions
# org_id: none                              # optional, only required if you are using OpenAI organization id
# audio_device: null                        # optional, audio input device (name or index)
                                            # use `asr2clip --list_devices` to see available devices
                                            # common values: "pulse", "pipewire", or device index like 12
"""

CONFIG_TEMPLATE_FULL = """
api_base_url: "https://api.openai.com/v1/"  # or other compatible API base URL
api_key: "YOUR_API_KEY"                     # api key for the platform
model_name: "whisper-1"                     # or other compatible model
# quiet: false                              # optional, `true` only allow errors and transcriptions
# org_id: none                              # optional, only required if you are using OpenAI organization id
# audio_device: null                        # optional, audio input device (name or index). Use --list_devices to see available devices

# xinference or other selfhosted platform
# api_base_url: "https://localhost:9997/v1" # or other compatible API base URL
# api_key: "none-or-random"
# model_name: "SenseVoiceSmall"             # or other compatible model

# SiliconFlow or other compatible platform
# api_base_url: "https://api.siliconflow.com/v1/"  # or other compatible API base URL
# api_key: "YOUR_API_KEY"                          # api key for the platform
# model_name: "FunAudioLLM/SenseVoiceSmall"
"""


def find_config_path(config_file: str = None) -> str | None:
    """Find the configuration file path.

    Args:
        config_file: Optional path to a specific config file.

    Returns:
        Path to the config file if found, None otherwise.
    """
    if config_file and os.path.exists(config_file):
        return config_file

    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path

    return None


def read_config(config_file: str) -> dict:
    """Read and parse the configuration file.

    Args:
        config_file: Path to the configuration file.

    Returns:
        Dictionary containing the configuration.

    Raises:
        SystemExit: If the config file is not found or cannot be read.
    """
    config_path = find_config_path(config_file)

    if config_path is None:
        print("Configuration file not found.")
        print("\nSearched locations:")
        for path in CONFIG_PATHS:
            print(f"  - {path}")
        print("\nTo create a new configuration file, run:")
        print("    asr2clip --generate_config")
        print("\nOr create and edit directly:")
        print("    asr2clip --edit")
        sys.exit(1)

    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            # Handle legacy config format
            if "asr_model" in config and len(config) == 1:
                return config["asr_model"]
            return config
    except Exception as e:
        print(f"Could not read configuration file {config_path}: {e}")
        sys.exit(1)


def open_in_editor(config_file: str = None):
    """Open the configuration file in the system's default editor.

    Args:
        config_file: Optional path to a specific config file.

    Raises:
        SystemExit: If no suitable editor is found.
    """
    config_path = find_config_path(config_file)

    # If no config exists, create a default one
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
        config_dir = os.path.dirname(config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

        with open(config_path, "w") as f:
            f.write(CONFIG_TEMPLATE)
        print(f"Created new config file: {config_path}")

    # Determine which editor to use
    editors_to_try = []
    if os.getenv("EDITOR"):
        editors_to_try.append(os.getenv("EDITOR"))

    if os.name == "nt":  # Windows
        editors_to_try.append("notepad")
    else:  # Unix-like
        editors_to_try.extend(["nano", "vi", "vim"])

    for editor in editors_to_try:
        try:
            subprocess.run([editor, config_path], check=True)
            return
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Failed to open editor '{editor}': {e}")
            sys.exit(1)

    print(f"No suitable editor found. Please edit manually: {config_path}")
    sys.exit(1)


def generate_config(
    output_path: str = None, force: bool = False, print_only: bool = False
) -> str | None:
    """Generate a template configuration file.

    Args:
        output_path: Path to write the config file. If None, uses DEFAULT_CONFIG_PATH.
        force: If True, overwrite existing file.
        print_only: If True, print to stdout instead of writing to file.

    Returns:
        Path to the generated config file, or None if print_only.
    """
    if print_only:
        print(CONFIG_TEMPLATE_FULL.strip())
        return None

    if output_path is None:
        output_path = DEFAULT_CONFIG_PATH

    # Check if file already exists
    if os.path.exists(output_path) and not force:
        print(f"Config file already exists: {output_path}")
        print("Use --edit to modify it, or delete it first to regenerate.")
        return output_path

    # Create directory if needed
    config_dir = os.path.dirname(output_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)

    # Write config file
    with open(output_path, "w") as f:
        f.write(CONFIG_TEMPLATE_FULL.strip() + "\n")

    print(f"Created config file: {output_path}")
    print("\nEdit it with your API credentials:")
    print("    asr2clip --edit")
    print("\nOr edit directly:")
    print(f"    $EDITOR {output_path}")

    return output_path


def get_api_config(config: dict) -> tuple[str, str, str, str | None]:
    """Extract API configuration from config dictionary.

    Args:
        config: Configuration dictionary.

    Returns:
        Tuple of (api_key, api_base_url, model_name, org_id).
    """
    api_key = config.get("api_key", os.environ.get("OPENAI_API_KEY"))
    api_base_url = config.get("api_base_url", "https://api.openai.com/v1")
    model_name = config.get("model_name", "whisper-1")
    org_id = config.get("org_id", os.environ.get("OPENAI_ORG_ID"))
    return api_key, api_base_url, model_name, org_id


def get_audio_device(config: dict, cli_device: str = None) -> str | int | None:
    """Get audio device from config or CLI argument.

    Args:
        config: Configuration dictionary.
        cli_device: Optional device specified via CLI.

    Returns:
        Audio device name, index, or None for default.
    """
    device = cli_device if cli_device is not None else config.get("audio_device", None)

    # Convert device to int if it's a numeric string
    if device is not None and isinstance(device, str) and device.isdigit():
        device = int(device)

    return device
