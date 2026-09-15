# Spec — Make `tracker link` record a cross-reference without claiming the ticket

## Capability changes

**Changed:** `work/manage-external-tracker-intake` (`cap-bd57b7`, Supported,
Feature `external-work-tracker`). Two sentences of its body stop being true:

- "`tcw work tracker link <slug> <key>` claims a ticket for an item I already
  have" — after this item, `link` claims nothing.
- "The binding is written by these commands, not by hand" stays, but the body
  must no longer imply the binding records who claimed the ticket, because
  `claimed-by` leaves the file.

Its closing sentence — "Keeping the ticket in step with the item's lifecycle …
[is a] separate [capability] that [is] not yet built" — is still true and gains
force: between this item and `work/synchronize-external-tracker-work`,
`tracker import` is the only command that claims.

No new capability, none removed. `work/synchronize-external-tracker-work`
(`cap-207f2c`, Missing) is untouched here; it is where claiming for an
already-linked item lands, and its planning doc
`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker` is updated by
this item's work to say so.

Recorded as `changed:` in the item's `capabilities.yaml` at implementation.

## Problem

`tcw work tracker link <slug> <ticket>` does two unrelated things in one command.
It writes the binding sidecar that says "this item is that ticket", and it
**claims** the ticket: `_tracker_link` calls `claim(client, ticket)`
(`tcw/work/cli.py:1887`) and returns 1 unless `outcome.claimed`
(`tcw/work/cli.py:1891`), so the binding is never written unless the claim took.
`claim` (`tcw/tracker/intake.py:272`) applies the configured claim transition and
assigns the ticket to the caller.

Recording a cross-reference is therefore inseparable from announcing that work
has started. A workspace wanting Jira tickets for ten queued backlog items, each
linked to its item, cannot have them: running `link` on tickets in `To Do` moves
all ten to `In Progress` and assigns them, so the tracker reports ten pieces of
work under way when none are.

The only way through today is an accident of the claim table. Row `1e`
(`tcw/tracker/intake.py:318`) binds with no transition when the ticket does not
offer the claim transition **and** is already assigned to the caller — a case
meant for finishing an interrupted claim. Tickets created in `Triage`, where
`Start` is not offered, and auto-assigned by a component default, fall into it.
The same ticket unassigned is refused by row `1f` (`tcw/tracker/intake.py:321`).
A workflow detail, not a way to work.

Three further consequences of routing `link` through the claim:

1. A ticket assigned to somebody else is refused by row `1b`
   (`tcw/tracker/intake.py:309`), though recording a reference takes the ticket
   from nobody.
2. `_unresolved_item` (`tcw/work/cli.py:1830-1843`) refuses both resolved
   statuses for `link` **and** `unlink`, so finished work cannot be linked to
   the ticket that tracked it, and a wrong binding on a finished item can never
   be repaired.
3. `_binding_for` (`tcw/work/cli.py:1714`) is typed against a `ClaimOutcome`,
   which only `claim` produces. The command cannot write a binding without
   claiming even if it wanted to.

Separately, the `tracker` subcommands do not explain themselves. `tracker link
--help` prints:

```text
usage: tcw work tracker link [-h] [--part PART] slug ticket

positional arguments:
  slug
  ticket

options:
  -h, --help   show this help message and exit
  --part PART  which of several items for this ticket (default: default)
```

No description, and neither positional is described — so nothing says which of
the two is the slug and which the ticket, and nothing says the command moves and
assigns the ticket in Jira, which is the single most important thing to know
before running it. The parsers are registered without `description=` at
`tcw/work/cli.py:2233-2258`.

## Goals

1. `link` writes the binding and makes no other change: no tracker transition,
   no assignee change, and nothing written to the work item but the binding
   sidecar.
2. `link` and `unlink` both work at every non-inbox status, `completed` and
   `discarded` included.
3. `link` accepts a ticket assigned to somebody else. `import` keeps refusing
   one.
4. `claimed-by` leaves `tracker.yaml` entirely — `import`'s bindings too — so no
   binding asserts a claim.
5. Every `tracker` subcommand's `--help` describes what it does, what each
   argument is, why it refuses, and shows an example.
6. Every positional argument in the whole `tcw` CLI carries a `help=` string.

## Non-goals

- **A `tracker claim <slug>` verb, and any change to `tcw work start`.**
  Claiming for an already-linked item belongs to
  `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`. Between
  the two items, `tracker import` is the only command that claims; that gap is
  accepted.
- **Migrating existing `tracker.yaml` files.** Nobody is on this version.
- **Which Jira site a binding belongs to** — the separate inbox entry
  `2026-09-14-a-tracker-binding-does-not-record-its-site.md`.
- **Full `description=`/`epilog=` prose for the non-`tracker` subcommands.**
  See § 6.
- **Changing `claim` itself.** Rows `1a`–`1f` keep their behaviour; `link`
  stops calling them.

## Design

### 1. `link` stops claiming

`_tracker_link` keeps `read_ticket` — it is what proves the ticket exists and
yields the canonical key, issue id and URL the binding stores, so a typo'd key
must still refuse — and drops the `claim` call and the `outcome.claimed` guard.
`read_ticket` also fetches transitions and the caller's account
(`tcw/tracker/intake.py:254-269`); those reads become unnecessary but are left
in place rather than split, so `show`, `import` and `link` keep reading a ticket
one way.

The order of the surviving guards is unchanged: `--part` validity, the item
exists, the item's own binding is neither `Bound` nor `Malformed`, then
`read_ticket`, then `find_binding` for another item holding this ticket and
part, then the write.

### 2. The binding no longer speaks of claiming

`binding_document` (`tcw/tracker/intake.py:161`) loses its `account_id` and
`account_name` parameters and the `claimed-by` block they write.
`_BINDING_KEYS` (`tcw/tracker/intake.py:177`) drops `"claimed-by"` so
`unlink_document` stops moving a key that is no longer written.

This is what makes goal 1 mechanically possible: with `claimed-by` gone, every
field `binding_document` needs — issue id, canonical key, URL — is on
`TicketRead` (`tcw/tracker/intake.py:212-224`) as well as on `ClaimOutcome`. So
`_binding_for` is retyped to take those three values rather than an `outcome`,
and both callers pass them.

`read_binding` (`tcw/tracker/intake.py:70`) never required `claimed-by`, so
bindings written before this change stay readable and stay `Bound`; the stale
key is simply ignored, and on `unlink` it is left in the document rather than
moved into the `unlinked` entry. Accepted: nobody is on this version.

### 3. Resolved items

`_unresolved_item` becomes a plain lookup — item exists or it does not — used by
both `link` and `unlink`; the `RESOLVED_STATUSES` refusal
(`tcw/work/cli.py:1839-1842`) goes. Its name goes with it, since it no longer
describes what it does.

In a node that does not retain resolved items, a completed item has no folder
and `st.get(slug)` returns `None`, so `link` refuses it as "no such work item".
That is correct and is the honest limit: this repository is such a node
(`.gitignore:29-32` keeps `docs/work/completed/` out of git), so the new
behaviour is only observable where retention keeps the item.

`find_binding` (`tcw/tracker/intake.py:131-155`) keeps skipping resolved items.
Half its stated reason expires here — "a resolved item's binding cannot be
repaired from here" stops being true once `unlink` accepts them — but the other
half stands: a discarded item's ticket may be taken again. Leaving the skip is
also the status quo, since a resolved item can already hold a binding written
while it was open. Its docstring is corrected to the surviving reason, and the
consequence is stated as a known limit rather than fixed: a ticket held by a
resolved item can be bound to a second, open item.

### 4. A ticket somebody else holds

Nothing to remove: row `1b` lives inside `claim`, which `link` no longer calls.
`link` makes no assignee check of its own, so it binds regardless of who holds
the ticket. `import` is untouched and keeps refusing.

### 5. `tracker` help

The five `tracker` parsers (`tcw/work/cli.py:2233-2258`) each gain
`description=` and `epilog=` under `RawDescriptionHelpFormatter`, and a `help=`
on every positional. Each description states every change the command makes in
the tracker **and** in the work store — for `link` after this item, that it
changes nothing in the tracker — plus when `--part` is needed with an example,
the main refusals, and one or two example invocations. The group's own
`help=` string and `import`'s ("claim a ticket and create a backlog item bound
to it") stay accurate; `link`'s ("claim a ticket and bind an existing item to
it") is rewritten.

### 6. The help sweep: CLI-wide for `help=`, `tracker`-only for descriptions

Walking `build_parser()` (`tcw/cli.py:467`) finds **46** positional arguments
across the whole CLI with no `help=`: 31 under `tcw work`, of which 5 are in the
`tracker` group, plus 15 across `tcw taxonomy` and `tcw capabilities`. All 46
get one — a single line each, mechanical. The gap the report found in `tracker`
is not special to it, and the sweep is CLI-wide rather than stopping at the
`work` command group, because nothing about the defect is particular to `work`.

Full `description=`/`epilog=`/examples are written for the `tracker` group only.
Doing that for all ~30 `tcw work` subcommands is several times this item's size
and is a different shape of work: it needs a house style for command prose
before it is worth starting. The narrowing is deliberate, and the two reasons
the `tracker` group goes first are that its commands take two positionals whose
order is not inferable from the command name, and that they reach a system
outside the repository.

### 7. Documentation

`README.md:368` describes `link` as "take it for an item you already have" and
§ Taking a ticket (`README.md:433-444`) folds `link` in with `import`'s claim.
Both are corrected, and the release notes and changelog get entries.
`skills/tcw-work/references/commands.md:93` says "claim a ticket for an existing
unresolved item" and is corrected on both counts — claiming and unresolved.

## Abstraction litmus test

**No new operation.** The change removes tracker calls and relaxes a status
guard; nothing is added to the store interface.

Each touched operation and its verdict:

- `write_sidecar` / `read_sidecar` for `tracker.yaml` — already store-interface
  operations, unchanged in shape. Dropping a field from the document changes the
  body, not the operation.
- `st.get(slug)` on a resolved item — store-interface. A non-filesystem store
  answers "does this item exist, and what is its status" the same way; that
  `docs/work/completed/` happens to be a gitignored folder here is a filesystem
  adapter detail and is why the honest limit in § 3 is phrased about *retention*
  rather than about a directory.
- `find_binding`'s scan — store-interface (`store.query()` plus a sidecar read
  per item). Unchanged.
- The `claim` call removed from `link` — a tracker-side operation, not a store
  one.

The resolved-status guard was never a store constraint; it was a policy written
into the CLI, which is the right layer for it to be removed from.

## Acceptance criteria

Numbering below matches the Design sections.

1. `tracker link <slug> <ticket>` against a ticket in a status that offers the
   claim transition exits 0, writes `tracker.yaml`, and makes **no** write to
   the tracker (the fake's write log is empty for the run).
2. After that run the ticket's status and assignee in the tracker are exactly
   what they were before.
3. `tracker link` changes no file in the item's folder but `tracker.yaml` — a
   byte-for-byte snapshot of every other file is equal before and after — and
   the item's status and owner are unchanged.
4. A `tracker.yaml` written by `link` contains no `claimed-by` key.
5. A `tracker.yaml` written by `import` contains no `claimed-by` key.
6. `unlink` on a binding written after this change moves `provider`, `project`,
   `part`, `ticket` and `bound` into the `unlinked` entry, and the entry has no
   `claimed-by`.
7. `tracker link` binds an item in `completed`, and one in `discarded`, exiting
   0 in a node whose `work.retain` keeps them.
8. `tracker unlink` removes a binding from an item in `completed`, and one in
   `discarded`, in such a node.
9. `tracker link` on a slug that no longer exists in the store refuses with "no
   such work item in this node" and exits 1.
10. `tracker link` binds a ticket assigned to another account, exiting 0 and
    leaving that assignee in place.
11. `tracker import` still refuses a ticket assigned to another account, naming
    the holder.
12. `tracker link` still refuses, changing nothing locally and writing nothing
    to the tracker, for: an item already bound (naming its ticket and telling
    the caller to `unlink`); a ticket and part another item holds (naming that
    item); a `tracker.yaml` on the item that cannot be read; a malformed
    `tracker.yaml` on some other item; an invalid `--part`; and no tracker
    configured.
13. `tracker link` on a ticket key that does not exist in the tracker refuses
    and writes no `tracker.yaml`.
14. `tcw work tracker link --help` prints a description naming every change the
    command makes, a `help=` line for `slug` and for `ticket`, the `--part`
    example, the refusals, and at least one example invocation. The same holds
    for `list`, `show`, `import` and `unlink`.
15. `tcw work tracker link --help` does not contain the words "claim" or
    "assign" as a description of what `link` does.
16. Every positional argument reachable from `build_parser()` — every
    subcommand of `tcw work`, `tcw taxonomy` and `tcw capabilities` included —
    carries a non-empty `help=`. Asserted by recursively walking the parser's
    `_SubParsersAction` choices, not by reading the source: a regex over
    `cli.py` undercounted this by 21 while the spec was being written.
17. `README.md` and `skills/tcw-work/references/commands.md` no longer describe
    `link` as claiming a ticket or as requiring an unresolved item; the release
    notes and changelog carry an entry for the change.
18. `pytest` and `tcw validate` pass.

### Coverage

Axes are the seven numbered Design sections. A cell is the test that covers that
criterion against that rule, or `n/a` with the line that makes it so.

| #   | 1 no claim            | 2 binding doc         | 3 resolved            | 4 other's ticket      | 5 tracker help       | 6 help sweep         | 7 docs               |
| --- | --------------------- | --------------------- | --------------------- | --------------------- | -------------------- | -------------------- | -------------------- |
| 1   | link_binds_without_writing_to_the_tracker | n/a — document shape, `intake.py:161` | n/a — item is `backlog`, `cli.py:1830` | n/a — ticket unassigned in fixture | n/a — runtime, not help text | n/a — as 14 | n/a — prose |
| 2   | link_leaves_status_and_assignee_alone | n/a — as 1 | n/a — as 1 | n/a — as 1 | n/a | n/a | n/a |
| 3   | link_binds_without_touching_the_body | n/a — as 1 | n/a — as 1 | n/a — as 1 | n/a | n/a | n/a |
| 4   | n/a — covered by 1 | link_writes_no_claimed_by | n/a — as 1 | n/a — as 1 | n/a | n/a | n/a |
| 5   | n/a — `import` still claims, `cli.py:1784` | import_writes_no_claimed_by | n/a — `import` creates a `backlog` item | n/a — `import` refuses, see 11 | n/a | n/a | n/a |
| 6   | n/a — `unlink` makes no tracker call, `cli.py:1908` | unlink_history_has_no_claimed_by | n/a — item is `backlog` | n/a | n/a | n/a | n/a |
| 7   | link_binds_a_resolved_item (asserts no tracker write) | n/a — as 1 | link_binds_a_resolved_item | n/a | n/a | n/a | n/a |
| 8   | n/a — as 6 | n/a — as 6 | unlink_removes_a_binding_from_a_resolved_item | n/a | n/a | n/a | n/a |
| 9   | n/a — refuses before the ticket read | n/a — nothing written | link_refuses_a_slug_that_does_not_exist | n/a | n/a | n/a | n/a |
| 10  | link_binds_a_ticket_someone_else_holds (asserts no tracker write) | n/a — as 1 | n/a — item is `backlog` | link_binds_a_ticket_someone_else_holds | n/a | n/a | n/a |
| 11  | n/a — `import` claims by design | n/a — nothing written | n/a — no item exists yet | import_refuses_a_ticket_someone_else_holds | n/a | n/a | n/a |
| 12  | each refusal asserts the fake's write log is unchanged | each asserts no `tracker.yaml` written | link_refuses_a_resolved_item is **deleted**, not adapted | n/a — assignee no longer a refusal | n/a | n/a | n/a |
| 13  | link_refuses_an_unknown_ticket | n/a — nothing written | n/a — item is `backlog` | n/a | n/a | n/a | n/a |
| 14  | n/a — help text, no runtime effect | n/a | n/a | n/a | tracker_help_describes_every_subcommand | n/a — descriptions are `tracker`-only by § 6 | n/a |
| 15  | n/a | n/a | n/a | n/a | tracker_link_help_does_not_promise_a_claim | n/a | n/a |
| 16  | n/a | n/a | n/a | n/a | the walk covers `tracker` too | every_positional_has_help (CLI-wide) | n/a |
| 17  | n/a | n/a | n/a | n/a | n/a | n/a | reviewed at `documentation-sync`; no test |
| 18  | pytest + `tcw validate` | same | same | same | same | same | `tcw validate` |

Two cells are findings rather than coverage and are called out because the table
exists to surface them. **Row 12 × rule 3**: `test_link_refuses_a_resolved_item`
(`tests/test_tracker_link.py:81`) and `test_unlink_refuses_a_resolved_item`
(`tests/test_tracker_link.py:143`) pin the behaviour this item removes; they are
deleted and replaced by criteria 7 and 8, not edited to assert the opposite of
what they were written for. **Row 17**: the only criterion with no executable
check, which is why it is discharged at `documentation-sync` in the plan rather
than by a test.

## Risks

- **Nothing claims a linked ticket until the outbound-sync item lands.** A user
  who linked an item and then started work has a ticket still sitting in its
  original status. Accepted deliberately (goal: non-goal 1), and the gap is
  named in the release note so nobody discovers it from the tracker.
- **`find_binding` still skips resolved items**, so a ticket held by a completed
  item can be bound to a second, open item with no refusal. Pre-existing, now
  reachable by one more path since a resolved item can be linked deliberately.
  Documented as a limit; fixing it would re-break the discard case the skip
  exists for.
- **A stale `claimed-by` in a binding written before this change** is ignored on
  read and left behind on `unlink` rather than moved into the history entry. No
  migration, by decision.
- **Linking a resolved item is untestable in this checkout**, because
  `docs/work/completed/` is gitignored here. The tests build their own fixture
  node with retention on, which is how every other tracker test already works
  (`tests/test_tracker_link.py:21-25`), so this costs a fixture rather than
  coverage.
- **Help text is prose and drifts.** Criteria 14–16 assert structure (a
  description exists, each positional has one, the word "claim" is absent from
  `link`'s) rather than wording, so the tests survive editing but cannot catch a
  description that becomes wrong in a way structure does not show.

## Notes

- Every `file:line` above was read in the working tree at commit `1c4347d`.
- The report's claim that row `1e` is what let the workspace bind at all was
  checked against `tcw/tracker/intake.py:316-321` and holds: `1e` requires both
  that no offered transition matches the configured claim name and that the
  ticket is already assigned to the caller.
- `tcw capabilities check` passes on the tree today, so the `changed:` delta
  above is recorded against a ledger with no standing problems.
