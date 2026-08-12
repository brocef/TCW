# Fix work inbox accept's entry resolution and initiative stamp

## Origin

Two GitHub issues, both filed 2026-08-12 by @brocef and both against
`tcw work inbox accept`, accepted as one item because they are one function,
one test surface, and one commit: `accept` rejects an identifier its own
`inbox list` prints, and it discards a frontmatter field `work delegate`
wrote expressly to survive the hand-off.

Reported against `tcw 0.21.0` on macOS 26.5.2, pyenv shim install.

**Sequencing note:** the backlog item
`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven` reworks how
`accept` ingests an entry (its spec, item 4, calls the current intake handling
"three different ways, and one of them is wrong"). Neither bug below is
addressed there, but the two touch the same code — land this first, or fold it
into that item's plan.

### Issue #13

GitHub issue [#13](https://github.com/brocef/TCW/issues/13), filed 2026-08-12 by @brocef.

> ### Environment
>
> - tcw version: `tcw 0.21.0`
> - OS / platform: macOS 26.5.2
> - Install method: pyenv shim (`/Users/brian/.pyenv/shims/tcw`)
>
> ### Steps to reproduce
>
> Two registered nodes: a workspace root and a child node `proposit-mobile`.
>
> 1. At the root, create a cross-node epic and delegate a slice to the child, stamping the initiative:
>
>    ```
>    tcw work new "Close the remaining mobile gaps vs the web app" --epic
>    tcw work delegate proposit-mobile "Build the mobile review results stage" \
>      --initiative 2026-08-12-close-the-remaining-mobile-gaps-vs-the-web-app
>    ```
>
>    The resulting inbox file carries the stamp in its frontmatter, as documented:
>
>    ```yaml
>    ---
>    from: proposit-app
>    initiative: 2026-08-12-close-the-remaining-mobile-gaps-vs-the-web-app
>    ---
>    ```
>
> 2. In the child node, accept it:
>
>    ```
>    tcw work inbox accept 2026-08-12-build-the-mobile-review-results-stage.md \
>      --title "Build the mobile review results stage"
>    ```
>
> 3. Inspect the new item's `state.yaml`:
>
>    ```
>    grep -E "^initiative:" docs/work/backlog/2026-08-12-build-the-mobile-review-results-stage/state.yaml
>    ```
>
> ### Expected vs. actual
>
> - Expected: the accepted item's `state.yaml` carries `initiative: 2026-08-12-close-the-remaining-mobile-gaps-vs-the-web-app`, since `work delegate --initiative` wrote that field expressly to survive the hand-off.
> - Actual: no `initiative` key is written at all (the grep exits 1). The stamp is not lost from the *text* — `accept` copies the frontmatter verbatim into the item's appended `## Inbox contents` → `### Inbox body` section, so it demonstrably reads the field — it just never applies it to `state.yaml`.
>
> ### Why it matters
>
> The failure is silent and it breaks epic tracking. `tcw work reconcile <epic>` at the root finds children by their `initiative` back-pointer, so a slice accepted this way is invisible in the rollup: the epic reports **"all blocked or complete"** while its just-delegated slices sit unlinked in the child's backlog. Nothing warns you. I hit this while filing three slices at once and only caught it because I checked each `state.yaml` by hand.
>
> `accept` also has no `--initiative` flag, so there is no way to supply it at accept time either.
>
> ### Remediation
>
> Preferred: have `work inbox accept` apply the frontmatter `initiative:` to the new item's `state.yaml`, so `delegate --initiative` → `accept` round-trips. The value is already parsed; it just needs to reach the state file.
>
> Failing that, add `--initiative` to `work inbox accept` and/or warn when an accepted entry carries a frontmatter key that accept silently discards.
>
> Current workaround, which every cross-node hand-off in our workspace has to remember:
>
> ```
> tcw work edit <new-slug> --initiative <epic-slug>
> ```
>
> Related in spirit to #7 (cross-node epic slices struggling to link their parent epic).
>

### Issue #14

GitHub issue [#14](https://github.com/brocef/TCW/issues/14), filed 2026-08-12 by @brocef.

> ### Environment
>
> - tcw version: `tcw 0.21.0`
> - OS / platform: macOS 26.5.2
> - Install method: pyenv shim (`/Users/brian/.pyenv/shims/tcw`)
>
> ### Steps to reproduce
>
> 1. Put an entry in a node's work inbox (here, via `tcw work delegate` from the parent node).
> 2. List the inbox:
>
>    ```
>    $ tcw work inbox list
>    2026-08-12-build-the-mobile-review-results-stage.md | file | 2026-08-12-build-the-mobile-review-results-stage
>    ```
>
>    Each row is `<filename> | file | <slug>`.
>
> 3. Accept it using the slug from the third column:
>
>    ```
>    $ tcw work inbox accept 2026-08-12-build-the-mobile-review-results-stage --title "Build the mobile review results stage"
>    tcw work inbox accept: no such inbox entry: 2026-08-12-build-the-mobile-review-results-stage
>    ```
>
> 4. Re-run with the `.md` extension and it succeeds:
>
>    ```
>    $ tcw work inbox accept 2026-08-12-build-the-mobile-review-results-stage.md --title "Build the mobile review results stage"
>    → now at docs/work/backlog/2026-08-12-build-the-mobile-review-results-stage
>    ```
>
> ### Expected vs. actual
>
> - Expected: `accept` takes any identifier `inbox list` prints for an entry — including the bare slug in the third column.
> - Actual: only the `.md` filename resolves. The bare slug — which `list` itself renders, and which matches the slug the accepted item ends up with — is rejected as "no such inbox entry".
>
> The error message also reads as though the entry is missing entirely, which sends you to `inbox list` to check whether it exists. It does exist; the output of that very command is what you just pasted.
>
> Every other `work` subcommand addresses items by bare slug (`tcw work show <slug>`, `tcw work edit <slug>`, `tcw work path <slug>`), so requiring a filename here is the odd one out.
>
> ### Remediation
>
> Resolve the entry argument by trying, in order: exact filename, then filename + `.md`, then slug match against the listed entries. This is the same class of fix as #3 (`capabilities set` rejecting inherited paths that `show`/`list` accept) — one subcommand refusing an identifier a sibling subcommand prints.
>
> If the strict form is deliberate, the error could say so: `no such inbox entry: <x> (did you mean <x>.md?)`.
>

## Product changes

## Technical changes

## Meta changes
