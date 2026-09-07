---
name: kb-collector
description: Collect YouTube, web URLs, and pasted text into George's Obsidian Knowledge vault using one deterministic Python entrypoint and a canonical Markdown format.
trigger: "^collect\\s+(.+)$"
---

# KB Collector

`kb-collector` is the workflow owner for source collection, routing, canonical Knowledge persistence, and the handoff to summary/annotation. The supported executable entrypoint is:

```bash
/Users/george/venv-mlx-whisper/bin/python \
  /Users/george/.hermes/skills/kb-collector/scripts/collect.py <youtube|url|text> ...
```

Do not hand-write a replacement note layout while this entrypoint is available. Do not call removed wrappers or install another transcription engine.

## Routing Contract

Read [`references/youtube-routing-contract.md`](references/youtube-routing-contract.md) before routing a `Collect` request.

- `Collect <URL>`: acquire once, save one canonical Knowledge note, and complete the source-faithful summary in the same workflow.
- `Collect <URL>, 先給我詳細總結` or `先不要存，我先看詳細總結`: preview and analyze in chat; write nothing until George chooses a destination.
- `跟 <project> 有關，放桌面`: create a Desktop/project working note only. Add Knowledge persistence only when George also asks to collect or save.
- `Collect <URL>，跟 <project> 有關，放桌面`: create the canonical Knowledge note and the linked Desktop/project note.
- Pasted text and long paragraphs follow the same routing. Use `source: pasted text` and `source_type: text`; preserve George's explicit thoughts as `George Annotation`.

`youtube-content` is a read-only helper for temporary transcript acquisition and source inspection. It does not own persistence and must not create a competing KB or project artifact.

## YouTube Acquisition

For a YouTube source, use this order when a transcript preview or caption-backed analysis is needed:

1. Creator-provided captions.
2. YouTube auto-generated captions.
3. Local MLX audio transcription when captions are missing or visibly unfit.

Caption acquisition is performed by the documented `youtube-content` helper workflow. Reuse one temporary transcript for preview and persistence; do not fetch the same video a second time merely because George selected a destination.

`collect.py youtube` is the deterministic audio-transcription and persistence entrypoint. It downloads audio and invokes exactly `/Users/george/venv-mlx-whisper/bin/mlx_whisper` with the configured large-v3-turbo model. It does not silently switch engines. If the caption workflow is selected, record the actual caption provenance in the final note; otherwise use the script's MLX-backed `transcript_source: whisper` output.

## MLX Runtime Contract

The only supported audio-to-text engine is `mlx`:

- Binary: `/Users/george/venv-mlx-whisper/bin/mlx_whisper`
- Model: `mlx-community/whisper-large-v3-turbo`
- Language: `zh`
- Hallucination guard: `--condition-on-previous-text False`
- Output: `--output-format txt` into the temporary audio directory
- Audio conversion: `ffmpeg` to mono 16 kHz WAV; `ffprobe` checks duration
- Audio longer than ten minutes is split into deterministic 600-second chunks

The script rejects any `KB_WHISPER_ENGINE` value other than `mlx`. Setup installs MLX and ordinary collector dependencies into the dedicated `/Users/george/venv-mlx-whisper` environment; it never installs Python packages globally.

## Canonical Markdown

`collect.py` owns the file structure. Every saved note has this frontmatter:

```yaml
date: YYYY-MM-DD                    # collection date
created: YYYY-MM-DDTHH:MM:SS+08:00  # collection timestamp
title: <title>
source: <exact URL or pasted text>
source_type: youtube|facebook|instagram|x|url|text
source_published_at: YYYY-MM-DD|null
transcript_source: whisper           # YouTube notes produced by collect.py
author: <source author or George>
collector: kb-collector
tags:
  - <tag>
```

Required body order:

1. `# <title>`
2. `## Source Snapshot` with source, type, author, publication date, and exact collection timestamp
3. `## AI Summary` with `<!-- AI Summary (<model>) -->` or the missing-summary placeholder
4. `## Analysis & Red Team` for assumptions, counterarguments, uncertainty, and applicability
5. `## George Annotation` for George's own interpretation or correction
6. `## Raw Transcript` for YouTube, or `## Content` for web/text sources
7. `## Collection Metadata`

Keep the source-faithful summary separate from red-team analysis and George's annotation. Never substitute collection time for source publication time.

## Summary Policy

Collection and MLX transcription are local/cheap. Source compression should use the configured cheap path, normally MiniMax-M3, when the main model is quota-limited. George-specific interpretation, red-team analysis, and annotation use the main model when needed. An explicit one-off model request does not change the default.

`AI_PROVIDER` remains an optional inline-summary compatibility setting. The current Hermes configuration may use `minimax`; `--summary` is preferred when the summary was already produced, because it avoids a second API call. Do not silently create a raw-only note when the required summary step is unavailable.

## Commands

Install the dedicated runtime and validate system tools:

```bash
cd /Users/george/.hermes/skills/kb-collector
./setup.sh
```

Collect a source:

```bash
/Users/george/venv-mlx-whisper/bin/python scripts/collect.py youtube "<YouTube URL>" --tags "topic,source"
/Users/george/venv-mlx-whisper/bin/python scripts/collect.py url "<URL>" --tags "topic"
/Users/george/venv-mlx-whisper/bin/python scripts/collect.py text "<text>" --title "<Title>" --tags "topic"
```

Pass an existing summary with `--summary` to persist it without another inline provider call. Run long collections through the direct execution tool with an adequate timeout; do not use a short-lived delegated session for audio work.

For existing Knowledge cleanup, use the deterministic normalizer and a backup directory:

```bash
/Users/george/venv-mlx-whisper/bin/python scripts/normalize_knowledge_markdown.py \
  --vault /Users/george/Documents/Georges/Knowledge \
  --backup-dir <backup-dir>
```

## Support Files

- `scripts/collect.py`: the single supported collector and Markdown writer.
- `scripts/normalize_knowledge_markdown.py`: backup-first Knowledge migration helper.
- `scripts/add_summary.py`: legacy one-off summary materialization helper; use only for existing notes that need repair.
- `references/youtube-routing-contract.md`: source/destination routing and caption provenance.
- `references/whisper-completion-and-manual-materialization.md`: MLX completion and manual materialization checks for unusual long jobs.
- `references/yt-dlp-direct-fallback.md`: captionless long-video recovery using the same MLX binary and canonical writer.

## Safety

- Never print, commit, or overwrite `.env` secrets.
- Never write to the Knowledge vault during a preview-only route.
- Verify the selected source and destination before writing.
- If a collection fails before transcription completes, do not create a raw-only canonical note.
