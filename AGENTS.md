# unofficial-velog-cli development

Develop and maintain the `vcli` source code in this repository. The bundled
`vcli-manage-posts` skill contains the separate workflow for operating a Velog
blog workspace.

## Development setup

- Require Python 3.12 or newer and use uv for environments and locking.
- Run `uv sync --locked --dev` before development.
- Run tests with `uv run --frozen python -m unittest discover -s tests`.
- Keep `uv.lock` synchronized when dependencies change.

## Architecture

- Keep `vcli` a Velog pull/push adapter, not a blog CMS.
- Keep publishable content in each user's local `.vcli/posts` workspace.
- Keep Velog linkage and sync evidence in `.vcli/registry.yaml`.
- Keep authentication local to `.vcli/velog-auth.json` and preserve its atomic,
  owner-only storage behavior.
- Calculate post state from files and registry evidence; do not store a `ready`
  state.

## Safety invariants

- Preserve local changes and remote-deletion evidence during pull reconciliation.
- Never add or implement `vcli push --all`.
- Keep push scoped to explicit post selection and preserve its confirmation.
- Block push when unresolved local image references remain.
- Never commit a real `.vcli` workspace or authentication data.

## Agent skill

- Keep the canonical portable skill at
  `src/vcli/resources/skills/vcli-manage-posts/SKILL.md`.
- Keep only `name` and `description` in shared skill frontmatter.
- Install skills into workspace-local `.agents/skills` and `.claude/skills`;
  never overwrite root `AGENTS.md` or `CLAUDE.md`.
- Treat existing or user-modified skill files as conflicts unless the user passes
  `--force`.
- Include skill resources in built packages and verify them through an isolated
  installation test.

## Change quality

- Add or update tests for behavior changes.
- Run the full test suite and `git diff --check` before handoff.
- Update README and CHANGELOG when commands or user workflows change.
