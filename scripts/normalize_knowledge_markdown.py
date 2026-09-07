#!/usr/bin/env python3
"""Normalize George's Knowledge markdown files to the canonical KB format."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


CANONICAL_KEYS = {
    "date",
    "created",
    "title",
    "source",
    "source_type",
    "author",
    "collector",
    "tags",
    "review_status",
    "last_reviewed",
    "annotations",
    "related_docs",
}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str, str]:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not match:
        return {}, text, ""
    raw = match.group(1)
    if yaml is None:
        return {}, text[match.end():], raw
    try:
        fm = yaml.safe_load(raw) or {}
        if not isinstance(fm, dict):
            fm = {}
    except Exception:
        fm = {}
    return fm, text[match.end():], raw


def filename_date(path: Path) -> str | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else None


def normalize_date(value: Any, path: Path) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if value:
        match = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
        if match:
            return match.group(0)
    return filename_date(path) or datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def normalize_created(value: Any, date_value: str) -> str:
    if isinstance(value, datetime):
        return value.astimezone().isoformat(timespec="seconds")
    if value:
        raw = str(value).strip()
        if "T" in raw and re.search(r"\d{4}-\d{2}-\d{2}", raw):
            if re.search(r"[+-]\d{2}:?\d{2}$", raw) or raw.endswith("Z"):
                return raw
            return raw + "+08:00"
        match = re.search(r"\d{4}-\d{2}-\d{2}", raw)
        if match:
            return match.group(0) + "T00:00:00+08:00"
    return date_value + "T00:00:00+08:00"


def infer_source_type(source: str) -> str:
    lowered = source.lower()
    if source == "pasted text":
        return "text"
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


def raw_source_value(fm: dict[str, Any]) -> str:
    source = str(fm.get("source") or fm.get("url") or "").strip()
    if not source or source.upper() in {"N/A", "NA", "NONE", "NULL"} or source.lower() == "n/a":
        return ""
    return source


def normalize_source(fm: dict[str, Any]) -> str:
    source = raw_source_value(fm)
    if not source:
        return "pasted text"
    if source.lower() == "pasted text" or source.startswith(("http://", "https://")):
        return source
    return "pasted text"


def clean_tag(tag: Any) -> str | None:
    value = str(tag).strip().strip("#").strip()
    if not value:
        return None
    value = re.sub(r"\s+", "-", value)
    value = value.strip(",")
    if re.fullmatch(r"[a-zA-Z]", value):
        return None
    if value in {"-", ",", "，"}:
        return None
    return value


def normalize_tags(raw_tags: Any) -> list[str]:
    values: list[Any]
    if isinstance(raw_tags, list):
        values = raw_tags
    elif isinstance(raw_tags, str):
        stripped = raw_tags.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            stripped = stripped[1:-1]
        values = re.split(r"[,，]", stripped)
    else:
        values = []

    seen = set()
    out = []
    for value in values:
        tag = clean_tag(value)
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out or ["knowledge"]


def extract_title(fm: dict[str, Any], body: str, path: Path) -> str:
    if fm.get("title"):
        return str(fm["title"]).strip().strip('"')
    match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[-\s]*", "", path.stem)
    return stem or path.stem


def strip_leading_title(body: str, title: str) -> str:
    body = body.lstrip()
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        first = lines[0][2:].strip()
        if first == title or first in title or title in first:
            return "\n".join(lines[1:]).lstrip()
    return body


def extract_section(body: str, heading_regex: str) -> tuple[str, str]:
    match = re.search(heading_regex, body, re.MULTILINE | re.IGNORECASE)
    if not match:
        return "", body
    start = match.end()
    next_heading = re.search(r"\n##\s+", body[start:])
    if next_heading:
        section = body[start:start + next_heading.start()]
        rest = body[:match.start()] + body[start + next_heading.start():]
    else:
        section = body[start:]
        rest = body[:match.start()]
    return section.strip(), rest.strip()


def extract_section_until(body: str, heading_regex: str, stop_headings: tuple[str, ...]) -> tuple[str, str]:
    match = re.search(heading_regex, body, re.MULTILINE | re.IGNORECASE)
    if not match:
        return "", body
    start = match.end()
    stop_pattern = r"\n##\s+(?:" + "|".join(stop_headings) + r")\b"
    next_heading = re.search(stop_pattern, body[start:], re.IGNORECASE)
    if next_heading:
        section = body[start:start + next_heading.start()]
        rest = body[:match.start()] + body[start + next_heading.start():]
    else:
        section = body[start:]
        rest = body[:match.start()]
    return section.strip(), rest.strip()


def remove_embedded_frontmatter(text: str) -> str:
    def repl(match: re.Match) -> str:
        block = match.group(1)
        if re.search(r"^(created|date|Date|source|author|tags|title):", block, re.MULTILINE):
            return "\n"
        return match.group(0)
    return re.sub(r"(?m)^---\n(.*?)\n---\n?", repl, text, flags=re.DOTALL)


def remove_leading_source_snapshot(text: str) -> str:
    _section, rest = extract_section(text, r"^##\s+Source Snapshot\s*$")
    return rest


def extract_legacy_annotation(body: str) -> tuple[str, str]:
    match = re.match(
        r"^\s*[—–-]+\s*\n+\s*annotations:\s*\n(?P<annotation>.*?)(?=\n\s*(?:---|—-|-----)\s*\n|^#\s+)",
        body,
        flags=re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        match = re.match(
            r"^\s*annotations:\s*\n(?P<annotation>.*?)(?=\n\s*(?:---|—-|-----)\s*\n|^#\s+)",
            body,
            flags=re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
    if not match:
        return "", body
    annotation = match.group("annotation").strip()
    rest = body[match.end():].lstrip()
    rest = re.sub(r"^(?:---|—-|-----)\s*\n+", "", rest).lstrip()
    return annotation, rest


def split_summary_and_content(body: str, source_type: str) -> tuple[str, str]:
    transcript_match = re.search(r"^##\s+(Raw\s+Transcript|Transcript)\b.*$", body, re.MULTILINE | re.IGNORECASE)
    if transcript_match:
        summary = body[:transcript_match.start()].strip()
        content = body[transcript_match.end():].strip()
        return clean_summary(summary), content

    content_match = re.search(r"^##\s+Content\b.*$", body, re.MULTILINE | re.IGNORECASE)
    if content_match:
        summary = body[:content_match.start()].strip()
        content = body[content_match.end():].strip()
        return clean_summary(summary), content

    marker = re.search(r"<!--\s*AI Summary.*?-->", body, re.IGNORECASE)
    if marker:
        after = body[marker.end():].strip()
        h1 = re.search(r"\n#\s+.+", after)
        if h1:
            summary = after[:h1.start()].strip()
            content = after[h1.start():].strip()
            content = re.sub(r"^#\s+.+\n+", "", content, count=1).strip()
            return clean_summary("<!-- AI Summary -->\n\n" + summary), content
        return clean_summary(body), ""

    if source_type == "youtube":
        return "", body.strip()
    if re.search(r"^##\s+(Summary|摘要|詳細筆記|Key Insights|Quick Note)\b", body, re.MULTILINE | re.IGNORECASE):
        return clean_summary(body), ""
    if re.search(r"^>\s*TLDR\b", body, re.MULTILINE | re.IGNORECASE):
        return clean_summary(body), ""
    return "", body.strip()


def clean_summary(summary: str) -> str:
    if not summary:
        return ""
    lines = []
    for line in summary.strip().splitlines():
        if line.strip() == "---":
            continue
        if re.match(r"^\*Collected by:", line.strip()):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"^<!--\s*AI Summary(?:\s*\([^)]+\))?\s*-->\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^##\s+AI Summary\s*", "", cleaned, flags=re.MULTILINE | re.IGNORECASE).strip()
    cleaned = remove_leading_source_snapshot(cleaned).strip()
    cleaned = remove_embedded_frontmatter(cleaned).strip()
    cleaned = re.sub(r"^#\s+詳細總結\s*", "### 詳細總結\n\n", cleaned, flags=re.MULTILINE).strip()
    return cleaned


def extract_metadata_lines(summary: str) -> tuple[str, list[str]]:
    kept = []
    meta = []
    for line in summary.splitlines():
        if re.match(r"^\*Summarized by:", line.strip()) or re.match(r"^\*Collected by:", line.strip()):
            meta.append(line.strip())
        else:
            kept.append(line)
    return "\n".join(kept).strip(), meta


def yaml_scalar(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    if not text:
        return '""'
    if re.search(r"[:{}\[\],&*#?|\-<>=!%@`]", text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def render_frontmatter(fm: dict[str, Any], extras: dict[str, Any]) -> str:
    lines = [
        "---",
        f"date: {yaml_scalar(fm['date'])}",
        f"created: {yaml_scalar(fm['created'])}",
        f"title: {yaml_scalar(fm['title'])}",
        f"source: {yaml_scalar(fm['source'])}",
        f"source_type: {yaml_scalar(fm['source_type'])}",
        f"author: {yaml_scalar(fm['author'])}",
        "collector: kb-collector",
        "tags:",
    ]
    for tag in fm["tags"]:
        lines.append(f"  - {yaml_scalar(tag)}")
    for key in ("review_status", "last_reviewed"):
        if key in fm and fm[key] not in (None, ""):
            lines.append(f"{key}: {yaml_scalar(fm[key])}")
    if fm.get("annotations"):
        lines.append("annotations:")
        annotations = fm["annotations"] if isinstance(fm["annotations"], list) else [fm["annotations"]]
        for annotation in annotations:
            lines.append(f"  - {yaml_scalar(annotation)}")
    if fm.get("related_docs"):
        lines.append("related_docs:")
        related = fm["related_docs"] if isinstance(fm["related_docs"], list) else [fm["related_docs"]]
        for doc in related:
            lines.append(f"  - {yaml_scalar(doc)}")
    for key, value in extras.items():
        if key not in CANONICAL_KEYS and value not in (None, ""):
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def normalize_file(path: Path) -> tuple[bool, str]:
    original = path.read_text(encoding="utf-8", errors="replace")
    fm_in, body, _raw_fm = split_frontmatter(original)
    title = extract_title(fm_in, body, path)
    original_source = raw_source_value(fm_in)
    source = normalize_source(fm_in)
    source_type = infer_source_type(source)
    date = normalize_date(fm_in.get("date") or fm_in.get("Date") or fm_in.get("created"), path)
    created = normalize_created(fm_in.get("created") or fm_in.get("Date") or fm_in.get("date"), date)
    source_note = original_source if original_source and original_source != source else ""
    author = str(fm_in.get("author") or source_note or ("George" if source == "pasted text" else "Unknown")).strip()
    tags = normalize_tags(fm_in.get("tags"))

    legacy_annotation, body = extract_legacy_annotation(body)
    body = strip_leading_title(body, title)
    _source_snapshot, body = extract_section(body, r"^##\s+Source Snapshot\s*$")
    collection_metadata, body = extract_section(body, r"^##\s+Collection Metadata\s*$")
    george_annotation, body = extract_section_until(
        body,
        r"^##\s+(George\s+Annotation|Annotation\s*\(George.*?\))\s*$",
        ("Raw\\s+Transcript", "Transcript", "Content", "Collection\\s+Metadata"),
    )
    ai_summary, body = extract_section_until(
        body,
        r"^##\s+AI Summary\s*$",
        ("George\\s+Annotation", "Raw\\s+Transcript", "Transcript", "Content", "Collection\\s+Metadata"),
    )
    if ai_summary:
        content, body = extract_section(body, r"^##\s+(Raw\s+Transcript|Transcript|Content)\b.*$")
        if not content:
            _legacy_summary, content = split_summary_and_content(body, source_type)
        summary = clean_summary(ai_summary)
    else:
        summary, content = split_summary_and_content(body, source_type)
    summary, metadata_lines = extract_metadata_lines(summary)
    if collection_metadata:
        for line in collection_metadata.splitlines():
            line = line.strip()
            if line and line not in metadata_lines and line.startswith("*"):
                metadata_lines.append(line)
    content = remove_embedded_frontmatter(content).strip()
    content = re.sub(r"^#\s+.+\n+", "", content, count=1).strip()

    fm_out = dict(fm_in)
    fm_out.update({
        "date": date,
        "created": created,
        "title": title,
        "source": source,
        "source_type": source_type,
        "author": author,
        "collector": "kb-collector",
        "tags": tags,
    })

    extra = {k: v for k, v in fm_in.items() if k not in CANONICAL_KEYS}
    heading = "Raw Transcript" if source_type == "youtube" else "Content"
    marker = "<!-- AI Summary (existing) -->" if summary else "<!-- Add AI summary here. -->"
    annotation_text = (george_annotation.strip() or legacy_annotation.strip()) if (george_annotation or legacy_annotation) else "<!-- Add George's annotation here. -->"
    content_text = content.strip() if content.strip() else "<!-- Source content not separated in previous version. -->"

    parts = [
        render_frontmatter(fm_out, extra),
        f"# {title}\n\n",
        "## Source Snapshot\n\n",
        "| Field | Value |\n|---|---|\n",
        f"| Source | {source} |\n",
        f"| Type | {source_type} |\n",
        f"| Author | {author} |\n\n",
        "## AI Summary\n",
        marker + "\n\n",
    ]
    if summary:
        parts.append(summary + "\n\n")
    parts.extend([
        "## George Annotation\n\n",
        annotation_text + "\n\n",
        f"## {heading}\n\n",
        content_text + "\n\n",
        "## Collection Metadata\n\n",
    ])
    if metadata_lines:
        parts.append("\n".join(metadata_lines) + "\n")
    else:
        parts.append(f"*Collected by: kb-collector normalization on {datetime.now().strftime('%Y-%m-%d')}*\n")

    normalized = "".join(parts)
    changed = normalized != original
    if changed:
        path.write_text(normalized, encoding="utf-8")
    return changed, source_type


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Knowledge markdown files.")
    parser.add_argument("--vault", default="/Users/george/Documents/Georges/Knowledge")
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser()
    backup_dir = Path(args.backup_dir).expanduser()
    files = sorted(vault.glob("*.md"))
    if not files:
        print("NO_MARKDOWN_FILES")
        return 1

    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest = backup_dir / "manifest.txt"
    changed = 0
    counts: dict[str, int] = {}

    for path in files:
        rel = path.name
        if not args.dry_run:
            shutil.copy2(path, backup_dir / rel)
        if args.dry_run:
            text = path.read_text(encoding="utf-8", errors="replace")
            fm, body, _ = split_frontmatter(text)
            st = str(fm.get("source_type") or infer_source_type(normalize_source(fm)))
            counts[st] = counts.get(st, 0) + 1
            continue
        did_change, source_type = normalize_file(path)
        changed += 1 if did_change else 0
        counts[source_type] = counts.get(source_type, 0) + 1

    if not args.dry_run:
        manifest.write_text(
            "\n".join([
                f"timestamp={datetime.now().isoformat(timespec='seconds')}",
                f"vault={vault}",
                f"files={len(files)}",
                f"changed={changed}",
                "source_type_counts=" + repr(dict(sorted(counts.items()))),
            ]) + "\n",
            encoding="utf-8",
        )

    print(f"files={len(files)}")
    print(f"changed={changed if not args.dry_run else 'DRY_RUN'}")
    print("source_type_counts=" + repr(dict(sorted(counts.items()))))
    print(f"backup_dir={backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
