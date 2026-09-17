# `complete` says the verify stage was skipped for a worktree item

## Desired outcome

Completing a `--worktree` item that was submitted and verified on its own branch
does not claim the verify stage was skipped.

## Context

Seen on 2026-09-17 completing
`2026-09-15-show-the-tracker-s-untriaged-tickets-on-tcw-work-inbox-list`, which was
started with `--worktree`. The lifecycle ran normally: `tcw work submit` was run from
inside the worktree, moving the item to `review` and committing that move on the
branch (`1fe68660`), and `refined-outcome.md` was written and committed there
(`20b379ce`).

`tcw work complete <slug> --resolution done --confirm`, run from the primary checkout,
printed:

```
tcw work complete: completing <slug> directly from active; the verify stage was skipped
```

and then merged the branch (`60dbb164`) and completed the item. The merge is what
brings the `review` status into the primary checkout, so at the moment the status is
read the item is still `active` there — the branch's own status move has not landed
yet. The warning is therefore reading a status that the same command is about to
replace.

The completion itself was correct; only the message is wrong. It is worth fixing
because it tells a user their process was skipped when it was followed, and the same
reading may feed gates that care about the status.

## Notes

- Worth checking whether anything else in `complete` reads the pre-merge status for a
  worktree item, rather than only this message.
- Related: the Definition of Done checklist printed with every box unticked in a
  non-interactive run, and completion continued. Whether that is intended is a
  separate question from this one.
