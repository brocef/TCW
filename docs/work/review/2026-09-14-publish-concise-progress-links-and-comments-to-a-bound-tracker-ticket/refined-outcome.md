# Refined outcome — Publish concise progress links and comments to a bound tracker ticket

## Decision

**Accepted**, on 2026-09-15, by the autonomous session driving the tracker bridge
epic. The user authorised that session to make the verify decision in their place,
so no user was asked.

## Evidence

- **Full suite, run the way CI runs it.** Bare `pytest` from
  `/Users/brian/Projects/TCW`, with the editable install restored to the primary
  checkout:
  - on merged `main` (`cf7ac9f6`): **3358 passed** in 867 s;
  - after the combined-review fixes (`43374e51`): **3361 passed** in 869 s.

  `tcw validate` printed `validate OK` and `tcw capabilities check` printed
  `capabilities OK`.
- **Web client.**
  - `tsc --noEmit` exits 0.
  - `vitest`: 64 passed.
  - Prettier finds no problem in the two changed web files. `pnpm typecheck`'s
    whole-repository Prettier check reports 804 files, which is unrelated to this
    item.
  - `pnpm check:build` left `tcw/serve/dist` unchanged.
- **Verifier.** The `tcw-verifier` agent found all 18 acceptance criteria met:
  - 327 tests passed across six tracker test files;
  - it added 7 command-line checks of its own for criteria that the committed tests
    prove only by calling functions directly;
  - the capability's final paragraph matches the spec's § Capability text exactly.

  It noted three things:
  - the inheritance test lives in `tests/test_tracker_comment.py`, not in
    `tests/test_tracker_inheritance.py` as the plan said;
  - the release note's upgrade warning is shorter than spec § 1, though the
    configuration reference covers the rest;
  - neither the merge-hint wording nor the wording for a refused (403) comment has a
    test.

  None of these is an acceptance criterion.
- **Hands-on and mutation checks** are recorded in `outcome.md`. No live Jira was
  contacted at any point.

## Review

- **This item's own code review:** two rounds, DONE (`outcome.md` § Review).
- **The combined review of the epic's four children** (binding surface, lifecycle
  sync, strict mode, progress comments) looked only for defects that exist because
  the changes interact. Two rounds, fixes merged as `43374e51`:
  - **Fixed — held record.** A held item's stale `sync` record locked it under strict
    mode with advice that could not help. Round 2 found that the first fix lost a
    finished item's move once its other part was unlinked. The record is now
    cleared only on an open item, and a test goes red without that guard.
  - **Fixed — unusable record.** An unusable record on an item with no mapped status
    survived `sync`.
  - **Fixed — documents.** Documents across the four items contradicted each other or
    the code: the serve refusal wording, the `drop` row, the `--json` and row shapes,
    the changelog's binding shape and its `assess_move` claim, and the read and board
    capabilities.
  - **Filed.** Strict mode does not check the transition before a move; `sync`'s
    owner rule can lock a strict item; a held item with an owed claim stays locked;
    any staged record blocks every worktree merge-back; two more binding readers
    classify unreadable files differently.
    - `docs/work/inbox/2026-09-15-strict-mode-and-sync-follow-ups-from-the-combined-review.md`
    - the widened `docs/work/inbox/2026-09-14-follow-ups-the-lifecycle-sync-review-left.md`
    - the extended `docs/work/inbox/2026-09-15-tracker-commands-classify-an-unreadable-binding-differently-from-show.md`

## Capabilities

`work/synchronize-external-tracker-work` ends with the progress-comment paragraph.
`work/read-a-work-item` and `work/view-the-board` name the comment record; that
change came from the combined review. The item's `capabilities.yaml` lists the one
capability the spec planned.

## Closeout

- **Route.** Merged into local `main` as `cf7ac9f6`, with the combined-review fixes
  as `43374e51`. Then `tcw work complete --already-integrated`. Nothing pushed.
- **Documentation.** README, release notes, changelog, the `skills/tcw-work` command
  reference and the `skills/tcw-configure` tracker reference.
- **Version.** None cut. Entries are in `docs/*/upcoming.md` for the coordinating
  session.
- **Follow-ups.** The three inbox notes above, plus
  `docs/work/inbox/2026-09-15-tracker-client-operations-trust-the-response-shape.md`.
  Nothing about real Jira has been verified: the comment document shape,
  `orderBy=-created`, `author.accountId`, and whether customers can see comments on
  Service Management projects. These are spec Risks 1 and 7, to confirm on first
  real use.
