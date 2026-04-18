---
name: kb-collector
description: Knowledge Base Collector - save YouTube, URLs, text to Obsidian with AI summarization. Auto-transcribes videos, fetches pages, supports weekly/monthly digest emails and nightly research.
trigger: "^collect\\s+(.+)$"
---

# KB Collector

Save YouTube videos, URLs, and text to Obsidian with automatic transcription and AI summarization.

## Usage

When the user asks to "collect" something (URL, video, or text):
1. **Long Tasks (YouTube/Large Pages)**: Use `sessions_spawn` to run the collection in the background so the main chat stays responsive.
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
- **Multilingual Processing**: Transcribes YouTube/Audio in any language and summarizes in the user's requested language.
- **Agent Integration**: Allows AI agents to pass pre-processed summaries directly via `--summary` flag.
- **AI Auto-Summarization**: After transcription, automatically calls MiniMax to generate a TLDR summary (if `AI_PROVIDER=minimax` in `.env`).
- **Nightly Insights**: Automated research scripts for tech and market trends.

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

### AI Provider Configuration
| Provider | API Format | Notes |
|----------|------------|-------|
| `minimax` | Anthropic Messages | Uses `MINIMAX_API_KEY` + `MINIMAX_BASE_URL` from environment |
| `openai` | OpenAI Chat | Uses `OPENAI_API_KEY` |
| `anthropic` | Anthropic Messages | Uses `ANTHROPIC_API_KEY` |
| `gemini` | Google Generative | Uses `GEMINI_API_KEY` |
| `openrouter` | OpenAI Chat | Uses `OPENROUTER_API_KEY` |
| `none` | (no AI) | Manual `--summary` required |

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

## Efficiency Tip for Agents
- **Preferred**: Pass `--summary "..."` with your own AI-generated summary to minimize cost and latency.
- **Alternative**: Set `AI_PROVIDER=minimax` in `.env` — KB Collector will automatically call MiniMax after transcription to generate TLDR.

## Output Format

### Filename
`{VAULT_PATH}/yyyy-mm-dd-title.md`

### Content Structure
- **Frontmatter**: date, tags, source, author
- **TLDR Section**: > **TLDR** (AI-generated summary)
- **Main Content**: Full transcript / article text
