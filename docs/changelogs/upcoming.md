# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

- 34438bb..HEAD — Plugin skill/command frontmatter now declares full spec
  metadata. All four axis skills (`tcw-work`, `tcw-taxonomy`, `tcw-capabilities`,
  `tcw-plugin`) gain `allowed-tools`, `when_to_use` (trigger phrases split out of
  `description`), `metadata.author`, and `license: Apache-2.0`; `tcw-plugin` also
  gains `compatibility`. Read-only `tcw` diagnostics are pre-approved everywhere;
  side-effecting `pipx` installs are pre-approved only inside `/tcw-init`
  `/tcw-doctor` (which also carry install `allowed-tools`).
- 34438bb..HEAD — Added `disable-model-invocation: true` to the install and
  destructive commands (`tcw-init`, `tcw-doctor`, `tcw-drive-work-to-completion`,
  `tcw-consolidate-plans`) so the model can no longer auto-invoke them; they stay
  user-invokable slash commands.
- 34438bb..HEAD — `/tcw-drive-work-to-completion` now takes a `<work-item-slug>`
  argument (`argument-hint`) and injects live `tcw work show` state into its
  prompt via `` !`tcw work show $ARGUMENTS 2>/dev/null` `` (gated by its own
  `allowed-tools: Bash(tcw *)`).

## Internal

- 34438bb..HEAD — Renamed each skill's on-demand doc directory
  `skills/*/docs/` → `skills/*/references/` (the spec-named optional directory),
  updating every in-SKILL link plus the `commands/*` and `AGENTS.md` references.
  `tcw-work/SKILL.md` now names its lifecycle leaves (`epic-lifecycle.md`,
  `task-lifecycle.md`) one hop out instead of only through the `lifecycle.md`
  dispatcher. No version-lockstep change (skill `metadata` is author-only, no
  `version`), so `scripts/cut_version.py` and `tests/test_plugin_manifests.py`
  are untouched.
