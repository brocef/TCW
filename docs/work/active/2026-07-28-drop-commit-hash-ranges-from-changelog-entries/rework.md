# Rework: Drop commit hash ranges from changelog entries

Verification accepted the seven shipped tasks — every acceptance criterion was
met and the suite is green. It did **not** accept two of the spec's Non-goals.
The user overrode both at the `verify` gate, so this is a scope expansion, not a
defect: nothing already shipped is wrong, and none of it is reverted.

## What the user changed

**1. The pending changelog's hashes go after all.**

The spec's Non-goals declared "the pending entries in `docs/changelogs/upcoming.md`
keep the hashes they already carry", and AC3 pinned that. The user's decision:
strip every commit hash from the pending changelog — the
`` Commit range: `24f4bc6..0886943`. `` footer that `verify` surfaced **and** all
12 per-entry `` (`hash`) `` suffixes — so the next release ships a changelog
consistent with the rule this item introduces.

The boundary that survives is the released one: `docs/changelogs/v*.md` stay
untouched. Rewriting shipped history is still off the table.

**2. A migration guide is written after all.**

The spec's Risks accepted "no migration note is written" for downstream projects
holding `<changes>` wrappers, on the grounds that the wrappers are inert Markdown
and the removal is announced in the release notes. The user's decision: write one
into `docs/`. The whole repository is the plugin payload — the cache at
`~/.claude/plugins/cache/tcw/tcw/<version>/` contains `docs/` verbatim — so a
guide placed there is readable by every plugin user without any packaging change.

Named `docs/migration-guide-0.15.X-to-0.16.0.md`, per the existing minor-boundary
convention and the user's choice of a minor bump.

## What implementation still has to do

| # | Task |
| --- | --- |
| R1 | Strip every commit hash from `docs/changelogs/upcoming.md`: the `Commit range:` footer line and all 12 per-entry `` (`hash`) `` suffixes. Entry prose otherwise unchanged; no `docs/changelogs/v*.md` opened. |
| R2 | Write `docs/migration-guide-0.15.X-to-0.16.0.md`. Unlike its predecessors it describes a **relaxation** — no user action is required — so it must say that plainly rather than inventing a ritual, and then describe the optional cleanup for anyone who wants their own `<changes>` wrappers gone. |
| R3 | Amend `spec.md`: both overridden Non-goals, the Goals they served, AC1, AC3, and the accepted risk that R2 now mitigates. Add an AC for the guide. |
| R4 | Re-run the full acceptance set and update `outcome.md`. |

## What does not change

- The seven original tasks (`d17ee2c`…`fd84f54`) stand as shipped.
- `docs/changelogs/v*.md` remain untouched — the released-history boundary is the
  one Non-goal verification left intact.
- No `tcw` CLI behavior changes; still prose plus one Python string.

## Notes

- AC1 gets *simpler* under R1, not harder: with the `Commit range:` footer
  deleted, the acceptance grep returns the single hit the spec originally
  predicted (`skills/tcw-post-mortem/SKILL.md:36`). The correction recorded in
  `4b6d70a` describes a state R1 removes, so it is rolled back to the original
  one-hit form with a note explaining why the intermediate state existed.
- AC3 inverts rather than disappears. It was "every `` (`hash`) `` suffix
  survives"; it becomes "none survives, and no released file was opened". The
  criterion still guards the released-history boundary, which is the part
  verification kept.
