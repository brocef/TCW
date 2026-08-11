# Roll back or reorder the pre-move set_field writes on a lost transition

## Product changes

A transition that loses a race to a competing process now reports the loss
cleanly (`2026-08-11-harden-effect-transition-against-a-lost-status-transition-race`),
but its *field writes have already landed*. The user-visible consequence: two
agents completing the same `review` item with different resolutions — A with
`done`, B with `wontfix` — can leave B's `resolution: wontfix` stamped on the
item A moved into `completed/`. The item then reads as closed-with-one-answer by
its folder and a different answer by its data.

The error message deliberately scopes its claim to the move ("This process did
not move it") rather than saying nothing was changed, precisely because this is
still true. That wording is the placeholder for this item.

## Technical changes

Writes that land *before* `_effect_transition` runs:

- `transition()` blanks `owner` and `started` via `set_field` when either end of
  the move is `active` (`tcw/store/base.py:1272-1274`).
- `complete()` stamps `resolution` via `set_field` before the move
  (`tcw/store/base.py:1397`).

On a lost race these have already been written, and via the pre-rename path they
land inside the folder the *winner* moved — so the loser's data ends up on the
winner's item.

This can produce exactly the status/resolution disagreement that
`_status_resolution_problems` (`tcw/store/fs.py`) still documents as something
"no code path can produce". That docstring is now known to be optimistic and
should be corrected by whatever fixes this.

The obvious fix — write the fields after the move — is blocked by a deliberate
ordering constraint documented at `tcw/work/cli.py:915-918`: the pre-transition
hook is evaluated last precisely so a hook cannot abort *after* a resolution has
been stamped onto an unmoved item. Any reordering has to keep that property, and
`tests/test_lifecycle_hooks.py::test_a_failing_pre_hook_writes_no_field` pins it.
So the candidates are a rollback of the writes on a failed move, or a reordering
that preserves the hook guarantee — a design decision of its own size, which is
why it was not smuggled into the `None`-guard item.

The current behavior is pinned by
`tests/test_external_work_store.py::test_lost_complete_leaves_its_resolution_written`,
which asserts the residual rather than the desired outcome and names this item.

## Meta changes

Found while implementing
`2026-08-11-harden-effect-transition-against-a-lost-status-transition-race`;
recorded in that item's spec (§Design 3) and non-goals rather than fixed there.
