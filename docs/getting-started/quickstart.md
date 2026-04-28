# Quick Start

## 1. Install

```bash
pip install asr2clip
```

## 2. Configure

Create and edit your configuration file:

```bash
asr2clip --edit
```

This opens the config file in your default editor. Fill in your ASR API credentials:

```yaml
api_base_url: "https://api.openai.com/v1/"
api_key: "YOUR_API_KEY"
model_name: "whisper-1"
```

## 3. Test

Verify your setup:

```bash
asr2clip --test
```

This checks clipboard support, audio device functionality, and API connection.

## 4. Record and Transcribe

```bash
# Single recording (press Ctrl+C to stop)
asr2clip

# Continuous with voice activity detection
asr2clip --vad

# Transcribe an audio file
asr2clip -i audio.mp3
```

The transcription result is automatically copied to your clipboard.
