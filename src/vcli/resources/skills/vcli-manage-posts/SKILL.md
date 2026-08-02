---
name: vcli-manage-posts
description: Safely pull, create, edit, validate, upload images for, and push Velog posts with vcli in an initialized blog workspace. Use for Velog content operations and synchronization through vcli, not when developing the vcli source code.
---

# Manage Velog Posts with vcli

Use `vcli` as a Velog adapter. Keep planning notes, series documentation, and external drafts outside the local `.vcli` store.

## Work in the Local Store

- Find the nearest initialized workspace before acting. Run `vcli init` only when the user wants to initialize the current folder.
- Treat `.vcli/posts/<slug>/content.md` and `.vcli/posts/<slug>/meta.yaml` as the only publishable post sources.
- Do not edit `.vcli/registry.yaml`, `.vcli/uploads.yaml`, or `.vcli/velog-auth.json` by hand.
- Keep `.vcli/` out of version control because it can contain posts and authentication data.

## Follow the Post Workflow

1. Run `vcli status` before meaningful changes.
2. Run `vcli pull` before local editing when remote Velog changes should be mirrored locally.
3. Run `vcli create <slug>` before writing a new post.
4. Edit only the post's `content.md` and `meta.yaml`.
5. Run `vcli status` again and then `vcli check <slug>`.
6. Show the user what will be published and obtain explicit approval before running `vcli push`.
7. Run `vcli push <slug>` for a single post, or interactive `vcli push` when the user requests selection.

Treat `draft`, `modified`, and `synced` as calculated states. Do not introduce or rely on a `ready` state.

## Handle Images Explicitly

- Run `vcli image upload <path> --json` when an agent must parse the uploaded URL.
- Insert the returned Velog CDN URL into `content.md` yourself.
- Do not expect image upload to edit the post.
- Resolve local image references before pushing. Push must remain blocked when unresolved local image references remain.
- Restore a pulled local image reference only when its mapping exists and its hash still matches.

## Preserve Publishing Safety

- Never run `vcli push` without explicit user approval.
- Never use or implement `vcli push --all`.
- Treat push as replacing the remote post with the selected local post, not as a merge.
- If the post was edited on the Velog website, pull before making new local edits.
- Run `vcli doctor` when workspace or authentication health is unclear.
