# Let complete --already-integrated check a branch worked in a worktree tcw did not create

From GitHub issue [#72](https://github.com/brocef/TCW/issues/72) (filed
2026-09-29 by @brocef), preserved as this item's `intake.md`.

## The request

`tcw work complete --already-integrated` checks that an item's branch has been
merged, but only for an item started with `tcw work start --worktree`, which is
what records the branch. Where agents make their own worktrees with
`git worktree add`, the flag is always refused:

```
tcw work complete: --already-integrated applies to an item started with --worktree; <slug> has none.
```

The workaround is to complete without the flag — which nothing then checks. So
the refusal removes the only integration check without offering another.

Asked for, as alternatives: let `--already-integrated` be told which branch to
check (`--branch <name>`), or let `start` record a branch without creating a
worktree (`start --branch <name>`), so that an item worked in a hand-made
worktree can still be checked for being merged when it completes.

Seen on tcw 2.6.4 (a proposit-core session).

## Out of scope

- The unticked Definition of Done list printed before the refusal: GitHub #67,
  fixed in 2.7.0.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue; nothing else was offered.
