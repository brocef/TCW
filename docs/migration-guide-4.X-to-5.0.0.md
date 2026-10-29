# Migrating from TCW 4.x to 5.0.0

> **Draft.** TCW 5.0 is not released, and most of its changes are not
> designed yet. This guide is a sketch that grows with the work: each change
> adds what a 4.x project has to do, and the sections marked _to be written_
> are filled in once the change they depend on is decided. Nothing here is a
> promise until 5.0.0 ships.

TCW 4.0 changed how projects are laid out and how they relate to each other,
and changed the work system only where the new layout reached it: names,
state files, nesting, and the commands and prompts that use them. TCW 5.0 is the overhaul of the work
system: how a work item moves through its stages, and how TCW works with Jira.
Taxonomy, capabilities, and the project layout 4.0 introduced (the `.tcw/`
folder, manifests, parent links, full identifiers and `tcw://` addresses) are
not expected to change.

This guide is written for a person and for an AI agent acting for one, as the
[3.x to 4.0 guide](migration-guide-3.X-to-4.0.0.md) is.

## Before you start

_To be written._ It will say:

1. how to check that a project is a 4.x project (its `tcw-version` lines);
2. whether 5.0 needs a migration run, and on which files, or only
   configuration changes made by hand;
3. what everyone sharing a project, or a Jira project, has to upgrade
   together;
4. how to hold automation below 5 until a project is ready
   (`pipx install 'tcw-cli<5'`).

## What changes in 5.0

Each entry says whether it is built, and what a 4.x project does about it.

### Built

- **Jira mode without the TCW Project and TCW Item fields.** In 4.x both
  fields are required. In 5.0, `work.jira.fields` may leave out `project`
  and `item`, both or neither, for a Jira site where new custom fields cannot
  be added. The item folders, each named with its ticket's key, then say
  which tickets are the project's items. [The Jira guide](guide/jira.md#running-without-the-tcw-fields)
  says what that loses.

  A 4.x project that keeps the fields does nothing. A project that wants to
  drop them removes both from `work.jira.fields`. A project that takes
  `work.jira` from a parent cannot drop an inherited key by deleting it: it
  writes `project: null` and `item: null` under `work.jira.fields` in its
  own `.tcw/tcw-config.yaml`. The values already on its tickets are left in
  place and no longer read. Every project sharing one
  Jira project must make the same choice: a project with the fields would
  adopt the request-stage items of one without them. Turning the fields on
  for a project that ran without them is not supported yet.

### Being designed

These came out of evaluating 4.0 on real projects whose Jira workflows are
fixed and short. None is decided.

- **Several stages sharing one Jira status.** 4.x needs a distinct status
  for every enabled stage, at least five. The proposal is that several
  stages may name one status, with the exact stage kept in the item's state
  file, so that a move between two such stages changes only the file. Still
  open: one mapping per TCW project, or one per issue type.
- **A work item spread over several tickets and Jira projects.** For
  example, an intake ticket that carries the request through the plan, then
  an epic, tasks and a QA story in a delivery project. 4.x keeps one item on
  one ticket, of one issue type, in one Jira project.
- **One TCW project reading more than one intake project.**
- **A read-and-comment mode.** A filesystem-mode item takes its request from
  a ticket and comments on it, but never moves it.
- **Keeping some stages local** while the ticket stays where people left it.

### Still to do on the work already built

None of these exists yet.

- A `tcw validate --remote` warning when projects sharing one Jira project
  made different choices about the TCW fields.
- Without the fields, one deleted ticket makes every `tcw work list` cost a
  refused search plus up to 100 single reads; TCW does not retry when Jira
  limits the request rate.
- Whether Jira Cloud's `key IN` search finds a ticket moved to another Jira
  project when asked for its old key, which no run against a real Jira has
  confirmed yet.

## Migrating one project

_To be written_ once it is known whether 5.0 has a `tcw migrate` step for
4.x projects.

## Migrating projects that share a Jira project

_To be written._ This section will cover the cases where the order matters:
projects that share one Jira project, and items that are parents or blockers
of items in another project.

## What each 4.x name becomes

_To be written._ This section will have one table per kind of name
(commands, flags, configuration keys, files, and output a script reads), as
in the 3.x to 4.0 guide. Each row is added in the same change that renames or
removes the name.

| 4.x | 5.0 | Notes |
| --- | --- | ----- |
|     |     |       |

## Scripts, hooks and agent instructions

_To be written._ This section will list what an agent taught the 4.x work
flow has to change, step by step, as the 3.x to 4.0 guide does for the
epic-parts flow.
