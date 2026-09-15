# Refined outcome — Refuse local work that no claimed tracker ticket authorizes

## Decision

**Accepted**, on 2026-09-15, by the autonomous session driving the tracker bridge
epic. The user authorised it to make the verify decision in their place, so no user
was asked.

## Evidence

- **Full suite, run the way CI runs it.** Bare `pytest` from `/Users/brian/Projects/TCW`
  on merged `main` (`db3c935f`), with the editable install restored to the primary
  checkout: **3297 passed** in 722 s. `tcw validate` printed `validate OK`, and
  `tcw capabilities check` printed `capabilities OK`.
- **Fixes after verification** (`90cc6e3f`):
  - The capability text now covers what the verifier found missing.
  - Two tests that had existed only as the verifier's one-off scripts are now in the
    repository. One is a discard of a ticket nobody claimed. The other is `sync`
    re-checking an owed claim under strict mode; it goes red when the strict check is
    removed from `deliver`.
  - `tests/test_tracker_strict.py`: 59 passed.
- **Verifier.** The `tcw-verifier` agent found 19 of 21 criteria met and 2 partly met.
  It ran 182 targeted tests and 10 throwaway checks against the fake tracker. It also
  ran the whole of `tests/test_tracker_sync.py` with every node forced to
  `strict: false`, and 68 passed.
  - **Criterion 21** (partly met): the capability text was missing three statements.
    Fixed in `90cc6e3f`.
  - **Criterion 19** (partly met): the file is unedited, and the verifier's forced
    `strict: false` run is the evidence for the "copy of C3's criteria 1–4". The
    repository keeps only `test_strict_false_runs_c3s_start_as_before` plus the
    shared-part tests. This is accepted: running a whole file twice under a patched
    helper would add a test harness, and it would be proving a default that
    `tracker_strict()` already returns.
- **Hands-on, with mutation checks**, both recorded in `outcome.md`: a node pointed at
  an address that cannot resolve. No live Jira was contacted at any point in this
  item.

## Accepted deviations

- **Criterion 16 needed a fix in C3's delivery.** When an item for another part of the
  ticket is present, earlier statuses are expected. This also changes behaviour with
  strict mode off, and only in that case. It fixes a real defect: the last part of a
  shared ticket was reported as conflicting.
- **An epic cannot start with `--worktree` under strict mode.** This came from review.
- **A hold made for a part that is not in this checkout** is not recognised. It is
  documented, and the message names both the possible hold and the fix. A follow-up
  is in `docs/work/inbox/`.
- **The binding-surface item's late review findings** were fixed on this branch
  (`0086d8ae`).

## Review

Two adversarial code review rounds: round 1 NOT DONE, with seven findings accepted or
narrowed; round 2 DONE, with two notes, both fixed. Details are in `outcome.md`
§ Review. The combined review of all the epic's children at the end covers these
files again.

## Capabilities

`work/require-tracker-backed-work` reads `Supported`. `work/open-a-work-item`,
`work/start-a-work-item`, `work/drop-a-work-item`,
`work/manage-external-tracker-intake` and `work/synchronize-external-tracker-work`
describe strict mode. The item's `capabilities.yaml` lists all six.

## Closeout choices

- **Route:** merged into local `main` as `db3c935f`, then
  `tcw work complete --already-integrated`. Nothing pushed.
- **Documentation:** all fired and all written: README, release notes, changelog, the
  `skills/tcw-work` command reference, and the `skills/tcw-configure` tracker
  reference.
- **Version:** none cut. The entries are in `docs/*/upcoming.md`.
- **Follow-ups:**
  - `docs/work/inbox/2026-09-15-a-tracker-hold-leaves-no-evidence-outside-this-checkout.md`
  - `docs/work/inbox/2026-09-15-tracker-commands-classify-an-unreadable-binding-differently-from-show.md`
  - `docs/work/inbox/2026-09-15-strict-tracker-mode-cannot-nest-or-group-children.md`
  - the parked backlog item
    `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
