# Refined outcome: keep a reporter's private project details out of an upstream TCW report

**Accepted.** The user accepted the work after the assessment was presented, and
re-confirmed the closeout route after the branch was rebased onto `main` for the
cloud-session suite fix. Opened as
[#34](https://github.com/brocef/TCW/pull/34), which is the route they chose.

## The evidence the decision rested on

All ten of `spec.md`'s acceptance criteria are met. A read-only pass over the
finished files assessed each one, including the four a grep cannot settle — that
no sentence anywhere in the skill reads as a gate, refusal, approval checkpoint or
redaction; that the delegation suggestion names no Claude-specific mechanism; that
both lists carry the Environment values on the keep side; and that the output
preference is stated as a preference. On the risk the spec named as most likely —
that "generic" would collapse into "vague" — the judgment was that it did not,
because everything a maintainer triages on is on the keep side and the worked
example demonstrates it rather than asserting it.

`python3 -m pytest -q`: **2529 passed, 1 skipped**, exit 0. The skip is the
scaffold test `main` now skips by design under uid 0. `tcw validate` and
`tcw capabilities check` both exit 0.

That same pass found four inaccuracies in this item's _recorded prose_ rather than
in the skill, and all four were corrected before acceptance rather than waived: a
claim that Prettier passed on every file touched, which was false for the one file
edited but not added; a commit count that named the task commits rather than the
branch; three different numbers for the worked example's length, one of which had
reached the changelog; and a garbled sentence in the section carrying the
guidance-not-a-gate point. It also found that the keep list had dropped the word
the spec chose deliberately — "message **template**" — which invited pasting a
message with an identifying path still inside it, the exact thing the example
swaps. That is now "the fixed part of its message".

## Capability ledger

Reconciled. `plugin/report-an-issue-upstream` reads `Supported`, carries this
item's slug as its `Planning doc`, and is the single entry under `new:` in the
item's `capabilities.yaml`. `tcw capabilities drift` reports none. No capability
was changed or removed.

## Closeout choices

- **Version: unchanged at 2.0.2.** The entries in `docs/changelogs/upcoming.md`
  and `docs/release-notes/upcoming.md` wait there for the next cut. v2.0.2 is
  published on `origin`, so folding this work into it was never an option; the
  user chose to keep the current version rather than cut a third patch for a
  documentation change. **This is the `version offered` criterion, discharged by
  offering rather than by cutting.**
- **Documentation: synced.** Three entries fired — the changelog, the release
  notes, and `skills/<component>/SKILL.md` by way of `tcw-plugin`'s router bullet.
  `README.md` was re-read and deliberately left alone; its `tcw-report` row
  describes where a report goes, which this change does not alter.
- **Originating GitHub issue: none.** `initial-request.md` records the item as
  filed from chat, so the criterion does not apply and nothing is deferred under
  it.
- **Follow-ups: none filed.** See below for the one thing found and not fixed,
  and why it is not an item yet.

## Deferred, with what it is blocked on

**The repository does not satisfy its own Prettier check, and nobody has decided
whether it should.** `pnpm prettier --check .` on `main` reports drift in
`AGENTS.md` and roughly twenty files under `docs/capabilities/`, all of it
predating this item. The one such file this item edits, `skills/tcw-plugin/SKILL.md`,
had the reformatting Prettier wanted on its unrelated lines reverted, so the diff
carries only the router clause.

It is not filed as a work item because the repair is not the hard part — a
whole-repo `prettier --write` is minutes. The open question is whether
`prettify:check` should gate CI at all, which is the user's call and the thing a
work item would be blocked on. Filing it without that answer would produce an
item whose spec stage cannot start.

## Notes

- The branch was rebased twice while in flight, which invalidated the commit
  hashes `outcome.md` cited. They were repointed at the commits that exist; a
  further rebase before the pull request merges would invalidate them again, and
  the table is the only place they appear.
- The first pytest run reported four failures, all environmental. `main`'s
  cloud-session suite item fixed three at their seams and skipped the fourth under
  root while this item was in review, which is why the record carries both
  results. The fourth needed this session's setuptools raised by hand, the way the
  provisioner now does at start-up, because it provisioned before that change
  landed.
