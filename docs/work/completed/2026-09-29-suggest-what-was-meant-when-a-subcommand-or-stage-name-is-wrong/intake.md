# Suggest what was meant when a subcommand or stage name is wrong

## Origin

GitHub issue [#69](https://github.com/brocef/TCW/issues/69), filed 2026-09-29 by @brocef.

> When a subcommand is mistyped, the error lists every valid choice but does not suggest the one that was meant. Two real cases seen on tcw 2.6.4:
>
> ```
> $ tcw tracker status
> tcw: error: argument group: invalid choice: 'tracker' (choose from 'init', 'provision', 'validate', 'serve', 'taxonomy', 'capabilities', 'work')
>
> $ tcw work status <slug>
> tcw work: error: argument cmd: invalid choice: 'status' (choose from 'init', 'inbox', 'nodes', ... 'drop', 'delete')
> ```
>
> - In the first case the agent meant `tcw work tracker show`. `tracker` exists, but one level down.
> - In the second case it meant `tcw work show`.
>
> Both agents worked around it by other means. The first went to read the ticket directly in Jira, because it concluded that the CLI had no way to show a ticket's sync state. In fact `tcw work tracker show` exists.
>
> **Asked for:** a suggestion when the typed word is a subcommand somewhere else in the tree ("did you mean `tcw work tracker`?"), and a short alias or suggestion for `status` → `show`.

GitHub issue [#71](https://github.com/brocef/TCW/issues/71), filed 2026-09-29 by @brocef — point 2 only — an artifact name given where a stage name is expected; point 1 is tracked in the item about planning gates on a started item.

> Two stage-gate problems. Both were hit by the proposit-core session on tcw 2.6.4.
>
> **1. An item that is already started cannot pass the request, spec or plan gates.**
>
> ```
> $ tcw work stage gate request <slug>
> tcw work stage gate: 'request' is not legal for an item in 'active'; it runs in backlog
> ```
>
> The item had been started before its planning documents were written. That happens when work is discovered mid-task and made into an item after the fact. There is then no legal way to run the gate for those documents, even though the lifecycle still expects them. The agent read the instructions with `stage prompt` and wrote the documents without the gate. That skips whatever the gate has bound to it.
>
> **Asked for:** either allow the planning gates on an active item whose planning artifacts are missing, or have the refusal say what to do (for example, "write it anyway with `stage prompt`; the gate's checks will not run", or "`rework` it to backlog first").
>
> **2. The artifact is named differently from the stage that writes it.**
>
> ```
> $ tcw work stage gate refined-outcome <slug>
> unknown stage 'refined-outcome'; expected one of inbox, request, spec, plan, implement, verify, postmortem
> ```
>
> `refined-outcome.md` is written in the verify stage, but nothing in the error says so. **Asked for:** when the word given is the name of an artifact, the error should name the stage that produces it ("refined-outcome.md is written in the verify stage").

Follow-up comment on #71 by @brocef, 2026-09-29:

> A related case from another agent on tcw 2.6.4. `tcw work start` on an item that has only `initial-request.md` goes ahead with a warning:
>
> > has no spec.md or plan.md; they can still be written while the item is active
>
> The plan stage's own instructions say to commit `plan.md` before `start`. So `start` lets an item past the point where the planning gates can still run, and gives only a warning. This is how items end up in the state described above, where the request, spec and plan gates refuse an active item. `stage prompt request` on such an item does print the instructions ("Printing its instructions anyway"), which is clear, but nothing can run the gate itself any more.
>
> Suggestion: either `start` refuses (or needs `--force`) when the planning artifacts the lifecycle binds are missing, or the gates accept an active item that lacks them.

## Triage notes

Both issues ask for the same thing: an error that names the intended word instead of only listing the valid ones.
