# Make start, submit, rework and complete print the true next step, the item's new folder, and what --confirm acknowledged

## Origin

GitHub issue [#58](https://github.com/brocef/TCW/issues/58), filed 2026-09-19 by @brocef — point 1 only — `submit` and `rework` print a status, not the folder; points 2–4 are tracked in the item "Make a stale item path fail loudly".

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

GitHub issue [#67](https://github.com/brocef/TCW/issues/67), filed 2026-09-29 by @brocef.

> `tcw work complete --confirm` prints the Definition of Done as a list of **unticked** boxes, then completes the item on the next line:
>
> ```
> Definition of Done — acknowledge each item:
>   [ ] tests pass
>   [ ] docs synced
>   [ ] capabilities reconciled
>   [ ] reviewed
> completed <slug> (done) → docs/work/completed/<slug>
> ```
>
> Seen on tcw 2.6.4, on every completion, by three separate agents. None of them could tell from the output whether `--confirm` had acknowledged the four items, whether they were assumed, or whether they were ignored.
>
> It also appears when the command then refuses. `complete --already-integrated` on an item that was not started with `--worktree` printed the same unticked list, then stopped with the refusal. That makes the list look like the reason for the stop.
>
> **Asked for:** one of these two:
> - when `--confirm` is given, print the items as acknowledged (`[x]`) and say that `--confirm` did it;
> - without `--confirm`, refuse and name the flag.
>
> Print the checklist only on the path that actually completes.

GitHub issue [#68](https://github.com/brocef/TCW/issues/68), filed 2026-09-29 by @brocef.

> Two of the "→ next:" hints point at the wrong step. Both seen on tcw 2.6.4, in a scratch project, and by several agents in real use.
>
> **1. `tcw work start` skips submit and verify.**
>
> ```
> started <slug> → docs/work/active/<slug>
> → next: when done & verified, run `tcw work complete <slug> --resolution done --confirm`
> ```
>
> The lifecycle goes implement, then `submit` to review, then verify, then complete. The hint goes straight to `complete`, so an agent that follows it skips review. Two agents noticed this and followed the stage docs instead. A less careful one would complete straight from active.
>
> **2. `tcw work submit` names a file that does not exist yet.**
>
> ```
> → next: verify the work, then either `tcw work complete <slug> --resolution done --confirm` or, to send it back, delete refined-outcome.md and run `tcw work rework <slug>`
> ```
>
> Right after `submit`, the folder holds `intake.md` and `state.yaml` and nothing else. `refined-outcome.md` is written later, at acceptance. The hint reads as if one is already there and has to be removed.
>
> **Asked for:**
> - `start` should point at the next stage (implement, then `submit`).
> - `submit`'s hint should say "if you have written refined-outcome.md, delete it", or leave the file out when it does not exist.

## Triage notes

All three issues change the lines these four transitions print, and two of them change the same `submit` line, so they are one item.
