# unofficial-velog-cli

Agent-first CLI for publishing Velog posts.

## Purpose

- Let agents pull, edit, validate, upload images for, and push Velog posts safely.
- Keep `vcli` as a Velog adapter, not a blog CMS.
- Planning notes, series docs, and external drafts are user-owned outside `vcli`.
- The publish source is the current workspace's local `.vcli` store.

## Local Store

- Run `vcli init` in the folder that owns the Velog workspace.
- Pushable posts live at `.vcli/posts/<slug>/content.md` and `.vcli/posts/<slug>/meta.yaml`.
- `.vcli/registry.yaml` stores only Velog linkage and sync evidence.
- `.vcli/uploads.yaml` stores image upload records.
- Velog auth is local: `.vcli/velog-auth.json`.
- Do not use global `~/.vcli/blog` as a hidden content root.

## Commands

- `vcli init`: create local `.vcli` store.
- `vcli login`: store Velog auth in the current `.vcli`.
- `vcli pull`: pull all Velog posts into `.vcli/posts`.
- `vcli create <slug>`: create a local draft.
- `vcli list`: list posts with calculated status.
- `vcli status`: show `draft`, `modified`, `synced`.
- `vcli check [slug]`: validate files and registry state.
- `vcli doctor`: inspect local store and auth.
- `vcli image upload <path>`: upload one image and print the Velog CDN URL.
- `vcli push`: interactively select draft/modified posts to push.
- `vcli push <slug>`: push one post.

## State Model

State is calculated, not stored.

- `draft`: no `velog_id`.
- `modified`: has `velog_id`, but current file hash differs from `last_synced_hash`.
- `synced`: has `velog_id`, and current file hash equals `last_synced_hash`.

`ready` is not used.

## Agent Workflow

1. Use `vcli pull` when remote Velog should be mirrored locally.
2. Use `vcli create <slug>` before writing a new post.
3. Edit only `.vcli/posts/<slug>/content.md` and `meta.yaml` for publishable content.
4. Run `vcli status` before and after meaningful edits.
5. Run `vcli check [slug]` before pushing.
6. Never run `vcli push` without explicit user approval.
7. Do not use or implement `vcli push --all`.

## Image Workflow

- `vcli image upload <path>` uploads one local image and prints only the URL.
- Use `vcli image upload <path> --json` when an agent must parse the result.
- `vcli image upload` never edits `content.md`.
- Insert the returned URL into `content.md` yourself.
- `push` blocks unresolved local image refs such as `./images/foo.png`.
- `pull` may download remote images into `.vcli/posts/<slug>/images/`.
- Pull image mappings live in `.vcli/posts/<slug>/images/mapping.json` and include hashes when possible.
- `push` restores only mapped local image refs whose hash still matches.

## Skills Policy

- Do not distribute repo-local `.agents/skills`.
- Agents should rely on this `AGENTS.md` and the `vcli` commands only.
