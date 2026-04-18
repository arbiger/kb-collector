# KB Collector

**Collect and archive YouTube videos, web pages, and text notes to Obsidian — with automatic transcription and AI summarization.**

KB Collector is an [OpenClaw](https://openclaw.ai) skill that runs on your Mac (or any machine with Python + ffmpeg). It fetches content from the web, transcribes audio/video, and saves structured Markdown notes to your Obsidian vault.

---

## ✨ Features

- **YouTube Transcription** — Extract subtitles/transcripts from any YouTube video using `faster-whisper` (local, no API needed)
- **Web Page Archiving** — Save full article text with metadata from any URL
- **Multi-Language ASR** — Transcribes audio in any language; summarize in your target language
- **AI Summarization** — Automatically generates a TLDR summary after transcription (supports MiniMax, OpenAI, Anthropic, Gemini, OpenRouter)
- **Agent-Ready** — AI agents can pass pre-computed summaries via `--summary` flag to save cost and latency
- **Digest Emails** — Optional weekly/monthly email digests of collected content
- **Nightly Research** — Cron-ready scripts for automated tech & market trend monitoring
- **Obsidian-Native** — Outputs standard Markdown with YAML frontmatter, ready for graph view / backlinks

---

## 🔧 Installation

### Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (for audio extraction)
- [Whisper](https://github.com/SYSTRAN/faster-whisper) (local transcription, CPU-based)

### Setup

```bash
# 1. Navigate to the kb-collector directory
cd kb-collector

# 2. Run the setup script (installs ffmpeg + Python deps)
./setup.sh

# 3. Configure your environment
cp .env.example .env
# Edit .env with your preferred settings (see Configuration below)
```

### Setup Script Details

`setup.sh` installs:
- **ffmpeg** via Homebrew (macOS) or apt (Linux)
- Python packages: `yt-dlp`, `faster-whisper`, `beautifulsoup4`, `lxml`, `html2text`, `requests`, `python-dotenv`

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

```env
# === Obsidian Vault ===
VAULT_PATH=~/Documents/Georges/Knowledge
NOTE_AUTHOR=George

# === AI Summarization Provider ===
# Options: minimax | openai | anthropic | gemini | openrouter | none
# Set to "none" if you want to provide summaries manually via --summary
AI_PROVIDER=minimax
```

### AI Provider Details

| Provider | API Format | Environment Variables Required |
|----------|-----------|-------------------------------|
| `minimax` | Anthropic Messages | `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` |
| `openai` | OpenAI Chat Completions | `OPENAI_API_KEY` |
| `anthropic` | Anthropic Messages | `ANTHROPIC_API_KEY` |
| `gemini` | Google Generative AI | `GEMINI_API_KEY` |
| `openrouter` | OpenAI-compatible | `OPENROUTER_API_KEY` |
| `none` | No auto-summary | Provide `--summary` manually |

---

## 📖 Usage

### Command Line

```bash
# Collect a YouTube video (with auto transcription + AI summary)
python3 scripts/collect.py youtube "https://www.youtube.com/watch?v=..." --tags "AI,LLM"

# Collect a web page
python3 scripts/collect.py url "https://example.com/article" --tags "tech,news"

# Save a text note directly
python3 scripts/collect.py text "Your content here" --title "Meeting Notes" --tags "work"

# Pass a pre-computed summary (saves API cost)
python3 scripts/collect.py youtube "URL" --summary "This video covers..." --tags "AI"
```

### Output Format

Notes are saved to `{VAULT_PATH}/yyyy-mm-dd-slugified-title.md`:

```markdown
---
date: 2026-04-18
title: "Video Title"
tags:
  - AI
  - LLM
source: "https://youtube.com/..."
author: "Channel Name"
---

> **TLDR**
> AI-generated summary of the content goes here...

## Transcript

00:00 - Introduction
00:30 - Main topic discussion
...

## Content

Full article or transcript text...
```

### YouTube Auto-Chunking

For videos > 10 minutes, the script automatically splits audio into **10-minute chunks** to avoid memory issues:
- Each chunk is transcribed separately
- Results are concatenated in order
- Whisper `tiny` model runs at ~60x realtime on CPU (a 29-minute video transcribes in ~30 seconds)

> ⚠️ **Mac Users**: `faster-whisper` uses CPU by default on macOS (MPS/GPU not supported). The `tiny` model is recommended for best performance.

---

## 🤖 For AI Agents (OpenClaw)

When invoked as an OpenClaw skill, use the `collect` trigger:

```
collect https://youtube.com/watch?v=... AI,LLM
collect https://example.com tech,news
collect Your text content here work,notes
```

### Execution Strategy

| Task Type | Recommended Method |
|-----------|-------------------|
| Short text / quick URLs | Run `collect.py` directly |
| YouTube videos (>2 min transcription) | Use `exec` with `background=true` |
| Long-running tasks | Spawn isolated session with `sessions_spawn` |

> ⚠️ **Important**: Do NOT use `sessions_spawn` for YouTube video transcription — sub-agents have a ~2-minute timeout that will kill the process before transcription finishes. Use `exec` tool directly instead.

**Example (OpenClaw exec):**
```
exec(
    command="python3 /path/to/kb-collector/scripts/collect.py youtube '[URL]' --tags 'AI'",
    background=true,
    timeout=900
)
```

### Efficiency Tip

AI agents should pass their own generated summaries via `--summary "..."` whenever possible. This avoids an extra API call to the summarization provider and reduces latency/cost.

---

## 📁 Project Structure

```
kb-collector/
├── SKILL.md          # OpenClaw skill definition
├── README.md         # This file
├── setup.sh          # Installation script
├── requirements.txt   # Python dependencies
├── .env.example      # Configuration template
├── .gitignore
└── scripts/
    └── collect.py    # Main collection script
```

---

## 🔒 Security Notes

- **API Keys**: Never commit your `.env` file. It contains API credentials and is gitignored by default.
- **Public Content Only**: KB Collector is designed for personal archival of publicly available web content. Respect copyright and terms of service.
- **API Key Storage**: Keys are read from environment variables at runtime, not hardcoded anywhere.

---

## 🚀 Advanced: Cron Automation

KB Collector supports automated collection via cron jobs. Examples:

```bash
# Nightly research (tech trends)
0 2 * * * python3 /path/to/kb-collector/scripts/collect.py url "https://news.ycombinator.com/" --tags "tech,startup"

# Weekly digest (every Monday 9am)
0 9 * * 1 python3 /path/to/kb-collector/scripts/digest.py weekly
```

See `scripts/` for available automation scripts.

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional AI provider support
- Better chunking strategies for long videos
- Alternative output formats (Notion, Logseq, etc.)
- Browser extension for one-click archiving

Open an issue or PR on GitHub.

---

*KB Collector is part of the [OpenClaw](https://openclaw.ai) skill ecosystem.*
