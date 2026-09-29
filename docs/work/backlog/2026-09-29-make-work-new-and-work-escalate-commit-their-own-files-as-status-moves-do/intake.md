# Make work new and work escalate commit their own files, as status moves do

## Origin

GitHub issue [#66](https://github.com/brocef/TCW/issues/66), filed 2026-09-29 by @brocef.

> `tcw work new` and `tcw work escalate` leave their files in git in two different uncommitted states, while status moves (`start`, `submit`, `rework`, `complete`) commit for themselves. Seen on tcw 2.6.4.
>
> **Reproduce** (a scratch `tcw init` project):
>
> ```
> echo body | tcw work new "First thing"
> git status --short
> A  docs/work/backlog/2026-09-29-first-thing/intake.md
> A  docs/work/backlog/2026-09-29-first-thing/state.yaml
> ```
>
> - After `new`, the item's files are **staged but not committed**, and HEAD does not move.
> - After `escalate`, the new inbox entry is **untracked** (`?? docs/work/`), so it is not even staged. This was reported by the proposit-core session.
> - After `start`, `submit`, `rework` or `complete`, a commit is made automatically.
>
> **Why it hurts:** the work skill says TCW commits its own transitions. Agents reasonably read that as covering creation too. Then the creation gets folded into whatever the next commit is, which is usually the request artifact, and the skill says not to do that. In a work store that several sessions commit to, a staged file left by one session can also be swept into another session's commit.
>
> **Asked for:** creation commands behave like transitions and make their own commit. Failing that, all creation commands should leave the same state, and should print that the files still need committing.
>
> Workaround in use: commit the item folder by hand right after `new` or `escalate`, with a commit limited to that path.
>
> Related backlog item: `decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git`.

## Triage notes

Related backlog item: `2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git` (the same question for `scaffold`). Related new item: the one for #73, since a staged file left by one session is what another session's commit sweeps up.
