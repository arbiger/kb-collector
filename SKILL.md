---
name: kb-collector
description: Knowledge Base Collector - save articles, text, and YouTube videos to Obsidian. Automatically transcribes YouTube videos with Whisper, fetches URLs, and supports weekly/monthly digest emails.
---

# KB Collector

Save articles, text, and YouTube videos to Obsidian with automatic transcription and summarization.

## Trigger

- `collect <URL|文字> <tags>` - Save content to Obsidian
- `digest weekly|monthly|yearly` - Send digest email

## Configuration

Set environment variables or edit the script to customize paths:

```bash
# Obsidian Vault path (default: ~/Documents/Georges/Knowledge)
export OBSIDIAN_VAULT="~/Documents/YourVault"

# Your name for notes
export NOTE_AUTHOR="YourName"
```

## Features

### YouTube Collection
- Download audio with yt-dlp
- Transcribe with Faster-Whisper
- Save with TLDR summary

### URL Collection
- Fetch and summarize web pages
- Auto-tag based on content

### Plain Text Collection
- Direct save with tags

### Digest
- Weekly/Monthly/Yearly review
- Auto-email via Gmail

## Dependencies

```bash
# Required
pip install yfinance yt-dlp faster-whisper

# Optional (for Gmail digest)
gog skill install gmail
```

## Usage

```bash
# Collect YouTube video
collect https://youtu.be/xxxxx stock,investing

# Collect URL
collect https://example.com/article python,api

# Collect plain text
collect "My note content" tag1,tag2

# Send weekly digest
digest weekly

# Send monthly digest
digest monthly
```

## Storage

Notes saved to: `{OBSIDIAN_VAULT}/yyyy-mm-dd-title.md`

Format:
```markdown
---
tags: [tag1, tag2]
source: https://...
date: 2026-03-03
---

# Title

TLDR summary...

## Content
...
```

## Credits

Inspired by personal note-taking workflows and Obsidian automation.
