# Voice Activity Detection

Voice Activity Detection (VAD) enables automatic transcription when you stop speaking.

## Enable VAD

```bash
asr2clip --vad
```

With VAD enabled, transcription triggers when:

1. Speech is detected (audio above threshold)
2. Followed by silence (audio below threshold for the specified duration)

## Adaptive Threshold

By default, VAD uses adaptive threshold that adjusts to ambient noise in real-time:

```bash
# Adaptive is enabled by default with --vad
asr2clip --vad

# Disable adaptive threshold (use fixed value)
asr2clip --vad --no_adaptive
```

## Calibration

Measure your environment's ambient noise to set an appropriate threshold:

```bash
asr2clip --calibrate
```

This records a short sample of ambient noise and suggests a threshold value.

## Custom Settings

```bash
# Custom silence threshold and duration
asr2clip --vad --silence_threshold 0.005 --silence_duration 2.0
```

## VAD Options

| Option | Default | Description |
|--------|---------|-------------|
| `--vad` | — | Enable voice activity detection |
| `--adaptive` | On (with `--vad`) | Adaptive threshold adjustment |
| `--no_adaptive` | — | Disable adaptive threshold |
| `--silence_threshold` | 0.01 | RMS threshold for silence detection |
| `--silence_duration` | 1.5s | Seconds of silence to trigger transcription |
| `--calibrate` | — | Calibrate threshold from ambient noise |
