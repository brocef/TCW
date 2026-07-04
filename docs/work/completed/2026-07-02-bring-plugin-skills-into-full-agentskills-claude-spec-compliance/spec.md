# Spec — bring plugin skills into full spec compliance

## Capability changes

**None.** Applied the product-first check: no new Vocabulary term, no new/changed
taxonomy Feature, no new user-facing capability of the `tcw` CLI or plugin. These
are frontmatter/metadata and authoring-quality changes to the skill/command
files. The one adjacent user-visible effect — a fresh plugin install runs `tcw`
without a per-command permission prompt — is friction reduction on an existing
capability, not a ledger entry. The tcw-capabilities gate is therefore skipped.

## Problem

Two spec audits (agentskills.io, code.claude.com/docs/en/skills.md) found the four
plugin skills (`tcw-work`, `tcw-taxonomy`, `tcw-capabilities`, `tcw-plugin`) have
**zero hard violations** but underutilize the spec: no `allowed-tools`, no
`metadata`, no `compatibility`/`license`, a two-hop reference chain, `docs/`
instead of the spec-named `references/`, and no use of `disable-model-invocation`
or command-layer dynamic context injection. The headline gap (`allowed-tools`) is
a **portability defect**: the friction-free `tcw` behavior on the author's machine
comes from machine-local `.claude/settings*.json` allowlisting that does not ship
with the plugin, so every fresh install prompts on each command.

## Goals

1. Add `allowed-tools` to all four skills (+ install commands) so a fresh install
   runs `tcw` without per-command prompts.
2. Flatten reference chains to one level (or document the two-hop as intentional).
3. Add `disable-model-invocation: true` to side-effecting/destructive commands.
4. Rename `skills/*/docs/` → `skills/*/references/` with all links updated.
5. Add `metadata` (`version` + `author`) to each skill, kept in lockstep.
6. Add `compatibility` to `tcw-plugin` (Python 3.11+, pipx).
7. Split trigger phrases into `when_to_use` on each skill.
8. Add `license: Apache-2.0` to each skill.
9. Add command-layer dynamic context injection where arg[0] is reliably a slug.

## Non-goals

- No change to `tcw` runtime code, CLI surface, or behavior.
- No new user capability; no taxonomy/capabilities edits.
- No `scripts/`/`assets/` skill bundling (skills stay thin CLI routers).
- No `paths` scoping (would narrow router triggering — see audit).

## Current-state findings

- **Working permission syntax** is `Bash(tcw *)` (space + glob) — confirmed in
  `~/.claude/settings.json:78` and matching Claude's own `Bash(python3 *)`
  docs example. agentskills' `Bash(git:*)` colon form is a different convention;
  Claude Code (primary consumer) parses the space form. **Decision: space form.**
- **Version lockstep** is enforced by `tests/test_plugin_manifests.py`
  (`test_five_version_fields_agree` asserts `len(set(...)) == 1` over 5 files) and
  driven by `scripts/cut_version.py` `VERSION_FILES` (file→regex map). Adding skill
  `version` means 4 new `VERSION_FILES` entries + extending the test. There is also
  `test_agents_marketplace_carries_no_version` guarding a deliberate no-version file
  — the pattern for "keep the guarded set honest" already exists.
- **Commands are model-invocable skills.** `commands/*.md` surface as `tcw:*`
  skills (e.g. `tcw:tcw-init`, `tcw:tcw-drive-work-to-completion`). Current
  frontmatter is `description`-only (`commands/tcw-init.md:1-3`,
  `commands/tcw-drive-work-to-completion.md:1-3`). These are the auto-invocable
  entry points to installs (`docs/setup.md` runs `pipx install` /
  `python3 -m pip install --user`; `docs/doctor.md` runs `pipx install --force`)
  and to full implementation runs.
- **`tcw-plugin` install commands invoke:** `pipx install`, `pipx ensurepath`,
  `pipx list --json`, `python3 -m pip install --user`, `python3 -c`,
  `command -v`, `sort -V` (`skills/tcw-plugin/docs/{setup,doctor}.md`).
- **Reference chains:** `tcw-work/SKILL.md → references/lifecycle.md →
  {task,epic}-lifecycle.md` (two hops) + `decompose.md ↔ cross-node-epic.md`
  lateral links. Other three skills are single-hop already.
- **`docs/` vs repo-level `docs/`:** the skill-local `skills/*/docs/` trees are
  entirely separate from the repo-level `docs/` (work/, changelogs/,
  release-notes/). Only the skill-local trees rename.

## Proposed behavior

### `allowed-tools` (proposed per-surface; space+glob form)

| Surface | allowed-tools |
|---|---|
| `tcw-work` | `Bash(tcw *) Bash(git *) Read Edit Write` |
| `tcw-taxonomy` | `Bash(tcw *) Read Grep Glob` |
| `tcw-capabilities` | `Bash(tcw *) Read Grep Glob` |
| `tcw-plugin` (orientation) | `Bash(tcw *) Bash(command -v *) Bash(pipx list *) Read` — **diagnostics only, no install pre-approval** |
| `commands/tcw-init.md` | `Bash(tcw *) Bash(command -v *) Bash(pipx *) Bash(python3 *)` |
| `commands/tcw-doctor.md` | `Bash(tcw *) Bash(command -v *) Bash(pipx *) Bash(python3 *)` |

Rationale: read-only diagnostics are pre-approved everywhere; the side-effecting
`pipx install` is pre-approved **only** inside the deliberately user-invoked
`/tcw-init` `/tcw-doctor` commands (which also get `disable-model-invocation`), so
an autonomous `pipx install` is never *pre-approved* — the model can still reach
the install path via the orientation skill, but the user gets a permission prompt
before it runs. `allowed-tools` only *pre-approves* — it does not restrict, and
for plugin skills it takes effect after the workspace-trust dialog.

### `disable-model-invocation: true` (proposed set)

- **Install/destructive (default yes):** `tcw-init`, `tcw-doctor` (installs);
  `tcw-drive-work-to-completion` (autonomous implementation + commits);
  `tcw-consolidate-plans` (has `--apply`/`--delete` that remove files).
- **Leave model-invocable:** `tcw-plan-work`, `tcw-audit-work-backlog` (read-only),
  `tcw-taxonomy-init`, `tcw-capabilities-init` (interactive bootstrap, no
  destructive default), and the four axis skills (routers must auto-load).

### Reference-chain flattening

`tcw-work/SKILL.md` links `lifecycle.md` (a thin dispatcher). Preferred fix: keep
`lifecycle.md` but have `SKILL.md` also name `task-lifecycle.md`/`epic-lifecycle.md`
directly with their gate conditions, so a SKILL.md reader sees all leaves one hop
out. Accept the `decompose.md ↔ cross-node-epic.md` lateral links (peers, not a
chain). Low priority relative to the rest.

### `metadata`, `compatibility`, `when_to_use`, `license`

- `metadata: { author: "<author>" }` on all four skills. **No `version`**
  (decision: author-only — Claude Code ignores `metadata` and adding `version`
  would grow the release lockstep for zero Claude-side benefit).
- `compatibility` on `tcw-plugin`: "Requires Python 3.11+; installs the tcw CLI
  via pipx from the plugin clone."
- `when_to_use`: move the trigger-phrase enumeration out of each `description`
  into `when_to_use` (same 1,536-char combined cap); keep the "what it is"
  sentence, key use case first, in `description`.
- `license: Apache-2.0` on all four skills (matches repo `LICENSE`).

### Dynamic context injection (command layer only)

Apply `` !`tcw work show $ARGUMENTS 2>/dev/null` `` (all-args token, verified in
the Phase 0 spike) only where arg[0] is reliably a work-item slug:
**`tcw-drive-work-to-completion`** (add `argument-hint: <work-item-slug>`).
**Skip `tcw-plan-work`** — its arg is a slug *or* free chat text, so injecting a
`tcw work show` on chat input is meaningless. Never inject in the always-on router
skills (would run `tcw` on every auto-load).

## Acceptance criteria

- All four `SKILL.md` carry `allowed-tools`, `metadata.author`, `when_to_use`,
  `license`; `tcw-plugin` also carries `compatibility`. (No skill `version`.)
- `tcw-init`, `tcw-doctor` carry install `allowed-tools`; the agreed
  disable-model-invocation set carries `disable-model-invocation: true`.
- `skills/*/docs/` renamed to `references/`; **no dangling links** — the scoped
  grep gates (relative `](docs/` links + live-surface paths) return nothing.
- `scripts/cut_version.py` and `test_plugin_manifests.py` are **untouched**
  (author-only metadata ⇒ no version lockstep growth).
- `tcw-work/SKILL.md` names its lifecycle leaves one hop out (or documents the
  two-hop as intentional).
- `tcw-drive-work-to-completion` injects live item state via arg[0].
- Full test suite green (`pytest`); `tcw --version` still resolves.

## Risks & dependencies

- **Rename breaks links** → mitigated by the grep verification gate.
- **Version set grows** → 4 new lockstep sources; mitigated by automating in
  `cut_version.py` + test. Fallback: ship `author` only, drop `version`.
- **Dynamic-injection syntax** unverified against this harness → plan includes a
  verification step; feature is isolated to one command, low blast radius.
- **allowed-tools cross-host** — Codex may not honor the field; it degrades to
  today's prompting behavior (no regression).

## Decisions (resolved with user, 2026-07-02)

1. **allowed-tools install posture:** pre-approve `pipx`/`python` installs **only**
   inside `/tcw-init` `/tcw-doctor`; read-only `tcw` diagnostics pre-approved
   everywhere. If the model reaches an install via the orientation skill, the user
   still gets a prompt.
2. **disable-model-invocation set:** `tcw-init`, `tcw-doctor`,
   `tcw-drive-work-to-completion`, `tcw-consolidate-plans` (installs + destructive).
3. **metadata:** **author-only** — add `metadata.author`; do **not** add `version`
   (Claude Code ignores it; not worth growing the release lockstep). `compatibility`
   (tcw-plugin) and `license: Apache-2.0` are still included.
