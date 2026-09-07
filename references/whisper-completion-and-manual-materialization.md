# MLX completion and manual KB materialization

## Why this exists

Very long captionless videos may be run as a direct MLX job before the final Markdown note is materialized. Reading a staged output before the process has exited can capture only a partial transcript.

## Required completion gate

1. Launch `/Users/george/venv-mlx-whisper/bin/mlx_whisper` with output directed to a video-ID-specific staging directory.
2. Verify the real process with `pgrep -fl mlx_whisper` and `ps -p <PID> -o pid=,pcpu=,etime=,stat=`.
3. Do not read or materialize the transcript while the real process exists, even if the `.txt` file is non-empty.
4. Wait until the process disappears, then verify the output size twice and confirm stderr is empty or understood.
5. Only then build the KB note. If a partial transcript was staged, replace the entire `## Raw Transcript` section from the final output; never append the final transcript to the partial copy.

## Manual materialization shape

Use this only when the caption workflow or a completed MLX job already produced the transcript and rerunning the download would duplicate work:

- preserve the canonical `kb-collector` frontmatter and required body headings;
- record the actual `transcript_source` (`creator_caption`, `youtube_auto_caption`, or `whisper`);
- write the source summary and metadata first;
- append the final transcript once, after the completion gate;
- verify every required heading occurs exactly once and that transcript length matches the final staging file;
- remove the video-ID-specific staging directory after verification.

This is a fallback materialization path, not permission to omit the source-faithful summary or raw evidence. Prefer the canonical `scripts/collect.py` writer whenever the source is being transcribed through its normal MLX path.
