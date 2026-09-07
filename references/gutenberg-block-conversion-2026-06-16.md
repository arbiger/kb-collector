# Markdown → Gutenberg Block Conversion

> Working reference for converting an Obsidian-style `.md` into a WordPress REST API body that renders correctly in the block editor.

Captured 2026-06-16 while publishing `2026-06-16-when-the-economist-says-taiwan-ai-boom-leaves-everyone-behind.md` to soundsofgeorge.com. Site uses block editor (Gutenberg); the basic HTML form (`<p>`, `<h2>`, `<ul>`) is accepted but doesn't render in the visual editor — blocks do.

## Block reference (the only 7 you need for blog posts)

| Markdown source | Gutenberg block markup |
|---|---|
| `# H1` | **DO NOT INCLUDE in body** — H1 is the post `title` field. Putting `<h1>` in body renders as a second title visually. |
| `## H2` | `<!-- wp:heading --><h2 class="wp-block-heading">...</h2><!-- /wp:heading -->` |
| `### H3` | `<!-- wp:heading {"level":3} --><h3 class="wp-block-heading">...</h3><!-- /wp:heading -->` |
| `> blockquote` | `<!-- wp:quote --><blockquote class="wp-block-quote"><p>...</p></blockquote><!-- /wp:quote -->` |
| `---` (horizontal rule) | `<!-- wp:separator --><hr class="wp-block-separator has-alpha-channel-opacity"/><!-- /wp:separator -->` |
| `- bullet` (consecutive) | `<!-- wp:list --><ul><li>...</li><li>...</li></ul><!-- /wp:list -->` (batch into ONE list block, not one per bullet) |
| paragraph | `<!-- wp:paragraph --><p>...</p><!-- /wp:paragraph -->` |

## Inline formatting (inside any block's content)

| Markdown | HTML |
|---|---|
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `` `code` `` | `<code>code</code>` |

Regex (Python, applied per-line / per-block content):

```python
s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
s = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',          s)
s = re.sub(r'`(.+?)`',       r'<code>\1</code>',      s)
```

## Working reference script (drop-in)

The exact Python that was used on 2026-06-16 for the 經濟學人 post. Reads a `.md` from `07 📰 Blog/published/`, strips frontmatter, drops the first H1, converts the rest, and writes `html` + `title` to `/tmp/`. Reusable as-is for any future blog post; the only thing that changes is the input path.

```python
#!/usr/bin/env python3
"""Convert Obsidian-style blog .md to Gutenberg block HTML for WP REST API."""
import re, sys

md_path = sys.argv[1] if len(sys.argv) > 1 else "/path/to/post.md"
with open(md_path, "r") as f:
    md = f.read()

# 1. Strip frontmatter
parts = md.split("---\n", 2)
frontmatter = parts[1] if len(parts) >= 3 else ""
body = parts[2].strip() if len(parts) >= 3 else md

# 2. Title from frontmatter
title_match = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
title = title_match.group(1).strip() if title_match else "Untitled"

# 3. Drop the first H1 (it duplicates post title)
seen_h1 = False
out = []
for line in body.split("\n"):
    if line.startswith("# ") and not seen_h1:
        seen_h1 = True
        continue
    out.append(line)
body = "\n".join(out).strip()

# 4. Inline → HTML
def inline(s):
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',          s)
    s = re.sub(r'`(.+?)`',       r'<code>\1</code>',      s)
    return s

# 5. Block-by-block conversion (batched lists, no repeated p tags)
blocks, para, lst = [], [], []
def flush_para():
    global para
    if para:
        t = " ".join(para).strip()
        if t:
            blocks.append(f'<!-- wp:paragraph -->\n<p>{inline(t)}</p>\n<!-- /wp:paragraph -->')
        para = []
def flush_list():
    global lst
    if lst:
        items = "".join(f"<li>{inline(x)}</li>" for x in lst)
        blocks.append(f'<!-- wp:list -->\n<ul>{items}</ul>\n<!-- /wp:list -->')
        lst = []

for raw in body.split("\n"):
    line = raw.rstrip()
    if line.startswith("> "):
        flush_para(); flush_list()
        blocks.append(f'<!-- wp:quote -->\n<blockquote class="wp-block-quote"><p>{inline(line[2:])}</p></blockquote>\n<!-- /wp:quote -->')
    elif line.startswith("## "):
        flush_para(); flush_list()
        blocks.append(f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{inline(line[3:].strip())}</h2>\n<!-- /wp:heading -->')
    elif line.startswith("### "):
        flush_para(); flush_list()
        blocks.append(f'<!-- wp:heading {{"level":3}} -->\n<h3 class="wp-block-heading">{inline(line[4:].strip())}</h3>\n<!-- /wp:heading -->')
    elif line.startswith("---"):
        flush_para(); flush_list()
        blocks.append('<!-- wp:separator -->\n<hr class="wp-block-separator has-alpha-channel-opacity"/>\n<!-- /wp:separator -->')
    elif re.match(r'^\s*-\s+', line):
        flush_para()
        lst.append(re.sub(r'^\s*-\s+', '', line))
    elif line.strip() == "":
        flush_para(); flush_list()
    else:
        flush_list()
        para.append(line)

flush_para(); flush_list()
html = "\n\n".join(blocks)

print(f"TITLE: {title}")
print(f"BLOCKS: {len(blocks)}")
print(f"HTML_LEN: {len(html)}")
```

## WordPress REST API push

```python
import base64, json, urllib.request

# Auth
auth = base64.b64encode(b"<email>:<application_password>").decode()
body = {
    "title": title,
    "content": html,
    "status": "draft",          # ALWAYS start with draft. Promote from WP UI.
    "slug": "<kebab-case-slug>",
    "excerpt": "<155-char summary>",
}
req = urllib.request.Request(
    "https://<site>/wp-json/wp/v2/posts",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as r:
    result = json.loads(r.read().decode())
    print("POST_ID:", result["id"], "URL:", result["link"], "STATUS:", result["status"])
```

## Rank Math SEO meta (separate POST after the post is created)

```python
import base64, json, urllib.request
auth = base64.b64encode(b"<email>:<application_password>").decode()
body = {
    "objectType": "post",
    "objectID": <post_id>,
    "meta": {
        "rank_math_title": "<60-char SEO title>",
        "rank_math_description": "<155-char meta description>",
        "rank_math_focus_keyword": "<primary keyword>",
        "rank_math_pillar_content": "off",
        "rank_math_schema_Article": "off",
    },
}
req = urllib.request.Request(
    "https://<site>/wp-json/rankmath/v1/updateMeta",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    method="POST",
)
urllib.request.urlopen(req, timeout=20).read()
```

The response is small and doesn't echo the meta — verify by GET-ing the public URL and grepping for `<title>` and `<meta name="description" content="...">`. WordPress's REST API doesn't return `rank_math_*` keys in the default post response (they're unregistered meta).

## Tags and categories (also separate POST, after the post is created)

```python
# Add tags
for tname in new_tags:
    enc = urllib.parse.quote(tname)
    existing = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"https://<site>/wp-json/wp/v2/tags?search={enc}",
                               headers={"Authorization": f"Basic {auth}"}),
        timeout=10).read())
    if existing:
        tag_ids.append(existing[0]["id"])
    else:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://<site>/wp-json/wp/v2/tags",
            data=json.dumps({"name": tname, "slug": tname}).encode(),
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            method="POST"), timeout=20).read())
        tag_ids.append(r["id"])

# PUT to update post with categories + tags
update = json.dumps({"categories": [<cat_id>], "tags": tag_ids}).encode()
req = urllib.request.Request(
    f"https://<site>/wp-json/wp/v2/posts/<post_id>",
    data=update,
    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    method="PUT",
)
urllib.request.urlopen(req, timeout=20)
```

## What does NOT work / known issues

- **Block editor may render the saved body as plain HTML** if your block markup is malformed (e.g. unbalanced `<!-- wp:xxx -->` / `<!-- /wp:xxx -->`). The WP REST API will still accept it; the visual editor will look fine in the preview, but the post will show a "this block contains unexpected or invalid content" warning when re-edited. Test by re-opening the post in WP Admin after publishing.
- **Critical error / 500 on public page** despite correct `<title>` and meta — usually LiteSpeed cache, Rank Math, or another plugin crashing during render. SEO meta writes anyway (those are stored in `postmeta` table before render). Debug is WP-side, not API-side. See `kb-collector` SKILL.md "Source material → George's personal blog post" pitfall #9.
- **WP returning empty `meta` field** when reading the post back via REST — this is normal for unregistered meta (Rank Math, Yoast, etc. don't register their meta keys as REST-readable). Not a sign that your meta write failed.
