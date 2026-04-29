# Basic Usage

## Single Recording

Record audio until you press Ctrl+C, then transcribe and copy to clipboard:

```bash
asr2clip
```

Press **Ctrl+C once** to stop recording and trigger transcription. Press **Ctrl+C twice** to force exit immediately.

## File Transcription

Transcribe an existing audio file:

```bash
asr2clip -i recording.mp3
```

Supported formats include MP3, WAV, FLAC, OGG, and other formats supported by ffmpeg.

## Save to File

Append transcription results to a file with timestamps:

```bash
asr2clip -o transcript.txt
```

## Quiet Mode

Suppress all output except transcription results and errors:

```bash
asr2clip -q
```

## Automatic Retry

If the API request times out, asr2clip automatically retries up to 3 times with a 2-second delay between attempts.

## Examples

```bash
# Record and transcribe
asr2clip

# Transcribe a file and save output
asr2clip -i lecture.mp3 -o notes.txt

# Use a specific audio device in quiet mode
asr2clip --device pulse -q

# Combine recording with file output
asr2clip -o ~/notes.txt
```
