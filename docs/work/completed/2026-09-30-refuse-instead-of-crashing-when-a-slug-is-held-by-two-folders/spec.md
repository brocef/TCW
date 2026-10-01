# Spec: Refuse instead of crashing when a slug is held by two folders

_Compressed spec, agreed with the maintainer for a small fix._

## Capability changes

None.

## Problem

The inbox entry reported `tcw validate` crashing with an uncaught `MultipleMatch`
when two folders hold one slug. **That part is already fixed**: #58 (commit
`eddfa41e`, landed the day after the entry was filed) added `duplicate_slugs`
and `_duplicate_problem` (`tcw/store/fs.py`, `check`, from line 7652), and
`validate` now reports "held by 2 folders — <a>, <b>". Reproduced against 2.8.0
at spec time.

The sweep for sibling defects (repo-wide, by running each `tcw work` verb on a
duplicated slug in a scratch project) found the same crash elsewhere:

- `tcw work list` crashes with a traceback — one duplicate takes the **whole
  board** down: `_render_board_item` calls `st.artifacts(it.slug)`
  (`tcw/work/cli.py:1075`), which calls `_find` (`tcw/store/fs.py:4934`), which
  raises `MultipleMatch`.
- `tcw work start` and `tcw work submit` crash with a traceback, from
  `st.get` → `_get_now` → `_find` (`tcw/work/cli.py:1608`, `:1753`).
- The top-level handler in `tcw/cli.py` `main` (line 550) catches `ValueError`
  and `yaml.YAMLError` but not `MultipleMatch`, which subclasses `Exception`
  (`tcw/store/base.py:3206`).

The verbs that do catch it (`show`, `edit`, `path`, `drop`, `rename`,
`complete`, `stage gate`) print only `slug resolves to 2 items: <slug>`: it names
neither folder nor says that `tcw validate` lists them. The blocker-cycle
refusal's remedy for a slug held twice (`tcw/store/base.py:4341-4342`) says
"remove the extra folder of each slug held twice" and deliberately does not
point at `validate`, because until #58 `validate` crashed.

## Goals

1. No `tcw work` verb prints a traceback for a slug held by two folders.
2. `tcw work list` still shows the board: each affected row is printed, marked
   as held by more than one folder, and every other row is unaffected.
3. The refusal names every folder holding the slug, from the project root as
   `validate` prints them, and says `tcw validate` lists every such slug.
4. The blocker-cycle refusal's remedy points at `tcw validate` for a slug held
   twice.

## Non-goals

- Preventing a duplicate from arising, or repairing one automatically.
- The web app (`tcw serve`): its behavior on a duplicate is not changed here.
  If the sweep during implementation finds it crashing, that is reported, not
  fixed in this item.
- `2026-09-30-keep-an-item-s-folder-in-one-place-and-its-status-only-in-state-yaml`
  will change how a duplicate can arise; this item fixes today's layout.

## Design

- `_find` raises `MultipleMatch` with a message naming each folder and pointing
  at `tcw validate`. Every verb that already prints the exception's text gets the
  better message for free.
- `main` in `tcw/cli.py` catches `MultipleMatch` as it does `ValueError`:
  `tcw: <message>`, exit 1. This is the safety net for `start`, `submit`, and any
  verb not yet swept.
- `_render_board_item` catches `MultipleMatch` from its artifact read and prints
  the row with a marker in place of the stage letters and a trailing
  `held by N folders — see tcw validate` segment.
- The remedy text in `tcw/store/base.py` near line 4342 gains the pointer.

All of this is presentation of an error the store already detects; no store
interface operation changes, so the abstraction test is not engaged.

## Acceptance criteria

In a scratch project where an item's folder is copied from `backlog/` into
`active/`:

1. `tcw work list` exits 0, prints no traceback, prints every other item's row
   as before, and prints the duplicated slug's rows with the "held by" marker.
2. `tcw work start <slug>` and `tcw work submit <slug>` exit 1 with a one-line
   `tcw…:` message and no traceback.
3. `tcw work show <slug>`'s message names both folders (`docs/work/active/<slug>`
   and `docs/work/backlog/<slug>`) and contains `tcw validate`.
4. `tcw work edit <other> --blocked-by <slug>` exits 1 with no traceback and its
   message contains `tcw validate`.
5. `tcw validate` output is unchanged from 2.8.0 for this case.

## Risks

- `MultipleMatch` text is matched by existing tests; changing it may need test
  updates. Those are updates to wording, not to behavior.
- `_find`'s re-walk (it tolerates an item mid-move) must be kept exactly.

## Notes

- Entry found reviewing
  `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`.
- Renamed at spec from `…-report-a-slug-held-by-two-folders-in-tcw-validate-instead-of-crashing`,
  since `validate` no longer crashes.

## Amended after spec review (2026-09-30)

An adversarial spec review ran before implementation, and reproduced a gap in
this design: catching around the artifact read is not enough. Three more calls
on the board path reach `_find` for the duplicated slug:

- `st.unresolved_blockers(it)` on the row of **another** item blocked by the
  duplicated slug (`tcw/store/base.py`, `unresolved_blockers`, catches only
  `ValueError`);
- `st.epic_completable(it)` for a duplicated epic;
- `_render_descendant_boards`' initiative lookup under `--include-descendants`.

Accepted design changes:

- A blocker whose slug is held twice counts as **still blocking** and is shown
  in the blocked item's row as usual. `unresolved_blockers` treats
  `MultipleMatch` like an unreadable blocker, where the fix belongs, rather
  than the board catching it.
- A duplicated epic reads as **not** ready to close.
- The descendant board treats a duplicated initiative holder as no holder.
- **One row.** The board already merges the two folders into one row (its
  ordering keys on the slug), so criterion 1 means: the slug's single row is
  marked. Showing both folders as rows is not in scope.

Added criteria:

6. With a second item blocked by the duplicated slug, `tcw work list` exits 0,
   prints that item's row with the blocker listed, and prints every other row.
7. With the duplicated slug an epic that another item names as its initiative,
   `tcw work list --include-descendants` exits 0.
