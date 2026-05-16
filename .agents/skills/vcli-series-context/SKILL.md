---
name: vcli-series-context
description: "Use when Codex needs to inspect existing local Velog posts and determine whether a new article should continue an existing series, follow a specific prior post, or stand alone."
---

# vcli: Series Context

Analyze the local Velog archive before planning a new post.

## What To Inspect

- `vcli status`
- `.vcli/registry.yaml`
- `.vcli/posts/<slug>/meta.yaml`
- Relevant existing `content.md` files

## Output

Produce a compact recommendation with:

1. Best matching prior post or series
2. Why this new article belongs there
3. What gap or next step this article should cover
4. Whether the article should be standalone instead

## Rules

- Present 1-3 realistic continuation options when more than one fit exists.
- Prefer explicit continuity over vague similarity.
- If a specific prior post should be referenced in the intro, say so.
- Do not draft the post here. Hand off to planning once the context is chosen.
