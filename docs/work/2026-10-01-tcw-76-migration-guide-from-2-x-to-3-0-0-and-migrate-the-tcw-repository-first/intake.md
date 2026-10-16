# TCW-76 — Migration guide from 2.x to 3.0.0, and migrate the TCW repository first

Imported on 2026-10-01 from [TCW-76](https://proposit.atlassian.net/browse/TCW-76) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review). Done last, once the 3.0 layout is settled.

h1. What this delivers

A written, agent-followed procedure that moves a project from 2.8 to 3.0.0, proven by migrating the TCW repository itself before release. The first migration is a Jira-mode migration of TCW's own board: 25 items (17 bound to tickets), 10 inbox entries, a 310-entry {{graveyard.yaml}} and a {{dod.yaml}}.

h1. The guide

* *The guide is the only migration tool.* No 2.x detection or conversion code ships in 3.0; {{tcw validate}} knows only the 3.0 layout.
* File: {{docs/migration-guide-2.8-to-3.0.0.md}}. Earlier 2.x projects upgrade to 2.8 first.
* Written for an agent: ordered steps, a check after each that the agent can make by inspection, and explicit points where it stops and asks the user. It asks once, with a consolidated plan, rather than once per item.

h1. Order

# Choose backend.
# *Jira mode: prepare Jira.* Add one status per enabled stage, add transitions for every move {{advance}} needs, and create the TCW Project, TCW Item, effort and complexity fields. Then run {{tcw validate --remote}}'s compatibility check.
# Rewrite config, key by key (table below).
# Flatten the store and give every item a stage (table below).
# Convert item files (field table below).
# *Jira mode: bind.*
#* Reconcile bound tickets with disk.
#* Create tickets for items and inbox entries that have none.
#* Set TCW Project and TCW Item.
#* Rename folders to {{<KEY>-<title words>}}.
# Move artifacts.
# Convert the inbox.
# Rewrite live references ({{parent}}, {{blocked-by}}, open items' artifacts). Old slugs in historical text are left alone.
# Review the project's own prompts, hooks, scripts and agent docs.
# Validate clean.

h1. Status folder to stage

||2.x folder||3.0 stage||
|inbox (loose {{.md}})|filesystem: an inbox-stage item; Jira: a ticket in the inbox status|
|backlog|request if only a request exists, spec if {{spec.md}} exists, plan if {{plan.md}} exists|
|active|implement|
|review|qa (old verify was the user's acceptance)|
|blocked|the stage its artifacts imply, keeping {{blocked-by}}|
|completed|completed|
|discarded|discarded; any resolution reason becomes a comment|

h1. Fields

* {{state.yaml}} + {{tracker.yaml}} → {{item.yaml}}:
** {{title}} → title.
** {{priority}}: integers become named values (≥40 highest, 30–39 high, 20–29 medium, 10–19 low, <10 lowest); missing becomes medium.
** {{effort}}, {{complexity}} and {{tags}} carry over.
** {{owner}} → assignee.
** {{blocked_by}} → {{blocked-by}}, with the project prefix (Jira mode: Blocks links).
** {{epic}}, {{initiative}} and {{type}} → {{parent}}.
** {{started}}, {{completed}}, {{phase}}, {{resolution}} and {{schema}} are dropped. A discard reason becomes a comment.
** The {{tracker.yaml}} keys {{part}}, {{unlinked}}, {{schema}} and {{bound}} are dropped once binding is done.
* *Artifacts:*
** {{intake.md}} + {{initial-request.md}} → {{request/request.md}} (filesystem) or the ticket body (Jira). Skip asking when the body already contains the text, and batch the rest.
** {{spec.md}} → {{spec/spec.md}}; {{plan.md}} → {{plan/plan.md}}.
** {{outcome.md}} → {{implement/round-1.md}}.
** {{refined-outcome.md}} → {{qa/round-N.md}} (accepted); {{rework.md}} → {{qa/round-N.md}} (rejected). In Jira mode that history becomes comments.
** {{capabilities.yaml}} → {{spec/capabilities.yaml}}; {{post-mortem.md}} → {{postmortem/postmortem.md}}.
* *Store root:*
** {{graveyard.yaml}} is deleted (git history keeps it).
** {{dod.yaml}} is deleted, since there is no Definition of Done in 3.0.
** Items deleted under 2.x retention stay deleted.

h1. Jira-mode binding

* Every item needs a ticket. For TCW that means 8 items plus 10 inbox entries.
** *"Yes":* the agent creates them with whatever Jira access it has (web UI, REST, an MCP tool). Completed items without a ticket are created directly in the completed status.
** *"No" for an item:* its folder is deleted (git history keeps it), since a Jira-mode item without a ticket is not legal.
* *Reconciling:* where disk and ticket disagree on status or properties, disk wins, since 2.x treated disk as the source. A pending sync record (e.g. TCW-9's {{sync: pending}}) means Jira lagged. The agent shows all differences and asks once.
* Tickets created during the redesign (TCW-67 to TCW-76 and later) get TCW Project backfilled.

h1. Config, key by key

* {{work.tracker.*}} → {{work.jira.*}} and {{work.stages.<stage>.status}}:
** {{candidate-query}} and {{inbox-query}} → the default inbox, or {{inbox-query}};
** {{statuses}} and {{pre-backlog}} → per-stage {{status}};
** {{transitions.start}} → removed.
* {{lifecycle.stages.*}} → {{work.stages.*}}, with {{builtin: true}} → {{inherit: true}}.
* {{lifecycle.transitions.*}} → the matching stage's {{pre}}/{{post}}.
* {{retain}}, {{auto-commit-transitions}}, {{publish-transitions}} and {{trunk-branch}} → removed.
* The project's own scripts and docs are reviewed and fixed. For TCW: {{scripts/require_artifact.py}}, {{docs/procedures/create-work.md}} and the {{CLAUDE.md}} sections on DoD and {{refined-outcome.md}}. Prose bindings are reviewed, and the agent points out text that relies on removed behavior.

h1. TCW's own 3.0 configuration (owned here)

* The opt-in git example from TCW-75: pull as prompt text, commit as a {{post}} hook that tolerates nothing to commit, and push as the owner chooses.
* TCW's own completion gate, as a demonstration of a project-defined gate (replacing {{dod.yaml}}).
* {{work.documentation}} entries rewritten: {{Tracker-Change}} and other triggers renamed for 3.0, and {{upcoming/}} files named by folder name.

h1. Sequencing

3.0 cannot read a 2.x board, and TCW's {{CLAUDE.md}} forbids driving the lifecycle with the CLI while {{tcw/}} is changing. So the migration:

* is done with the 3.0 code frozen;
* uses the working-tree CLI only for the final {{validate}};
* lands in the same change that switches TCW to 3.0, so TCW's own gates never see a half-migrated board.

h1. Update from TCW-69's spec (2026-10-01)

The migration guide needs to cover:

* *Hook variables:* {{TCW_STATUS}}, {{TCW_TRANSITION}} and {{TCW_NODE_ROOT}} become {{TCW_STAGE}}, {{TCW_FROM_STAGE}} and {{TCW_PROJECT_ROOT}}, and {{TCW_RESOLUTION}} goes.
* *Moved settings:* {{work.lifecycle.timeout}} and {{output-cap}} move to {{work.hooks}}.
* *Templates:* {{work.lifecycle.artifacts}} templates become {{file}} bindings with a {{when:}} condition in the stage's {{prompt}} list. This repo's {{spec-bug.md}} is the first example.
* *Bindings:* a {{skill}} in {{pre}} and {{when: {type: …}}} are now config errors.
* *The* {{Planning doc}} *field:* decide what happens to it on capability records, since 3.0 drift no longer reads it.
* *Declared record changes:* {{capabilities.yaml}} stays at the item folder's root ({{<item>/capabilities.yaml}}), not {{spec/capabilities.yaml}} as the artifact table above says.
