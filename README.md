# KB Collector

Knowledge Base Collector - Save YouTube videos, URLs, and text to Obsidian with automatic transcription.

## Features

- **YouTube Collection** - Download audio, transcribe with Whisper, save with TLDR
- **URL Collection** - Fetch and summarize web pages
- **Plain Text** - Direct save with tags
- **Digest** - Weekly/Monthly/Yearly review emails

## Installation

```bash
# Install dependencies
pip install yt-dlp faster-whisper

# Or use the collect.sh script directly
```

## Usage

```bash
# Collect YouTube video
./scripts/collect.sh "https://youtu.be/xxxxx" "stock,investing"

# Collect URL
./scripts/collect.sh "https://example.com/article" "python,api"

# Weekly digest
./scripts/digest.sh weekly
```

## Configuration

Edit scripts to set your Obsidian vault path:

```bash
OBSIDIAN_VAULT="~/Documents/YourVault"
```

## Requirements

- yt-dlp
- faster-whisper
- Python 3.9+

## License

MIT
