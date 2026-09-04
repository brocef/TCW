Found by an adversarial review of the partial-graph work, 2026-09-04.
Reproduced.

`epic_completable` returns False whenever `incomplete_graph_note()` is non-empty.
`complete()` computes `from_backlog_epic = … and self.epic_completable(item)` and
then raises `IllegalTransition` **before** the `if not force:` block. So in this
feature's own target scenario — a checkout missing one connected project — a
`backlog` epic whose visible slices are all resolved cannot be completed at all:

```
$ tcw work complete <epic> --resolution done --confirm --force
tcw work complete: cannot complete from backlog as 'done' (→ completed)
```

Two things are wrong. The message blames the status transition; the cause is the
unreachable project, which is named nowhere. And the sibling gate ten lines below
says *"or use `--force`"* — which cannot reach this one, because the refusal
happens before the force check.

`test_an_epic_is_not_completed_over_slices_this_checkout_cannot_see` calls
`st.start(epic.slug)` first, moving the epic to `active` where
`(active, completed)` *is* a legal transition — so `--force` works there and the
backlog route is never exercised. The fixture makes the bug impossible.

Related, and the same shape: **`incomplete_graph_note` swallows every
exception** (`except Exception: return ""`), so any failure to open the registry
reads as "the graph is complete" — failing the completion gate *open*, the one
direction the surrounding comment argues must not happen.

And **it lists the same project once per declaring config**: `_unreachable_edge`
dedupes on the whole `UnreachableProject` (id + `declared_in` + declaration), so
one absent project declared by two present configs renders as
`missing connected project(s): proj-c, proj-c`.
