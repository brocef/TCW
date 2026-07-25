# Migrating from 0.14.x to 0.15.0

Version 0.15.0 adds a fourth work status, `discarded`, and routes every non-`done`
closure into it. `completed/` now means exactly "we shipped this".

Existing projects keep working — nothing is rejected on upgrade — but items you
closed as `wontfix`, `duplicate`, or `superseded` before 0.15.0 are still sitting
in `completed/`, where the new rule says they don't belong.

## 1. Find the items that disagree

`tcw validate` reports every item whose status contradicts its resolution:

```sh
tcw validate
```

Each one reads like:

```
2026-01-14-some-idea: resolution 'wontfix' belongs in 'discarded' but the item is in 'completed'
```

## 2. Move them

Status is the folder, so the move _is_ the status change — do not edit
`state.yaml`:

```sh
git mv docs/work/completed/<slug> docs/work/discarded/
```

Repeat per reported item, then confirm:

```sh
tcw validate                      # clean
tcw work list --status discarded  # the moved items
```

Keep this as its own commit, separate from any feature work.

## 3. Re-point any `completed/<slug>` locators

A status-path locator (`completed/<slug>`, accepted by any work command) must
match the item's real status, so any locator naming a moved item now fails.
Search your project docs for the `completed/` form and re-point it, or switch to
the bare slug — a bare slug never encodes status and never needs this fixup:

```sh
rg 'completed/[a-z0-9-]+' docs/
```

Bare `tcw://W/<slug>` references are unaffected.

## 4. Note the new reserved project ID

Project IDs may not collide with work-status names, so `discarded` joins `t`,
`c`, `w`, `local`, `backlog`, `active`, and `completed` as reserved. If a
connected project is registered under the ID `discarded`, rename it before
upgrading. This is rare enough that TCW does not attempt an automatic rename.

## What you don't have to do

- **Ignore `docs/work/discarded/`** — if you exclude `docs/work/completed/` from
  formatting or other tooling, add `docs/work/discarded/` beside it. Both hold
  frozen items.
- **Nothing else.** `tcw work drop` is unchanged (still a hard delete for a
  mis-created item), the four resolutions are unchanged, and no existing command
  changed its flags.
