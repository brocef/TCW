# Name the item's actual body artifact in the builtin spec and plan stage prompts

## Origin

GitHub issue [#22](https://github.com/brocef/TCW/issues/22), filed 2026-08-19 by
@brocef. Accepted during a `tcw-triage-issues` sweep.

## Inbox body

The reporter's text, verbatim:

> ### Environment
>
> - tcw version: `tcw 1.0.0`
> - OS / platform: macOS 26.5.2 (darwin)
> - Install method: pip into pyenv 3.14.6 (via the plugin's `SessionStart` installer)
>
> ### Steps to reproduce
>
> 1. Create an item the way 1.0.0 creates them — piped input, or `tcw work inbox accept`. It gets `intake.md` and no `initial-request.md`; `tcw work list` shows `i` and `tcw work show --json` reports `"initial-request": false`.
> 2. `tcw work stage spec <slug>`
>
> ### Expected vs. actual
>
> Actual — the builtin `spec` stage prompt opens with:
>
> ```
> **Inputs.** `initial-request.md` and its `## References` — the starting set for
> research, not the limit of it. With neither that section nor an "asked; none
> provided" note in `## Notes`, nobody asked: research from scratch rather than
> reading silence as "there was nothing to point at". Repository discovery is
> unrestricted; a spec written without reading the code it changes is a guess.
> ```
>
> It names a file that does not exist on the item, and no other file. An agent handed this prompt on an intake-only item is told to read a missing document, and is given no instruction about the `intake.md` sitting right there — which on an inbox-adopted item is the entire request.
>
> The stage prompt for `spec` is also the only place the agent is told what to read, so the omission is load-bearing rather than cosmetic. The same wording appears in the `plan` stage's inputs.
>
> Expected: the prompt names whichever body artifact the item actually has, or names both and says how they differ — that the intake is raw arrival kept verbatim, and the request is the written-up version. The `## References` instruction should degrade sensibly on an item that has only intake.
>
> ### Why it lands specifically on 1.0.0
>
> Under 0.21.x every item had an `initial-request.md` because creation wrote one, so the prompt was always true. 1.0.0 deliberately stopped writing it — which is the right call — but the builtin stage prompts still assume the old guarantee. On our workspace 60 of the current items are intake-only, so this is the common case now, not the edge one.
>
> ### Remediation
>
> Have the stage prompt resolve the body artifact the same way `tcw work show` does (request when present, intake otherwise) and name what it found — the resolution logic already exists, since `show` does exactly this and `--json` already reports the `artifacts` map.
>
