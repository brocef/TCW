# Jira work backend: Jira as the single owner of status and the request

TCW 2.x keeps a work item's status, title and properties on disk and copies status
out to a Jira ticket afterwards. A large amount of machinery exists only to keep the
two in step: a sync step after every lifecycle move, a record of moves that did not
reach Jira yet (a retry queue in all but name), `link`/`unlink` to bind and unbind
tickets, claims, and a strict mode that refuses local work no claimed ticket
authorizes. TCW 3.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68))
removes the copying instead of improving it: in a project that chooses Jira, each
fact lives only in Jira or only in the repository.

This slice is that Jira configuration. It builds on the core work model
([TCW-69](https://proposit.atlassian.net/browse/TCW-69)) and is the second of its two
backends; [TCW-70](https://proposit.atlassian.net/browse/TCW-70) is the filesystem one.

## What is wanted

A Jira Cloud work backend in which:

1. **Jira owns everything a non-engineer reads or changes** about a work item: its
   status, the request (the ticket body), assignee, priority, estimates, labels,
   parent and blocking links. TCW reads these live and writes them directly. None of
   them is stored on disk, so there is nothing to keep in sync.
2. **The repository owns the technical record**: specs, plans, implementation and
   review rounds, handoffs, and the declared capability changes, laid out exactly as
   TCW-69 defines for both backends.
3. **Every work item has exactly one ticket, and the ticket exists first.** The item
   folder is named `<KEY>-<title words>` (for example `TCW-67-formalize-jira-in-work-lifecycle`),
   the key in the name is authoritative, and `item.yaml` holds only a link to the
   ticket. Two custom fields on the ticket, *TCW Project* and *TCW Item*, say which
   TCW project and which item it belongs to.
4. **Each enabled stage is exactly one Jira status**, and a stage change is always
   one workflow transition, carrying the reason as a comment when there is one. TCW
   never walks a ticket through statuses in between, and refuses when the workflow
   does not offer exactly one way to the target.
5. **The inbox is Jira's**: tickets with no item. `tcw work tickets list` shows
   them and `tcw work tickets adopt <KEY>` turns one into an item, so people outside
   engineering can write tickets that never mention TCW and still have them picked up.
6. **QA happens on the ticket.** A person accepts or rejects by moving it out of
   the qa status; a rejection carries a comment saying why.
7. **Delegation** (`tcw work new "title" --project <id>`) can create work in another
   project that uses Jira, as far as that project can be reached from here.
8. **`tcw validate --remote`** checks the Jira side: that the workflow offers
   every move TCW needs, that the custom fields exist, and that each item and its
   ticket agree. Plain `tcw validate` stays offline.
9. **The 2.x tracker integration is removed**: sync, the record of moves owed to
   Jira, link/unlink, claims, strict mode and every `tcw work tracker` command.

The agreed decisions, refined after an adversarial review, are in the ticket;
`intake.md` holds it as imported, including its "Update from TCW-69's spec" section.
They are the requirement. Where they differ from the epic's attached decision record,
the ticket is current. Where they differ from TCW-69's finished spec on anything
TCW-69 defines (the stage table, the backend operations, `advance`, configuration
shape, exit codes), TCW-69 is current.

## Constraints

- **Jira Cloud only.** No Jira Server or Data Center, and no second tracker.
- **Simplicity of implementation comes first.** Each operation should be one
  predictable sequence of requests. Nothing from 2.x is kept because it exists; the
  HTTP client is kept only if it fits.
- **Breaking changes are expected.** This ships in 3.0.0. No 2.x compatibility
  code; moving an existing project over is the written migration guide (TCW-76).
- **Designed for any Jira project**, not only TCW's own: company-managed and
  team-managed projects, workflows the owner did not design, statuses with other
  names.
- **The network is needed only where Jira owns the fact.** Creating items and
  reading status need Jira; plain `tcw validate` and every check of what git owns
  must work offline.
- **TCW never changes git state.** It writes files and names them on stderr.
- **Tests cannot reach the real Jira in continuous integration.**
- **Every operation passes the abstraction litmus test**
  ([`docs/lifecycle/abstraction.md`](../../../lifecycle/abstraction.md)).

## Out of scope

Owned by the sibling slices, not this one:

- The model itself: stage table, properties, layout, `advance`, gates, the backend
  interface and `work.*` parsing: TCW-69.
- The filesystem backend, and switching the CLI over from the 2.x work store: TCW-70.
- Personal configuration layers, and which keys a person may override: TCW-72.
- The final command names, the stdout/stderr contract and the exit-code table:
  TCW-73. This slice implements its Jira commands within that contract.
- Stage prompts and skills, including the `setup` skill's workflow walkthrough:
  TCW-74. Guides, including `docs/guide/jira.md`: TCW-75. Migrating existing
  projects, including TCW's own board and Jira project: TCW-76. The web viewer:
  TCW-77.

## Notes

- **There was no requester to ask.** This request was written by an agent from the
  ticket, the epic, its decision record, the sibling tickets and TCW-69's spec,
  without a conversation. Everything below marked *assumption* is inference, for the
  `spec` stage to confirm or overturn.
- Reference material was not asked for, since there was nobody to ask; the
  references below are the ones the epic's reference pack supplies, plus repository
  files found while reading.
- **Assumption:** the 2.x tracker code is removed by this slice, as the ticket's
  first section says ("This replaces the current tracker integration"). TCW-70
  removes the 2.x work store that much of that code is built on, so the `spec`
  stage must say which slice deletes which part.
- **Assumption:** the ticket's configuration block is a sketch. Anything Jira
  requires that it leaves out (for example the issue type a new ticket is created
  with) is for the `spec` stage to add.
- **Open questions the ticket hands to `spec`:** behavior with team-managed
  projects and with parents in another Jira project; and transitions whose screens
  have required fields, such as a resolution on the done status. The `spec` stage
  also has to decide how the backend is tested without the real Jira, and whether a
  manual run against a real Jira project is part of acceptance.
- **Superseded backlog items.** Several 2.x items in `docs/work/backlog/` describe
  tracker features this slice removes or absorbs (for example
  `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`
  and `2026-09-15-write-work-item-properties-to-mapped-tracker-fields`). Whether
  they are discarded or merged is the owner's call; `spec` lists them.
- **Self-hosting.** This changes `tcw/` itself, so from implementation onwards the
  repository's own board is driven by editing files, not through the CLI, as
  `CLAUDE.md` requires.

## References

- [TCW-71](https://proposit.atlassian.net/browse/TCW-71): the ticket; the agreed
  decisions for this slice (`intake.md`).
- [TCW-69](https://proposit.atlassian.net/browse/TCW-69) and its `spec.md`: the
  model this backend implements, including the eight backend operations,
  `external_stages`, `inbox_items`, and the qa reason rules. Must not be redefined
  here.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68): the epic's vision, and the
  attached decision record of the design session.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70): the sibling backend, and
  the slice that removes the 2.x work store the tracker code depends on.
- [TCW-72](https://proposit.atlassian.net/browse/TCW-72),
  [TCW-73](https://proposit.atlassian.net/browse/TCW-73),
  [TCW-74](https://proposit.atlassian.net/browse/TCW-74),
  [TCW-76](https://proposit.atlassian.net/browse/TCW-76),
  [TCW-77](https://proposit.atlassian.net/browse/TCW-77): slices that consume this
  backend (credentials and identity, the command surface, the setup walkthrough,
  migration, the viewer's Jira mode).
- `tcw/tracker/jira.py`: the 2.x Jira Cloud client, a candidate for reuse as the
  HTTP layer.
- `tests/tracker_fake.py`: the 2.x stateful fake Jira used in tests, a candidate
  for reuse.
- `docs/work/backlog/2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate/`:
  prior thinking on checking a Jira workflow ahead of time, including the
  permission problem with reading workflow definitions.
