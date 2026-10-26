---
verdict: accepted
judges: 2
---

# Review round 2 — TCW-117

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-26 in a frozen worktree at `e7a90c4d`, against review round 1's
thirteen findings, over `81ab0df9..e7a90c4d`. Round 1's results carry
forward.

## Checks run

- The full suite as CI runs it, by the dispatching session at `5e5a7643`:
  `2246 passed, 2 skipped` and `5840 passed, 111 skipped`, the web checks
  clean, recorded in `implement/round-2.md`.
- By the reviewer, each finding's behaviour re-run through a guarded wrapper
  in scratch projects (4.0 and one made with 3.0.2), no Jira; the document
  tests `619 passed, 2 skipped`.
- The migration guide's way back run as written on a migrated 3.0.2 project:
  afterwards 3.0.2 `tcw validate` gives 0/0/0, the file list matches the one
  before the run, and no `.tcw` folder is left. `git clean -fd` deletes a
  person's own untracked files; the guide warns of it, says to run
  `git clean -nd` first, and asks for nothing uncommitted before the run.

## Round 1's findings

All thirteen answered. Finding 6 was narrower than round 1 said: a parent's
term is accepted by its whole path or full identifier, and only its leaf slug
is refused (exit 2); the skill now says so.

## Findings, folded in

Three one-line corrections the reviewer found, which belong to this change,
made by the dispatching session in `782f96ab` (the document tests then gave
`1222 passed, 2 skipped`):

1. `skills/configure/references/personal.md:28-30` and `work.md:42-43`
   (round 2's own sentence): a `tcw-version` line in the user-wide file stops
   every command run in a project, not every command (`tcw project new`
   still runs).
2. `docs/guide/configuration.md:83-84` (older, missed by round 1) still said
   the user-wide file "needs no `tcw-version`"; it now says it must not hold
   one.
3. `docs/guide/cli.md:232-235` (made ambiguous by round 2's bullet): a
   listing whose inherited content cannot be read shows its own declarations
   with a warning under the default `--scope own`, and stops with exit 7
   under `--scope up`.

The ledger record `docs/capabilities/taxonomy/add-a-term/description.md:3`
keeps a 3.x wording; it is migrated with the other records at TCW-118.

No finding remains that belongs to this change.

## Needs a separate change

None new; round 1's list stands.
