# Make a stale item path fail loudly: complete checks for the verify artifact, validate finds a slug under two statuses, and the stage text says where to write

## Origin

GitHub issue [#58](https://github.com/brocef/TCW/issues/58), filed 2026-09-19 by @brocef — points 2–4 and the follow-up comment; point 1 (what `submit` and `rework` print) is tracked in the item about transition output.

> ### Motivation
>
> An agent driving an item through the lifecycle holds the item's folder path in
> its context across many turns. `tcw work submit` moves that folder from
> `active/<slug>/` to `review/<slug>/`, and the `verify` stage then writes
> `refined-outcome.md`. If the agent writes to the path it was already holding,
> the write lands in a directory that no longer holds the item — recreating
> `active/<slug>/` with one orphan file in it.
>
> **Nothing in that sequence fails.** The write succeeds. `git add` succeeds. A
> glob for the filename finds it, at the stale path, which reads as confirmation.
> `tcw work complete` then correctly moves `review/<slug>/` → `completed/<slug>/`
> and reports success. The item ends up `completed` with its acceptance record
> sitting outside it, and every command that could say so reports health.
>
> I hit this on a real item and spent a while convinced `complete` had skipped a
> file, because that is what the symptom looks like from the outside. It had not:
> `git_mv` moves a directory, not a file list, so skipping one file is not
> something it can do. The fault was entirely mine. But the tool had four
> opportunities to say so and took none of them, and three of those look
> inexpensive to close.
>
> All behaviour below was confirmed on tcw **2.4.0** (macOS) in a clean scratch
> project — `tcw init` in an empty git repo, node id `example-node`, item
> `2026-09-19-fix-the-thing`. Names are mirrored; the commands and output are
> verbatim.
>
> ### Description
>
> **1. The transitions that move an item mid-lifecycle report a status; the ones
> that create, advance or close it report a path.**
>
> ```
> tcw work new:      → created at docs/work/backlog/<slug>
> tcw work start:    started <slug> → docs/work/active/<slug>
> tcw work submit:   submitted <slug> → review
> tcw work rework:   reworking <slug> → active
> tcw work complete: completed <slug> (done) → docs/work/completed/<slug>
> tcw work drop:     dropped <slug>
> ```
>
> `submit` and `rework` are exactly the two transitions after which a stage is
> asked to write an artifact into the folder that just moved — `verify` writes
> `refined-outcome.md` after `submit`, and `implement` writes `outcome.md` after
> `rework`. They are also the two that report a status name rather than a path.
>
> `submit`'s own next-step line makes the mismatch plain:
>
> ```
> → next: verify the work, then either `tcw work complete …` or, to send it back,
>   delete refined-outcome.md and run `tcw work rework …`
> ```
>
> It names the file to write and not the directory to write it in. Printing
> `→ docs/work/review/<slug>` and `→ docs/work/active/<slug>` would make both
> consistent with their siblings and put the correct path directly above the
> instruction that needs it.
>
> (Captured with stdout and stderr combined, so the text of each line is exact but
> the stream and relative ordering of the `→ next:` hint are not asserted.)
>
> **2. `complete` never checks for `refined-outcome.md`.**
>
> An item completes as `done`, exit 0, no warning, with no `refined-outcome.md`
> anywhere in the folder being moved. That artifact's presence is what
> distinguishes acceptance from rework — `rework` refuses to run while it exists,
> and the whole `verify` stage is built around producing it — but `complete` does
> not read it. A warning, or a `--force` to proceed without it, would catch both
> the stale-path case and the simpler one of completing an item nobody verified.
>
> **3. Nothing detects the same slug under two statuses.**
>
> With `review/<slug>/` holding the item and `active/<slug>/` holding one stray
> file, committed and clean:
>
> ```
> $ tcw validate
> validate OK
>
> $ tcw work show 2026-09-19-fix-the-thing
> 2026-09-19-fix-the-thing  [review]
>
> $ tcw work list
> 2026-09-19-fix-the-thing | review | SPO | - | Fix the thing
> ```
>
> All three report one healthy item. `validate` has no stricter mode that could
> have caught it — its options are `[-h] [--no-recurse] [path]`. A scan for a slug
> appearing under more than one status directory looks like a natural fit for
> `validate`, which already exists to check store integrity.
>
> **4. The stage docs are inconsistent about this hazard, and the inconsistency
> runs the wrong way.**
>
> `tcw work stage prompt postmortem` says to produce the artifact *"in the item's
> folder wherever that folder currently lives"* — the moving-folder hazard is
> anticipated there. `tcw work stage prompt verify` says only *"Produce exactly
> one of two"*, with no path guidance, even though `verify` runs immediately after
> the transition that moves the folder. `implement` is in the same position after
> `start`.
>
> `tcw work path <slug>` already resolves correctly at every status — backlog,
> active, review and completed — so the remedy exists; agents just have no reason
> to reach for it and no signal when they should. One clause in the `verify` and
> `implement` stage text, matching the wording `postmortem` already uses, would
> likely prevent most of this.
>
> ### Benefits
>
> Each of the four is independently small, and any one of them would have turned
> my silent corruption into an immediate, attributable message.
>
> They matter more for agent-driven use than for a human at a terminal. A human
> runs `submit`, sees the item move, and is usually looking at the directory. An
> agent holds a path from an earlier turn, has no view of the filesystem between
> commands, and treats a successful write as evidence it wrote to the right place.
> The failure is silent, survives commit, and produces a completed item that looks
> whole — which is the worst combination for something that is meant to be a
> durable record.
>
> Points 1 and 4 are wording changes. Point 2 is a file-existence check at a
> transition that already refuses on other grounds. Point 3 is a directory scan in
> a command whose stated job is integrity.
>
> I am happy to open separate issues for any of these if you would rather track
> them apart, or to send a PR for the `submit` output line, which is the smallest
> and probably the highest-value of the four.

Follow-up comment on #58 by @brocef, 2026-09-29:

> Adding to this from a real run on tcw 2.6.4, with three agent sessions in the same workspace:
>
> `start` moves an item from `backlog/` to `active/`, and `submit` moves it from `active/` to `review/`. Paths already handed to reviewer and verifier agents went stale in the middle of their run: an agent is given `docs/.../active/<slug>/spec.md`, the item is submitted, and the path no longer exists. Two separate agents hit this. The workaround was to look the path up again with `tcw work path <slug>` after every transition, and to tell spawned agents to do the same rather than trust the path in their prompt.
>
> A stable path would remove the problem at the source. Examples: a `docs/work/items/<slug>/` folder with the status kept only in `state.yaml`, or a stable symlink. Failing that, the "fail loudly" behaviour asked for in this issue would at least turn a silent wrong path into an error.

## Triage notes

The follow-up comment on #58 suggests a folder that never moves (status kept only in `state.yaml`). That is a much larger design change to the store layout; it is recorded here for the spec stage to weigh, not taken as the ask.

A related path problem, found in code review of
`2026-09-29-make-start-submit-rework-and-complete-print-the-true-next-step-the-item-s-new-folder-and-what-confirm-acknowledged`
and left for this item: for a qualified reference (`tcw work start kid/<slug>`,
and the same for `submit`, `rework` and `complete`), the folder printed after the
transition is relative to the child project, not to the directory the command
ran in, so it names a path that does not exist from where the user is standing.
`start` and `complete` already did this; that item made `submit` and `rework`
print a folder too, in the same form. Printing an absolute path, or one relative
to the working directory, would fix all four.
