# KB Collector

`kb-collector` is the Hermes skill for collecting YouTube sources, web URLs, and pasted text into George's Obsidian Knowledge vault. `scripts/collect.py` is the only supported collection entrypoint; it writes the canonical Markdown format and uses the dedicated MLX transcription environment for YouTube audio.

## Runtime

The supported audio-to-text runtime is:

- Executable: `/Users/george/venv-mlx-whisper/bin/mlx_whisper`
- Model: `mlx-community/whisper-large-v3-turbo`
- Language: `zh`
- Required guard: `--condition-on-previous-text False`

YouTube transcript acquisition remains captions-first: creator captions, then YouTube auto captions, then MLX audio transcription when captions are unavailable or visibly unfit. The caption helper is documented in the Hermes `youtube-content` skill. `collect.py youtube` is the deterministic MLX audio fallback and persistence path.

## Setup

`setup.sh` creates or validates `/Users/george/venv-mlx-whisper`, installs `mlx-whisper` and the ordinary collector dependencies into that isolated environment, and checks `yt-dlp`, `ffmpeg`, and `ffprobe`. It never installs Python packages globally.

```bash
cd /Users/george/.hermes/skills/kb-collector
./setup.sh
```

Copy `.env.example` to `.env` only when configuring a new installation. Existing `.env` files are preserved; never commit them.

## Commands

```bash
/Users/george/venv-mlx-whisper/bin/python scripts/collect.py youtube "https://www.youtube.com/watch?v=..." --tags "topic,source"
/Users/george/venv-mlx-whisper/bin/python scripts/collect.py url "https://example.com/article" --tags "topic"
/Users/george/venv-mlx-whisper/bin/python scripts/collect.py text "Pasted content" --title "My Note" --tags "topic"
```

Use `--summary` when a summary was already produced by the approved summary workflow. The supported `AI_PROVIDER` values are `minimax` and `none`; `minimax` uses MiniMax-M3 and `none` skips inline summarization.

## Canonical Output

Every note is saved as `YYYY-MM-DD-<title>.md` under `VAULT_PATH` and contains:

1. YAML frontmatter with collection date/time, exact source, source type, original publication date, author, collector, and tags.
2. `# <title>`
3. `## Source Snapshot`
4. `## AI Summary`
5. `## Analysis & Red Team`
6. `## George Annotation`
7. `## Raw Transcript` for YouTube or `## Content` for other sources
8. `## Collection Metadata`

For YouTube notes created by `collect.py`, `transcript_source: whisper` records the MLX-backed audio provenance. Caption-backed notes must record their actual caption provenance when materialized through the documented caption workflow.

The source publication date (`source_published_at`) is kept separate from the collection date (`date`) and timestamp (`created`). Pasted text uses `source: pasted text` and `source_type: text`.

## Existing Knowledge Cleanup

Use the backup-first normalizer for old notes:

```bash
/Users/george/venv-mlx-whisper/bin/python scripts/normalize_knowledge_markdown.py \
  --vault /Users/george/Documents/Georges/Knowledge \
  --backup-dir <backup-dir>
```

The Annotation Review Desk is maintained in the durable project folder, not in this runtime skill.

## Development

Run the focused tests without a model download or network call:

```bash
python3 tests/test_collect_format.py
```

The live Hermes checkout at `/Users/george/.hermes/skills/kb-collector/` is the runtime source and the GitHub source repository. The durable project folder at `/Users/george/Documents/Georges/01 🎯 Projects/kb-collector/` holds operating documentation and the Annotation Review Desk; it is not a second runtime or source mirror. This cleanup intentionally does not commit or push.
