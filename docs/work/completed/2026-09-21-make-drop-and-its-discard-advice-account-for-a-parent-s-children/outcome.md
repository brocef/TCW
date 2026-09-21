# Outcome: make drop and its discard advice account for a parent's children

## What shipped

- `tcw/store/base.py`: new `drop_refused_over_children(slug, beneath)`, which
  `WorkStore.drop` and the CLI both use. Its advice is limited to what the CLI can
  carry out. It never offers re-parenting (no CLI verb) or dropping resolved
  children (impossible). Instead it advises discarding the parent, which keeps
  the record the children's `parent:` names, after closing any child still open.
- `tcw/work/cli.py` `_drop`: refuses a backlog item with independent descendants
  before the `--confirm` gate. The discard advice for an active or review item
  also names its open descendants. The resolved check uses `RESOLVED_STATUSES`.
  The `--parent` help no longer says "nested".
- Changelog and release notes: one entry each.

## Tests

Five tests in `tests/test_work.py`: a parent with an open child, before the gate;
all children resolved, where the advice is run and succeeds; mixed open and
resolved; an active parent's advice naming the open child; the `--parent` help.
Each failed before its fix. `test_work`, `test_child_status` and
`test_serve_write` together gave 411 passed.

## What the spec got wrong

Goal 2 first said to advise re-parenting resolved children with
`tcw work edit --parent`, but no such option exists. It was rewritten at
implementation to advise discarding the parent. After verify it was rewritten
again to cover the mixed case.

## Hands-on check

In a scratch node: a backlog parent with an open child was refused on the first
`drop`, with no "Would delete". After the parent was started, `drop` gave the
discard advice followed by "First complete or discard the items still open
beneath it: <kid>".

## Autonomous decisions

- No advisor consult. This was a small follow-up to the combined review's
  findings 1–3, and the fixes were settled by reading the code.
- Re-parenting, as the combined review proposed for resolved children: rejected,
  because the CLI has no re-parent verb (only the web app's PATCH route can). The
  advice is to discard the parent instead, and a test runs that command.
- Code review (adversarial-code-reviewer): DONE. Its optional mixed-children test
  was added.
- Verify (tcw:verifier): all criteria met. Its medium finding was right: the mixed
  case still said "Drop, discard or re-parent them", which can't clear the refusal.
  Fixed at verify: close the open ones, then discard the parent. Its two
  low findings (the spec was rewritten at implementation; the plan names a test by
  its file) are recorded here.
