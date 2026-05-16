# unofficial-velog-cli

AI-first CLI for managing Velog posts through a local `.vcli` store.

## Purpose

- Remove copy/paste work when AI agents write Velog posts.
- Keep `vcli` focused as a Velog pull/push adapter, not a blog CMS.
- Let users manage planning notes, series folders, and external drafts outside `vcli`.
- Treat `.vcli/posts/<slug>` as the only local publish target.

## Local Store

- Run `vcli init` in the folder that should own the local Velog store.
- Actual post files live in `.vcli/posts/<slug>/content.md` and `.vcli/posts/<slug>/meta.yaml`.
- `.vcli/registry.yaml` stores Velog linkage and sync evidence only.
- Velog auth is stored in the current local store at `.vcli/velog-auth.json`.
- Do not use `~/.vcli/blog` as a hidden default content root.

## Supported Commands

| Command | Meaning |
|--------|------|
| `vcli init` | Create a local `.vcli` store |
| `vcli login` | Store Velog auth |
| `vcli pull` | Pull Velog posts into `.vcli/posts` |
| `vcli create <slug>` | Create a local draft under `.vcli/posts` |
| `vcli list` | Show local posts with calculated state |
| `vcli status` | Show `draft`, `modified`, and `synced` states |
| `vcli check [slug]` | Validate post files and registry state |
| `vcli doctor` | Inspect local `.vcli` and auth state |
| `vcli push` | Select draft/modified posts and push them to Velog |
| `vcli push <slug>` | Push one post to Velog |

## State Model

State is calculated, not stored.

- `draft`: no `velog_id`.
- `modified`: has `velog_id`, but current file hash differs from `last_synced_hash`.
- `synced`: has `velog_id`, and current file hash equals `last_synced_hash`.

`ready` and `published` are not lifecycle states in the new model.

## Agent Rules

- Use `vcli create` before writing a new Velog draft.
- Use `vcli pull` when the Velog remote should become the local source.
- Check `vcli status` before and after meaningful edits.
- Never run `vcli push` without explicit user approval.
- Do not use bulk push. `vcli push --all` is intentionally unsupported.
- `pull` must not overwrite locally `modified` posts.
