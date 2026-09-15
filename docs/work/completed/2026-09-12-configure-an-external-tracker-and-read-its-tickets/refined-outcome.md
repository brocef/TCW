# Refined outcome: configure an external tracker and read its tickets

## Decision

**Accepted, 2026-09-14.** The user delegated verification to the agent ("you can
self verify it, I don't need to decide"), so this acceptance is the agent's
assessment against the spec, not a separate human review. Two criteria are
accepted with a recorded qualification (11 and 2, below); neither is a defect in
what shipped.

## Evidence

Every command below was run on 2026-09-14 against `main` at or after `41f18b45`,
which merges the #36 follow-up.

- **Tracker test files and the documented-command test:** `python -m pytest`
  over `tests/test_tracker_{absent,claimability,cli,client,config,replay,validate}.py`
  and `tests/test_documented_cli_surface.py` — **374 passed**.
- **Full suite:** **2814 passed** on the `work/tracker-claim-notes` branch before
  the merge. The merge brought in only other items' planning documents under
  `docs/work/backlog/`; after it, the tracker, replay and plugin-manifest tests
  were re-run on `main` (58 passed) and `tcw validate` exits 0.
- **`tcw capabilities check`** and **`tcw validate`**: both exit 0 after the
  capability flip.

| # | Criterion | Verdict | Evidence |
| - | --------- | ------- | -------- |
| 1 | No tracker configured: commands succeed, never mention a tracker, never import the tracker modules, output stable | Met | `test_tracker_absent.py`: `test_each_command_still_succeeds`, `test_no_command_mentions_a_tracker`, `test_the_jira_client_is_never_imported` (a fresh interpreter per command), `test_output_is_identical_across_consecutive_runs` |
| 2 | No existing test edited to accommodate the tracker | Met, qualified | See below |
| 3 | `tracker list`/`show` with no tracker refuse and name `work.tracker` | Met | `test_with_no_tracker_configured_both_refuse_and_name_the_key` |
| 4 | Each missing required key reported by `validate` | Met | `test_a_missing_required_key_is_reported_by_validate`, run once per key |
| 5 | Bad `provider` named with its value; `strict` reported as unknown | Met | `test_a_bad_provider_is_reported_with_its_value`, `test_strict_is_reported_as_unknown` |
| 6 | Malformed block reported, board still prints | Met | `test_a_malformed_block_does_not_break_a_board_read`, `test_a_malformed_block_still_lets_items_be_created_and_listed` |
| 7 | `validate` makes no network call, reads no credential variable, is fast | Met | `test_validate_makes_no_network_call`, `test_validate_reads_no_credential_environment_variable`, `test_validate_is_fast_with_an_unroutable_base_url` |
| 8 | Six error causes, six messages; a 400 is not read as "already claimed" | Met | `test_the_six_causes_produce_six_different_messages`, `test_each_status_raises_its_own_cause`, `test_no_cause_is_named_for_contention`, `test_a_400_body_is_carried_but_not_interpreted` |
| 9 | A server that never answers times out | Met | `test_a_server_that_never_answers_times_out_rather_than_hanging` (a real socket) |
| 10 | No secret in output, errors or tracked files | Met | `test_no_command_or_error_path_prints_the_token`; a grep of `tests/fixtures/tracker/` for tokens, e-mail addresses and site hosts found none |
| 11 | **[live]** Exclusive / not exclusive / not determined | Met as corrected, qualified | See below |
| 12 | **[live]** `list` rows; `show` status and assignee | Met | `outcome.md` "Live verification"; replayed by `test_tracker_replay.py` |
| 13 | **[live]** Claim name not offered: said so, lists offered names, not called a misconfiguration | Met | `outcome.md`; `test_a_claim_name_this_ticket_does_not_offer_is_reported_but_not_condemned`, and since #36 `test_the_claim_not_offered_note_covers_a_ticket_that_has_not_reached_the_claim` |
| 14 | Capability `Supported`; `capabilities check` and `validate` exit 0 | Met | Flipped in `e8998309`; both commands exit 0 |

**Criterion 11 was never updated after the spec's own correction.** Design §4
records that one ticket can prove a workflow is *not* exclusive but never that it
*is*, because a ticket already claimed no longer offers the claim and so cannot
say where it led. The criterion still reads "against the conforming fixture,
`tracker show` on a ticket in the landing status reports **exclusive**", which
`show` cannot do: it never has the landing status. GitHub issue #36 observed
exactly this on a real exclusive workflow. What shipped matches the corrected
design: `assess()` returns `EXCLUSIVE` when a caller supplies the landing status
(`test_a_directed_workflow_is_exclusive_once_in_the_landing_status`), `show`
reports `not exclusive` on the non-conforming fixture (observed live), and
`not determined` otherwise. The criterion is a stale sentence in the spec, not
missing behavior. Confirming `exclusive` at the moment of a claim belongs to
`2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`.

**Criterion 2.** No assertion in an existing test changed to make room for the
tracker. One existing helper did change: `_help` in
`tests/test_documented_cli_surface.py` now runs this repository's CLI instead of
the `tcw` on PATH (`59162aa5`), alongside the expected `"tcw work tracker"`
entry. It was needed because the build ran in a worktree whose new command the
installed CLI could not see, and it makes the test measure what it claims to. It
is disclosed in `outcome.md` and accepted.

## Capability ledger reconciled

`work/inspect-external-tracker-work` (`cap-1b0a04`) moved `Missing` → `Supported`
in `e8998309`. Its `description.md` was empty and now describes what shipped,
including the honest limit on exclusivity and that the claim name is never
condemned. The three sibling capabilities under `external-work-tracker`
(`manage-external-tracker-intake`, `synchronize-external-tracker-work`,
`require-tracker-backed-work`) stay `Missing`; later children own them.

## Deferred, deliberately

- **No version cut.** The user chose to complete without changing the version.
  The tracker commands themselves already shipped in v2.1.0 and v2.1.1; the #36
  wording fix is recorded in `docs/{changelogs,release-notes}/upcoming.md` and
  reaches users at the next cut.
- **Team-managed Jira projects** and **whether a non-administrator can read a
  workflow definition** remain untested, as `outcome.md` records; the second
  belongs to C4.
- **GitHub issue #36 stays open.** This item did not come from an issue, so the
  Definition of Done's issue line does not apply. #36's side notes are fixed here,
  but its main request is
  `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`, which is
  unblocked by this completion, and the reply already posted on #36 says the issue
  stays open until that ships.

## Definition of Done

- **tests pass** — see Evidence.
- **docs synced** — `documentation-sync` evaluated at the end of the #36
  follow-up: guide, command reference, changelog and release notes updated;
  README's statements remain true and do not quote either note.
- **capabilities reconciled** — see above.
- **reviewed** — the original build was reviewed during spec and plan, as
  `outcome.md` records. The #36 follow-up had no separate reviewer; it is two
  message strings, their docs, and two tests, self-reviewed.
- **version offered** — offered; the user declined a version change.
- **originating GitHub issue** — not applicable; see above.
