# Basic Usage

## Single Recording

Record audio until you press Ctrl+C, then transcribe and copy to clipboard:

```bash
asr2clip
```

## File Transcription

Transcribe an existing audio file:

```bash
asr2clip -i recording.mp3
```

Supported formats include MP3, WAV, FLAC, OGG, and other formats supported by ffmpeg.

## Save to File

Append transcription results to a file:

```bash
asr2clip -o transcript.txt
```

## Quiet Mode

Suppress all output except transcription results and errors:

```bash
asr2clip -q
```

## Examples

```bash
# Record and transcribe
asr2clip

# Transcribe a file and save output
asr2clip -i lecture.mp3 -o notes.txt

# Use a specific audio device in quiet mode
asr2clip --device pulse -q
```
