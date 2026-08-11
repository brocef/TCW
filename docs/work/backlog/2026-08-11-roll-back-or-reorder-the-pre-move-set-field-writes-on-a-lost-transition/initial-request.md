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

## Also in scope: `get_detail`'s `None` escaping a non-optional signature

Folded in at the parent item's verify stage (2026-08-11) — same shape, one layer
up, and it wants the same decision about what a losing writer should get back.

`get_detail` (`tcw/store/fs.py`) now returns `None` when it loses the race, which
its `-> WorkDetail | None` signature has always allowed. But two callers end with
`return self.get_detail(slug)` while declaring `-> "WorkDetail"`, not optional:

- `create_work` (`tcw/store/fs.py:2852`)
- `update_work` (`tcw/store/fs.py:2955`)

So on that timing they hand `None` to a caller the signature promised would never
receive one, and the failure surfaces somewhere downstream instead.

**This is not a regression, and that is why it was not fixed under the guard
item.** Before the guard, the same timing raised `TypeError` inside `get_detail`;
now it is an `AttributeError` at the caller. One opaque crash swapped for
another, relocated rather than worsened. Every present-day caller is safe: the
two `serve` callers (`tcw/serve/__init__.py:588`, `624`) and the internal one
(`fs.py:2961`) all test for `None`, so nothing user-facing breaks today.

The fix belongs with this item because it is the same question — what does a
write path that loses the race return or raise? — and answering it twice, in two
different ways, is how the two layers drift apart.

## Meta changes

Found while implementing
`2026-08-11-harden-effect-transition-against-a-lost-status-transition-race`;
recorded in that item's spec (§Design 3) and non-goals rather than fixed there.
The `get_detail` half was found by the local-LLM review at that item's verify
stage and folded in here by the user's decision.
