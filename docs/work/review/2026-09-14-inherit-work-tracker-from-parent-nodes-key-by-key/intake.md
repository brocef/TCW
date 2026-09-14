# Inherit work.tracker from parent nodes, key by key

## Origin

GitHub issue [#36](https://github.com/brocef/TCW/issues/36), filed 2026-09-14
by @brocef.

> ### Motivation
>
> `work.tracker` has to be written out in full in every node's `tcw-config.yaml`. In a workspace with one parent node and several child nodes that all read the **same** Jira project, the blocks are identical except for `candidate-query`. The only thing that should differ is which slice of the project each node lists.
>
> Our setup has six nodes (a workspace root, a repository root beneath it, and packages beneath that). Each node lists the tickets filed against itself or anything beneath it, using one Jira component per node. The result is six copies of this block:
>
> ```yaml
> work:
>     tracker:
>         provider: jira-cloud
>         base-url: https://example.atlassian.net
>         candidate-query: project = EX AND component = api AND status = "To Do" AND (assignee = currentUser() OR assignee IS EMPTY)
>         credentials:
>             email-env: EXAMPLE_JIRA_EMAIL
>             token-env: EXAMPLE_JIRA_API_TOKEN
>         transitions:
>             claim: Start
> ```
>
> Only `candidate-query` changes from node to node (`component = api`, `component = web`, `component in (shared, ui)`, `project = EX` at the root, and so on). `provider`, `base-url`, `credentials` and `transitions.claim` describe the Jira site and its workflow, not the node, so they are the same everywhere.
>
> The copies drift apart easily. Renaming the claim transition in Jira, moving to another site, or renaming a credential variable means editing every node. A node that is missed still parses, so nothing reports it, and it keeps the old value: for example, it goes on reporting every ticket as offering no `Start`. A copy damaged during the edit is worse, because `parse_tracker_config` rejects the whole block, so that node has no tracker at all until someone notices.
>
> Nothing inherits today: `tcw/store/fs.py` reads `work.tracker` from the node's own config only, and among the connections between nodes, only the taxonomy's `extends` resolves anything from another node.
>
> ### Description
>
> Let a node's `work.tracker` inherit from its `connected-projects.parent`, key by key, with the child's keys winning. A child that only narrows the query would then write:
>
> ```yaml
> work:
>     tracker:
>         candidate-query: project = EX AND component = api AND status = "To Do"
> ```
>
> A few details that seem worth settling in the design:
>
> - **Merge per key, not per block.** A child that writes `tracker:` should not lose the parent's `credentials` and `transitions` by doing so. Nested mappings (`credentials`, `transitions`) would merge the same way.
> - **Opting out.** A child that genuinely tracks nothing, or reads a different site, needs a way to say so, for example `tracker: none`, or simply supplying its own `base-url`.
> - **Validation.** `tcw validate` would check the merged result, and its problem messages would name the file each value came from, as `tracker_problems` already prefixes messages with the file they came from.
> - **Inherit one level or all the way up.** Whether this goes one level or up the whole chain of parents matters for three-level workspaces like ours (workspace root → repository root → packages). All the way up is what we would want, but taxonomy `extends` resolves only one level, so a note on which rule applies would help either way.
>
> This concerns the **work** axis, and fits alongside the planned claim, sync and strict-mode tracker items rather than replacing any of them. Those will add more keys under `work.tracker` (landing statuses, sync transitions, a strict flag), which makes the duplication grow.
>
> ### Benefits
>
> - One place to change the site, credentials, or workflow transition names for a whole workspace.
> - No stale copy is left in a node someone forgot, silently reporting against old values.
> - Adding a node to a workspace takes one line of tracker configuration instead of a full block.
>
> ### Side notes from testing the same integration (no separate issue needed)
>
> We ran a ticket through a directed workflow by hand (Triage → `Accept` → To Do → `Start` → In Progress → `Complete` → Done), running `tcw work tracker show` at each step. On tcw 2.1.1 everything behaved as documented. Two pieces of wording read as more certain than the situation is:
>
> 1. **The note for a claim that is not offered covers only two cases.** For a ticket in Triage (*before* the claim applies) the output was:
>
>    ```
>    claimable: not claimable
>    workflow: not determined from this ticket
>    note: work.tracker.transitions.claim is 'Start', which this ticket does not offer. It offers: 'Accept', 'Cancel'. Either the name is wrong, or this ticket is past the point where it applies — one ticket cannot tell those apart.
>    ```
>
>    The ticket was neither misnamed nor past the point; it had not reached it yet. Something like "the name is wrong, or this ticket is not at the point where it applies (before it, or already past it)" would cover all three.
>
> 2. **The To Do note points to a check that `show` cannot perform.** For the same ticket in To Do it said:
>
>    ```
>    note: 'Start' leads to 'In Progress'. Exclusivity can only be read from a ticket already in that status.
>    ```
>
>    Running `show` on the ticket once it was In Progress still printed `workflow: not determined from this ticket`, because `show` never passes `landing_status` to `assess()`. We understand why: a ticket that does not offer the claim cannot say where the claim leads, and the docstring in `claim.py` explains this well. A second `Start` on that ticket was in fact refused by Jira with HTTP 400, so the workflow was exclusive. The note is just worded as though a second `show` would answer it. Rewording it to say exclusivity is confirmed at claim time, or from the workflow definition, would stop readers from trying.
>
> ### Environment
>
> - tcw version: tcw 2.1.1
> - OS / platform: macOS 26.6.2
> - Install method: editable
> - Tracker: Jira Cloud, company-managed project with a custom directed workflow
>

## Triage notes

- The two wording notes under "Side notes from testing" (`tcw/tracker/claim.py`,
  the claim-not-offered and To Do notes) are not this item's scope. They were
  recorded on the active item
  `2026-09-12-configure-an-external-tracker-and-read-its-tickets`, which owns
  that code.
- The report says taxonomy `extends` resolves one level only. That is out of
  date: `2026-07-01-transitive-taxonomy-inheritance` (completed) made it
  resolve through the whole chain of parents, which is a precedent for the
  "inherit one level or all the way up" question.
