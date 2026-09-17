# Outcome — Show the tracker's untriaged tickets on `tcw work inbox list`

Built in the worktree on `work/2026-09-15-show-the-tracker-s-untriaged-tickets-on-tcw-work-inbox-list`.

## What shipped, task by task

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 — `inbox-query` key | `6386757e` | `TrackerConfig.inbox_query`, in `TRACKER_KEYS`, parsed only when present; blank or non-string is a problem. Tests in `test_tracker_config.py`, `test_tracker_validate.py`, `test_tracker_inheritance.py`. |
| 2 — `InboxEntryNotFound` | `d9a30cce` | Declared in `tcw/store/base.py`, named in `inbox_show`/`inbox_accept`'s docstrings, raised at the three `no such inbox entry` sites in `tcw/store/fs.py` (the plan said two; `_inbox_path` has two raises). |
| 3 — two sections on `inbox list` | `cc50ff7c` | `_inbox_list` + `_inbox_tickets`; `_ticket_row` shared with `tracker list`. |
| 4 + 5 — resolution, `show`/`accept` of a ticket, strict mode | `5da7c384` | `_inbox_ticket` (store first, tracker on not-found only), `_inbox_show_ticket`, `_print_ticket` factored out of `_tracker_show`; `--ticket` (`dest="force_ticket"`) on both, `--part` on accept; `_tracker_import(args, label=…)`, with `_tracker_client` and `_print_refusal` now taking the full verb. Strict refusal applies to raw entries only. |
| 6 — standing guarantees | `5da7c384` | Sentinel test over every new path (`test_no_inbox_path_prints_the_token`); subprocess test that inbox commands load no `tcw.tracker*` module without a tracker (`test_tracker_absent.py`). |
| 7 — capability ledger | `ccf5561f`, `a97517e8` | The four planned descriptions, plus `skills/commands-process-inbox` (see below). |
| Documentation Sync | `29cbbb32` | README, `docs/guide/jira.md` (new "Tickets in the inbox" section, key table, strict table), `docs/guide/work.md`, release notes, changelog, `skills/work/references/commands.md`, `skills/commands-process-inbox/SKILL.md`, `skills/configure/references/tracker.md`. |

## Test result

- Full suite after the code (bare `pytest`, as CI runs it): **3662 passed** in 14m04s.
- After the documentation commit, every test file that reads skills, README, guides or
  capabilities: **2095 passed**.
- `tcw validate`: OK. `tcw capabilities check`: OK.
- Every new test was run red before its code. Mutation checks, each confirmed red and
  then restored: searching with `candidate_query` instead of `inbox_query`; refusing
  every strict `inbox accept`; skipping the raw-entry lookup in `inbox show`; importing
  `tcw.tracker.jira` before the no-`inbox-query` return in `_inbox_ticket`.
- By hand, in a throwaway node pointed at an unreachable site: `inbox list` printed the
  raw-intake section, `(not listed)`, the cause on stderr, exit 1.

## What the plan or spec got wrong

- **A fifth capability changes.** The plan's documentation block updates
  `skills/commands-process-inbox/SKILL.md` to work tickets, but the ledger entry
  `skills/commands-process-inbox` said the skill processes "every raw entry". Its
  description was updated and it was added to `capabilities.yaml` under `changed:`.
  The skill now tells the agent to confirm before accepting a ticket, because that
  claims it in Jira — a guard the plan did not mention.
- **Tasks 4 and 5 are one commit, not two.** Their tests exercise both commands
  together (the neither-resolves and ambiguity tests run `show` and `accept`), so
  splitting would have left a commit with half-passing tests.
- **Test files differ from the plan.** `inbox accept <ticket>` tests went in
  `tests/test_tracker_import.py`, whose `FakeJira` models claims; `_responses` in
  `test_tracker_cli.py` cannot. The no-tracker-import test went in
  `tests/test_tracker_absent.py`, which already carries the subprocess probe the plan
  described. Nothing was added to `tests/test_work.py` beyond task 2's test.
- **Accepting a ticket reads it once more than `tracker import` does.** To tell "no
  such ticket" apart from other errors and name both possibilities (criterion 20),
  `_inbox_ticket` fetches the issue before delegating, so `inbox accept <key>` makes
  one extra GET. It changes nothing in Jira.
- **`inbox-query: null` alone** is reported as `work.tracker.inbox-query: required`,
  the same message a lone `null` gets for other keys. The spec did not cover it; the
  wording is odd for an optional key but matches the existing rule that a lone null
  is reported.
- Line numbers in the plan had drifted (for example `_inbox_list` was at `:451`, not
  `:448`); no task depended on them.

## Not done here

- **The check against a live Jira site** from the plan's Verification section: a real
  `inbox-query`, a malformed one, and a real 404 for a ref that is neither. The suite
  replaces the transport, so whether Jira answers a non-key ref such as `nope` with
  404 (giving the "names both" message) or with 400 (giving "could not be looked up as
  a ticket: …") is unverified. Both paths are handled; only the wording differs.

## Notes

- Criterion 23: no existing `tests/test_tracker_*.py` test was edited; only new tests
  were appended.
- The editable install currently points at the worktree. Re-point it with
  `pip install -e /Users/brian/Projects/TCW` before `tcw work complete`.
