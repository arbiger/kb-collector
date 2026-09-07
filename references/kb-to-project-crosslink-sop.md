# KB Note → Project Reference Note: Naming & Location SOP

When George says something like "this can go into `precaster-seo` as reference" or "this is useful for project X" — the KB note (full source) stays in `~/Documents/Georges/Knowledge/`, and a **condensed reference note** goes into the project's folder. This SOP is the convention I (Hermes) have to follow when picking filename and location.

## Location rules

| Project type | Where the reference note goes | Subfolder pattern |
|--------------|-------------------------------|-------------------|
| Has `AGENTS.md` workflow + `SEO-AUDITS/<site>/...` audit tree | `<project>/SEO-AUDITS/CROSS-SITE/` if framework/principle spans multiple sites | framework, methodology, reference |
| Per-site content (specific to one BU's site) | `<project>/SEO-AUDITS/<site>/` | per-site evidence |
| Generic project (no `AGENTS.md`, no audit tree) | `<project>/references/` or `<project>/research/` | depends on project |
| Personal / people note | `~/Documents/Georges/04 👤 People/George/` or `~/Documents/Georges/03 📚 Resources/` | cognition, profile |

**Always `ls` the project first** to see its existing convention before deciding subfolder. Look at how prior reference notes are named + located (e.g. precaster-seo uses `CROSS-SITE/2026-MM-DD-<source>-<topic>-<author>.md`).

## Filename pattern

`YYYY-MM-DD-<source>-<topic>-<author-or-handle>.md`

- `<source>`: `youtube` / `twitter` / `web` / `podcast` / `paper` / `internal`
- `<topic>`: 2-4 words slug, content-derived (e.g. `SEO-three-systems`, `ai-agent-playbook`, `scoreapp-funnel`)
- `<author-or-handle>`: 1 word, surname or @ handle (e.g. `zimu`, `Neil-Patel`, `Priestley`)

**Examples (real from precaster-seo):**
- `2026-05-29-ai-agent-seo-reference.md` (youtube, ai-agent-playbook, Neil-Patel)
- `2026-05-29-Seth-Godin-future-of-marketing.md` (youtube, future-of-marketing, Seth-Godin)
- `2026-06-04-twitter-SEO-three-systems-zimu.md` (twitter, SEO-three-systems, zimu)

## Content shape (project reference note vs KB note)

| Section | KB note (`Knowledge/`) | Project reference note |
|---------|------------------------|------------------------|
| Raw transcript / full source | ✅ Full | ❌ Don't copy — link only |
| AI summary | ✅ | ✅ Condensed (project-relevant takeaways only) |
| George annotation | ✅ | ✅ |
| Cross-link to other refs in same project | — | ✅ Required — show how this fits the project's existing reference web |
| Project-specific implications | — | ✅ Required — table or bullet mapping to project's BUs / sites / KPIs |
| Source URL | ✅ | ✅ + KB note path |

**Length target**: Project reference note = 1/4 to 1/2 of KB note size. If you find yourself copying 80% of the KB note, the project note is the wrong artifact — keep summary + decisions in project, full source in KB.

## Cross-link rules (bidirectional)

- KB note `Knowledge/YYYY-MM-DD-...md` **must** end with a `## Cross-link` section pointing to the project reference note path
- Project reference note **must** start (or end) with a `**KB original:**` pointer back to the KB note
- If the project has multiple related reference notes (e.g. precaster-seo has `2026-05-29-ai-agent-seo-reference.md` and this one), add a "与既有 reference 的关系" subsection explicitly stating complement/contradict/extend relationship

## George's decision gate

- Don't auto-create project reference notes. George has to say "放到 X" / "可以 reference" / similar first.
- After he says yes, ask yourself (or him) **which** subfolder before writing — if uncertain between `CROSS-SITE/` and a per-site folder, default to `CROSS-SITE/` and explain why.
- If the KB note is **only** relevant to one specific BU, put it in `<project>/SEO-AUDITS/<that-site>/` not `CROSS-SITE/`.
- For BUs/projects **outside** the precaster umbrella, use that project's existing convention (always `ls` first).

## What NOT to do

- ❌ Don't move the KB note into the project folder — KB is the canonical source, project is the digest
- ❌ Don't create a reference note without George's explicit "yes put it in X" — even if it obviously fits
- ❌ Don't write a 1-page project note that's mostly the KB note re-summarized — that's not a reference, it's a duplicate
- ❌ Don't update `<project>/AGENTS.md` just because you have a new methodology — AGENTS.md is the entry point agents read first; changes there ripple. Only update when the methodology is being adopted as default workflow.
