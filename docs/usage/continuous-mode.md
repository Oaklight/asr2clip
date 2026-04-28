# Continuous Mode

Continuous mode is designed for long recordings such as meetings, lectures, or interviews.

## Fixed Interval Mode

Transcribe at regular intervals:

```bash
# Transcribe every 60 seconds
asr2clip --interval 60 -o ~/meeting.txt
```

## VAD + Interval

Combine voice activity detection with a maximum interval:

```bash
# Auto-transcribe on silence, but at least every 120 seconds
asr2clip --vad --interval 120 -o ~/meeting.txt
```

## Behavior

In continuous mode:

- Audio is recorded continuously
- Transcription happens automatically (on silence or at interval)
- Press **Ctrl+C once** to stop — remaining audio is transcribed before exit
- Transcripts are appended to the output file with timestamps

## Tips

- Always use `-o FILE` to save transcripts — clipboard only holds the latest result
- Combine with `--vad` for natural speech-boundary segmentation
- Use `--interval` as a fallback to ensure nothing is missed during long pauses
