# Refined outcome — Migrate TCW itself to the 1.0.0 lifecycle and write the consumer migration guide

## Decision

**Accepted.** The user accepted the work and directed that a new item be opened
for the defect this one surfaced (see "What verification changed" below).

## What was verified

All thirteen acceptance criteria were run rather than asserted; the results are
in `outcome.md` and are not repeated here. The load-bearing ones:

- `1592 passed, 0 failed` against a `1581 passed` baseline captured before any
  change, with the +11 accounted for exactly (5 new tests, 6 new Markdown files
  hitting an existing per-file parametrization).
- Prompt composition verified programmatically against file contents and offsets,
  not by eye: `spec` resolves builtin → `abstraction.md` → `harness.md`,
  `implement` resolves builtin → `implementation.md` → `harness.md`.
- The `plan` stage gate refuses with 0 bytes on stdout for an item with no spec
  and returns 4508 bytes for one with a spec.
- `when: { tags: [bug] }` selects the bug template and only the bug template.

## What verification changed

The item's most-cited finding — recorded in `outcome.md` and in the shipped guide
as *"a rule another skill reads out of `CLAUDE.md` by name cannot move into a
stage prompt"* — was **misclassified as a limitation.** It is a defect in the
layering, and the user identified it as such on reading the result.

TCW's own shipped prompts are the source of it: `tcw/work/prompts/plan.md:20-21`
and `tcw/work/prompts/implement.md:27-28` both instruct the agent to "evaluate
every Documentation Sync entry in the project's agent guide (`AGENTS.md` or
`CLAUDE.md`)". That is TCW — in the release whose entire point is that TCW tells
you what to do at each stage — delegating to a Markdown-section-scraping
convention instead of to its own configuration.

**This does not invalidate anything that shipped here.** Every criterion still
holds, the guide is accurate for 1.0.0 as tagged, and the `## Documentation Sync`
and `## Versioning` sections genuinely could not move *given the code as it stood*.
What changes is the conclusion drawn from it: the guide currently advises readers
to work around the constraint, and once the constraint is removed that advice
becomes a description of a fixed bug.

Tracked as its own item rather than reworked into this one, per the user's
decision: the work here is finished and correct, and mixing a docs deliverable
with a CLI feature would make both harder to review.

## Follow-on items

| Item | Origin |
| ---- | ------ |
| `2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git` | Found during implementation; `tcw work scaffold` calls `self._stage(p)` at `tcw/store/fs.py:3538`. |
| Documentation-sync polymorphism (opened next) | Found at verification, as described above. Folds into the unpushed v1.0.0. |

## Notes

- The accepted risk named in the spec — that an agent never running
  `tcw work stage` now sees 54 lines of `AGENTS.md` instead of 80 — was put to
  the user and accepted. It is about to shrink further: once documentation-sync
  reads its entries from `tcw-config.yaml`, the `## Documentation Sync` section
  can leave `AGENTS.md` too.
- The spec was reviewed by `codex` only. `bllm-review` returned zero bytes in
  over forty minutes and never completed, so the second reviewer the user's
  standing preference calls for did not run. Recorded in `outcome.md` and
  repeated here because it is a gap in this item's evidence, not a detail.
