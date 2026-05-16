---
name: vcli-post-drafter
description: "Use when Codex already has an approved post plan and should write the actual Velog draft into .vcli/posts content.md and meta.yaml after running vcli create."
---

# vcli: Post Drafter

Draft the actual article after the plan is approved.

## Workflow

1. Confirm the post already exists under `.vcli/posts/<slug>/`.
2. Fill `content.md` with the planned structure.
3. Update `meta.yaml` with title, description, tags, visibility, and series as needed.
4. Preserve continuity with the chosen prior post or series.
5. Immediately show the drafted result to the user so they can react without opening the file manually.

## Rules

- Keep the draft readable and concrete.
- Prefer short sections that can be iterated on through review.
- After writing, include the title plus a meaningful body preview in the response. Do not answer with only "drafted" or file paths.
- If the draft is short enough to scan comfortably, prefer showing the whole draft. Otherwise show the opening section and the most important new section.
- Do not call `vcli push`.
