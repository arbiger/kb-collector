#!/usr/bin/env python3
"""
KB Collector - Save YouTube, URLs, Text to Obsidian with AI Summarization
Refactored version with argparse and .env support.
Refined for Agent-friendly use (Optional AI, Metadata emphasis).
"""

import os
import sys
import subprocess
import argparse
import logging
import json
import math
import signal
from datetime import datetime
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
load_dotenv()

VAULT_PATH = os.path.expanduser(os.getenv("VAULT_PATH", "~/Documents/Knowledge"))
DEFAULT_AUTHOR = os.getenv("NOTE_AUTHOR", "User")
AI_PROVIDER = os.getenv("AI_PROVIDER", "none").lower()

def get_video_info(url):
    """Get YouTube video title and uploader using yt-dlp"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--get-title', '--get-filename', '-o', '%(uploader)s', url],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n')
        title = lines[0] if len(lines) > 0 else ""
        uploader = lines[1] if len(lines) > 1 else "Unknown"
        
        # Clean filename: remove illegal characters and limit length
        clean_title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()[:100]
        return clean_title or f"Video-{datetime.now().strftime('%H%M%S')}", uploader
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return f"Video-{datetime.now().strftime('%H%M%S')}", "Unknown"

def download_youtube_audio(url):
    """Download YouTube audio as m4a"""
    output_base = "/tmp/kb_collector_audio"
    try:
        logger.info(f"Downloading audio from {url}...")
        subprocess.run(
            ['yt-dlp', '-f', 'bestaudio[ext=m4a]', '--extract-audio', 
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
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', audio_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0

def get_whisper_model():
    """Load Whisper model once per session (GPU-accelerated on Mac M4 Pro)"""
    from faster_whisper import WhisperModel
    # Use "tiny" model for speed — works on CPU (MPS/CoreML not supported by faster-whisper on Mac)
    try:
        model = WhisperModel("tiny", device="mps", compute_type="float16")
        logger.info("Whisper: using tiny+mps (Metal GPU)")
    except Exception as e:
        logger.warning(f"mps failed ({e}), falling back to cpu")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("Whisper: using tiny+cpu")
    return model

# Global model instance (loaded once per session)
_whisper_model = None

def get_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = get_whisper_model()
    return _whisper_model

def transcribe_chunk_whisper(wav_path):
    """Transcribe a single audio file using the shared Whisper model"""
    model = get_model()
    segments, info = model.transcribe(wav_path, language="zh", beam_size=5)
    return " ".join([seg.text for seg in segments])

def transcribe_audio(audio_path, chunk_duration=600, timeout=900):
    """
    Transcribe audio using faster-whisper (local, GPU-accelerated).
    For audio longer than 10 minutes, splits into chunks to avoid memory issues.
    Overall transcription is protected by a timeout (default 15 min).
    """
    if not audio_path or not os.path.exists(audio_path):
        return None

    def _do_transcribe():
        logger.info("Starting transcription via faster-whisper (tiny)...")

        # Convert m4a to wav
        wav_path = audio_path.replace('.m4a', '_whisper.wav')
        try:
            subprocess.run(
                ['ffmpeg', '-y', '-i', audio_path, '-ar', '16000', '-ac', '1', wav_path],
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
                        ['ffmpeg', '-y', '-ss', str(start), '-t', str(chunk_duration),
                         '-i', wav_path, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', chunk_path],
                        capture_output=True, check=True, timeout=30
                    )
                except Exception as e:
                    logger.error(f"Chunk creation failed: {e}")
                    continue

                chunk_text = transcribe_chunk_whisper(chunk_path)
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
        return transcribe_chunk_whisper(wav_path)

    # Wrap entire transcription with overall timeout
    # For 12-min video: tiny+cpu takes ~12s, so 15min timeout is very safe
    success, result = with_timeout(timeout, _do_transcribe)
    if not success:
        logger.error(f"Transcription timed out after {timeout}s")
        return None
    return result

def summarize_text(text, title=""):
    """Summarize text using configured AI provider"""
    if not text:
        return ""

    if AI_PROVIDER == "none" or not AI_PROVIDER:
        return ""

    api_key = os.getenv(f"{AI_PROVIDER.upper()}_API_KEY")
    base_url = os.getenv(f"{AI_PROVIDER.upper()}_BASE_URL", "")
    if not api_key:
        logger.debug(f"No API key for {AI_PROVIDER}, skipping internal summary.")
        return ""

    try:
        if AI_PROVIDER == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url or None)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional research assistant. Summarize the following content into a concise TLDR (2-3 sentences) in the same language as the content."},
                    {"role": "user", "content": f"Title: {title}\n\nContent: {text[:8000]}"}
                ]
            )
            return response.choices[0].message.content.strip()
            
        elif AI_PROVIDER == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[
                    {"role": "user", "content": f"Summarize this in 2-3 sentences:\n\n{text[:8000]}"}
                ]
            )
            return response.content[0].text.strip()

        elif AI_PROVIDER == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"Summarize this in 2-3 sentences:\n\n{text[:8000]}")
            return response.text.strip()

        elif AI_PROVIDER == "minimax":
            import requests
            # MiniMax uses Anthropic API format at https://api.minimax.io/anthropic
            minimax_base = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
            payload = {
                "model": "MiniMax-M2.5",
                "messages": [
                    {"role": "user", "content": f"標題：{title}\n\n請用 2-3 句話總結以下內容，重點說明核心觀點：\n\n{text[:8000]}"}
                ],
                "max_tokens": 300
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(f"{minimax_base}/v1/messages", json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            # Anthropic/MiniMax format: content is a list of blocks (text + thinking)
            content = result.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        return block.get("text", "").strip()
            return ""

        elif AI_PROVIDER == "openrouter":
            import requests
            payload = {
                "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
                "messages": [
                    {"role": "system", "content": "You are a professional research assistant. Summarize in 2-3 sentences."},
                    {"role": "user", "content": f"Title: {title}\n\nContent: {text[:8000]}"}
                ],
                "max_tokens": 300
            }
            headers = {"Authorization": f"Bearer {api_key}", "HTTP-Referer": "https://kb-collector"}
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

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

def save_to_obsidian(content, title, url, tags, tldr=None, source_author="Unknown"):
    """Save formatted markdown to Obsidian vault"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    safe_title = title.replace('/', '-')
    filename = f"{date_str}-{safe_title}.md"
    filepath = os.path.join(VAULT_PATH, filename)
    
    os.makedirs(VAULT_PATH, exist_ok=True)
    
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    formatted_tags = ", ".join(tag_list)
    
    frontmatter = f"""---
created: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}
source: {url or 'N/A'}
author: {source_author}
tags: [{formatted_tags}]
---

# {title}

"""
    if tldr:
        frontmatter += f"> **TLDR:** {tldr}\n\n"
    
    frontmatter += "---\n\n"

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            f.write(content)
            f.write(f"\n\n---\n*Collected by: {DEFAULT_AUTHOR} on {datetime.now().strftime('%Y-%m-%d')}*\n")
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
        title, uploader = get_video_info(args.url)
        audio_path = download_youtube_audio(args.url)
        transcript = transcribe_audio(audio_path)
        
        if transcript:
            summary = args.summary or summarize_text(transcript, title)
            tags = "youtube," + args.tags
            save_path = save_to_obsidian(transcript, title, args.url, tags, tldr=summary, source_author=uploader)
            if save_path:
                logger.info(f"✅ Successfully saved YouTube note: {save_path}")
        else:
            logger.error("❌ Transcription failed. No note saved.")
        
        # Cleanup temp files
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        wav_path = audio_path.replace('.m4a', '_qwen.wav') if audio_path else None
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)

    elif args.command == "url":
        logger.info(f"Fetching URL: {args.url}")
        content, title, author = fetch_url(args.url)
        summary = args.summary or summarize_text(content, title)
        tags = "web," + args.tags
        save_path = save_to_obsidian(content, title, args.url, tags, tldr=summary, source_author=author)
        if save_path:
            logger.info(f"✅ Successfully saved URL note: {save_path}")

    elif args.command == "text":
        title = args.title or f"Note-{datetime.now().strftime('%H%M%S')}"
        summary = args.summary or summarize_text(args.content, title)
        save_path = save_to_obsidian(args.content, title, None, args.tags, tldr=summary, source_author=args.author or "N/A")
        if save_path:
            logger.info(f"✅ Successfully saved text note: {save_path}")

if __name__ == "__main__":
    main()
