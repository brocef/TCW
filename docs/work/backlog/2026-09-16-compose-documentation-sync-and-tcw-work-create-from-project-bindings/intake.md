# Compose documentation-sync and tcw-work-create from project bindings

Child 6 of the epic
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Blocked by children 1 and 2. Spec this against what child 2 actually shipped.

## What to deliver

- Convert `skills/documentation-sync/**` and `skills/tcw-work-create/**`,
  including their `references/`, to compose from the procedure mechanism, today's
  text as the default. Child 1's verdict on whether references travel with their
  skill governs how.
- Ledger: `changed:` entries for both skills.

## Constraints

- **`skills/tcw-work-create/references/find-overlap.md` is not converted.**
  Child 1 classified it fixed under Rule 1 (`skills/README.md`): it defines the
  search for existing work and its four overlap relations, a board rule a
  project must not be able to replace. It does not travel with its skill.
  Added 2026-09-16 after child 1 was accepted.
- **The board invariants in `tcw-work-create` stay in the fixed part** — one
  outcome per idea, the overlap search before creating. An override that can
  disable them turns a rule into a suggestion.
- If `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
  has landed, `documentation-sync`'s version-cut path reuses its configuration
  rather than gaining a second one.
- Do not change the marker key (child 1 owns it).

## Acceptance criteria carried from the epic

Epic criteria 8 and 11 for these two skills.

## Origin

Opened by the epic's `implement` stage (plan task 6) on 2026-09-16.
