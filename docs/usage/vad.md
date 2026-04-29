# Voice Activity Detection

Voice Activity Detection (VAD) enables automatic transcription when you stop speaking.

## Enable VAD

```bash
asr2clip --vad
```

With VAD enabled, transcription triggers when:

1. Speech is detected (audio above threshold)
2. Followed by silence (audio below threshold for the specified duration)

## How It Works

asr2clip uses **multi-feature detection** for robust speech recognition:

- **RMS energy** — measures overall audio volume
- **Zero-crossing rate** — distinguishes speech from noise (speech has lower ZCR)
- **Speech-band frequency ratio** — checks energy concentration in 300-3000 Hz (the human speech band)

All three features must agree before audio is classified as speech, reducing false triggers from keyboard noise, fans, or other non-speech sounds.

## Adaptive Threshold

By default, VAD uses adaptive threshold that adjusts to ambient noise in real-time:

```bash
# Adaptive is enabled by default with --vad
asr2clip --vad

# Disable adaptive threshold (use fixed value)
asr2clip --vad --no_adaptive
```

The adaptive threshold continuously monitors background noise and adjusts sensitivity accordingly, so you don't need to recalibrate when the environment changes.

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

## Behavior Details

- **Minimum speech duration**: 0.5s — short bursts of noise are ignored
- **Maximum speech duration**: 30s — transcription is forced after 30 seconds of continuous speech
- **Speech gap tolerance**: 0.3s — brief pauses within speech are not treated as silence
- **Auto-calibrate on startup**: ambient noise level is measured when recording begins
