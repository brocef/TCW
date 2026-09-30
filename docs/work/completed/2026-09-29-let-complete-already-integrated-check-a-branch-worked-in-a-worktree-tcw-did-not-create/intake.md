# Let complete --already-integrated check a branch worked in a worktree tcw did not create

## Origin

GitHub issue [#72](https://github.com/brocef/TCW/issues/72), filed 2026-09-29 by @brocef.

> `tcw work complete --already-integrated` works only for an item started with `--worktree`. In a workspace where agents make their own worktrees (`git worktree add`), the flag is always refused, even when the branch has already been merged into main by hand:
>
> ```
> tcw work complete: --already-integrated applies to an item started with --worktree; <slug> has none.
> ```
>
> The same run then printed the unticked Definition of Done list and stopped (see the separate issue about that list). The workaround was to rerun without the flag, which works because nothing then checks integration. So the refusal takes away the only integration check without replacing it.
>
> Seen on tcw 2.6.4 (proposit-core session).
>
> **Asked for:** let `--already-integrated` take the branch it should check (`--branch <name>`), or let `start` record a branch without creating the worktree (`start --branch <name>`). Then an item worked in a hand-made worktree can still be checked for being merged at completion.

## Triage notes

The unticked Definition of Done list printed before the refusal is #67, tracked in the item about transition output.
