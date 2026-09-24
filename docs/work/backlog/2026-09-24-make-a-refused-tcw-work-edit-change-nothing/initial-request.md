# Make a refused tcw work edit change nothing

## What is wanted

When `tcw work edit` refuses any part of a command, it changes nothing. Today
`tcw work edit X --blocked-by foo --tag unregistered` records the blocker and
only then exits 1 over the tag.

## Why

`_edit` (`tcw/work/cli.py`) applies `--unblocked-by`, `--blocked-by` and
`--blocks` through separate store calls before `update_work` validates tags and
estimates. The `--type` change added its own check before the blocker writes;
tags and estimates have none. A refused command that still wrote something
leaves the user unsure what state the item is in.

## Notes

- Found by code review of
  `2026-09-15-let-tcw-work-edit-change-an-item-s-type-to-or-from-epic`.
- The intake names two possible fixes (validate everything before the first
  write, or fold the blockers into the single `update_work` call, which already
  takes `blockers=`). Choosing between them is the spec's job.
- The same must hold for the web app's edit path if it shares this sequence.
- Reference material: asked; none provided beyond the intake.
