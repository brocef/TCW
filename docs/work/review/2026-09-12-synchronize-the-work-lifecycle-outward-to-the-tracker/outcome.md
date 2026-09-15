# Outcome — Synchronize the work lifecycle outward to the tracker

## What shipped, task by task

| Plan task | Commit | What |
| --------- | ------ | ---- |
| 1 — fake tracker | `73072332` | `SYNC` workflow, `down`, `install_sites`. |
| 2 — `statuses` | `ada50f26` | `TrackerConfig.statuses`, `_parse_tracker_statuses`, `target_status`. |
| 3 — the record | `39473581` | `Bound.sync`, `WorkItem.tracker.sync`, schema, `with_sync_record`, `unlink` takes it. |
| 4 — site check | `26af6f5b` | `same_site`, `find_binding(base_url=)`, passed by `import` and `link`. |
| 5 — delivery | `e7735dc2` | `tcw/tracker/sync.py`. |
| 6 + 7 — commands and `sync` | `fc33cce6` | `_deliver_after` in `start`/`submit`/`rework`/`complete`; `tcw work tracker sync`; `_local_owner`. One commit, not two: the `sync` half of criterion 4's test needs both. |
| 8 — show, list, web | `4a538581` | `tracker sync:` line, row state, web Ticket field state; client rebuilt. |
| 9 — capabilities | `08612db6` | Five capabilities; `synchronize-external-tracker-work` → Supported. |
| Documentation Sync | `33af7224` | README, release notes, changelog, `tcw-work` command reference, `tcw-configure` tracker reference. |
| Review round 1 fixes | `3a472a49`, `e6e42ff0` | See § Review. |
| Review round 2 fixes | `f19b131a` | See § Review. |
| Follow-ups | `e6e42ff0` | `docs/work/inbox/2026-09-14-follow-ups-the-lifecycle-sync-review-left.md`. |

## Test results

- Full suite, `python -m pytest` in the worktree with the editable install pointed at
  it, after the documentation commit and before review: **3218 passed** in 670 s. The
  full suite after round 2: **3231 passed** in 669 s. Bare `pytest` on merged `main`
  is run at verify.
- `tests/test_tracker_sync.py` 65 passed; all `tests/test_tracker_*.py` 451 passed
  after round 2.
- Web: `pnpm test` 64 passed; `tsc --noEmit` and `pnpm lint` clean; Prettier run on
  the three changed web files.
- Hands-on: a scratch node whose tracker `base-url` is `https://127.0.0.1:9` (nothing
  listening; no live Jira was contacted and no credential exists): `tcw work start`
  on a bound item exited 1 with "moved to active and was committed; HO-1 was not
  updated in the tracker (pending): could not reach the tracker …"; `tcw work list`
  ended the row `| ticket: HO-1 (pending)`; `show` printed the `tracker sync:` line
  ending "the claim is still owed"; `tcw work tracker sync --all` printed the pending
  line and exited 1. That run found the missing full stop before "Run", fixed in
  `e6e42ff0`.

**Mutation checks** — each went red for the named reason, then was restored:

- `find_binding` called without `base_url` → the two-site import test exited 0.
- `active` requirement removed → two config tests.
- *expected* check removed → the drift test on the `EVERYWHERE` workflow (the first
  version of that test used a status offering no route to the target, and stayed
  green under this mutation; rewritten).
- Assignment check removed → nine "never moved" / hand-written binding tests.
- Parts hold removed → the shared-ticket test.
- `sync`'s owner rule removed → the `--all` skip test.
- `_deliver_after` returning 0 for pending → the start-conflict and pending tests.
- Hold skipped for an owed claim → the review's shared-ticket-with-owed-claim test.
- `pending_deletion` check removed from `finish` → both unretained-item tests.
- Round 2: the nearest-status slice, the open-work owed claim, and the
  already-yours shortcut each reverted → their tests.
- **One mutation did not go red:** replacing the empty-`since` fallback with "unknown"
  leaves `test_a_move_recorded_before_the_configuration_was_fixed_is_delivered`
  green, because an unknown expectation also lets that ticket move. The fallback's
  narrowing is pinned directly by
  `test_an_empty_since_on_complete_accepts_only_the_nearest_mapped_status` instead.

## What the plan or spec got wrong

- **The five-subcommand help test had to change.** `tests/test_tracker_help.py`
  pins exactly five `tracker` subcommands; adding `sync` makes six. Edited to six.
- **`deliver_claim` / `deliver_move` became one `deliver`**, with `assess_move` as
  the pure part. `Outcome` has `recorded` and `claimed` rather than `claim_owed`.
  `assess_move` covers steps 4–7; the site check (step 2) stays outside it, so C4
  calls `same_site` and `assess_move` separately.
- **Spec § 5 said `sync` treats an unreadable record as no record and overwrites it.**
  It is checked, never moved (no record means no safe expectation), and the problem
  record is removed only when the check finds the ticket in step.
- **`sync` prints a `held` line** for a part whose ticket another open part holds, and
  counts it as success — the spec listed only current, pending, conflicting, skipped.
- **Six holes in the spec's rules**, found by review (§ Review): an owed claim
  skipping the parts hold; a record with an unknown `since` never clearing; an owed
  claim ignoring where the ticket already was, and claiming for abandoned work;
  clearing a record on an item about to be removed; a staged record blocking a
  worktree merge; `move: auto-delete` in a record. The spec is not rewritten; this
  section and the code's comments are the record.
- **`sync`'s epilog named `--owner`**, which `sync` does not take.
- **Criterion 22 is weaker than it reads**: the fake's error texts never contain the
  token, so the test proves TCW does not print the variable itself, not that a real
  Jira error body would be scrubbed (the client carries up to 500 characters of a
  response body into its messages).

## Review

**Round 1** — `adversarial-code-reviewer` on `477d07e6..33af7224`, NOT DONE. Every
finding reproduced or traced against the code before acting.

| Finding | Decision | Why |
| ------- | -------- | --- |
| An owed claim skips the hold, so one part closes a shared ticket | **Accepted** | Reproduced by a test; the hold now runs first. |
| A record with empty `since` never clears, with a false "moved in the tracker" reason | **Accepted** | Reproduced for `record_unsent` and a discard recorded while down; `since` falls back to where the recorded move started. |
| An owed claim ignores where the ticket is; claims for abandoned work | **Accepted** | Both reproduced; shortcut to current for a finished item whose ticket is closed the same way, and no claim when finished work has no mapping. |
| Clearing a record on an item about to be removed blocks the removal | **Accepted** | Reproduced; `finish` writes nothing to such an item. |
| A staged record blocks `complete`'s worktree merge | **Narrowed** | Reproduced. A hint naming the record and `sync` is printed; the general problem (any staged sidecar, including `link`/`unlink`) is filed as a follow-up. |
| `move: auto-delete` in a record crashes `sync` and `complete` | **Accepted** | The record now refuses it as unusable. |
| Unreadable record in `sync` contradicts spec § 5 | **Accepted, narrowed** | See "What the plan or spec got wrong". |
| `sync` epilog names `--owner` | **Accepted** | Fixed. |
| `MOVE_STATUS_MOVE` fallback unreachable | **Accepted** | Removed. |
| Stale record kept under a hold; `sync --all` exits 1 on it | **Accepted** | `held` now counts as success in `sync`. |
| Two failed moves plus a hand move read as drift | **Deferred** | Filed in the follow-ups note. |
| Unreadable sibling bindings do not hold; unstarted parts do | **Rejected as defects** | Both follow the spec's "open item bound to the same ticket"; an unreadable binding is not known to be bound. |

**Round 2** — the reviewer agent did not answer a second round on C5, so a bounded
Codex review (read-only sandbox, confirmed from its session header) reviewed
`33af7224..3a472a49`, NOT DONE:

| Finding | Decision | Why |
| ------- | -------- | --- |
| An owed claim on an open ticket already at its target and assigned to the caller is retried, which can move it back first | **Accepted** | Test added; now current without a transition. |
| Empty `since` on `complete` accepted both review and active, so a ticket sent back to active could be carried forward | **Accepted** | Only the nearest mapped earlier status. |
| The no-target shortcut cancelled an owed claim for open work | **Accepted** | Only finished work drops an owed claim. |
| The merge hint prints for unrelated merge failures | **Accepted** | Printed only when `tracker.yaml` is staged. |
| `check_only` writes | **No defect** | — |

No third round was run on this item alone; the combined review of C5, C3 and C4 at
the end of the epic covers these files again.

## Autonomous decisions

- **Claim failure at `start`** — Codex: refuse the local start; Opus: start locally
  and record. Chose Opus's (epic identity rule 4; refusal is strict mode's).
- **Mapping** — Codex: event log with target statuses; Opus: status targets with a
  failure-only record. Chose Opus's shape with every named hole closed.
- **Progress links** — both advisors and the spec review: split only if explicit in
  the epic; the review and Codex preferred a child. Created
  `2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket`
  as an `--initiative` child, which keeps the epic open. The team lead was told
  before the plan was committed; no reply had arrived.
- **Site check in `find_binding`** — both advisors: include; the spec review: leave
  it to the inbox note. Included (same helper).
- **Spec review blocking findings** — all five accepted (spec Notes).
