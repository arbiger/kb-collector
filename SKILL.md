---
name: kb-collector
description: Knowledge Base Collector. Save YouTube, URLs, and text to Obsidian with AI summarization. Supports multi-language transcription and summarization.
---

# KB Collector

Save and synthesize information from various sources into your Obsidian vault.

## Capabilities
- **Multilingual Processing**: Transcribes YouTube/Audio in any language and summarizes in the user's requested language.
- **Agent Integration**: Allows AI agents to pass pre-processed summaries directly via `--summary` flag.
- **Nightly Insights**: Automated research scripts for tech and market trends.

## Setup & Config
1. Run `./setup.sh` to install `ffmpeg` and Python dependencies.
2. Configure `.env`:
   ```env
   VAULT_PATH=~/Documents/Knowledge
   AI_PROVIDER=none # Set to 'openai' if you want internal AI logs
   ```

## Usage
- **YouTube**: `python3 scripts/collect.py youtube "[URL]"`
- **Web**: `python3 scripts/collect.py url "[URL]"`
- **Direct Note**: `python3 scripts/collect.py text "[Content]" --title "[Title]"`

## Efficiency Tip for Agents
If you are an AI agent, **ALWAYS** generate the summary yourself and pass it using `--summary` to minimize cost and latency.

## Output Format
Notes are saved to: `{VAULT_PATH}/yyyy-mm-dd-title.md` with full frontmatter, a > **TLDR** section, and the main content.
