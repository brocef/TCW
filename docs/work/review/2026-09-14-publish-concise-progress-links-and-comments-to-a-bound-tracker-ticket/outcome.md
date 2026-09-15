# Outcome — Publish concise progress links and comments to a bound tracker ticket

## What shipped, task by task

| Plan task | Commit | What |
| --------- | ------ | ---- |
| 1 — configuration | `07645f83` | Adds `work.tracker.comments` and `link`, plus `TrackerConfig.comments`/`link`, `_parse_tracker_link` and `link_for`. |
| 2 — client and fake | `71715fa6` | Adds `JiraClient.add_comment` and `recent_comments`, plus `_document_text`. The fake tracker stores comments. Both operations are covered by the timeout test. |
| 3 — the record | `6e489928` | Adds the `comment` key in `tracker.yaml`: `Bound.comment`, `_comment_record`, the closed schema, `with_comment_record`, and carrying it into `unlink`. The web type and its fixture follow. |
| 4 — publishing | `7ad926e8` | Adds `tcw/tracker/progress.py`: `publish`, `retry`, `hold`. |
| 5 — wiring | `d4956cfb` | `_deliver_after` returns 0/1/2. `tracker sync` visits items that owe comments. Adds the `show` line, the row note and the merge hint. |
| 6 — capability | `3414e0ed` | Updates `work/synchronize-external-tracker-work`. |
| Documentation Sync | `86fe7789` | README, release notes, changelog, the `tcw-work` command reference, and the `tcw-configure` tracker reference. `skills/tcw-work/SKILL.md` was checked: it names no tracker behaviour, so it is unchanged. |
| Review round 1 fixes | `a1a02908` | See § Review. |
| Review round 2 fixes | `659e7997` | See § Review. |

## Test results

- **Full suite.** `pytest` in the worktree, with the editable install pointed at it, after the documentation commit: **3350 passed** in 865 s. Bare `pytest` on merged `main` runs at verify.
- **After both rounds of fixes.** `tests/test_tracker_comment.py`: 54 passed.
- **Unedited sibling tests.** `tests/test_tracker_sync.py` and `tests/test_tracker_strict.py` are unedited and pass (criterion 1).
- **Hands-on check.** I used a scratch node with `comments: true`, a `link`, and `base-url` set to `https://tcw-strict-check.invalid`, a name that cannot resolve. No tracker was reached, and the credentials were made-up values.
  - `tcw validate` printed OK.
  - `start` on a hand-bound item exited 1 with the pending status message.
  - `show` printed both `tracker sync: pending after start …` and `tracker comment: pending after start …`.
  - The board row ended `ticket: X-1 (pending, comment pending)`.
  - `tracker sync` printed the pending status and "comment still owed", then exited 1.
  - The token appeared in no file.

**Mutation checks.** Each of these went red for the reason named, then was restored:

| Broken | Test that went red |
| ------ | ------------------ |
| No check of link placeholders, or a format spec allowed | `test_a_bad_comment_setting_is_a_problem` (unknown, positional, format-spec, conversion, nested) |
| `retry` never looks for the marker first | `test_a_post_that_landed_without_an_answer_is_not_repeated` |
| A marker from any author counts | `test_the_marker_in_another_accounts_comment_does_not_count` |
| No assignee check | `test_a_ticket_that_is_not_yours_gets_no_comment_and_no_record`, `test_a_retry_on_a_ticket_no_longer_yours_drops_the_comment` |
| A failed status step is ignored, in `publish` or in `_deliver_after` | `test_a_status_that_did_not_follow_owes_the_comment`, `test_a_reassigned_ticket_owes_both_until_it_comes_back` |
| Event ids without the random part | `test_every_move_has_its_words_and_its_own_event` |
| No part clause | `test_a_discard_names_its_resolution_and_a_part_is_named` |
| A comment-only item runs the check-only status step | `test_a_comment_that_did_not_post_is_owed_and_synced_after_the_ticket_moved_on` |
| Auto-delete keeps an item whose comment failed | `test_a_lost_comment_does_not_keep_an_unretained_item` |
| `--all` ignores comment records | the moved-on test and `test_sync_drops_an_owed_comment_once_comments_are_off` |
| `hold` does nothing; comments off not retried; a lost comment's message says to run sync | the three round 1 tests |

## What the plan or spec got wrong

- **The plan said `_deliver_after` returns a tuple.** Every caller already used its value as an exit code. So it returns 0, 1 (status failed) or 2 (only the comment failed), and callers exit `min(delivered, 1)`. The plan was corrected in `a1a02908`.
- **The spec's link validation missed format specs and conversions.** `{slug:d}` and `{slug!r}` passed `tcw validate`, then failed or rendered wrongly when a comment was posted. Found in review and fixed.
- **The spec's first version had four contradictions**, which the spec review caught before planning (see spec § Notes): the assignee-versus-status order; a child node unable to turn comments off; comment debt that could never clear; and event ids that could collide within one second.
- **The spec said a comment on a binding from another site simply does not go.** For an owed comment, `sync` then reported success for ever. It now reports conflicting.

## Review

Two rounds by the `adversarial-code-reviewer` agent. I checked each finding against the code.

**Round 1 (DONE, with fixes to make).**

1. *`{slug:d}`, `{slug!r}`, nested specs and spaces pass validation and break at post time.* **Accepted.**
2. *A comment that fails on an item being auto-deleted tells the user to run a sync that cannot find the item.* **Accepted.** The message now says the comment cannot be retried.
3. *A comment owed on a binding from another site never clears, and `sync` exits 0.* **Accepted.** It now reports conflicting.
4. *With comments off and the status step still failing, `hold` rewrote the record instead of removing it.* **Accepted.**
5. *`hold` and the CLI path for a malformed record had no tests.* **Accepted.** Tests added.

- Plan drift on the return value: **accepted**, and the plan is fixed.
- Duplicated timestamp code: **accepted**; `_now` is reused.
- Response-shape trust in client operations: **filed** as `docs/work/inbox/2026-09-15-tracker-client-operations-trust-the-response-shape.md`. It affects every operation, not just this item's.

**Round 2 (DONE).** All five fixes confirmed, with no new defects; the reviewer ran 327 tests across six tracker test files. Two non-blocking notes, both **accepted** and fixed in `659e7997`:

- a comment owed on a binding from another site now rewrites its record as conflicting, so `show` agrees with `sync`;
- the test now checks that `sync` exits 1.

Nothing new needed a separate change.

## Autonomous decisions

- **Build this item instead of discarding it.** This was the team lead's direction.
- **Opt-in, one link template, no `{branch}`.** Codex and Opus agreed. `{branch}` was dropped on Opus's finding that the branch does not exist yet when `start` delivers.
- **Event ids that differ for repeated moves.** Codex. They are random rather than time-based after the spec review.
- **Look for the marker only on retries, and count only the account's own comments.** Opus.
- **A separate `comment` record, not a field in `sync`.** Opus, because a `sync` record would lock the item under strict mode. Codex would have let strict mode gate on it; I did not take that, because a missing note authorizes nothing.
- **One owed comment, replaced by later moves (coalescing).** Opus. Codex preferred a queue, or else stating coalescing plainly; the spec and capability state it.
- **A v3 document, not v2 wiki markup.** Opus.
- **No stop.** Both advisors said nothing here is hard to undo, provided duplicate avoidance is bounded and that bound is stated.
