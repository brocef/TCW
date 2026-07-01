# Optional effort and complexity fields for work items

Add two optional metadata fields to work items:

- **Effort** — how much work the item is: `low | medium | high | very-high`
- **Complexity** — how hard the item is: `low | medium | high | very-high`

Both are optional and unset by default. They are estimation/triage signals only —
they do not affect board ordering, blocking, or the lifecycle state machine.

## Product changes

- `tcw work new` and `tcw work edit` gain `--effort` and `--complexity` flags,
  each accepting one of `low | medium | high | very-high`.
- `tcw work show` displays effort and complexity when set (alongside `priority`).
- One new capability, analogous to the existing "Prioritize a work item".

## Technical changes

- Two new optional scalar fields on `WorkItem`, persisted in `state.yaml` via the
  existing generic `set_field` path (same shape as `priority`/`initiative`).
- The value set lives in the abstract spine (`base.py`) as a shared constant; the
  CLI enforces it via argparse `choices=` (same idiom as `complete --resolution`).

## Meta changes

None.

## Decisions already made (from brainstorming)

- Value set is fixed: `low | medium | high | very-high`, shared by both fields.
- `tcw work list` is **unchanged** — no new column; effort/complexity surface only
  in `tcw work show`.
- No clear-to-empty flag, no filtering, no sorting by these fields (YAGNI; the
  data is stored plainly so any of these can be added later without migration).

## Non-goals

- Changing board ordering or the priority mechanism.
- Any numeric/story-point scale — these are coarse ordinal labels only.

## Open questions

None outstanding — the design was settled during brainstorming.
