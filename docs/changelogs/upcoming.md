# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Internal

- **This repository configures its own work lifecycle.** `tcw-config.yaml` gains
  a `work.lifecycle` block: `prompt:` bindings on `spec`, `plan`, and
  `implement`, each led by `builtin: true` so TCW's shipped instructions are
  composed with rather than replaced; a `when: { tags: [bug] }` spec template
  under `artifacts:`; and two `pre:` checks. Nothing under `tcw/` changes — this
  is the node's own configuration, and the first exercise of the 1.0.0
  configuration surface against a project with real rules.
- **`docs/lifecycle/`** holds the prose those bindings resolve: `abstraction.md`
  (the litmus test and the abstract spine, bound at `spec` and `plan`),
  `harness.md` (Claude/Codex parity, bound at `spec` and `implement`),
  `implementation.md` (the implementation rules, bound at `implement`), and
  `templates/spec.md` + `templates/spec-bug.md`. All moved verbatim out of
  `AGENTS.md`, which drops from 80 lines to 54.
- **`scripts/require_artifact.py`** — the `plan` stage's `pre` check. Reads
  `TCW_SLUG` from the hook environment and asks `tcw work show --json` whether a
  named artifact is present, rather than composing a store path. Not packaged
  (`pyproject.toml` includes `tcw*` only); fails closed on an unset `TCW_SLUG`,
  a missing `tcw`, or unreadable JSON.
- **`tests/test_repo_lifecycle.py`** — five tests over the real repo tree rather
  than a `tmp_path` fixture, since the subject is this node's own configuration.
  The load-bearing one is `test_repo_templates_carry_every_builtin_heading`:
  `artifacts:` is first-match-wins, so a bound template replaces the built-in,
  and nothing else would catch this repo's `spec` template drifting from
  `tcw.work.templates._SPEC` when a future release adds a section.
  `test_the_moved_rules_are_reachable` is what makes deleting the prose from
  `AGENTS.md` safe to commit.
- **Ten references repointed** from `AGENTS.md` to `docs/lifecycle/` —
  `README.md` (2), `tcw/store/base.py` and `tcw/store/fs.py` (module docstrings,
  comment text only), and `docs/plan/` (6). `AGENTS.md` keeps
  `## Documentation Sync` and `## Versioning`, which
  `skills/documentation-sync/SKILL.md` locates by name in `CLAUDE.md` and which
  therefore cannot move into a stage prompt.
- **`docs/migration-guide-0.21.X-to-1.0.0.md`**, linked from
  `docs/release-notes/v1.0.0.md`.
