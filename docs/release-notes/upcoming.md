# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Make a Jira ticket for a work item

TCW could take a ticket and turn it into a work item, and it could record that an
item and a ticket you already had were the same work. It could not go the other
way. A team with a TCW backlog had to script against Jira's own API to get it
into the tracker — which is what this project did for 53 items, and what
[#43](https://github.com/bcefali/tcw/issues/43) reports at 116.

**`tcw work tracker create <slug>` now makes the ticket and binds it.**

```sh
tcw work tracker create 2026-09-14-rename-the-widget
tcw work tracker create --all --dry-run    # what a sweep would make
tcw work tracker create --all              # every open item with no ticket
```

The summary is the item's title and the description is the item's own request.
The type comes from your configuration, with an override for epics and bugs.

Set `work.tracker.create.on-new: true` and filing an item makes its ticket:
`tcw work new` and `tcw work inbox accept` of a raw entry. **Filing never fails
because the tracker is unreachable** — the item is written and the ticket is
recorded as *owed*, shown on the board as `ticket: owed since <date>`, and made
later by `tcw work tracker create`. This is off unless you turn it on.

### If you already configure `statuses`, read this

**Your first `tracker create` will be refused** until you add `backlog` to it:

```yaml
work:
    tracker:
        statuses:
            backlog: To Do # ← new, and required before `create` will run
            active: In Progress
        create:
            project: EX
            issue-type: Task
```

That refusal is deliberate, and it is the whole reason the setting is required.
Jira decides which status a brand-new issue starts in, and in a project with a
triage column that is usually the very status `inbox-query` selects. A ticket
left there would come back through `tcw work inbox` as new inbound work, and
offer to create a second item for the one that just created it. So TCW moves
every created ticket to `statuses.backlog`, and would rather create nothing than
create a ticket it cannot put somewhere safe.

A few other things worth knowing:

- An item that already has a ticket is reported, not given a second one.
- A `completed` or `discarded` item is refused. A ticket created only to be
  closed is noise; bind an existing one with `tcw work tracker link`.
- If a run is interrupted after the ticket is made but before it is bound, the
  key is on disk. Running the command again binds that key rather than making
  another ticket, and the board shows the item as `<KEY> made, not bound` in the
  meantime. If that ticket is gone, `tcw work tracker unlink <slug> --reason
  "<why>"` forgets the key so you can start again; it changes nothing in Jira.
- `tcw work tracker sync` does not settle an owed ticket. It retries status
  changes for items that already have one. Ask it about an item that is owed a
  ticket and it tells you to run `tcw work tracker create`.
- Filing an item **on the web board** records the ticket as owed rather than
  making it. The web app does not talk to Jira at all, so `tcw work tracker
  create --all` is what settles those.
- `strict: true` and `create.on-new: true` can both be set. Strict mode refuses
  `tcw work new` for everything except an epic, and creation-on-filing covers
  epics — so the pair means "tasks come from tickets, epics filed here get
  theirs made".
- TCW does not set a parent or epic link in Jira. A created ticket is a ticket;
  the hierarchy stays in TCW.
