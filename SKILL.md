---
name: kb-collector
description: Knowledge Base Collector - save YouTube, URLs, text to Obsidian with AI summarization. Auto-transcribes videos, fetches pages, supports weekly/monthly digest emails and nightly research.
---

# KB Collector

Save YouTube, URLs, and text to Obsidian with automatic transcription and AI summarization.

## Features

- **YouTube Collection** - Download audio, transcribe with Whisper, AI-summarize (OpenAI/Anthropic/Gemini)
- **URL Collection** - Fetch web pages, clean content, and AI-summarize
- **Plain Text** - Direct save with AI-generated TLDR
- **Nightly Research** - Automated AI/LLM/tech trend tracking via Tavily API
- **Centralized Config** - Manage everything in a simple `.env` file

## Installation

```bash
# Clone the repository
git clone https://github.com/arbiger/kb-collector.git
cd kb-collector

# Run setup script (installs dependencies and creates .env)
./setup.sh
```

## Configuration

Edit the `.env` file in the root directory:

```env
VAULT_PATH=~/Documents/Knowledge
NOTE_AUTHOR=YourName
AI_PROVIDER=none # Set to 'openai' only if you want internal summarization
```

## Usage

### Agent-Friendly Collection (Recommended)
If you are an AI agent, you can fetch content and pass a pre-generated summary:

```bash
python3 scripts/collect.py url "https://example.com" --summary "A great article about X."
```

### Manual Collection
```bash
# Collect YouTube video (will extract uploader and title automatically)
python3 scripts/collect.py youtube "https://youtu.be/xxxxx" --tags "stock,investing"

# Collect URL
python3 scripts/collect.py url "https://example.com/article" --tags "python,api"

# Collect plain text
python3 scripts/collect.py text "My note content" --title "Custom Title" --author "Original Author"
```

### Nightly Research

Automated tech trend tracking - saves results to Obsidian.

```bash
# Save to Obsidian only
./scripts/nightly-research.sh --save

# Save to Obsidian AND send email
./scripts/nightly-research.sh --save --send
```

## Dependencies

- **Python Packages**: `yt-dlp`, `faster-whisper`, `python-dotenv`, `requests`, `beautifulsoup4`, `openai`, `anthropic`, `google-generativeai`
- **System**: `ffmpeg` (for audio extraction)

## Output Format

Notes are saved to: `{VAULT_PATH}/yyyy-mm-dd-title.md` with full frontmatter, a > **TLDR** section, and the main content.
