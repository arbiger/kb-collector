# Unified YouTube and Source Routing Contract

`kb-collector` is the policy owner for deciding whether a source is kept, where it is written, and how the final Knowledge note is shaped. `youtube-content` is a helper for temporary transcript acquisition and read-only analysis.

## Routes

| User wording | Required outcome |
| --- | --- |
| `Collect <URL>` | Acquire the source once. Write a canonical Knowledge note and complete its source-faithful AI Summary in the same workflow. |
| `Collect <URL>, 先給我詳細總結` | Acquire the source once. Return a detailed source summary and optional red-team analysis in chat. Do not write a file until George explicitly selects a destination. |
| `先不要存，我先看詳細總結` | Run read-only analysis only. Do not write Knowledge, Desktop, project, or pending files. |
| `跟 <project> 有關，放桌面` | Write a Desktop or named-project working note only. Do not save the source to Knowledge unless George also asks to collect or save it. |
| `Collect <URL>，跟 <project> 有關，放桌面` | Write both: a canonical Knowledge source note and a linked Desktop or named-project working note. |
| `Pasted text or a long paragraph` | Treat the payload as `source: pasted text` and `source_type: text`. Apply the same chat-only, Knowledge, and Desktop/project routing choices. |

Knowledge persistence and Desktop/project writeback are independent choices. Do not infer one from the other.

## Acquisition

For YouTube, acquire a transcript once in this order:

1. Creator-provided captions.
2. YouTube auto-generated captions.
3. Local Whisper only when captions are missing or visibly unfit.

Caption acquisition is performed by the documented `youtube-content` helper workflow. `collect.py youtube` is the deterministic MLX audio fallback and persistence entrypoint; it is not a caption fetcher. Reuse the temporary transcript for preview and persistence. Do not fetch or transcribe the same video again merely because George later chooses a destination.

## Canonical Note Semantics

- `AI Summary` records the speaker's or source's meaning faithfully. Do not blend in the collector's judgment.
- `Analysis & Red Team` is optional. Put transferability, assumptions, counterarguments, uncertainty, and applicability here.
- `George Annotation` preserves George's own interpretation or correction. When pasted text is explicitly George's thought, preserve his wording here or in a George-authored note rather than treating it as an external claim.
- `Raw Transcript` or `Content` retains the source evidence.

Record `transcript_source: creator_caption`, `youtube_auto_caption`, or `whisper` whenever the final collector knows the provenance. Notes produced directly by `collect.py youtube` use `whisper` to identify its MLX-backed audio path.

Keep source time separate from collection time: `source_published_at` is the original source publication date in `YYYY-MM-DD` or `null` when unavailable; `date` and `created` record when George collected the item. Show both in `Source Snapshot`.
