# Plan — bring plugin skills into full spec compliance

Depends on three user decisions in `spec.md` "Open decisions". Defaults below
assume: installs pre-approved only in `/tcw-init` `/tcw-doctor`; the proposed
disable-model-invocation set; `metadata.version` wired into lockstep.

## Phase 0 — Verify dynamic-injection syntax (spike, do first)

Confirm the harness's command arg-substitution + bash-injection syntax before
Phase 4 relies on it. **Lead with `$ARGUMENTS`** (all-args token, unambiguously
supported) rather than a positional token — positional indexing is easy to get
off-by-one (`$0` vs `$1` for "first arg", version-dependent) and a single-slug
command only needs `$ARGUMENTS`. Create a throwaway command with `argument-hint`
and `` !`tcw work show $ARGUMENTS` ``; run it with a real slug; confirm the item
shows inline. Record the working form; if injection doesn't work at all, drop
Phase 4 (isolated, non-blocking).

## Phase 1 — Frontmatter additions (parallel across the 4 skills)

Per-skill edits to `skills/<name>/SKILL.md` frontmatter. Independent files → the
four can be done in parallel.

- **All four:** add `allowed-tools` (spec table), `metadata: {author}` (author-only
  per decision — **no `version`**), `when_to_use` (move trigger phrases out of
  `description`), `license: Apache-2.0`.
- **`tcw-plugin` only:** also add `compatibility` (Python 3.11+, pipx).
- Touch points: `skills/tcw-work/SKILL.md`, `skills/tcw-taxonomy/SKILL.md`,
  `skills/tcw-capabilities/SKILL.md`, `skills/tcw-plugin/SKILL.md`.
- Verify: `python -c "import yaml,glob; [yaml.safe_load(open(f).read().split('---')[1]) for f in glob.glob('skills/*/SKILL.md')]"` parses all frontmatter.

## Phase 2 — Command frontmatter (parallel; independent of Phase 1)

- Add install `allowed-tools` to `commands/tcw-init.md`, `commands/tcw-doctor.md`.
- Add `disable-model-invocation: true` to the agreed set: `commands/tcw-init.md`,
  `commands/tcw-doctor.md`, `commands/tcw-drive-work-to-completion.md`,
  `commands/tcw-consolidate-plans.md`.
- Verify: frontmatter parses (same yaml check over `commands/*.md`).

## Phase 3 — Rename `docs/` → `references/` (parallel across skills; do after Phase 1's SKILL.md edits land to avoid churn)

- `git mv skills/<name>/docs skills/<name>/references` for each of the four skills.
- Update every **relative** in-file link `](docs/…)` → `](references/…)` in each
  `SKILL.md` (they are relative — e.g. `skills/tcw-work/SKILL.md:21` is
  `](docs/lifecycle.md)`, no `skills/` prefix) **and** in the moved docs'
  cross-links (`references/lifecycle.md → {task,epic}-lifecycle.md`,
  `references/decompose.md ↔ cross-node-epic.md`).
- **Full set of live files that hardcode the old `skills/*/docs/` path** — all must
  be updated or the `/tcw-*` command breaks at runtime:
  - `commands/tcw-init.md:5` → setup.md
  - `commands/tcw-doctor.md:5` → doctor.md
  - `commands/tcw-taxonomy-init.md:5` → taxonomy `init.md`
  - `commands/tcw-capabilities-init.md:5` → capabilities `init.md`
  - `commands/tcw-plan-work.md:5` and `commands/tcw-drive-work-to-completion.md:5`
    → lifecycle.md
  - `AGENTS.md:43` skill-authoring note (**`CLAUDE.md` is a symlink to `AGENTS.md`
    — edit `AGENTS.md`**)
  - `.claude-plugin/`/`.codex-plugin/` manifests hardcode **no** skill-doc paths
    (verified) — nothing to change there.
- **Verification gate (acceptance criterion), scoped to live surfaces only:**
  - `grep -rn "](docs/" skills/` → empty (catches the *relative* SKILL.md/doc
    links that actually dangle after the move — the whole-repo `skills/*/docs/`
    grep misses these).
  - `grep -rn "skills/[^ ]*/docs/" skills commands AGENTS.md tests .claude-plugin .codex-plugin`
    → empty. **Do NOT grep the whole repo:** `docs/work/completed/**`,
    `docs/changelogs/v*.md`, and this item's own spec/plan/initial-request are
    frozen archive that legitimately mention the old path and must not be edited.

## Phase 4 — Dynamic context injection (depends on Phase 0)

- `commands/tcw-drive-work-to-completion.md`: add `argument-hint: <work-item-slug>`
  and the verified injection line (`` !`tcw work show $ARGUMENTS 2>/dev/null` `` —
  the `2>/dev/null` so a mistyped slug injects nothing rather than a shell error)
  so the live item state renders into the prompt.
- Skip `tcw-plan-work` (arg may be free chat text).
- Verify: run the command with a real slug; item state appears inline.

## Phase 5 — Version lockstep wiring — **DROPPED** (decision: author-only metadata)

Skill `metadata` carries no `version`, so `scripts/cut_version.py` and
`tests/test_plugin_manifests.py` are untouched. No action. (Retained as a heading
so the phase numbering in the parallelization summary still reads cleanly.)

## Phase 6 — Documentation sync (triggers expected to fire)

- **`skills/*/SKILL.md` [Skill-Driven-Component]** — this item *is* the change; no
  separate driving-skill doc to sync beyond the edits themselves.
- **`AGENTS.md`** (**`CLAUDE.md` is a symlink to it — edit `AGENTS.md`**) — update
  the "Versioning" section if the guarded file count goes 5→9; update the
  skill-authoring note (`AGENTS.md:43`, `docs/` → `references/`) if that convention
  is now house style; note the new `allowed-tools`/`disable-model-invocation`
  conventions.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — add an entry (Changed:
  skill frontmatter now declares allowed-tools/metadata/etc.; Internal: version
  lockstep now covers skill files) with the commit hash range.
- **`docs/release-notes/upcoming.md` [Public-API]** — one plain-language line only
  if the reduced-permission-prompt effect is worth surfacing to users; otherwise
  skip (no user-facing behavior change).
- **`README.md`** — no change expected (CLI surface unchanged); confirm during
  documentation-sync.
- Run the `skill-cefailures:documentation-sync` skill before completion.

## Parallelization summary

- **Phase 0** first (unblocks Phase 4).
- **Phases 1 and 2** independent, fully parallel.
- **Phase 3** after Phase 1 (avoids editing SKILL.md twice); internally parallel per skill.
- **Phase 4** after Phase 0.
- **Phase 5** dropped (author-only metadata — no version wiring).
- **Phase 6** last.

## Verification commands (final gate)

- `pytest -q` (full suite green, incl. `test_plugin_manifests.py`).
- `grep -rn "skills/[^ ]*/docs/" . --include=*.md --include=*.json` → empty.
- Frontmatter YAML parses for all `skills/*/SKILL.md` and `commands/*.md`.
- `tcw --version` resolves.
- Manual: fresh-install smoke (optional) — confirm `tcw` runs without a per-command
  prompt when the plugin's `allowed-tools` are honored.

## Out of scope / deferred

- Renaming `docs/` → `references/` is cosmetic; if it risks churn it can be split
  to a follow-up item without blocking the higher-value frontmatter work.
- `metadata.version` dropped: author-only per decision 3 (Phase 5 removed).
