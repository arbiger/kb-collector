# yt-dlp + MLX fallback for `collect.py youtube` failures

Use this recovery path only when the normal `collect.py youtube` run fails and YouTube captions are unavailable or visibly unfit. Keep the same MLX runtime and canonical writer; do not introduce a second transcription script.

## Decision tree

```text
YouTube URL
  -> creator captions
  -> YouTube auto captions
  -> collect.py youtube (yt-dlp audio + MLX)
  -> manual materialization only after a completed MLX job
```

## Fresh audio recovery

Clear only the exact temporary files for the failed run, then download a fresh audio file:

```bash
rm -f /tmp/kb_collector_audio.m4a /tmp/kb_collector_audio_whisper.wav
rm -f /tmp/kb_collector_audio_whisper.txt
rm -f /tmp/kb_audio_chunks/chunk_*.wav /tmp/kb_audio_chunks/chunk_*.txt

yt-dlp -x --audio-format wav \
  -o "/tmp/yt_<video_id>/audio.%(ext)s" \
  "https://youtu.be/<video_id>"

ffprobe -v error -show_entries format=duration -of csv=p=0 \
  /tmp/yt_<video_id>/audio.wav
```

For a direct one-file transcription, use the exact supported executable and flags:

```bash
/Users/george/venv-mlx-whisper/bin/mlx_whisper \
  /tmp/yt_<video_id>/audio.wav \
  --model mlx-community/whisper-large-v3-turbo \
  --language zh \
  --condition-on-previous-text False \
  --output-format txt \
  --output-dir /tmp/yt_<video_id>
```

Wait for the process to exit and verify the resulting `.txt` file before materializing the canonical note. See `whisper-completion-and-manual-materialization.md` for the completion gate.

## Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Metadata works but audio returns HTTP 403 | YouTube client/rate limit | Retry `yt-dlp` with an appropriate extractor client or wait; do not change the transcription engine |
| Audio duration is much longer than the video | Stale temporary WAV | Remove the exact stale files above and download again |
| Output is empty or partial | MLX process is still running | Verify the process and wait for stable output |
| Output has repetitive text at the opening | Music, silence, or mixed-language opener | Mark the uncertain span for review; do not silently present it as fact |

The canonical `collect.py` path removes its own WAV and MLX text sidecars after the YouTube note is written or the run fails.
