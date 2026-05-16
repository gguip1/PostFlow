---
name: vcli-review-loop
description: "Use when Codex has a draft post and should iterate on it through user feedback before any Velog push."
---

# vcli: Review Loop

Drive the draft through feedback rounds until the user is satisfied.

## Workflow

1. Show the current draft or the changed section before asking for feedback.
2. Ask for focused feedback on structure, tone, missing details, and examples.
3. Apply the user's requested changes to `content.md` and `meta.yaml` when needed.
4. Repeat until the user explicitly approves.

## Rules

- Prefer targeted questions over broad "any feedback?" prompts when the next step is unclear.
- Keep edits incremental and aligned with the accepted plan.
- After each revision, show the changed text itself, not just a summary of what changed.
- Do not push the post on your own. Approval must come from the user.
