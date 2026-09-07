# Memory Tool Quirks — Field Notes (2026-06-25, extended 2026-06-28)

Quirks hit in real sessions when calling the `memory` tool for MEMORY.md / USER.md edits. Apply to **any** skill that writes through `memory`, not just kb-collector. Companion to `hermes-identity-config-alignment` pitfall #18.

---

## 1. Batch `replace` is unreliable inside `operations` arrays

**Symptom:** `memory` action=`batch`, `operations=[{action:"replace", old_text:"...", content:"..."}, {action:"add",...}, ...]` returns `success` with `usage: 97%` claim, **but the `replace` did not apply** — only the `add` ops did. You `read_file` MEMORY and the replaced entry is unchanged.

**Verified:** 2026-06-25, 6-op batch (3 replace + 3 add), only the 3 adds applied, 2 extra turns spent diagnosing.

**Fix:** Never mix `replace` with other ops in a batch. Either:
- Single-op `memory` call with `action="replace"`, `old_text="..."`, `content="..."`
- Or batched `add` + `remove` only (those are reliable together)

**Workaround when you need replace + add atomically:** split into two `memory` calls — first replace (single-op), verify with read_file, then add. Adds an extra turn but is reliable.

---

## 2. `remove` with `§` separator in `old_text` fails with "No entry matched"

**Symptom:** The entry IS in the file but `memory remove` returns `"No entry matched"`. The `old_text` string contains a `§` character (the separator between entries).

**Root cause:** The `memory` tool normalizes / strips `§` from `old_text` matching, so your entry fingerprint doesn't match what's stored.

**Fix:** Pass only the entry content body (e.g. `**Title:** body text.`) as `old_text`. **Do not** include the trailing `§` separator. If you're removing the last entry, just match the entry text — no separator needed (there isn't one after the last entry anyway).

---

## 3. `patch` after `write_file` + `cat >> file` flags "file modified since last read" — expected, ignore

**Symptom:** You `write_file` a new file, then `terminal` + `cat >>` to append content, then `patch` to insert a final small section. `patch` warns `file modified since last read` (or similar).

**This is normal.** `patch` tracks per-file read state in the agent context, but `cat >>` happens in a subprocess and isn't visible to the patch tool's read tracking. The warning is a false positive — the patch will still apply correctly.

**Fix:** Don't waste a turn re-reading the file to "clear the warning". Just confirm the resulting content with a follow-up `read_file` or `grep` after the patch, only if the patch was critical. For routine multi-step writes (frontmatter → transcript → annotation), the pattern works fine.

---

## 4. `remove` (single-op, no `§` in `old_text`) can wipe adjacent entries across § separator — silent collapse (verified 2026-06-28)

**Symptom:** You call `memory remove` with a clean `old_text` (entry body only, no `§` character). Tool returns `success: true, usage: 37%` — usage dropped dramatically. You `read_file` MEMORY and find that **two entries are gone instead of one** — the matched entry plus the entry immediately below the next `§` separator.

**Verified:** 2026-06-28, OMLX migration. Removing `**Serial subagent for OMLX-bound tasks...**` (the §-joined pair of "Serial subagent" + "Subagent timeout is not always timeout") returned `entry_count: 3, usage: 37%`. The file had 5 entries originally; the remove was supposed to drop just the first one. Two entries were collapsed into one removal.

**Why this happens:** The `memory` tool's entry-boundary detection is fuzzy. When `old_text` matches a content block whose structure happens to span across `§`, the tool greedily consumes the separator + next entry as part of the matched region. The previous quirk #2 (failure on § in old_text) and this new #4 (collapse across § boundary) are two failure modes of the same fuzzy matcher — just on opposite sides.

**Fix:**
1. After every `memory remove`, **immediately `read_file` MEMORY.md** and verify the remaining entries match what you intended.
2. If an adjacent entry was unintentionally collapsed, re-add it via `memory add` with the original content.
3. This verification is mandatory regardless of whether quirk #2 fires — both quirks share the same root cause and verify-after-remove catches both.
4. For migrations removing multiple entries, prefer removing **one at a time + verify each** rather than batching multiple removes — the per-op cost is one extra turn but the diagnostic clarity is worth it.

**Pattern that worked in 2026-06-28 OMLX migration:**
- Remove entry A → read_file → verify A gone, B/C/D/E intact
- Remove entry B → read_file → verify B gone, C/D/E intact
- ... etc.
- Then add fact_store facts + MEMORY refs in separate calls
- Total cost: ~5 turns for a 5-entry → 1-entry migration, but no surprises

---

## Budget arithmetic traps

### 5. Budget calc is against FINAL state, not net change

**Symptom:** `memory` tool reports `After applying all N operations, memory would be at 2,448/2,200 chars`. You planned a batch with `remove` (-300) + `add` (+500) = net +200. The math says over budget by 248.

**Why:** The budget calc is computed against the **final state** of MEMORY after all ops apply, not the net delta. `remove` operations don't credit the budget — the tool only counts what the file would contain post-write.

**Fix:** Plan headroom for the `add`s, not the net change. If you need to add 500 chars and you want to stay under 2,200, you need 500 chars of headroom in the current file (regardless of how much you remove in the same batch).

---

### 6. Double-count: remove + add of replacement still counts the add, not the net

**Symptom:** You include `remove` of an old entry (300 chars) AND `add` of its replacement (300 chars) in the same batch, expecting net zero. Budget calc says over by 300.

**Why:** Same as quirk #5 — budget only counts adds, doesn't credit removes even within the same batch.

**Fix:** Split into two batches:
- Batch 1: just the `remove`. Verify usage drops by ~300.
- Batch 2: just the `add` of the replacement. Now budget calc reflects the actual final state correctly.

Verified 2026-06-25 saved 250 chars by reordering.

---

## Quick reference: safe edit patterns

| Operation | Safe pattern | Why |
|---|---|---|
| Add 1 entry | Single `add` call | No edge cases |
| Remove 1 entry | Single `remove` call + **immediate `read_file` verify** | Catches quirk #4 collapse |
| Replace 1 entry | Single `replace` call + `read_file` verify | Avoids batch-replace unreliability |
| Multiple adds | Batch `add` ops | Reliable |
| Multiple removes | One-at-a-time + verify each | Catches quirk #4 |
| Mixed replace + add | Two separate calls: replace first (verify), then add | Never batch these |
| Migrate N entries to fact_store | Remove one + add fact (or vice versa), then move to next | Verify each step |

---

## When these quirks DON'T apply

- USER.md edits: same `memory` tool, same quirks
- SOUL.md edits: NOT via `memory` tool — use `patch` or `write_file` directly on the SOUL.md file
- fact_store: uses `fact_store` tool, not `memory`, with its own (different) quirks (entity resolution, trust_score, etc.)