# Outcome: point a refused drop to the discard route

## What shipped

- `tcw/work/cli.py` `_drop`: reads the item before the `--confirm` gate. For an
  item in `active` or `review` it refuses and names
  `tcw work complete <slug> --resolution wontfix --confirm`. It says a `completed`
  or `discarded` item is already resolved. A slug matching two folders gets a
  `tcw work drop:` message instead of a traceback, and that also covers the old
  unguarded `locate` call on the no-`--confirm` path, because `get` now runs first.
- `skills/work/SKILL.md:40`: `discard` now carries its `complete --resolution` spelling.
- Changelog and release notes: one entry each.

## Tests

`tests/test_work.py`: an active item (with and without `--confirm`, and then the
suggested command, which lands it in `discarded`); an item in review; a resolved
item as both `done` and `wontfix`. Before the fix, all three new tests failed. A
mutation check, dropping `completed` from the resolved branch, turned the `done`
case red. `tests/test_work.py`: 215 passed. Earlier, `test_work`, `test_serve_write`,
`test_tracker_strict` and `test_store_editor` together gave 535 passed, and the
skill and plugin tests gave 239 passed.

## What the spec got wrong

Criterion 1 says stderr "does not mention `--confirm`", but the command it asks
for contains `--confirm`. The meaning is "no advice to re-run with `--confirm`",
and that is what the test checks.

## Hands-on check

In a scratch node: after starting an item, `tcw work drop <slug>` printed the
refusal naming the command and exited 1. The named command discarded the item,
and a second `drop --confirm` said it was already resolved.

## Autonomous decisions

- No advisor consult. The fix is a message and its timing, the spec's Design
  was settled by reading the code, and no choice was irreversible.
- Code review (adversarial-code-reviewer): DONE. It asked for a clean message on
  a duplicate slug (fixed), a `completed` case in the resolved test and removal of
  its dead skip (fixed), and a test running the suggested command (added). Nothing
  rejected.
- Left for separate work: whether `complete --resolution wontfix` behaves on a
  legacy nested child that reads `active` from its parent's folder. After the
  children-status item, new children have their own folder, so only boards made
  before v2.5.1 can have one.
- Verify (tcw:verifier): all six criteria met; accept. Its one finding is folded in: on a node that deletes resolved items, a failed archive can leave a resolved item waiting to be removed, so the "already resolved" message now also names `tcw work delete <slug>`, which finishes that removal. The test asserts it.
