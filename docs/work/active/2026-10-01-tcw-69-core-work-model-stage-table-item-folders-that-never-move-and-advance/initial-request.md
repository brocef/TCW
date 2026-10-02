# Core work model: stage table, item folders that never move, and advance

TCW 3.0 needs a work model that is simple to implement and predictable to use. Every
other slice of the redesign (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68))
builds on it: the filesystem backend, the Jira backend, the CLI pass and the web
viewer.

## What is wanted

A backend-independent definition of the work axis that answers five questions once,
in one place:

1. **What a work item is.** One set of properties (title, stage, priority, effort,
   complexity, tags, assignee, parent, blocked-by), the same in both backends and
   taken by the same flags on `new`, `edit`, `list` and `show`. No stored slug, no
   history list, no per-item schema version, no epic type: an item with children is
   an epic.
2. **How it is identified.** `{tcw-config.id}/{folder name}`, everywhere, including
   across projects. "Project" replaces "node" and "connected project".
3. **Where it lives.** One folder per item that never moves and is never deleted by
   TCW. No status directories. Each stage that produces something has its own
   folder: revised documents are `<stage>/<stage>.md`, looping stages write
   `round-N.md` with a verdict, and handoffs are timestamped files in the stage
   folder.
4. **Which stages it moves through.** The stages are data, in one built-in table
   (inbox, request, spec, plan, implement, review, qa, completed, discarded, and
   postmortem as a side stage). A project can disable the optional ones. Stage names
   appear nowhere but that table, so project-defined stages can come later.
5. **How it moves.** One command, `tcw work advance`, replaces start, submit, rework,
   complete and drop. A move runs only the target stage's `pre` gates; a gate refuses
   unless the caller forces the move and gives a reason, and a forced move leaves a
   comment as its trace. `discard` is shorthand for moving to discarded.

It also defines the small set of operations every backend must implement (create,
read, list, update properties, set stage, comment, rename), the built-in gates (the
capability-records gate after implement, and the completion gate on accepted
rounds), the per-stage configuration shape, and the rule that TCW never changes git
state.

The agreed decisions, refined after an adversarial review, are in the ticket
([TCW-69](https://proposit.atlassian.net/browse/TCW-69)); `intake.md` holds them as
imported. They are the requirement. Where they differ from the epic's attached
decision record, the ticket is current.

## Constraints

- **Simplicity of implementation comes first.** Each operation should be atomic and
  predictable. Imagine writing TCW from scratch; do not keep a 2.x feature because
  it exists.
- **Breaking changes are expected.** This ships in 3.0.0. No 2.x compatibility code;
  migration is a written guide (TCW-76).
- **Designed for any project,** not tuned to one workspace.
- **Every operation must pass the abstraction litmus test**
  ([`docs/lifecycle/abstraction.md`](../../../lifecycle/abstraction.md)): both
  backends implement it.
- **TCW never changes git state.** It writes files, names them on stderr, and may
  read git for checks.

## Out of scope

Owned by the sibling slices, not this one:

- The filesystem backend's storage details (`item.yaml`, folder date prefix, inbox
  items, comment files, rename): TCW-70.
- The Jira backend (status mapping, transitions, adoption, QA on the ticket): TCW-71.
- Personal configuration and the `inherit` chain for prompt/hook lists: TCW-72.
- The final command surface, stdout/stderr contract and exit-code table across all
  three axes: TCW-73. This slice uses that table for `advance`.
- Rewriting the stage prompts and skills: TCW-74. Documentation: TCW-75. The web
  viewer: TCW-77. Migration: TCW-76.

## Notes

- **Where the input came from.** The requirement was worked out with the owner in a
  brainstorming session on 2026-09-30/10-01 (TCW-67, closed as Won't Do in favour of
  TCW-68). The owner asked the agent to make educated decisions and confirm them
  rather than asking point by point. Reference material was asked for during that
  session; what was offered is listed below.
- **Assumption:** this slice delivers the model *and* the shared layer both backends
  use (folder layout, stage folders, rounds, handoffs, `path`), since TCW-70 says
  those are TCW-69's.
- **Open questions the ticket hands to `spec`:** the exact `capabilities.yaml` schema
  (including new taxonomy entries), and whether `validate` should report a
  filesystem item whose stage is ahead of its artifacts.
- **Self-hosting.** This changes `tcw/` itself, so from implementation onwards the
  repository's own board is driven by editing files, not through the CLI, as
  `CLAUDE.md` requires.

## References

- [TCW-69](https://proposit.atlassian.net/browse/TCW-69): the ticket; the agreed
  decisions for this slice.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68): the epic, its vision, and the
  attached `TCW-68-design-decisions-2026-09-30.md` that records the whole session.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70),
  [TCW-71](https://proposit.atlassian.net/browse/TCW-71),
  [TCW-73](https://proposit.atlassian.net/browse/TCW-73): the slices that draw the
  boundary of this one.
- `tcw/work/recursion.py`: today's `capability_gate`, which the records gate replaces.
