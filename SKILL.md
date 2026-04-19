---
name: kb-collector
description: Knowledge Base Collector - save YouTube, URLs, text to Obsidian with AI summarization. Auto-transcribes videos, fetches pages, supports weekly/monthly digest emails and nightly research.
trigger: "^collect\\s+(.+)$"
---

# KB Collector

Save YouTube videos, URLs, and text to Obsidian as raw markdown. The script handles collection only — **AI summarization is a separate step done by the primary model**.

## Two-Step Workflow

```
Step 1 (Python/kb-collector): Download → Transcribe → Save raw .md
Step 2 (Primary Model):         Read .md   → Write detailed summary → Save back to .md
```

**Why two steps?**
- The primary model (MiniMax-M2.7) writes better, more contextual summaries than a hardcoded internal call
- Summarization style, depth, and focus are controlled by the model, not the script
- No hardcoded AI provider dependencies in the collection layer

## Usage

When the user asks to "collect" something (URL, video, or text):
1. **Long Tasks (YouTube/Large Pages)**: Use `exec` tool to run the collection directly (NOT `sessions_spawn` — subagent has ~2-min timeout that kills long transcription).
2. **Short Tasks (Text/Small URLs)**: You can run `python3 scripts/collect.py` directly if it's quick.

### Example Spawning
> "I will spawn sub-agent for this mission, I will notify you when done 📥"

```bash
sessions_spawn(
    agentId="collector",
    prompt="Collect: [input] with tags [tags]. Save to Obsidian."
)
```

## Capabilities
- **Collection only**: kb-collector handles download, transcription, and raw markdown output
- **Multilingual Processing**: Transcribes YouTube/Audio in any language
- **Agent Integration**: Allows AI agents to pass pre-processed summaries via `--summary` flag
- **Nightly Insights**: Automated research scripts for tech and market trends

## Long Audio Handling (Auto-Chunking)

For YouTube audio > 10 minutes, the script automatically splits into **600-second (10-min) chunks** to avoid memory issues:
- Audio > 10 min → split into ~10-min chunks
- Each chunk transcribed separately → results concatenated
- **ASR**: faster-whisper `tiny` model (local, no API needed)
  - ⚠️ MPS/GPU not supported on Mac — always falls back to CPU
  - tiny ~60x realtime on CPU (29-min video in ~30 seconds)
  - ⚠️ Do NOT use `sessions_spawn` for YouTube video collection — the subagent has a ~2-min timeout that will kill the process before transcription finishes. Use `exec` directly instead.

## Setup & Config
1. Run `./setup.sh` to install `ffmpeg` and Python dependencies.
2. Configure `.env`:
   ```env
   VAULT_PATH=~/Documents/Georges/Knowledge
   NOTE_AUTHOR=George
   AI_PROVIDER=minimax   # Options: minimax | openai | anthropic | gemini | openrouter | none
   ```

### Legacy: Internal AI Summarization
The script has a legacy `AI_PROVIDER` option for inline summarization (kept for backward compatibility). For better results, use the two-step workflow above instead:

| Provider | API Format | Notes |
|----------|------------|-------|
| `minimax` | Anthropic Messages | Legacy inline summary |
| `openai` | OpenAI Chat | Legacy inline summary |
| `anthropic` | Anthropic Messages | Legacy inline summary |
| `gemini` | Google Generative | Legacy inline summary |
| `openrouter` | OpenAI Chat | Legacy inline summary |
| `none` | (no AI) | **Recommended** — use two-step workflow |

## Usage

### ⚠️ Long YouTube Videos (>2 min transcription) — Use `exec`

For video transcription, run directly via `exec` tool (not `sessions_spawn`):

```bash
python3 /Users/george/.openclaw/workspace/skills/kb-collector/scripts/collect.py \
  youtube "[YouTube URL]" \
  --tags "tag1,tag2"
```

`sessions_spawn` has a ~2-min subagent timeout that will kill the process before long video transcription completes.

### Short Tasks / One-liners
- **YouTube**: `python3 scripts/collect.py youtube "[URL]" [--summary "你的摘要"]`
- **Web**: `python3 scripts/collect.py url "[URL]" [--summary "你的摘要"]`
- **Direct Note**: `python3 scripts/collect.py text "[Content]" --title "[Title]" [--summary "你的摘要"]`

## Workflow for Agents

### Step 1: Collect raw content
```bash
python3 /path/to/collect.py youtube "[YouTube URL]" --tags "youtube,research"
```
→ Output: Raw .md file with transcript/content, no summary

### Step 2: Summarize with primary model
Read the saved .md file, then write a detailed structured summary and append/update it in the file.

**Tip**: Pass `--summary "..."` to skip Step 2 if you already have a summary ready.

```bash
python3 /path/to/collect.py youtube "[YouTube URL]" --summary "Your detailed summary here" --tags "youtube"
```

## Output Format

### Filename
`{VAULT_PATH}/yyyy-mm-dd-title.md`

### Content Structure
- **Frontmatter**: date, tags, source, author
- **Title**: H1 title
- **Transcript/Content**: Full raw text (no summary in two-step workflow)
- **Summary**: Added later by primary model, typically at top as TLDR block
