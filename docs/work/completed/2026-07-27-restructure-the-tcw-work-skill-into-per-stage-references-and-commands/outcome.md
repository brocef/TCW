# Outcome

All five tasks shipped. **944 Python tests** (from 873), `tcw validate` OK.

The router is **58 lines**, down from 170. Four documents deleted, twelve
written.

## What shipped

`skills/tcw-work/` is now one document per lifecycle id — seven
`stage-<id>.md` files on a fixed **Purpose / Inputs / Produce / Steps / Exit**
shape, plus `transitions.md`, `hooks.md`, `delegation.md`, `epic-deltas.md`,
`cross-node-deltas.md`, `tags.md`, and `commands.md`. Every step carries an actor
and one of the four enforcement markers.

`lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`, and `process-inbox.md`
are gone. The first two were ~85% identical and had already drifted — the
measured fact that opened this epic.

## The parity test is the deliverable

`tests/test_skill_lifecycle_parity.py`, 71 checks, written **before** the
documents and red at that point. It asserts one document per id and no orphans,
`Produce` and `Inputs` covering what `LIFECYCLE_STEPS` says, five sections in
order, every marker recognized, no ordinals, no reference to a deleted document,
and a router that reaches every reference within its budget.

**Proven to fail on real drift, in both directions**, before being trusted:
renaming `outcome.md` to `results.md` throughout `stage-implement.md`'s `Produce`
turns it red, and removing `initial-request.md` from `stage-plan.md`'s `Inputs`
turns it red. A guard nobody has watched fail is not yet known to be a guard.

It deliberately does **not** claim to check that a step's marker is *correct*.
`LIFECYCLE_STEPS` records gates, not procedures, so there is nothing to compare a
procedure against, and asserting otherwise would be the same dishonesty this
epic exists to remove.

## Four things the work corrected

**The manifests needed no edit.** Both declare directories, so new skills and
commands are picked up automatically. The epic plan listed "plugin manifests list
every new command and skill" as a deliverable; it was wrong about how they work.
The `agents` key *was* new, and is the one manifest change.

**`Produce` could not mean "the one artifact".** Review caught this before
implementation: `verify` writes one of two depending on the verdict, and `inbox`
writes none. Both are named values now, not exceptions bent to fit a rule — and
the test treats "no artifact" as a value it can check.

**The 60-line budget needed a destination table, not willpower.** Every section
displaced from the 170-line router has a named home, written down before the cut.
The first draft came in at 61 lines; the rule is extract, never grow, so the
router lost a paragraph rather than the budget gaining a line.

**Historical documents legitimately name deleted files.** The dangling-reference
check excludes `docs/work/`, `docs/changelogs/`, and `docs/release-notes/`. A
shipped changelog saying "added `lifecycle.md`" is a true statement about v0.6.1,
and rewriting history to keep a grep clean is worse than the grep.

## Manual sign-off, honestly labelled

Two acceptance criteria are **not** test-verified and are not claimed to be:

- **No rule is stated twice.** Reviewed by hand while writing; the destination
  table was the mechanism, since each displaced section moved to exactly one
  place. Reasonable confidence, not proof.
- **Every stage document is followable by a Codex agent** with no injection, no
  custom agents, and no slash commands. Each stage document names
  `tcw work lifecycle --stage <id>` — a command both harnesses run — and
  `--directive` appears only in `hooks.md`, labelled as Claude-only sugar. The
  parity test checks the command *appears*; it cannot check the document is
  followable.

## Notes

**`pr` is now certainly dead.** Child 1 added it; 2a and 2b were each predicted
to consume it and did not; stage documents have no reason to read a field. Child
5 is the last chance, and it will not use it either. **It should be deleted at
epic close** under the same pattern applied to `phase` and `dod`.

`tcw-verifier` cost exactly what the spec allowed: an `agents/` directory and one
manifest key. It did not need the escape hatch.

The `commands.md` and `tags.md` references were not in the epic plan. They fell
out of the destination table — the alternative was keeping a 170-line router or
deleting content that is currently useful, and neither is better.
