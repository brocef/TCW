## Inbox manifest

- `2026-09-17-tcw-work-edit-writes-blockers-before-refusing-a-bad-tag.md`

## Inbox body

# tcw work edit writes blockers before refusing a bad tag

## Desired outcome

A `tcw work edit` that is refused changes nothing: no blocker is added or removed
when another part of the same command is rejected.

## Context

Found by code review of
`2026-09-15-let-tcw-work-edit-change-an-item-s-type-to-or-from-epic`.

`_edit` (`tcw/work/cli.py`) applies `--unblocked-by`, `--blocked-by` and `--blocks`
through separate store calls, then calls `update_work`, which validates tags
(`_validate_tags`) and estimates. So
`tcw work edit X --blocked-by foo --tag unregistered` records the blocker and then
exits 1 over the tag. The `--type` change added a pre-check before the blocker
writes for its own refusal; tags and estimates have none.

## Notes

- Either validate every field before the first write, or fold blockers into the one
  `update_work` call (it already takes `blockers=`).
