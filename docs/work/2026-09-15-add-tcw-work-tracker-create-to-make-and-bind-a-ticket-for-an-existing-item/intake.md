# Add tcw work tracker create to make and bind a ticket for an existing item

## Origin

GitHub issue [#43](https://github.com/brocef/TCW/issues/43), filed 2026-09-15 by @brocef:
**Add tcw work tracker create: make and bind a ticket for an existing work item**

> ### Motivation
>
> The tracker integration can go in one direction only: from a ticket to a work item. `tcw work tracker import` creates an item from a ticket, and `link` binds two things that already exist. There is no command that creates a ticket for an item that already exists.
>
> That is the first thing a team with an existing TCW backlog needs. In our first real use we had 125 open items across six nodes, only 9 of which had tickets. Getting the other 116 into Jira meant writing a script against the Jira REST API, outside TCW, that:
>
> - created each ticket with the item's title as its summary and a description written from the item's request documents
> - chose an issue type (Epic for items with child items, Bug for items tagged `bug`, Task otherwise)
> - set the ticket's parent from the item's parent item or its epic (`initiative`)
> - set components from the node the item lives in
> - moved the ticket out of the workflow's initial status to the one matching the item (backlog → To Do)
> - ran `tcw work tracker link <slug> <key>` in the right node, and kept a record of created keys so a re-run would not create a second ticket
>
> All of that is information TCW already has, and most of it is decided the same way for every item, so every team adopting the integration will write a version of that script.
>
> ### Description
>
> Add a command that creates a ticket for an existing item and binds it, for example:
>
> ```text
> tcw work tracker create <slug> [--type <issue type>] [--parent <ticket>] [--dry-run]
> tcw work tracker create --all [--status backlog,active,review] [--dry-run]
> ```
>
> Configured under `work.tracker`, inheriting like the rest of the block:
>
> ```yaml
>         create:
>             project: EX
>             issue-type: Task
>             issue-types:            # optional, first match wins
>                 epic: Epic          # item type epic, or an item with child items
>                 tag:bug: Bug
>             components: [api]       # per node, so each node sets its own
>             description: request    # which item document seeds the description
> ```
>
> Behaviour worth having:
>
> - **Summary and description** from the item's title and its request (or intake). Formatting would be converted to the tracker's own format, which for Jira Cloud is its document format (ADF), not Markdown.
> - **Parent** from the item's parent item or `initiative` when that item is bound, so epics are created before their children. `--all` can order that itself.
> - **Status** brought to the item's status through the configured `transitions` and `statuses`, using the same rules as sync. A backlog item's ticket ends where the claim transition starts. With `--all`, an already-bound item is skipped, never created twice.
> - **Safe to re-run.** Write the binding immediately after the ticket exists, so an interrupted run resumes by linking rather than creating a duplicate. This is the same property `import` already has for an interrupted claim.
> - **`--dry-run`** prints what would be created, with type, parent and components, so a large first run can be checked before anything is written.
>
> This concerns the **work** axis (tracker bindings). It pairs with #37, which covers writing the item reference into a field on the ticket.
>
> ### Benefits
>
> - Adopting the integration on an existing backlog becomes one command instead of a custom script.
> - Tickets created this way are consistent: same types, same parent links, same starting status.
> - The two directions line up: `import` brings ticket-first work into TCW, and `create` brings item-first work into the tracker.
