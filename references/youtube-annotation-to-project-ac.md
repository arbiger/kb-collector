# YouTube/KB Annotation → Project AC Pattern

Use this pattern when George asks to collect/summarize a video or article, then adds his own conclusions and asks whether they can be used for ideation or tied to a project.

## Workflow

1. Keep the full source artifact in `~/Documents/Georges/Knowledge/`:
   - raw transcript/content
   - AI summary
   - George's annotation/conclusion
2. Insert George's conclusion as an explicit annotation block, not just a chat reply:
   ```md
   <!-- George Annotation -->
   ---
   ## George 的轉化結論 / Annotation
   ...
   *Annotated by: George; captured by Hermes on YYYY-MM-DD*
   ---
   ```
3. If the annotation affects a project, create/update a project-level summary or AC record under that project, linking back to the KB note.
4. Do not copy the full transcript/content into the project folder. Project folders are for summary, decisions, links, and implementation state.
5. When analyzing project fit, explicitly check whether the existing project direction is only a content/production workflow and whether it needs a conversion mechanism such as:
   - funnel CTA
   - assessment/scorecard
   - lead magnet
   - email capture
   - qualified lead/follow-up KPI

## Example from 2026-05-16

George collected a Daniel Priestley / ScoreApp video. The useful transfer was not only “write more content”; it was:

```text
content/social/blog → trust/warm-up → assessment/scorecard → signal capture/segmentation → human or agent-assisted follow-up
```

For NuGROWS Marketing, this changed the project from a pure content studio (Blog/Social + SB7 + ready-to-post) into a funnel system:

- NuGROWS consumer assessment: Hair Vitality Score / 15-Minute Ritual Finder
- LDM/OEM assessment: Project Readiness / Module Selection checklist
- KPI shift: posts published → assessment completions, email capture, qualified leads, follow-up conversion
