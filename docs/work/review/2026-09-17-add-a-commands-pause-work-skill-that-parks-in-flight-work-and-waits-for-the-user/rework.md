# Rework: simplify the skill and the handoff naming

Rejected at `verify` on 2026-09-17. The skill works and every acceptance criterion
was met, but it is over-specified: it tells an agent what to write in a document
the agent is better placed to judge, and it pays for a naming scheme it does not
need. Three changes, all reductions.

## 1. Stop dictating the handoff's contents

The spec's five-item content list becomes roughly one sentence: *write a handoff
document containing any context an agent would need to resume the work you were
doing at the time of the pause.* An agent that has been working the item knows
what mattered; a checklist written in advance cannot, and mostly produces
ceremony.

Keep only the constraints that exist because something outside the agent's view
would otherwise break:

- **no `tcw://` links** — `tcw validate` resolves links in every Markdown file
  under the work store (`tcw/validate.py:62`, `:313`) and a project may gate
  `complete` on it, so a dangling one refuses the completion;
- **the branch name** — nothing else records it for a non-worktree item, so a
  resumer on another machine cannot find the work without it.

Both are facts about the system, not advice about note-taking.

## 2. Rename to `handoff-{timestamp}.md`

Drop the stage id. It bought a guarantee nobody asked for and cost two rules:
the `inbox` exclusion (there is no item folder at that stage) and "delete any
handoff already present" (because a same-stage pause would collide). A timestamp
collides with nothing, so both rules disappear rather than being restated.

Consequences to carry through:

- Several handoffs may now coexist. A resuming agent reads what it finds —
  newest last — and deletes what it read. That replaces the collision rule.
- The `inbox` carve-out goes away entirely: with no stage in the name there is
  nothing stage-shaped to exclude. A pause with no work item still writes no
  handoff, for the ordinary reason that there is nowhere to put one.
- Timestamps are UTC and filesystem-safe, so they sort.

## 3. The whole skill under 80 lines

It is ~136. The cuts in 1 and 2 pay for most of it; the rest comes from the
status table, the worktree paragraph and the tracker-identity aside — all true,
all already recorded in `spec.md`, and none of it something an agent needs in
front of it to pause well.

## What this does not change

The procedure itself stands and is not up for rework: coherent resting point →
ask whether to commit and push, no answer is a yes → commit and push → write the
handoff → commit and push it as a second push → report → fall silent. No
transition runs. The resume-side read-and-delete stays where it is, in
`skills/work/SKILL.md`'s "Finding your place" and the two command skills that
were pointed at it.

## Artifacts this invalidates

`spec.md`'s Design section (the naming, the content list, the `inbox`
exclusion, the collision rule) and acceptance criterion 7, and `plan.md`'s Task 3
body. Both are updated as part of this rework rather than left describing a
shape that no longer ships. `outcome.md` is superseded by the next pass.
