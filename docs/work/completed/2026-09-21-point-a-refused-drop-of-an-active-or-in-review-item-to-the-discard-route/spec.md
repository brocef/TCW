# Point a refused drop of an active or in-review item to the discard route

## Capability changes

None. `tcw work drop` still deletes only backlog items, and discarding still goes
through `tcw work complete --resolution <not-done>`. Only a refusal's wording and
the moment it is shown change. No ledger delta is needed.

## Problem

An agent could not find a way to discard an active item. Everything it tried
existed, but nothing on its path pointed to the route that works:

- `tcw work drop <active item> --confirm` prints
  `tcw work: cannot drop from active (only backlog)` (the message is raised in
  tcw/store/base.py:3947, printed by `_drop` in tcw/work/cli.py:3814-3816). It names
  no alternative.
- Without `--confirm`, `_drop` (tcw/work/cli.py:3790-3802) refuses first with
  "Re-run with --confirm", before it checks the status. Taking that advice leads
  to a second refusal. A previous fix already moved the missing-item check ahead
  of this gate for the same reason (tcw/work/cli.py:3792-3796); the status check
  was left behind it.
- skills/work/SKILL.md:40 lists `discard` beside `start`, `submit`, `rework` and
  `complete`, which are all verbs you can type. `discard` is not one
  (tcw/store/base.py:1033). The linked transitions.md explains that at line 169,
  but the list itself reads as a list of commands.

The strict-tracker branch of `_drop` (tcw/work/cli.py:3808-3812) already names
the discard command. The ordinary refusal does not.

Sibling sweep, repo-wide: `grep` for `drop`, `discard` and "only backlog"
across tcw/, skills/, README.md. The web API's DELETE (tests/test_serve_write.py:1193)
returns 422 for an active item. It is an HTTP API whose client, the web UI, shows
its own controls, so it is out of scope. No other refusal suggests a verb that
does not exist.

## Goals

1. Refusing to drop an item that is not in backlog names the discard command,
   with the item's slug filled in.
2. That refusal comes before the `--confirm` gate, so a non-backlog item never
   gets advice to add `--confirm`.
3. The work skill's transition list no longer reads as though `discard` were a
   command.

## Non-goals

- Adding a `tcw work discard` verb. `base.py:1033-1040` records why discard is
  reached through `complete`: hooks key on the move, not the verb.
- Letting `drop` delete non-backlog items.
- Changing the web API.

## Design

In `_drop`, right after the item is resolved and before the `--confirm` gate,
read the item (`st.get(bare)`, the public read in tcw/store/base.py:3127). If it
exists and its status is not `backlog`, print one line to stderr and return 1:

    tcw work drop: <slug> is <status>, and drop only deletes a backlog item. To discard it, keeping a record: `tcw work complete <slug> --resolution wontfix --confirm` (or duplicate / superseded).

For an item already `completed` or `discarded`, nothing can move it, so the
message says only that it is already resolved. The adapter's own
`IllegalTransition` in `drop` stays as the guard for any other caller.

In skills/work/SKILL.md:40 change `discard` to
`discard` (`complete --resolution wontfix|duplicate|superseded`).

## Acceptance criteria

1. With an item in `active`, `tcw work drop <slug>` (no `--confirm`) exits 1,
   prints nothing on stdout, does not mention `--confirm` on stderr, and stderr
   contains `tcw work complete <slug> --resolution wontfix --confirm`.
2. The same holds with `--confirm`, and the item is still active afterwards.
3. The same holds for an item in `review`.
4. For an item in `completed`, `tcw work drop <slug> --confirm` exits 1 and stderr
   says it is already resolved, without suggesting `complete`.
5. Existing behavior is unchanged: a backlog item without `--confirm` is refused
   with "Would delete", with `--confirm` it is dropped, and a missing item says
   "no such work item" (tests/test_work.py:1959-1987 pass unchanged).
6. skills/work/SKILL.md's transition line names the `complete --resolution` spelling
   next to `discard`.

## Risks

- Reading the item before the gate adds one store read. That's negligible, and
  `locate` already does one there.
- A qualified slug (`<project-id>/<slug>`): the message uses the slug as typed,
  so the suggested command works from where it was typed.
