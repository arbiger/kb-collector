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
> "我 spawn 一個子任務去處理 collect 任務，完成後會通知你 📥"

```bash
sessions_spawn(
    agentId="collector",
    prompt="Collect: [input] with tags [tags]. Save to Obsidian."
)
```

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

### Filename
`{VAULT_PATH}/yyyy-mm-dd-title.md`

### Content Structure
- **Frontmatter**: date, tags, source, author
- **TLDR Section**: > **TLDR** (AI-generated summary)
- **Main Content**: Full transcript / article text
