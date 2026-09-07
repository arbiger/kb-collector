# Web Content Extraction — Truncated Pages

When `browser_snapshot` or `web_extract` returns partial content (truncated, login wall, or "Website Not Supported"), try this sequence:

## Fallback 1: `browser_console` (for X/Twitter/dynamic JS pages)

```javascript
document.querySelector('article')?.innerText || document.body.innerText
```

This bypasses the DOM element limit and pulls full text from X/Twitter threads that get truncated in `browser_snapshot`.

**Usage pattern:**
1. `browser_navigate` → the URL
2. `browser_console` with the expression above
3. Parse the returned string for the full article

## Fallback 2: Nitter (Twitter/X alternative frontend)

```
https://nitter.net/{username}/status/{tweet_id}
```

Open-source, no JS login wall. May still get truncated but often works when browser_navigate fails.

## Fallback 3: URL cleanup

- X/Twitter URLs with `?si=` tracking params can cause parsing issues in subprocess calls
- YouTube URLs with `?si=` params: the param is just a share tracker, the base video ID is what matters
  - ✅ `https://youtu.be/sQW-Xo0GnNc` works
  - ❌ `https://youtu.be/sQW-Xo0GnNc?si=...` gets mangled by shell parsing

## Pitfall: yt-dlp "Video unavailable" on valid videos

- yt-dlp may report `Video unavailable` even when the video plays fine in browser
- Cause: server IP geolocation differs from user's location
- If browser can play it but yt-dlp can't → video is valid, just geoblocked for the server
- Workaround: no CLI fix; content must be extracted via browser-based approach (Fallback 1)

## Pitfall: Page is fully JS-shell with zero content (NOT truncated)

When `collect.py url` succeeds but the saved .md contains only a JS-required/login wall banner (e.g. X/Twitter returning `JavaScript is not available. Please enable JavaScript to continue...`, or a site returning 200 OK with an empty `<div id="app">`):

- This is **NOT** the same as truncated content — the page is fully JS-rendered SPA, no SSR, no content in raw HTML
- `web_extract` and `collect.py` get the literal JS shell string
- `browser_snapshot` will show login UI, not the article
- **Fix: `browser_navigate` first to let JS load, then `browser_console` to extract**

```python
# 1. Navigate — JS gets time to render
browser_navigate(url=URL)

# 2. Console extract (article selector is X/Twitter specific, use body fallback)
result = browser_console(expression='document.querySelector("article")?.innerText || document.body.innerText')
```

- If `article` exists (X/Twitter thread, blog post in `<article>` tag) → returns the full text
- If no `<article>` tag → falls back to `document.body.innerText` (noisy but complete)
- **Verify before rewriting KB note**: the console result should be hundreds-thousands of chars, not the JS shell string. If it's still the shell, the SPA didn't load (cookie consent wall, geoblock, or bot detection) — try Nitter (Fallback 2) or stop and tell George

- **KB note recovery pattern**: When the first `collect.py` run saved a JS shell, don't re-collect. Patch the existing .md: replace the body with the extracted content, add frontmatter `author` and proper `title`, then do Step 2 summary in the same turn.
