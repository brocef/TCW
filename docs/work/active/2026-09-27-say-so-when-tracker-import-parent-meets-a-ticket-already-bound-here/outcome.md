# Outcome: Say so when tracker import --parent meets a ticket already bound here

## What shipped

1. **Tests** (`45725aa3`) — `tests/test_tracker_strict_gate.py`, six tests after
   the earlier item's criterion 4 tests, one per acceptance criterion. Criteria
   1, 2, 5 and 6 failed on main (exit 0). Criteria 3 and 4 passed on main, as
   they should; they were mutation-checked by making the new branch refuse every
   re-run, which turned all three of their tests red.
2. **The check** (`8b631fee`) — `_tracker_import` (`tcw/work/cli.py`): in the
   "already bound, assigned to me" branch, a `--parent` or `--initiative` the
   bound item lacks prints one stderr line per mismatch after the slug and exits
   1; nothing is written. The help text's re-run sentence and refusal list say
   so.
3. **Review fixes** (`9816bba1`) — the item is read only when a placement was
   asked for (a plain re-run no longer walks the board an extra time); an item
   resolved or removed between the binding lookup and the read is reported
   instead of raising; "is not under P" became "whose parent is not P", since
   only the direct parent is compared.
4. **Documentation** (`4d6155d5`) — changelog and release notes extend the
   entries that introduced the options; `docs/guide/jira.md` "Running it again is
   safe"; `skills/work/references/commands.md` import row; capabilities
   `work/manage-external-tracker-intake` and `work/require-tracker-backed-work`,
   declared in `capabilities.yaml`.

5. **Verify fold-in** — a test for the item-gone branch
   (`test_a_bound_item_gone_before_it_is_read_is_reported`), which the verifier
   found untested; mutation-checked by removing the guard (it fails with the
   `AttributeError` the guard prevents). Blank lines in the test file tidied.

## Test result

Full suite in the worktree, at `9816bba1`: 4733 passed, 3 skipped in 1308.15s (0:21:48) (main before this item: 4727 passed).

## What the plan or spec got wrong

- The spec first said `--parent` would be resolved through `get` so that
  "another spelling" of the slug would not count as a mismatch. `get` accepts
  only an exact slug; the spec review caught it and the sentence was removed
  before implementation.
- The finding this item came from suggested pointing people to
  `tcw work edit --parent`, which does not exist. The message points to the web
  app's item editor, which does have a parent field, and to
  `tcw work edit --initiative` for the initiative.
- The plan's hands-on check assumed the fake tracker could be driven from a
  shell by hand. It is a test helper, not a server; the hands-on check was the
  help text read from the built CLI plus the tests' own CLI runs, and no real
  Jira project was used.

## Review

- Spec review: no design defect; wording fixes adopted (see `spec.md` Notes).
- Code review (adversarial-code-reviewer): DONE, no blocking finding. Both
  non-blocking points (a missing `None` check, the "not under" wording) fixed in
  `9816bba1`. Nothing rejected.
