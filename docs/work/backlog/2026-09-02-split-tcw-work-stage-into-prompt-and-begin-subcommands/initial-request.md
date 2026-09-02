# Split `tcw work stage` into `prompt` and `begin` subcommands

## The request

Raised in conversation while resuming a different work item. The requester's
first formulation:

> The `tcw work stage` CLI command (and corresponding implementation) requires
> both the stage ID and a work item slug. I want to modify this to *only*
> require the stage ID, and a work slug would be optional.
>
> The idea here is that, unless the package using TCW generates stage
> instructions dynamically based on the work item contents or metadata, the
> stage instructions will be the same every time. Furthermore, if there is a
> dynamic instruction script, they are free to support a default instruction set
> (null/undefined slug).

Asked whether a stage's `pre` checks should still run when no slug is given,
they reframed the request into what it actually was:

> Your question actually reminded me of an issue I have with the current design.
> I really just want a CLI command to get the instructions for a stage, not
> necessarily to begin that stage. Whatever CLI command it is (`tcw work stage`
> with flags, new command entirely, etc) it should *not* have any side effects
> (at least for what it controls, if the prompt generation script has
> side-effects there's nothing we can do about that).

That second statement is the request. The first is a symptom of it.

## The shape they asked for

Subcommands under `stage`, with the bare form retired:

> - `tcw work stage pre <stage_id> <slug>` to run the pre commands
> - `tcw work stage begin <stage_id> <slug>` to do `pre` and `plan` combined
>   (current behavior of `tcw work stage`)
> - `tcw work stage <stage_id> <slug>` no longer supported, must use `pre`,
>   `plan`, or `begin` subcommands

The read verb was originally proposed as `plan`. It was renamed to `prompt`
after it was pointed out that `plan` is already a lifecycle stage id — making
`tcw work stage plan plan` a legal command — and already means the `--no-exec`
execution plan (`res.plan`, `PlanEntry`). `prompt` matches the `prompt:`
configuration key the verb resolves. The requester agreed:

> Let's change `work plan` to `work prompt` since that's really what it is.

## Decisions taken during intake

Each was put to the requester with the trade-offs and answered explicitly.

| Decision | Answer |
| --- | --- |
| Where the work lands | On `claude/tcw-work-list-zx961v`; that branch merges to `main` locally once this item finishes. Nothing ships in between. |
| Does `prompt` accept an optional slug | Yes — without it the instructions resolve generically; with it they personalize, still with no gates. |
| `inbox`, which never has an item | Verbs are permitted with no slug; a slug is refused. |
| Which verb agent-facing documents call | `begin`, preserving every current gate and guarantee. `prompt` appears only where inspection is intended. |
| Keep or shim the bare form | Removed, as originally stated — reaffirmed after being told a shim via `_normalize` would be about three lines and that removal was a choice rather than a constraint. |
| Ship the `pre` verb | Dropped. Two independent reviewers found no caller anywhere in the repository, and `begin` contains it, so it can be added when someone asks. |

## Notes

The requester asked for the spec to be multi-reviewed rather than reviewing it
themselves, and stated they will not review the work until implementation is
complete.

Reference material was not requested separately; the conversation above is the
whole of it.
