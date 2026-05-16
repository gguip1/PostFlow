---
name: vcli-blog-writer
description: "Use when Codex should orchestrate the full Velog writing flow with unofficial-velog-cli: choose the right existing series context, plan the article, draft it, iterate with user feedback, decide whether images are needed, and only push after explicit approval."
---

# vcli: Blog Writer

Treat this skill as the only user-facing entrypoint. Use the other `vcli-*` skills as internal helpers.

## Default Flow

1. Inspect the current repo context, run `vcli status` when available, and read existing local Velog posts under `.vcli/posts`.
2. Use `vcli-series-context` to decide whether this post continues an existing article or series.
3. Use `vcli-post-planner` to propose title, angle, audience, and outline.
4. After the plan is accepted, run `vcli create <slug> --title ...`.
5. Use `vcli-post-drafter` to write `content.md` and update `meta.yaml`.
6. Use `vcli-review-loop` to refine the draft through user feedback.
7. Use `vcli-image-planner` when the post may benefit from screenshots, diagrams, or a thumbnail. If an image should actually be generated, use the existing `imagegen` skill.
8. Use `vcli-push-gate` before any `vcli push` command.

## Rules

- Do not ask the user to choose helper skills. You choose them.
- Do not run `vcli push` without explicit user approval.
- After creating or revising a draft, show the actual draft text in the response. Do not stop at reporting file paths or that the draft was updated.
- By default, show the title, series context, and a meaningful preview of the draft body. If the user asks, show the full draft.
- Keep the post grounded in the current repo's actual work and the existing local Velog archive.
- Prefer continuing an existing series when a clear connection exists. If not, explain why the post should stand alone.
