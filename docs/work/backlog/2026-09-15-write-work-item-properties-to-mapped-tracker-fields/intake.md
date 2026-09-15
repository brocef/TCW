# Write work item properties to mapped tracker fields

## Origin

GitHub issue [#37](https://github.com/brocef/TCW/issues/37), filed 2026-09-14 by @brocef:
**Write the work item reference to a configured tracker field when binding a ticket**

> ### Motivation
>
> A binding made with `tcw work tracker import` or `tcw work tracker link` points one way only. The work item records the ticket in `tracker.yaml` (key, id and URL). The ticket gets nothing, so someone reading the ticket in Jira has no way to see which work item it belongs to.
>
> Teams that want the reverse reference usually add a custom field to their Jira project for it. We did: a single-line text field named "TCW Item" that holds `<project-id>/<slug>`, for example:
>
> ```text
> TCW Item: example-api/2026-09-10-consolidate-the-route-error-handling
> ```
>
> That value is what makes the ticket side searchable in JQL, visible on boards, and usable in Jira filters and automation. Today it has to be typed by hand after every `link` or `import`, or edited in bulk later. After linking nine tickets we had to go back and fill it in on all nine, copying each project id and slug from `tracker.yaml`. It is easy to forget, easy to mistype (slugs are long), and nothing notices when it drifts from the binding.
>
> ### Description
>
> Let a node name a tracker field that TCW fills with the item reference whenever it makes a binding.
>
> ```yaml
> work:
>     tracker:
>         # ...existing settings...
>         fields:
>             item: customfield_10042 # or the field's display name, "TCW Item"
> ```
>
> Behaviour:
>
> - **`import` and `link`** write the reference to that field after the binding is recorded. The default value is `<project-id>/<slug>`, the same stable identifier a `tcw://W/<project-id>/<slug>` link uses, so the ticket names the item exactly as TCW's own references do and never by a filesystem path; an optional template (for example `item-format: "{project}/{slug}"`, with `{part}` available) would cover teams using a different convention, but the default alone would already cover most setups.
> - **`unlink`** clears the field, but only if it still holds this binding's value, so a reference someone has since pointed elsewhere is left alone.
> - **Inheritance** works like the rest of `work.tracker` (v2.1.3): set `fields.item` once at the workspace root and every child node uses it.
> - **Only a field write.** It needs no transition and no change of assignee. That keeps it compatible with a `link` that records cross-references without claiming the ticket, which we have also asked for separately.
>
> Details worth deciding in the design:
>
> - **When the write fails.** Jira refuses a field that is not on the ticket's edit screen, or one the account cannot edit. The binding is already recorded by then, so the command should keep it, print Jira's reason and exit non-zero, and running the same command again should fill the field in without creating a second binding. This matches how `import` already finishes after an interrupted claim.
> - **Length.** Jira caps a single-line text field at 255 characters. A project id plus a long slug can come near that; refusing with a clear message is better than truncating.
> - **Several items for one ticket (`--part`).** One text field cannot hold several references. The options are to write only the default part, to join the values, or to refuse, and the documentation should say which.
> - **Checking it.** `tcw validate` should keep its no-network rule and only check the setting's shape. `tracker show` could print the field's current value and whether it matches the binding, which is where drift would be noticed.
> - **Name or id.** Accepting the display name is friendlier, but names are not unique in Jira. Resolving the name to an id, and refusing when it matches more than one field, avoids writing to the wrong one.
>
> This concerns the **work** axis (tracker bindings), and fits beside the planned outbound synchronization and board display of bindings rather than replacing either.
>
> ### Benefits
>
> - Both ends of a binding agree without anyone copying slugs by hand.
> - Jira users can find, filter and report on tickets by work item, and follow a ticket back to its item, without access to the repository.
> - Jira automation can key off the field, for example flagging tickets in progress with no work item.

Comment on #37 by @brocef, 2026-09-15:

> **Suggestion: widen this issue from one field to a mapping of work item properties, kept in step on edit (priority, estimates, tags).**
>
> ### Motivation
>
> Once a ticket is bound, the work item and the ticket describe the same work, but the only thing TCW keeps in step between them is status. Every other property a team cares about on the Jira side has to be copied by hand and kept current by hand.
>
> This issue asks for one such field: the work item reference, written when a ticket is bound. That covers the reverse link, but it is one case of a wider need. Work items already carry properties that teams also track in Jira:
>
> - `priority`, an integer set with `tcw work new --priority N` or `tcw work edit <slug> --priority N`
> - `effort` and `complexity` (low, medium, high, very-high)
> - `tags`
> - `title`
> - the owning epic (`initiative`), which corresponds to a ticket's parent
>
> A concrete example: we would like to switch our Jira project to a numeric priority field so it can hold the same integer our work items use. Then every board and filter would sort the way `tcw work list` does. Today that means setting the number twice, in two places, and it drifts the first time someone runs `tcw work edit --priority` and forgets the ticket.
>
> ### Description
>
> Generalise the `fields` block proposed above into a mapping from item properties to tracker fields:
>
> ```yaml
> work:
>     tracker:
>         # ...existing settings...
>         fields:
>             item: customfield_10042          # the reference proposed above: <project-id>/<slug>
>             priority: customfield_10050      # a number field
>             effort: customfield_10051        # a select list; values mapped below
>             tags: labels
>         field-values:
>             effort:
>                 low: S
>                 medium: M
>                 high: L
>                 very-high: XL
> ```
>
> Behaviour:
>
> - **When fields are written.** On `import` and `link`, TCW writes every mapped field. On `tcw work edit`, it writes any mapped property that changed. That makes an edit to a bound item one more outbound move, handled like the status moves: after the local change and its commit, a failure recorded in `tracker.yaml`, and a retry with `tcw work tracker sync`.
> - **Direction.** Only from the item to the ticket, as status sync works today. TCW never reads a field back into the item.
> - **Value conversion.** An integer property goes to a number field as-is. An enumerated property (effort, complexity) goes through `field-values` when the target is a select list. Tags go to labels or to a multi-select field. A value with no mapping is not sent, and `validate` reports it.
> - **Only mapped properties.** With no `fields` block nothing changes, and nothing is ever written to a field that was not named.
> - **Inheritance.** Same rules as the rest of `work.tracker`: set once at the workspace root and every child node uses it.
>
> Details worth settling in the design, beyond those this issue already lists:
>
> - **Priority direction and scale.** TCW's rule is "higher is more urgent". A Jira number field has no built-in direction, so the documentation should state that the value is copied unchanged. A team using Jira's own Priority field (High/Medium/Low) would need a range mapping instead, for example `80-100: Highest`, which could come later.
> - **Overwriting a hand edit.** If someone changes the field in Jira, the next `tcw work edit` of that property overwrites it. That fits "the item is the source", but it is worth saying plainly, and `tracker show` could report fields whose current value differs from the item.
> - **Backfilling.** Items bound before a mapping is added need a way to fill their fields, for example `tcw work tracker sync --all --fields`, since no edit will happen to trigger it.
>
> This concerns the **work** axis (tracker bindings and outbound sync). It extends this issue rather than replacing it.
>
> ### Benefits
>
> - Priority, estimates and labels set in TCW appear on Jira boards, filters and reports without anyone copying them over.
> - Values stop drifting between the two sides, because an edit to the item carries through to the ticket.
> - A team can adopt Jira views, such as boards sorted by priority or filtered by label, without giving up TCW as the place the work is planned.

## Triage (2026-09-15)

Accepted with its widening comment: the item covers writing the work item reference
**and** a mapping of other item properties (priority, estimates, tags) to tracker
fields, kept in step on edit. Kept separate from GitHub #43 (`tracker create`), which
it pairs with, because each is a large change on its own.
