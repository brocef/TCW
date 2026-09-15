# Initial request — Tombstone resolved work items so references to them stay resolvable

A `tcw://W/<slug>` reference to a work item that has been completed or discarded
is indistinguishable from a reference to a slug that never existed. Both come
back from `tcw validate` as:

```
no such work item: 2026-08-26-publish-provisioned-store-writes-to-their-remote
```

The first is a normal, healthy fact about a project that finishes work. The
second is a typo. Reporting them identically means the healthy case is noise,
and because `tcw validate` is wired as the `complete` transition's `pre` hook in
this repo's `tcw-config.yaml`, that noise is currently fatal: four such
references exist, `tcw validate` exits 1, and **no item in this repository can
be completed at all**. The gate is broken by the very transition it guards.

## What is asked for

A **graveyard**: a record that a given slug *was* a valid work item at some
point, so `tcw validate` can tell a resolved reference from a bogus one and stop
complaining about the former.

An entry records that the slug existed and was resolved. It deliberately does
**not** record where the item's documents went — no repository, no commit, no
locator of any kind.

## Explicitly out of scope

- **Changing how `complete` and `discard` interact with git.** An earlier
  sketch had them make two commits — one placing the item in `completed/`, one
  deleting it — so that history held exactly one commit containing the resolved
  item. That is withdrawn. The commands' git behaviour stays as it is.
- **Deciding how long resolved work documents are kept.** That is the repo
  manager's call, and the mechanism already exists: `completed/` and
  `discarded/` are gitignored by default (`.gitignore:28`), and a manager who
  wants the documents retained in the tracked tree simply does not ignore them.
  TCW should not have an opinion.
- **Mapping a slug to the commit that removed it.** Considered and dropped: a
  recorded commit is a promise that the documents are retrievable there, and
  that promise does not survive a squash-merge (which collapses the add and the
  delete into a net no-op), a rebase (which changes the SHA), or a shallow
  clone. A pointer that silently stops working is worse than no pointer, and
  omitting it removes the whole problem.

## Constraints

- The four references that currently fail must stop failing, so `tcw work
  complete` works again in this repository. Entries written by future
  completions do not achieve that on their own — the items those references
  name were resolved before any graveyard existed, so there must be some way to
  record a slug after the fact.
- Whatever holds the graveyard has to be reachable by a store that is not a
  filesystem — the abstraction litmus test applies as it does to every
  operation.

## Notes

- **Reference material: asked; none provided.** The in-repo material the spec
  will work from — `.gitignore:28`, `resolved_ignore_rules` and `git_mv` in
  `tcw/store/fs.py`, the `tcw://` resolver, and the four failing references — is
  discovery, not requester-supplied context.
- The requester's word for this is "graveyard file". The item's title says
  "tombstone"; they are the same thing, and the spec should settle on one name.
- Related: `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`
  asks for suppressible references and graded exit codes. This item removes much
  of that item's motivation — resolved references are the reason `tcw validate`
  is unusable as a gate today — so the two need reconciling. Not merged into it,
  because suppression and exit-code grading remain useful independently.
- Recorded as inference, for `spec` to confirm or overturn: the graveyard is
  expected to be written by `complete` and `discard` themselves. The exclusion
  above is about their *git* behaviour and about document retention, not about
  leaving the commands untouched.
