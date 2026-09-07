#!/usr/bin/env python3
"""
KB Collector - Save YouTube, URLs, Text to Obsidian with AI Summarization
Refactored version with argparse and .env support.
Refined for Agent-friendly use (Optional AI, Metadata emphasis).
"""

import os
import subprocess
import argparse
import logging
import math
import signal
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError(" Transcription timed out")

def with_timeout(seconds, func, *args, **kwargs):
    """Run func with a timeout. Returns (success, result)."""
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        result = func(*args, **kwargs)
        return True, result
    except TimeoutError:
        return False, None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
# Load the skill-local .env regardless of the caller's current working directory.
# This matters because Hermes often invokes the script by absolute path from another cwd.
_SKILL_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_SKILL_DIR / ".env")
load_dotenv()  # allow caller cwd/env to override only when explicitly provided

VAULT_PATH = os.path.expanduser(os.getenv("VAULT_PATH", "~/Documents/Knowledge"))
DEFAULT_AUTHOR = os.getenv("NOTE_AUTHOR", "User")
AI_PROVIDER = os.getenv("AI_PROVIDER", "none").lower()
SUPPORTED_SUMMARY_PROVIDERS = {"minimax", "none"}


def validate_summary_provider(provider):
    """Reject summary providers that are not part of the supported runtime."""
    normalized = (provider or "none").strip().lower()
    if normalized not in SUPPORTED_SUMMARY_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_SUMMARY_PROVIDERS))
        raise ValueError(
            f"Unsupported AI_PROVIDER={provider!r}; supported provider(s): {supported}"
        )
    return normalized


def resolve_command(name):
    """Resolve system tools, then tools installed beside the MLX venv."""
    found = shutil.which(name)
    if found:
        return found
    venv_candidate = Path(MLX_WHISPER_BIN).parent / name
    if venv_candidate.is_file():
        return str(venv_candidate)
    return name

def normalize_source_published_at(value):
    """Normalize provider publication dates to YYYY-MM-DD, or return None."""
    value = (value or "").strip()
    if len(value) == 8 and value.isdigit():
        try:
            return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    if len(value) == 10:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def get_video_info(url):
    """Get YouTube video title, uploader, and publication date using yt-dlp."""
    try:
        result = subprocess.run(
            [resolve_command('yt-dlp'), '--print', '%(title)s', '--print', '%(uploader)s', '--print', '%(upload_date)s', url],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n')
        title = lines[0] if len(lines) > 0 else ""
        uploader = lines[1] if len(lines) > 1 else "Unknown"
        published_at = normalize_source_published_at(lines[2] if len(lines) > 2 else None)
        
        # Clean filename: remove illegal characters and limit length
        clean_title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()[:100]
        return clean_title or f"Video-{datetime.now().strftime('%H%M%S')}", uploader, published_at
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return f"Video-{datetime.now().strftime('%H%M%S')}", "Unknown", None

def download_youtube_audio(url):
    """Download YouTube audio as m4a"""
    output_base = "/tmp/kb_collector_audio"
    try:
        logger.info(f"Downloading audio from {url}...")
        subprocess.run(
            [resolve_command('yt-dlp'), '-f', 'bestaudio[ext=m4a]', '--extract-audio',
             '--audio-format', 'm4a', '-o', f'{output_base}.%(ext)s', url],
            capture_output=True, check=True, timeout=900
        )
        return f"{output_base}.m4a"
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e.stderr.decode() if e.stderr else str(e)}")
        return None

def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe"""
    try:
        result = subprocess.run(
            [resolve_command('ffprobe'), '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', audio_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0

SUPPORTED_WHISPER_ENGINES = {"mlx"}
WHISPER_ENGINE = os.environ.get("KB_WHISPER_ENGINE", "mlx").strip().lower()
MLX_WHISPER_BIN = os.environ.get(
    "MLX_WHISPER_BIN", "/Users/george/venv-mlx-whisper/bin/mlx_whisper"
)
MLX_WHISPER_MODEL = os.environ.get(
    "MLX_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo"
)

def validate_whisper_engine(engine):
    """Reject unsupported engines instead of silently selecting a fallback."""
    normalized = (engine or "").strip().lower()
    if normalized not in SUPPORTED_WHISPER_ENGINES:
        supported = ", ".join(sorted(SUPPORTED_WHISPER_ENGINES))
        raise ValueError(
            f"Unsupported KB_WHISPER_ENGINE={engine!r}; supported engine(s): {supported}"
        )
    return normalized


def whisper_wav_path(audio_path):
    """Return the deterministic temporary WAV path for any audio extension."""
    source = os.path.splitext(os.fspath(audio_path))[0]
    return f"{source}_whisper.wav"


def cleanup_transcription_artifacts(audio_path):
    """Remove the WAV and MLX text sidecars created for one audio file."""
    if not audio_path:
        return
    wav_path = whisper_wav_path(audio_path)
    candidates = [wav_path, os.path.splitext(wav_path)[0] + ".txt"]
    for path in candidates:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as exc:
            logger.warning("Could not remove temporary transcription file %s: %s", path, exc)

def transcribe_chunk_mlx(wav_path):
    """Transcribe a single audio file via mlx-whisper subprocess (primary engine on Apple Silicon).

    Verified 2026-08-29 on M4 Pro: 26:41 zh video = 54 s (after model cached).
    --condition-on-previous-text False is mandatory to suppress tail hallucination
    (e.g. `我说` repeating 60+ times) that large-v3-turbo emits by default.
    """
    if not os.path.isfile(MLX_WHISPER_BIN):
        logger.error(
            f"mlx-whisper not found at {MLX_WHISPER_BIN}. "
            f"Run setup.sh or set MLX_WHISPER_BIN to an installed mlx_whisper executable."
        )
        return None
    try:
        output_dir = os.path.dirname(os.path.abspath(wav_path))
        basename = os.path.splitext(os.path.basename(wav_path))[0]
        txt_path = os.path.join(output_dir, basename + ".txt")
        # Never accept a stale sidecar if the subprocess exits without writing fresh output.
        if os.path.exists(txt_path):
            os.remove(txt_path)
        result = subprocess.run(
            [
                MLX_WHISPER_BIN,
                wav_path,
                "--model", MLX_WHISPER_MODEL,
                "--language", "zh",
                "--condition-on-previous-text", "False",  # suppress tail hallucination
                "--output-format", "txt",
                "--output-dir", output_dir,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10 min ceiling per chunk (mlx-whisper ~30x realtime)
        )
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        # Keep stdout as a compatibility fallback for alternate mlx-whisper versions.
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"mlx-whisper timed out on {wav_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"mlx-whisper failed: {e.stderr or e}")
        return None
    except Exception as e:
        logger.error(f"mlx-whisper error: {e}")
        return None

def transcribe_audio(audio_path, chunk_duration=600, timeout=900):
    """
    Transcribe audio through the supported local MLX Whisper executable.

    For audio longer than 10 minutes, splits into chunks to avoid memory issues.
    Overall transcription is protected by a timeout (default 15 min).
    """
    if not audio_path or not os.path.exists(audio_path):
        return None

    engine = validate_whisper_engine(WHISPER_ENGINE)
    chunk_fn = transcribe_chunk_mlx
    logger.info("Starting transcription via engine=%s (model=%s)...", engine, MLX_WHISPER_MODEL)

    def _do_transcribe():
        # Convert m4a to wav
        wav_path = whisper_wav_path(audio_path)
        try:
            subprocess.run(
                [resolve_command('ffmpeg'), '-y', '-i', audio_path, '-ar', '16000', '-ac', '1', wav_path],
                capture_output=True, check=True, timeout=60
            )
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            return None

        # Check duration and chunk if needed
        duration = get_audio_duration(wav_path)
        logger.info(f"Audio duration: {duration:.1f}s ({duration/60:.1f} min)")

        # For audio > 10 minutes, split into chunks
        if duration > 600:
            logger.info(f"Audio > 10 min ({duration/60:.1f} min), splitting into {chunk_duration}s chunks...")
            chunk_dir = "/tmp/kb_audio_chunks"
            os.makedirs(chunk_dir, exist_ok=True)

            # Clean up old chunks
            for f in os.listdir(chunk_dir):
                os.remove(os.path.join(chunk_dir, f))

            all_transcripts = []
            num_chunks = int(math.ceil(duration / chunk_duration))

            for i in range(num_chunks):
                start = i * chunk_duration
                chunk_path = f"{chunk_dir}/chunk_{i}.wav"
                logger.info(f"Transcribing chunk {i+1}/{num_chunks} ({start}s-{start+chunk_duration}s)...")

                try:
                    subprocess.run(
                        [resolve_command('ffmpeg'), '-y', '-ss', str(start), '-t', str(chunk_duration),
                         '-i', wav_path, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', chunk_path],
                        capture_output=True, check=True, timeout=30
                    )
                except Exception as e:
                    logger.error(f"Chunk creation failed: {e}")
                    continue

                chunk_text = chunk_fn(chunk_path)
                if chunk_text:
                    all_transcripts.append(chunk_text)
                    logger.info(f"Chunk {i+1} done: {len(chunk_text)} chars")
                else:
                    logger.warning(f"Chunk {i+1} transcription failed")

            # Clean up chunk dir
            try:
                for f in os.listdir(chunk_dir):
                    os.remove(os.path.join(chunk_dir, f))
                os.rmdir(chunk_dir)
            except Exception:
                pass

            if all_transcripts:
                transcript = " ".join(all_transcripts)
                logger.info(f"Transcription complete ({len(all_transcripts)} chunks): {len(transcript)} chars")
                return transcript

        # For short audio (<= 10 min), transcribe directly
        return chunk_fn(wav_path)

    # Wrap entire transcription with overall timeout
    # For 12-min video: tiny+cpu takes ~12s, so 15min timeout is very safe
    success, result = with_timeout(timeout, _do_transcribe)
    if not success:
        logger.error(f"Transcription timed out after {timeout}s")
        return None
    return result

def summarize_text(text, title=""):
    """Summarize text using the configured MiniMax provider, or skip when disabled."""
    if not text:
        return ""

    provider = validate_summary_provider(AI_PROVIDER)
    if provider == "none":
        return ""

    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        logger.debug("No API key for minimax, skipping internal summary.")
        return ""

    try:
        SUMMARY_PROMPT = f"""你是專業的研究分析助理。請根據以下內容，生成一份**詳細的結構化摘要**。

要求：
1. 使用與內容相同的語言（繁體中文）
2. 至少包含：\n   - **核心論點**：作者/講者最主要想表達什麼\n   - **關鍵證據與細節**：支撐論點的重要細節、數據或引用\n   - **重要分析**：值得記住的洞見或有趣的觀點\n   - **總結一句話**：用一句話濃縮全文最重要的事\n3. 結構清晰，用 markdown 標題分層\n4. 不要只是簡短概括，要有實質內容\n\n標題：{title}\n\n內容：{text[:8000]}"""

        import requests
        # MiniMax uses Anthropic API format at https://api.minimax.io/anthropic.
        minimax_base = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
        payload = {
            "model": "MiniMax-M3",
            "messages": [
                {"role": "user", "content": SUMMARY_PROMPT}
            ],
            "max_tokens": 2000
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.post(f"{minimax_base}/v1/messages", json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        # Anthropic/MiniMax format: content is a list of blocks (text + thinking).
        content = result.get("content", [])
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    return block.get("text", "").strip()
        return ""

    except Exception as e:
        logger.error(f"AI summarization failed: {e}")
    
    return ""

def fetch_url(url):
    """Fetch and clean URL content, extracting title and author"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Title extraction
        title = soup.title.string if soup.title else "web-note"
        clean_title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()[:60]

        # Author extraction (best effort)
        author = "Unknown"
        author_meta = (
            soup.find("meta", attrs={"name": "author"}) or 
            soup.find("meta", attrs={"property": "article:author"}) or
            soup.find("meta", attrs={"name": "twitter:creator"})
        )
        if author_meta:
            author = author_meta.get("content", "Unknown")
        else:
            # Try to find common patterns
            author_tag = soup.find(class_=["author", "byline", "creator"])
            if author_tag:
                author = author_tag.get_text().strip()

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        # Extract text
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        return content, clean_title, author
    except Exception as e:
        logger.error(f"Error fetching URL: {e}")
        return str(e), "error-fetching", "N/A"

def infer_source_type(source):
    """Return a stable source_type value for frontmatter."""
    if not source:
        return "text"
    lowered = source.lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "youtube"
    if "facebook.com" in lowered or "fb.watch" in lowered:
        return "facebook"
    if "instagram.com" in lowered:
        return "instagram"
    if "x.com" in lowered or "twitter.com" in lowered:
        return "x"
    if lowered.startswith(("http://", "https://")):
        return "url"
    return "text"


def format_tags(tags):
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    return "\n".join(f"  - {tag}" for tag in tag_list)


def default_summary_model():
    return "MiniMax-M3" if validate_summary_provider(AI_PROVIDER) == "minimax" else "provided"


def save_to_obsidian(
    content,
    title,
    url,
    tags,
    tldr=None,
    source_author="Unknown",
    summary_model=None,
    source_published_at=None,
):
    """Save formatted markdown to Obsidian vault"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    created_str = datetime.now().astimezone().isoformat(timespec="seconds")
    safe_title = title.replace('/', '-')
    filename = f"{date_str}-{safe_title}.md"
    filepath = os.path.join(VAULT_PATH, filename)
    
    os.makedirs(VAULT_PATH, exist_ok=True)

    source = url or "pasted text"
    source_type = infer_source_type(url)
    transcript_source_line = "transcript_source: whisper\n" if source_type == "youtube" else ""
    source_published_at = normalize_source_published_at(source_published_at)
    source_published_at_value = source_published_at or "null"
    source_published_at_display = source_published_at or "Unknown"
    formatted_tags = format_tags(tags)
    content_heading = "Raw Transcript" if source_type == "youtube" else "Content"

    frontmatter = f"""---
date: {date_str}
created: {created_str}
title: {title}
source: {source}
source_type: {source_type}
source_published_at: {source_published_at_value}
{transcript_source_line}author: {source_author}
collector: kb-collector
tags:
{formatted_tags}
---

# {title}

## Source Snapshot

| Field | Value |
|---|---|
| Source | {source} |
| Type | {source_type} |
| Author | {source_author} |
| Published | {source_published_at_display} |
| Collected | {created_str} |

"""
    if tldr:
        summary_label = summary_model or "provided"
        summary_body = tldr.strip()
        summary_comment = f"<!-- AI Summary ({summary_label}) -->"
    else:
        summary_body = ""
        summary_comment = "<!-- Add AI summary here. -->"

    frontmatter += f"""## AI Summary
{summary_comment}

{summary_body}

## Analysis & Red Team
<!-- Add analysis and red-team notes here. -->

## George Annotation
<!-- Add George's annotation here. -->

"""

    frontmatter += f"## {content_heading}\n\n"

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            f.write(content)
            f.write(f"\n\n## Collection Metadata\n\n")
            f.write(f"*Collected by: {DEFAULT_AUTHOR} on {date_str}*\n")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="KB Collector - Save knowledge to Obsidian")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Common args
    def add_common_args(p):
        p.add_argument("--tags", "-t", default="research", help="Tags for the note")
        p.add_argument("--summary", "-s", help="Manually provide a summary (bypasses AI)")

    # YouTube Parser
    youtube_parser = subparsers.add_parser("youtube", help="Collect from YouTube")
    youtube_parser.add_argument("url", help="YouTube URL")
    add_common_args(youtube_parser)

    # URL Parser
    url_parser = subparsers.add_parser("url", help="Collect from URL")
    url_parser.add_argument("url", help="Web URL")
    add_common_args(url_parser)

    # Text Parser
    text_parser = subparsers.add_parser("text", help="Save plain text")
    text_parser.add_argument("content", help="Text content")
    text_parser.add_argument("--title", help="Optional title")
    text_parser.add_argument("--author", help="Source author")
    add_common_args(text_parser)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "youtube":
        # Validate before yt-dlp metadata/audio work or any large temporary file is created.
        validate_whisper_engine(WHISPER_ENGINE)
        title, uploader, source_published_at = get_video_info(args.url)
        audio_path = download_youtube_audio(args.url)
        try:
            transcript = transcribe_audio(audio_path)

            if transcript:
                summary = args.summary or summarize_text(transcript, title)
                summary_model = "provided" if args.summary else default_summary_model()
                tags = "youtube," + args.tags
                save_path = save_to_obsidian(
                    transcript,
                    title,
                    args.url,
                    tags,
                    tldr=summary,
                    source_author=uploader,
                    summary_model=summary_model,
                    source_published_at=source_published_at,
                )
                if save_path:
                    logger.info(f"✅ Successfully saved YouTube note: {save_path}")
            else:
                logger.error("❌ Transcription failed. No note saved.")
        finally:
            cleanup_transcription_artifacts(audio_path)
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)

    elif args.command == "url":
        logger.info(f"Fetching URL: {args.url}")
        content, title, author = fetch_url(args.url)
        summary = args.summary or summarize_text(content, title)
        summary_model = "provided" if args.summary else default_summary_model()
        tags = "web," + args.tags
        save_path = save_to_obsidian(content, title, args.url, tags, tldr=summary, source_author=author, summary_model=summary_model)
        if save_path:
            logger.info(f"✅ Successfully saved URL note: {save_path}")

    elif args.command == "text":
        title = args.title or f"Note-{datetime.now().strftime('%H%M%S')}"
        summary = args.summary or summarize_text(args.content, title)
        summary_model = "provided" if args.summary else default_summary_model()
        save_path = save_to_obsidian(args.content, title, None, args.tags, tldr=summary, source_author=args.author or "N/A", summary_model=summary_model)
        if save_path:
            logger.info(f"✅ Successfully saved text note: {save_path}")

if __name__ == "__main__":
    main()
