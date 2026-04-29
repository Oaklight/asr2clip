# Configuration

## Config File Format

asr2clip uses YAML configuration files:

```yaml
api_base_url: "https://api.openai.com/v1/"  # ASR API endpoint
api_key: "YOUR_API_KEY"                     # API key
model_name: "whisper-1"                     # Model name
# quiet: false                              # Optional: disable logging
# audio_device: "pulse"                     # Optional: audio input device
```

## Config File Locations

Config files are searched in the following order:

1. `./asr2clip.conf` — current directory
2. `~/.config/asr2clip/config.yaml` — XDG config (recommended)
3. `~/.config/asr2clip.conf` — legacy
4. `~/.asr2clip.conf` — legacy

## Managing Configuration

```bash
asr2clip --edit            # Open config in editor (creates if needed)
asr2clip --generate_config # Generate config at ~/.config/asr2clip/config.yaml
asr2clip --print_config    # Print config template to stdout
asr2clip -c /path/to/file  # Use a specific config file
```

## Supported Backends

### OpenAI Whisper

```yaml
api_base_url: "https://api.openai.com/v1/"
api_key: "sk-..."
model_name: "whisper-1"
```

### SiliconFlow

```yaml
api_base_url: "https://api.siliconflow.cn/v1/"
api_key: "YOUR_KEY"
model_name: "FunAudioLLM/SenseVoiceSmall"
```

### Xinference (Self-hosted)

```yaml
api_base_url: "http://localhost:9997/v1/"
api_key: "not-used"
model_name: "SenseVoiceSmall"
```

### Local ASR Server

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sensevoice-small"
```

See [Local ASR Server](../usage/local-asr.md) for setup instructions.

## Audio Device Selection

```bash
asr2clip --list_devices    # List all audio input devices
asr2clip --device pulse    # Use specific device by name
asr2clip --device 12       # Use specific device by index
```

Or set in the config file:

```yaml
audio_device: "pulse"  # or device index
```
