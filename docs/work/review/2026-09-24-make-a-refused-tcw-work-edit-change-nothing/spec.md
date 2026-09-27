# Spec: make a refused tcw work edit change nothing

## Capability changes

None. `tcw work edit` keeps its surface; a refusal simply stops writing part of
the change first.

## Problem

`_edit` (`tcw/work/cli.py:2373-2430`) writes in this order:

1. `st.remove_blocker(bare, ref)` for each `--unblocked-by` (`cli.py:2410-2411`);
2. `st.add_blocker(bare, ref)` for each `--blocked-by` (`cli.py:2412-2413`);
3. `st.add_blocker(ref, bare)` for each `--blocks` — a write to *another* item
   (`cli.py:2414-2415`);
4. `st.update_work(...)` for title, priority, effort, complexity, initiative,
   tags and type (`cli.py:2417-2426`).

Each of 1-3 is its own write. Validation of tags (unregistered → refused) and of
effort/complexity happens only inside step 4 (`tcw/store/fs.py:6860-6884`). So
`tcw work edit X --blocked-by foo --tag unregistered` records the blocker and
then exits 1. The same holds for a refusal inside steps 2-3 after step 1 wrote
(e.g. `--unblocked-by a --blocked-by X` on X itself removes `a`, then refuses
the self-block), and for `--blocked-by A --blocks A`, which writes A as X's
blocker and then refuses the reverse link as a cycle.

**Sibling defect (repo-wide sweep).** The only other writer of blockers is
`update_work(blockers=...)`, used by the web app's PATCH
(`tcw/serve/__init__.py:1159-1178`). It builds entries with `_entry_for` only
(`fs.py:6886-6897`) and never runs the self-block and cycle checks that
`add_blocker` runs (`tcw/store/base.py:3788-3798`). So the web app can save an
item as blocking itself, or close a blocking cycle. `create_work` cannot: nothing
can name an item that does not exist yet.

## Goals

1. Any refusal from `tcw work edit` — unregistered tag, bad effort/complexity,
   bad type change, missing `--unblocked-by` match, self-block, cycle (through
   `--blocked-by`, `--blocks`, or both together), unknown `--blocks` item — leaves
   every item's `state.yaml` exactly as it was.
2. `update_work(blockers=...)` refuses a *newly added* self-block or cycle, as
   `add_blocker` does, so the web app gets the same guard.
3. Blocker semantics are otherwise unchanged: removals still fail closed,
   additions are still idempotent, `--unblocked-by X --blocked-by X` still means
   remove-then-add.

## Non-goals

- Atomicity against concurrent writers or I/O failure. The guarantee is about
  refusals the command itself decides. `--blocks` writes other items, so after
  the target item is written a reverse-link write can still fail if another
  process changed the graph in between, or on disk failure. A multi-item
  transactional write is out of proportion here.
- Rejecting cycles that already exist. `update_work` checks only entries not
  already on the item, so saving an item that already sits in a cycle (or
  removing one of its blockers to break it) still works.

## Design

- **Store (abstract, `tcw/store/base.py`).** Extract `add_blocker`'s self/cycle
  refusal into `_check_new_blocker(slug, entry)`. Add a public, non-writing
  `check_blocker_edits(slug, *, add, remove, blocks)` that refuses exactly what
  the equivalent `remove_blocker` / `add_blocker` / reverse `add_blocker` calls
  would refuse, *taken together*: removals are applied to a proposed list first,
  and a `--blocks` reverse link is checked against the item's proposed blockers,
  not the stored ones. Any store can implement it (it is a query over items and
  their blocker relations), so it passes the abstraction test.
- **`FsWorkStore.update_work`.** For each resolved blocker entry not already on
  the item (`_same_entry`), call `_check_new_blocker` before writing.
- **`_edit`.** Order becomes: type-change check → `check_blocker_edits` →
  `update_work` (fields; validates tags and estimates, writes nothing if it
  refuses) → blocker writes via the existing `remove_blocker` / `add_blocker`
  calls, now pre-validated. Existing entries are never round-tripped through
  `_entry_for` (which could turn an external entry into a slug entry).

## Acceptance criteria

1. `tcw work edit X --blocked-by Y --tag not-registered` exits 1 and X's
   `state.yaml` is byte-identical afterwards.
2. `tcw work edit X --unblocked-by A --blocked-by X` exits 1; X still has blocker A.
3. `tcw work edit X --blocked-by A --blocks A` exits 1; neither X nor A changed.
4. `tcw work edit X --blocks Y --effort nonsense` exits 1; Y and X unchanged.
5. `tcw work edit X --unblocked-by A --blocked-by A` still succeeds (A remains).
6. `update_work(X, blockers=["X"])` raises; `update_work(X, blockers=[<an item
   that X already blocks>])` raises; `update_work(X, blockers=<the unchanged
   list of an item already in a cycle>)` succeeds.
7. The existing edit, blocker and web-save tests pass, as does the full suite.

## Risks

- A caller relying on `update_work` accepting a self-block. None found in
  `tcw/` or `tests/` (`tests/test_store_editor.py:254,357`,
  `tests/test_show_json.py:171` use plain slugs or `[]`).

## Notes

- Design chosen after consulting two advisors (Codex, Opus), both recommending
  this option over validating everything in the CLI; see `outcome.md`'s
  "Autonomous decisions".
