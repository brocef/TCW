# TCW-69 — Core work model: stage table, item folders that never move, and advance

Imported on 2026-10-01 from [TCW-69](https://proposit.atlassian.net/browse/TCW-69) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review).

h1. What this delivers

The backend-independent model every other slice builds on: what a work item is, how it is identified, which stages it moves through, how it moves, and the small set of operations every backend implements.

h1. Identity

* A work item's slug is {{{tcw-config.id}/{work item folder name inside tcw-config.work.path}}} and identifies the item everywhere, including across projects.
* "Project" is the one term for a TCW-configured repo or package (replacing "node" and "connected project"), in commands, config keys and code.
* Item folders never move: there are no status directories. The folder exists from the moment the item exists.
* TCW never deletes item folders. "Finished" means completed or discarded; {{list}} hides finished items by default.
* {{validate}} warns about references to missing items. A reference into a project that cannot be resolved locally is reported as unresolved, not as an error.
* Renaming an item can leave references in other projects stale; {{validate}} in those projects reports them.

h1. Item properties (one set, shared by both backends)

* title, stage, priority (highest, high, medium, low, lowest), effort (low, medium, high, very-high), complexity (same scale), tags, assignee (optional), parent (optional slug), blocked-by (slugs, possibly in other projects).
* The slug is not stored. There is no per-item schema version and *no* {{history}} list.
* Creation date: filesystem mode reads it from the folder name's date prefix; Jira mode from the ticket.
* Only {{blocked-by}} is stored; "blocks" is found by scanning, and {{edit --blocks}} writes the other item's {{blocked-by}}. A blocker is always an item.
* {{parent}} is the only hierarchy field; the epic type and {{--initiative}} go. An item with children is an epic. No depth limit in the model.
* {{new}}, {{edit}}, {{list}} and {{show}} take the same flags in both modes.

h1. The stage table

Stages are data: one built-in table. Stage names appear only in that table, so project-defined stages can be added later. Columns: name, kind, order, artifact, prompt, gates, enabled.

||Stage||Kind||Artifact||Can be disabled||
|inbox|flow|none|no|
|request|flow|{{request/request.md}} (Jira mode: ticket body)|no|
|spec|flow|{{spec/spec.md}}, {{spec/capabilities.yaml}}|yes|
|plan|flow|{{plan/plan.md}}|yes|
|implement|flow|{{implement/round-N.md}}|no|
|review|flow|{{review/round-N.md}}|yes|
|qa|flow|{{qa/round-N.md}} (Jira mode: the ticket)|yes|
|completed|terminal|none|no|
|discarded|terminal|none|no|
|postmortem|side|{{postmortem/postmortem.md}}|yes|

* Only stages with an artifact get a folder. A side stage never changes an item's stage.
* An item's stage may be *absent* when the backend cannot report one (Jira: an unmapped status). Operations that need a stage refuse (exit 3); {{advance --to <stage> --force --reason}} sets one.

h1. Moving items: {{advance}}

{{tcw work advance <slug> [--to <stage>] [--force --reason <text>] [--dry-run]}} replaces start, submit, rework, complete and drop.

* A bare {{advance}} goes to the next enabled flow stage, or back to implement when the latest review or qa round is rejected.
* {{--to}} may name any stage. Moving back needs no force. *Skipping forward past an enabled stage requires* {{--force}}.
* Only the target stage's {{pre}} gates run. A failure refuses the move (exit 3) unless {{--force}}.
* {{--force}} requires {{--reason}}. A forced move, and every discard, posts a comment with the reason through the backend's comment operation. That is the trace in both modes.
* {{post}} hooks run after the move; a failure keeps the move and exits 6.
* {{--dry-run}} runs the gates only (replaces {{stage gate}}).
* {{discard <slug> --reason <text>}} is shorthand for {{advance --to discarded}}.
* Creating an item ({{new}}, {{adopt}}, delegation) is not a move and runs no gates. {{new}} starts at request; {{new --stage inbox}} is allowed in filesystem mode.

h1. Built-in gates

* *Records gate* on the stage after implement (review, or whichever enabled stage follows): {{spec/capabilities.yaml}} deltas match the records. {{new}} paths exist and are not {{Missing}}; {{removed}} paths are gone; {{changed}} paths exist. This replaces today's completion-time {{capability_gate}} (tcw/work/recursion.py), whose logic assumes planned {{Missing}} records and must be rewritten.
* *Completion gate*: the latest round of each enabled verification stage kept as files is {{accepted}}. In Jira mode the qa verdict is the status move itself (see TCW-71), so only review rounds are checked there.
* *No Definition of Done.* {{dod.yaml}} is removed; a project gates completion however it likes with its own {{pre}} hooks.
* {{capabilities drift}} reads {{spec/capabilities.yaml}} from completed items.

h1. Stage folders and files

* Revised documents are {{<stage>/<stage>.md}}. Loop stages write {{round-N.md}}, numbered per stage, with {{verdict: accepted | rejected}} in front matter.
* Handoffs: {{<stage>/handoff-<UTC timestamp, YYYYMMDDTHHMMSSZ>.md}}; the newest wins.
* TCW supplies paths (e.g. {{tcw work path <slug> review --next}}); the agent writes the files.

h1. Configuration shape

* Per stage: {{work.stages.<stage>: { enabled, status (Jira mode), prompt, pre, post }}}. The {{transitions}} block is removed.
* {{prompt}}, {{pre}}, {{post}} and {{procedures}} lists resolve through the {{inherit}} chain defined in TCW-72.
* Removed keys: {{auto-commit-transitions}}, {{publish-transitions}}, {{trunk-branch}}, {{retain}}. Unknown or removed keys are an error, so a leftover 2.x key is caught.

h1. Backend operations

Every backend implements: create, read, list, update properties, set stage, comment, rename. {{path}} and artifact files are shared layout, not backend operations. TCW-70 and TCW-71 implement these.

h1. Git

TCW never changes git state (no add, commit, mv, rm, reset, checkout, merge, worktree or push). It writes files, names them on stderr, and may read git for checks.

h1. Open questions for the spec

* Exact {{capabilities.yaml}} schema, including new taxonomy entries.
* Whether {{validate}} should also report an item whose stage is ahead of its artifacts in filesystem mode (a hand-edited {{stage}}), as it does for Jira.
