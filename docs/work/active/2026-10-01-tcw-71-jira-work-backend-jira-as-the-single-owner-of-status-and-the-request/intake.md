# TCW-71 — Jira work backend: Jira as the single owner of status and the request

Imported on 2026-10-01 from [TCW-71](https://proposit.atlassian.net/browse/TCW-71) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review). Builds on TCW-69.

h1. What this delivers

The Jira-first configuration: Jira owns everything a non-engineer reads or changes about a work item, and the repository owns the technical record. Nothing Jira owns is copied to disk, so there is nothing to keep in sync. This replaces the current tracker integration (sync, retry queue, link/unlink, claims, strict mode). Jira Cloud only.

h1. Ownership and identity

* Jira owns status, the request text (ticket body), assignee, estimates, tags (labels), parent/child and blocking links. TCW reads Jira live and writes to it directly.
* Every work item has exactly one ticket; not every ticket has a work item.
* The ticket always exists before the item. Folder names are {{<KEY>-<title words>}} (no date prefix), e.g. {{tcw/TCW-67-formalize-jira-in-work-lifecycle}}.
* {{item.yaml}} holds only {{ticket: <url>}}, as a convenience link. The key in the folder name is authoritative; {{validate}} flags a mismatch.
* {{rename}} may change only the part after the key.
* TCW always sets two custom fields on tickets it creates or adopts: *TCW Project* (the owning project's {{tcw-config.id}}) and *TCW Item* (the slug). "Required" means TCW always sets them, not that Jira's field configuration enforces them.

h1. Configuration (sketch)

{code:yaml}work:
  backend: jira
  jira:
    site: https://example.atlassian.net
    project: TCW
    credentials: {email-env: TCW_JIRA_EMAIL, token-env: TCW_JIRA_API_KEY}
    fields: {project: TCW Project, item: TCW Item, effort: Effort, complexity: Complexity}
    priorities: {highest: Highest, high: High, medium: Medium, low: Low, lowest: Lowest}
    inbox-query: ...      # optional; widens the default inbox
  stages:
    inbox:     {status: Triage}
    request:   {status: To Do}
    spec:      {status: Specifying}
    # ...one distinct status per enabled stage{code}

The effort and complexity fields are optional; if they are not configured, those flags are refused with a clear message.

h1. Stages and statuses

* Each enabled stage maps to exactly one status; no two stages share one. The stage is read directly from the status.
* *Status only changes through a workflow transition.* {{advance}} uses the one transition offered from the current status whose destination is the target stage's status. If there is none, or more than one, it refuses (exit 3) and lists what was offered. It never walks through intermediate statuses. It re-reads the status afterwards to confirm the move applied.
* Other statuses may exist. An item in an unmapped status has no stage (TCW-69).
* Moving a ticket by hand in Jira counts as a forced move without a recorded reason; {{tcw validate --remote}} reports items whose status is ahead of their artifacts.
* Forced moves and discards post a ticket comment with the reason.

h1. Inbox and adoption

* In Jira mode *an inbox entry is never an item*: it is a ticket without one. {{new}} and {{adopt}} both start the item at request.
* Default inbox: tickets in the configured Jira project at the inbox status, where TCW Item is empty and TCW Project is either this project or empty. That way tickets written by people outside engineering, who won't fill in TCW fields, still appear. A project can widen this with {{inbox-query}}.
* {{tcw work tickets list}} lists them; {{tcw work tickets adopt <KEY>}} adopts one: refuse (exit 3) if TCW Item is already set, then set TCW Project and TCW Item, then create the folder, then move to request. Two people adopting the same ticket at the same moment is a known limit.

h1. QA in Jira mode

* QA happens on the ticket. The verdict is the status move out of qa: to completed (accepted) or back to implement (rejected). A rejection requires a comment saying why.
* There are no {{qa/round-N.md}} files. The implement prompt reads the latest rejection comment. The completion gate checks only review rounds (TCW-69).

h1. Property mapping

* title to Summary; stage to Status; priority to Priority (mapped in config); effort and complexity to configured fields; tags to Labels; assignee to Assignee; parent to Parent; blocked-by to a Blocks link.
* Children are created as the parent's type allows (Epic, Task, Sub-task), and Jira's refusal is reported clearly.
* {{show}} displays links to tickets that have no item as bare keys.
* {{list}} uses one batched JQL query on TCW Project, not one request per item.

h1. Delegation

* {{tcw work new "title" --project <id>}} creates the ticket in the target's Jira project and puts it in the target's inbox status, with TCW Project set. If the target's folder can be created (path resolved, work store present, no uncommitted changes in it), it also creates the folder, sets TCW Item and moves the ticket to request. Otherwise the ticket stays in the target's inbox.
* stdout prints a slug or a ticket key, so the caller knows which happened.
* Delegation runs no gates, since creation is not a move.
* The target's Jira site, project, inbox status and credential variable names come from its config, or from the delegator's connected-project entry.

h1. Network, identity and compatibility

* Jira mode needs the network to create items or read status. {{tcw validate}} checks only what git owns and never needs the network. {{tcw validate --remote}} adds the Jira checks.
* The user's identity comes from the Jira credentials.
* *Workflow compatibility* is part of {{tcw validate --remote}}. It checks that a distinct status exists for each enabled stage, that every move {{advance}} needs is offered as a transition, and that the custom fields exist. The {{setup}} skill uses it to work through any needed changes with the user; nothing is changed automatically.

h1. Open questions for the spec

* Behavior with team-managed projects, and cross-project parents.
* Transition screens with required fields (e.g. a resolution on the done status).

h1. Update from TCW-69's spec (2026-10-01)

* {{set_stage(folder, stage, note)}} should send the note as the transition's comment in the same request, and return the status read back afterwards.
* New operation {{lookup(key)}}: return the folder named exactly {{<KEY>-…}}, or none.
* qa is an external stage. Accepting is {{advance --to completed --reason …}} and rejecting is {{advance --to implement --reason …}}; both post the reason as a comment. A bare {{advance}} from qa is refused.
* {{advance --to inbox}} is refused in Jira mode, since an inbox entry is a ticket without an item.
