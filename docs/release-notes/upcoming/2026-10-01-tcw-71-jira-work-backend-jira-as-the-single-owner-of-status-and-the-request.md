## Jira as the home of your work items

A project can now keep its work items in Jira. Set `work.backend: jira` and a
`work.jira` block in `tcw-config.yaml`, and each item is a Jira ticket: Jira
holds its stage, its request, its comments, and its assignee, priority,
estimates, labels, parent and blocking links. The repository keeps only the
technical record — specs, plans and implementation rounds — in one folder per
ticket, named after the ticket's key. This replaces the 2.x `work.tracker`
connection, which is gone; the migration guide explains how to move across.

- **Each stage is one Jira status.** `tcw work advance` makes exactly one
  workflow transition, and any reason you give lands on the ticket as a
  comment in the same step. QA happens on the ticket: leaving QA asks for a
  reason, and nothing is written in the repository for it.
- **New items start as tickets.** `tcw work new` creates the ticket first and
  its folder second. A ticket key works anywhere an item is named, so
  `tcw work show TCW-67` finds the item.
- **Tickets filed in Jira become items with `tcw work tickets adopt <KEY>`.**
  `tcw work tickets list` shows the ones waiting. If an adoption or a `new`
  stops part way, running `adopt` again finishes it.
- **File work into a Jira-mode project from another project** with
  `tcw work new --project <id>`. The ticket lands in that project's Jira
  inbox; a `jira` block in your `connected-projects` entry describes a
  project that is not on this machine.
- **`tcw validate --remote` checks a Jira project against your configuration,**
  reading only: the fields TCW needs on each screen, every stage's status,
  and that the workflow offers one transition for every move TCW makes. It
  also checks each item folder against its ticket. Plain `tcw validate` never
  contacts Jira.
- **TCW never commits for you in Jira mode.** The item folders it writes are
  left for you to commit.
