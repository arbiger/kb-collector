# KB-Collector cost control and active path — 2026-05-15

## Why this exists

George noticed Codex/GPT quota dropping quickly. KB-Collector is high risk because collection/transcription is cheap, but Step 2 summarization can make the active main model read long transcripts/pages.

## Durable policy

- Treat KB-Collector as a heavy-use workflow.
- Step 1 collection/transcription runs locally through the dedicated MLX runtime.
- Step 2 summary must default to MiniMax-M3 when the active main model is expensive/quota-limited (for example openai-codex/gpt-5.5).
- Do not use Codex/GPT to summarize long YouTube transcripts, large web pages, or batch collections unless George explicitly asks to spend premium quota.
- If MiniMax is unavailable, either ask George, pass a prewritten `--summary`, or save raw/pending-summary rather than silently spending Codex.

## Active path pitfall

George has a two-layer skill convention:

- `~/.hermes/skills/openclaw-imports/` = imported/staging inventory
- `~/.hermes/skills/<name>/` or category folders = intended active skills

However Hermes currently scans recursively, so a skill under `openclaw-imports/kb-collector` can still be active. Before editing KB-Collector config or scripts, verify which physical skill directory is actually loaded. Do not assume `~/.hermes/skills/kb-collector/` exists.

As of the session, the only active `name: kb-collector` found was:

`/Users/george/.hermes/skills/openclaw-imports/kb-collector/`

## Script config pitfall

`collect.py` must load the skill-local `.env`, not only the caller's current working directory. Hermes often invokes scripts by absolute path from another cwd. The robust pattern is:

```python
from pathlib import Path
_SKILL_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_SKILL_DIR / ".env")
load_dotenv()
```

Then verify by importing from `/tmp` and checking `AI_PROVIDER` / `VAULT_PATH`.

## Override & Comparison (2026-06-08)

The cost-control policy above is the **default** for all KB-Collector runs. Two narrow exceptions are explicitly allowed, both preserve the two-step workflow:

1. **Premium-model override (one-off).** George explicitly says "用 GPT-5.5 寫 summary" etc. Workflow:
   - DO NOT edit `collect.py` defaults or set `AI_PROVIDER=openai`
   - Run the premium model yourself (delegate_task with the appropriate provider/model, or call via the configured route) to produce the summary
   - Pass the result to `collect.py` via `--summary "..."` so the script just persists it
   - The two-step architecture is intact; only the model that *writes* the summary changed for this one run

2. **Side-by-side model comparison.** George says "比較一下" / "看下變化" / "A 跟 B 差在哪". Convention:
   - Rename existing summary block to `<!-- AI Summary (model-name) -->` (e.g. `(MiniMax-M3)`)
   - Add the new model's block above it as `<!-- AI Summary (other-model) -->`
   - Keep `George Annotation` at the bottom of the summary area, untouched
   - Don't change frontmatter tags; the two labeled blocks are the comparison artifact
   - This is for ad-hoc eyeballing, not durable model-eval records

Both flows are reversible: the default stays M3, the override is per-run, and side-by-side blocks can be collapsed back to a single block once George decides.

If the request is ambiguous ("用好一點的" / "用 AI 寫" / "best model for this"), ask before spending premium quota or building a comparison block. The default is cheap and good enough for ~all KB work.
