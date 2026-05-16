---
name: vcli-publish-gate
description: "Use when Codex has a reviewed Velog draft and must verify explicit approval before pushing through vcli."
---

# vcli: Publish Gate

Handle the final Velog push gate.

## Checklist

1. The user has explicitly approved the draft for publication.
2. The draft already reflects the latest feedback.
3. `meta.yaml` is complete enough to publish.
4. Any optional image work is already resolved.

## Commands

After explicit user approval:

1. Run `vcli status` and confirm the target is `draft` or `modified`.
2. Run `vcli push <slug>`.

## Rules

- Never push on implied approval.
- If approval is ambiguous, ask directly.
- If validation fails, fix the draft before trying again.
- Do not use bulk push for publication.
