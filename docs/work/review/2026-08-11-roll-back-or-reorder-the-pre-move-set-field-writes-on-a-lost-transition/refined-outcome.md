# Refined outcome — Roll back or reorder the pre-move set_field writes on a lost transition

## Decision

**Accepted** by the user on 2026-08-13, on the assessment presented at `review`.
Resolution: `done`.

## Evidence

All eleven acceptance criteria met.

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | A lost `complete` leaves `resolution` untouched; the pinned test inverted, not deleted | `test_lost_complete_leaves_its_resolution_written` now asserts `resolution is None` |
| 2 | A lost `submit` leaves `owner`/`started` | `test_lost_submit_leaves_the_claim_intact` |
| 3 | A winning transition still writes its fields | `test_a_transition_that_wins_still_writes_its_fields` |
| 4 | The field write is inside the transition commit | `test_the_transition_commit_carries_the_field_write`; `test_every_transition_commits_its_own_move` unmodified |
| 5 | Hook guarantee preserved, comments corrected | `test_a_failing_pre_hook_writes_no_field` unmodified; `cli.py` comments rewritten |
| 6 | `_status_resolution_problems` docstring corrected | `grep "no code path can produce" tcw/` empty |
| 7 | Five read-back sites raise `ValueError` | five store-level tests + one for `create`'s `.item` |
| 8 | `tcw work new` exit 1 / no traceback; `POST /api/work` 422 | `test_cli_new_reports_a_lost_read_back_without_a_traceback`, `test_create_read_back_lost_is_not_a_500` |
| 9 | No `set_field` on a path reaching a transition | read, not grepped — `base.py`'s remaining take-over write returns before the transition |
| 10 | A refused stage after the move is `TransitionCommitError` | `test_a_refused_stage_after_the_move_is_a_transition_commit_error` |
| 11 | Full suite green | `pytest -q` 1294 passed (1285 before) |

Dogfooded end to end: this item's own `→ review` commit (`e438a68`) carries its
`state.yaml` with `owner`/`started` blanked, and the working tree was clean after
it. `tcw validate` OK.

## Capabilities

No ledger delta, as the spec predicted. `work/complete-a-work-item`,
`work/discard-a-work-item`, `work/submit-a-work-item-for-review`,
`work/rework-a-reviewed-work-item` and `work/open-a-work-item` all keep their
wording and their `Supported` status; the one unconditional promise checked at
spec time (`open-a-work-item` prints the generated slug) is preserved by the
error naming the ref.

## Deferred

Nothing carried forward. Two adjacent things were named as chosen exclusions and
stay excluded, with reasons recorded in the spec's Non-goals: `update_work`'s
write-then-re-parent ordering, and the absence of a claiming protocol for
`submit`/`rework`/`complete`.

The honest residual, unchanged from the spec: a process killed between a
successful move and its field write still leaves a resolved item with no
resolution. It is narrower than what it replaced, it lands on an item the process
owns, and `tcw validate` reports it.

## Closeout

- No post-mortem. Verification surfaced nothing unforeseen — the targeted review
  ran before implementation and its findings were folded into the spec and plan
  rather than discovered late.
- Version cut: offered to the user separately; not part of this item.
