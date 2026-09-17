# Add a commands-pause-work skill that parks in-flight work and waits for the user

## What is wanted

A new command skill in this repository, `commands-pause-work`, that an agent invokes when
the user tells it to stop for a while.

**The case it is for.** The user needs to step away mid-task and wants one convenient thing
to type instead of hoping the agent stops somewhere sensible. How long they are gone, and
what they come back to, is not known at the moment they type it:

- **A brief disconnect.** Off the internet for a few minutes, an errand, a flaky
  connection. They return to the same session with its context intact and say carry on.
- **A cold resume.** A reboot, a container that does not survive, or picking the work back
  up on a different machine entirely. Nothing of the session survives; the work item is the
  only thing left.

The skill cannot tell these apart when it runs, so it has to leave the work in a state where
either one works. That is the whole difficulty: a brief pause wants to be cheap, and a cold
resume wants everything written down.

The skill does three things, in order:

1. **Stops the work gracefully.** Not an abrupt halt wherever the interruption lands — the
   agent brings what it is doing to a coherent resting point first, and does not start
   anything new on the way out.
2. **Writes whatever notes resuming needs into the relevant `tcw work` item(s).** On a brief
   pause these are insurance. On a cold resume they are the only channel there is, so they
   have to be good enough that an agent with no memory of the session — possibly on another
   machine, from a fresh clone — can pick the work up from the board alone.
3. **Waits.** It does not complete the item, discard it, hand it on, or decide on its own to
   carry on. It holds until the user says to continue.

The plugin already ships command skills for starting and finishing work —
`commands-plan-work`, `commands-drive-work-to-completion`, `commands-verify-work`,
`commands-process-inbox`. There is nothing for stopping part-way.

## Constraints

Decided with the requester while writing this request:

- **Cheap when there is little in flight, thorough when there is a lot.** The value is
  convenience, and a pause that takes several minutes of tidying before the agent falls
  silent defeats its own purpose — the user is already walking away. But the notes still
  have to survive a cold resume. Effort should scale with what is actually in flight, not
  with a fixed checklist.
- **The item stays `active` and stays claimed.** Paused work is still the pausing agent's
  work; it is not released for someone else to pick up.
- **Work in progress is committed on the branch, marked as work-in-progress.** A pause must
  not depend on a checkout or a container surviving the gap, and a different machine can
  only see what was pushed — so reaching the remote is part of this, not an optional extra.
- **Skill only — no Python changes.** The deliverable is a new `skills/commands-pause-work/`
  skill plus whatever registers it in this repository. It works with the transitions and
  artifacts `tcw` already has; it does not add a paused status, a pause verb, or a new store
  field.
- It must hold to the same rules as the other skills in this plugin: the shape and
  frontmatter they share, routing through the `work` and `work-stage` skills rather than
  restating stage instructions, and working under Codex as well as Claude Code.

## Out of scope

- A first-class notion of "paused" in the `tcw` CLI or the store.
- A resume command. Picking work back up is already `commands-drive-work-to-completion`'s
  "find your place" behaviour; this item's job is to make sure it finds something worth
  reading.
- Recovering a claim held by a process that died — that is a separate tracked item (see
  References); a graceful pause is the case where nothing died.
- Pausing as a way to park work indefinitely or hand it to a different person. If a pause
  turns out to be permanent, that is an ordinary stop and the item's own lifecycle handles
  it.

## Notes

- Asked for directly in chat on 2026-09-17. The requester's own words are preserved in
  `intake.md`; both the brief-disconnect and the cold-resume cases were given while this
  request was being written.
- Reference material: asked; the requester answered that there is none beyond this
  repository — the four existing command skills, `skills/README.md`, and the lifecycle
  documents are the prior art.
- **A tension `spec` has to resolve, not inherit.** "Stays claimed" and "resume on another
  machine" pull against each other: a claim records an owner identity, and an agent resuming
  from a fresh clone elsewhere is not that identity. Either resuming a paused item needs
  `--take-over --owner`, which the skill should then say plainly in the notes it leaves, or
  keeping the claim only means not releasing it here and the identity question is the
  resumer's to handle. Settle which, and say so; the constraint above was given before the
  cold-resume case was, so it should not be read as having decided this.
- Also open for `spec`: what "a coherent resting point" means concretely for a half-applied
  edit; where the resume notes live, given that a pause is not a lifecycle stage and so has
  no artifact of its own in the stage table; whether an unpushed or unpushable branch is a
  pause that failed or a pause that reports and continues; and how "waits" is expressed to
  an agent whose turn ends anyway — including whether the skill should say anything about
  not being woken by its own scheduled check-ins or background tasks.

## References

- `skills/commands-drive-work-to-completion/SKILL.md`, `skills/commands-plan-work/SKILL.md`,
  `skills/commands-verify-work/SKILL.md`, `skills/commands-process-inbox/SKILL.md` — the
  four existing command skills. The new one has to match their shape and the way they route
  through `work` / `work-stage` instead of restating stages.
- `skills/README.md` — the rules a skill in this plugin follows, including `dynamic_skill`
  and which skills a project may override.
- `docs/work/backlog/2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability/` —
  related: it holds that every skill gets one capability and that skills must work under
  Codex too. Both apply to a skill added now.
- `docs/work/backlog/2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app/` —
  related, and now closer than it first looked. It covers recovering a claim left by a
  process that died, and `--take-over` is currently broken from the CLI. If `spec` decides a
  cold resume needs take-over, a paused item is resumable only once that item lands.
- `docs/work/backlog/2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields/` —
  related: it records which branch an item is being implemented on. A cold resume on another
  machine needs exactly that to find the WIP commit.
- `docs/work/backlog/2026-09-16-point-open-work-items-at-the-renamed-skills/` — related: a
  new command-skill name lands in the same set of references that item is reconciling.
