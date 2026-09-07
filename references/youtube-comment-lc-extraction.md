# YouTube `&lc=` Comment Extraction (verified 2026-07-07, qEA2QjU7l2k)

## What this solves

A `Collect` URL shaped like `https://youtube.com/watch?v=<VIDEO_ID>&lc=<long-base64>` is pointing at **one specific comment** on the video — usually a viewer's TL;DR / "她/他自己做的總結" that George wants documented alongside the video source. The naive two paths (web_extract, browser_console) both fail silently. Use the yt-dlp recipe below to dump all comments server-side and walk the JSON to find the target.

## The recipe (one-shot)

```bash
yt-dlp --skip-download --write-comments --write-info-json \
  "https://www.youtube.com/watch?v=<VIDEO_ID>" \
  -o "/tmp/yt_<VIDEO_ID>_meta.%(ext)s"
```

Cost: ~1-3 MB JSON, 5-15s on YT side for typical popular videos (popular videos have 500-1000+ comments → 30-60s for the comment-pagination phase).

## Walk the JSON to find the targeted comment

The `*.info.json` has `d['comments']` as a list of top-level comments, each with `'replies'` (or similar nested keys) holding reply dicts. Use a recursive walk to find any node whose `id` matches:

```python
import json

d = json.load(open('/tmp/yt_<VIDEO_ID>_meta.info.json'))
comments = d.get('comments', [])
print(f'total comments: {len(comments)}')

def walk(node):
    if isinstance(node, dict):
        cid = node.get('id', '')
        text = node.get('text', '')
        if cid and text:
            yield (cid, node.get('author', ''), text)
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)

target = '<lc base64 string, e.g. UgzFPdUazfxkxMyGjwp4AaABAg>'
for cid, author, text in walk(comments):
    if target in cid:
        print('---', cid, '|', author)
        print(text)
```

Substring match (`target in cid`) is intentional — yt-dlp's `id` field sometimes has a leading namespace prefix that doesn't appear in the bare `lc=` URL fragment, so exact-match fails. The first match is reliably the right one.

## Verified output (2026-07-07, qEA2QjU7l2k)

- Video: `dumb content strategy that made us millions` by David Fragomeni
- 901 comments total in the dump
- `lc=UgzFPdUazfxkxMyGjwp4AaABAg` matched exactly 1 comment: by `@Blueprint30App`
- Comment was the viewer's TL;DR (3 sections + 12 SOPs) of the 14:28 video — more executable than the video itself
- This is why George flagged the comment specifically in his `Collect` follow-up ("這個是他的一個評論，好像是她自己做的總結")

## Why the naive paths fail

| Path | Failure mode |
|---|---|
| `web_extract` on the `&lc=` URL | Returns the video page (transcript + description). `lc=` is a hash anchor that `web_extract` does not resolve against YT's JS-rendered thread. |
| `browser_navigate` + `browser_console` + `document.body.innerText` | Returns the video player + recommended-videos section. The comment thread is rendered inside a shadow DOM that the console bridge does not traverse — `innerText` can be empty (`document.body.innerText.length === 0`) or only contain the player chrome. |
| Direct GET on the `&lc=` URL via curl | Same as `web_extract` — YT needs JS to render the comment thread. |

## KB note authoring after pulling

When the `&lc=` comment is a viewer's TL;DR / "her own summary" of the video, treat it as a **second source** alongside the video itself. Structure the KB note with two distinguishable raw sections:

```markdown
## Transcript
<raw video transcript from /tmp/yt_<id>/full_text.txt>

## @<handle> 留言（George 指定的「她/他自己做的總結」原文）
<verbatim comment text>

<!-- AI Summary -->
## 詳細總結
- 一句話：<what the video says>
- @<handle> 的濃縮：
  <how the comment reorganizes the video's framework>
- <further Hermes analysis / application>
```

The two `#` headings (`## Transcript` + `## @<handle> 留言`) are the source-of-truth markers. The AI summary then **refers to both** and explains how the comment is a TL;DR of (or different angle on) the video — that structural framing is what makes future re-reads traceable. Don't auto-merge into one narrative; the two-source structure is what George asked for when he flagged the comment specifically.

## Cross-references

- KB note from this case: `~/Documents/Georges/Knowledge/2026-07-07-david-fragomeni-dumb-content-strategy-three-types.md`
- Bundled `youtube-content` skill has the broader yt-dlp + transcript workflow (transcript extraction is parallel but separate; this reference is specifically about extracting **comments**, not transcripts)
