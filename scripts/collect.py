#!/usr/bin/env python3
"""
KB Collector - Save YouTube, URLs, Text to Obsidian with AI Summarization
Refactored version with argparse and .env support.
"""

import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
load_dotenv()

VAULT_PATH = os.path.expanduser(os.getenv("VAULT_PATH", "~/Documents/Knowledge"))
NOTE_AUTHOR = os.getenv("NOTE_AUTHOR", "User")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()

def get_video_title(url):
    """Get YouTube video title using yt-dlp"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--get-title', url],
            capture_output=True, text=True, timeout=30
        )
        title = result.stdout.strip()
        # Clean filename: remove illegal characters and limit length
        title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()[:100]
        return title or f"Video-{datetime.now().strftime('%H%M%S')}"
    except Exception as e:
        logger.error(f"Error getting video title: {e}")
        return f"Video-{datetime.now().strftime('%H%M%S')}"

def download_youtube_audio(url):
    """Download YouTube audio as m4a"""
    output_base = "/tmp/kb_collector_audio"
    try:
        logger.info(f"Downloading audio from {url}...")
        subprocess.run(
            ['yt-dlp', '-f', 'bestaudio[ext=m4a]', '--extract-audio', 
             '--audio-format', 'm4a', '-o', f'{output_base}.%(ext)s', url],
            capture_output=True, check=True, timeout=300
        )
        return f"{output_base}.m4a"
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e.stderr.decode() if e.stderr else str(e)}")
        return None

def transcribe_audio(audio_path):
    """Transcribe audio with faster-whisper or fallback to whisper CLI"""
    if not audio_path or not os.path.exists(audio_path):
        return None

    logger.info("Starting transcription...")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, language="zh")
        transcript = " ".join([seg.text for seg in segments])
        return transcript
    except Exception as e:
        logger.warning(f"faster-whisper failed, falling back to whisper CLI: {e}")
        try:
            result = subprocess.run(
                ['whisper', audio_path, '--model', 'tiny', '--output_format', 'txt', 
                 '--output_dir', '/tmp', '--language', 'Chinese'],
                capture_output=True, text=True, timeout=600
            )
            txt_path = audio_path.replace('.m4a', '.txt')
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
        except Exception as fallback_e:
            logger.error(f"Whisper CLI also failed: {fallback_e}")
    return None

def summarize_text(text, title=""):
    """Summarize text using configured AI provider"""
    if not text:
        return "No content to summarize."

    api_key = os.getenv(f"{AI_PROVIDER.upper()}_API_KEY")
    
    if not api_key:
        logger.warning(f"No API key found for {AI_PROVIDER}. Using basic snippet.")
        return text[:300] + "..." if len(text) > 300 else text

    try:
        if AI_PROVIDER == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional research assistant. Summarize the following content into a concise TLDR (2-3 sentences)."},
                    {"role": "user", "content": f"Title: {title}\n\nContent: {text[:10000]}"}
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
                    {"role": "user", "content": f"Summarize this in 2-3 sentences:\n\n{text[:10000]}"}
                ]
            )
            return response.content[0].text.strip()

        elif AI_PROVIDER == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"Summarize this in 2-3 sentences:\n\n{text[:10000]}")
            return response.text.strip()

    except Exception as e:
        logger.error(f"AI summarization failed: {e}")
    
    return text[:300] + "..." if len(text) > 300 else text

def fetch_url(url):
    """Fetch and clean URL content"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Try to find the title
        title = soup.title.string if soup.title else "web-note"
        title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()[:60]

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        # Extract text
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        return content, title
    except Exception as e:
        logger.error(f"Error fetching URL: {e}")
        return str(e), "error-fetching"

def save_to_obsidian(content, title, url, tags, tldr=None):
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
tags: [{formatted_tags}]
author: {NOTE_AUTHOR}
---

# {title}

> **TLDR:** {tldr or 'No summary available.'}

---

"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            f.write(content)
            f.write(f"\n\n---\n*Saved: {datetime.now().strftime('%Y-%m-%d')}*\n")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="KB Collector - Save knowledge to Obsidian")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # YouTube Parser
    youtube_parser = subparsers.add_parser("youtube", help="Collect from YouTube")
    youtube_parser.add_argument("url", help="YouTube URL")
    youtube_parser.add_argument("--tags", "-t", default="youtube,research", help="Tags for the note")

    # URL Parser
    url_parser = subparsers.add_parser("url", help="Collect from URL")
    url_parser.add_argument("url", help="Web URL")
    url_parser.add_argument("--tags", "-t", default="web,research", help="Tags for the note")

    # Text Parser
    text_parser = subparsers.add_parser("text", help="Save plain text")
    text_parser.add_argument("content", help="Text content")
    text_parser.add_argument("--title", help="Optional title")
    text_parser.add_argument("--tags", "-t", default="note", help="Tags for the note")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "youtube":
        title = get_video_title(args.url)
        audio_path = download_youtube_audio(args.url)
        transcript = transcribe_audio(audio_path)
        
        if transcript:
            summary = summarize_text(transcript, title)
            save_path = save_to_obsidian(transcript, title, args.url, args.tags, tldr=summary)
            if save_path:
                logger.info(f"✅ Successfully saved YouTube note: {save_path}")
        else:
            logger.error("❌ Transcription failed. No note saved.")
        
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

    elif args.command == "url":
        logger.info(f"Fetching URL: {args.url}")
        content, title = fetch_url(args.url)
        summary = summarize_text(content, title)
        save_path = save_to_obsidian(content, title, args.url, args.tags, tldr=summary)
        if save_path:
            logger.info(f"✅ Successfully saved URL note: {save_path}")

    elif args.command == "text":
        title = args.title or f"Note-{datetime.now().strftime('%H%M%S')}"
        summary = summarize_text(args.content, title)
        save_path = save_to_obsidian(args.content, title, None, args.tags, tldr=summary)
        if save_path:
            logger.info(f"✅ Successfully saved text note: {save_path}")

if __name__ == "__main__":
    main()
