# Spec: Say so when tracker import --parent meets a ticket already bound here

## Capability changes

- **Changed** `work/manage-external-tracker-intake`: running the same import
  again still gives the item already there, but when the run asks for a
  `--parent` or `--initiative` that item does not have, it says so and exits 1
  instead of reporting success. The item is not changed.
- **Changed** `work/require-tracker-backed-work`: the paragraph on nesting a
  child by `tracker import --parent` / `--initiative` says these apply only to
  the item the import creates.

## Problem

`_tracker_import` (`tcw/work/cli.py:2663`) checks `--parent` before the ticket
is touched (`tcw/work/cli.py:2694-2701`), then looks for an open item already
bound to the ticket and part (`tcw/work/cli.py:2708-2713`). When one exists and
the ticket is assigned to this account, it prints the item's slug and
`→ already bound: …` and returns 0 (`tcw/work/cli.py:2714-2719`). `parent` and
`initiative` are used only by `create_work` further down
(`tcw/work/cli.py:2762-2763`), which this branch never reaches.

So `tcw work tracker import EX-1 --parent P`, run for a ticket imported earlier
without `--parent`, exits 0 with the item still at the top level. The same holds
for `--initiative`. Both options are new in this release; nothing in v2.6.2
behaved this way.

The two other branches for an already-bound ticket (not claimed, or held by
somebody else, `tcw/work/cli.py:2720-2732`) already exit 1, so they do not
mislead; they are unchanged.

## Goals

1. When the ticket is already bound here and assigned to this account, and the
   run gave `--parent` naming an item that is not the bound item's parent, the
   command exits 1 and says the bound item was not moved under that parent.
2. The same for `--initiative` naming an epic that is not the bound item's
   initiative, with the hint `tcw work edit <slug> --initiative <epic>`, which
   exists (`tcw/work/cli.py:2483`).
3. When the given `--parent` and `--initiative` already match the bound item —
   a re-run of the command that created it — the result is unchanged: the slug,
   `→ already bound`, exit 0.
4. The bound item and its ticket are not changed in any of these cases.

## Non-goals

- Moving the existing item under the parent, or setting its initiative. The
  import's options describe the item it creates, and moving a bound item on a
  re-run would be a new, surprising effect of an idempotent command.
- A `tcw work edit --parent` option. There is none today, and the message will
  not suggest one.
- The branches that already exit 1, and `inbox accept`, which passes no
  `--parent` or `--initiative`.

## Design

In the `ticket.assignee_id == ticket.me_id` branch of `_tracker_import`, before
returning 0, read the bound item (`st.get(existing)`) and compare:

- `--parent`: the given reference resolved through `st.get(parent)` (already
  known to exist, checked at `tcw/work/cli.py:2697`) against the bound item's
  `parent`. Comparing slugs, not the text given, so a reference that `get`
  accepts in another spelling is not a mismatch.
- `--initiative`: the given text against the bound item's `initiative`, as
  stored.

Each mismatch prints one line to stderr, for example:

```
tcw work tracker import: EX-1 (part default) is already bound to <slug>, which
is not under <parent>; import sets --parent only on an item it creates, so
<slug> was not moved.
```

and the command exits 1. The slug is still printed to stdout first, as today,
so a script that reads it keeps working. The `label` argument keeps the message
right for `inbox accept`, although that path never passes these options.

Storage: this is CLI logic over `get`, which every store has.

## Acceptance criteria

1. A ticket imported without `--parent`, then imported again with `--parent P`:
   exit 1, stderr names `P` and the bound item's slug and says it was not moved,
   and the item's `parent` is still empty.
2. The same with `--initiative E` on an item with no initiative: exit 1, stderr
   names `E` and includes `tcw work edit <slug> --initiative E`; the item's
   initiative is still empty.
3. A ticket imported with `--parent P`, then imported again with `--parent P`:
   exit 0, stdout is the slug, stderr contains `already bound` — the same as
   today.
4. A ticket imported with `--parent P`, then imported again with no `--parent`:
   exit 0, as today.
5. In criteria 1 and 2 the fake tracker records no write, and the item's
   `state.yaml` is byte-for-byte unchanged.

## Risks

- **A script that re-runs an import with different placement now sees exit 1.**
  That is the point: it was being told the placement happened.
- **Sweep.** The other commands that take `--parent` or `--initiative` are
  `tcw work new` (creates, so always applies them) and `tcw work edit
  --initiative` (applies it). `tracker link` and `tracker create` take neither.
  No other command accepts these options and then skips them.
