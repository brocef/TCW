# Plan: point a refused drop to the discard route

## Tasks

1. **Tests first.** Modify `tests/test_work.py`: add, beside
   `test_drop_of_a_missing_item_does_not_advise_confirm`, a test that starts an
   item and checks criteria 1 and 2 (no `--confirm`, then with it). A second test
   submits it to review and checks criterion 3. A third completes an item under
   `retain` defaults and checks criterion 4. If the node's defaults delete
   completed items at once, that test uses a retained status or drops criterion 4
   to a store-level check; say which in outcome.md. They fail before task 2.
2. **Code.** Modify `tcw/work/cli.py` `_drop`: after `_resolve`, `item = st.get(bare)`.
   If the item is not None and its status is not `backlog`, print the refusal on
   stderr and return 1. Resolved statuses (`completed`, `discarded`) get the
   "already resolved" wording. Proven by task 1's tests going green and the
   existing drop tests (criterion 5) staying green.
3. **Skill.** Modify `skills/work/SKILL.md:40` (criterion 6).

## Documentation Sync

- `docs/changelogs/upcoming.md`: add a Fixed entry.
- `docs/release-notes/upcoming.md`: add one short plain-language line.
- `skills/work/SKILL.md`: task 3.
- README.md: its drop row (line 484) already says drop refuses a non-backlog
  item. No change.
- The jira guide, the other guides and the configure references: not triggered.
  No tracker command, key or file location changes.

## Verification

Run the drop tests and the full `tests/test_work.py` in the worktree venv. By
hand, in a scratch node: start an item, run `tcw work drop <slug>`, and read the
message. Then run the command it suggests and confirm the item lands in
discarded.
