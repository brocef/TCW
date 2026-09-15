# Spec: build taxonomy list's tree from real parentage instead of sorting path strings

## Capability changes

None. Checked against the ledger: `taxonomy/list-the-taxonomy` describes reading
the tree back and does not specify an ordering rule, so its wording stays true
before and after. This is a defect in how an existing capability behaves. No
`capabilities.yaml` sidecar for this item.

## Problem

`_list` (`tcw/taxonomy/cli.py:52-60`) derives order and depth from two
independent expressions that can disagree:

```python
for t in sorted(st.list_all(local_only=args.local),
                key=lambda t: (t.origin != "local", t.qualified)):   # :56  order
    indent = "  " * t.slug.count("/")                                # :57  depth
```

Order comes from the **joined** path string; depth comes from the segment count.
`-` (0x2D) sorts before `/` (0x2F), so a root slug that is a hyphen-extension of
another root slug lands *between* that root and its children and inherits their
indentation.

Reproduced at HEAD, verbatim from the issue's steps:

```
event  [V] (local)
event-reporting  [F] (local)
  log-batch  [V] (local)
  stat  [V] (local)
```

`log-batch` and `stat` are children of `event`, not of `event-reporting`. On
disk the tree is unambiguous (`docs/taxonomy/event/log-batch/meta.yaml`), and
`tcw taxonomy show event/log-batch` reports the real parent.

Two things make this worse than a cosmetic slip:

- **Nothing flags it.** The data is correct, so `tcw taxonomy check` and
  `tcw validate` both pass. `list` is the primary way a human or an agent reads
  the tree back, so a wrong parent here is simply believed.
- **The collision is actively encouraged.** `skills/tcw-taxonomy/references/init.md`
  has Features name the interaction area over a term, which is exactly what
  produces `Event` / `Event Reporting`, `Watermark` / `Watermarking`,
  `Category` / `Category Sync`.

## Goals

- Ordering can never interleave a subtree with an unrelated sibling.
- Rendered indentation always reflects real parentage.
- Sibling order within a level is stable and alphabetical.
- Inherited terms remain distinguishable from local ones.

## Non-goals

- **Changing `list`'s output format.** Same two-space indent, same
  `<leaf>  [V|F] (origin)` row shape. Only row *order* changes, and only where it
  was wrong.
- **Changing `--local`, the `[V]`/`[F]` markers, or the origin suffix.**
- **Fixing the web editor.** It has no defect — see Design.
- **Adding a `--tree`/`--flat` switch.** Nobody asked for one, and the current
  output is already meant to be a tree.
- **Hoisting orphaned nested terms.** See Risks.

## Design

### Sort on the tuple of path segments

One change, at `tcw/taxonomy/cli.py:56`:

```python
key=lambda t: (t.origin != "local", t.origin, tuple(t.slug.split("/")))
```

Comparing segment tuples compares path *structure* rather than path *text*. A
parent's tuple is a strict prefix of its children's, so children always sort
immediately after their parent and before any sibling that merely shares a
textual prefix:

| slug | old key | new key |
| --- | --- | --- |
| `event` | `"event"` | `("event",)` |
| `event-reporting` | `"event-reporting"` | `("event-reporting",)` |
| `event/log-batch` | `"event/log-batch"` | `("event", "log-batch")` |
| `event/stat` | `"event/stat"` | `("event", "stat")` |

Old order interleaves (`event`, `event-reporting`, `event/log-batch`,
`event/stat`) because `"event-"` < `"event/"`. New order is
`("event",)` < `("event","log-batch")` < `("event","stat")` < `("event-reporting",)`
— a correct depth-first pre-order.

Because the traversal is now a genuine pre-order, `slug.count("/")` at `:57`
becomes a *correct* depth for every row, so the existing indent line needs no
change. The two expressions stop disagreeing not by merging them but by making
the ordering one the tree order the depth one already assumed.

**Why not build an explicit node tree.** The issue offers both. An explicit tree
is what `tcw/work/cli.py:365-380` does for the work board, and what the web
client's `buildPathTree` (`web/client/src/model/tree.ts:17-46`) does — but both
need one because they carry *non-path* parentage (a work item's `parent`/
`initiative` field can point outside its path). Taxonomy parentage **is** the
path: `Term.slug` is documented as "path from the taxonomy root"
(`tcw/store/base.py:142`). With parentage and path identical, a segment-tuple
sort and an explicit tree produce the same order, and the sort is one line
against roughly thirty. Building a tree here would add an intermediate structure
to re-derive information the slug already carries.

### Inherited terms: grouped per origin, which is structural not cosmetic

The request asks whether inherited terms should interleave with local ones once
ordering is per-level. **They must not**, and the reason is stronger than
presentation: they are not in the same tree.

`FsTaxonomyStore.list_all` (`tcw/store/fs.py:774-779`) builds its result from
`self._local_slugs()` plus, per `extends` alias, that **separate store's**
`_local_slugs()`. Each origin is an independent taxonomy with its own root set
and its own slug namespace; `Term.qualified` (`tcw/store/base.py:155-158`)
prefixes the alias precisely because the bare slug is only unique within an
origin. A local `event` and an inherited `event` are different terms, and no
local term is ever a child of an inherited one.

So the key keeps `t.origin != "local"` as the outer term (local block first) and
adds `t.origin` as the second, replacing the alias-prefix grouping that
`t.qualified` used to provide implicitly. Sorting the segment tuple across
origins would splice two unrelated trees together and produce exactly the class
of false parentage this item exists to remove.

### Nothing else renders this tree

The request asks what else consumes the flat sorted `list_all()`. Checked:

- `tcw/taxonomy/cli.py:57` is the **only** indentation-from-slug-depth site in
  the Python tree (grep for `count("/")` / `indent` across `tcw/`).
- The **web editor has no defect**: `buildPathTree`
  (`web/client/src/model/tree.ts:17-46`) inserts every path segment as a map
  entry and attaches each node to `map.get(parentPath)` — real parentage, never
  a string sort. It cannot exhibit this bug.

## Acceptance criteria

1. The issue's exact reproduction renders `event-reporting` as a root with no
   children, and `log-batch`/`stat` indented under `event`:

    ```
    event  [V] (local)
      log-batch  [V] (local)
      stat  [V] (local)
    event-reporting  [F] (local)
    ```

2. Ordering is a depth-first pre-order: every term appears immediately after its
   parent and before its parent's next sibling, at any nesting depth (test with
   at least three levels).
3. Siblings within a level are alphabetical.
4. Inherited terms still sort after all local terms, grouped by origin alias,
   and an inherited tree is never interleaved with the local one.
5. `--local` is unaffected.
6. Row format is byte-identical to before for any taxonomy that did not exhibit
   the collision — indent width, markers, origin suffix.
7. A regression test pins the hyphen-vs-slash collision specifically
   (`event` / `event-reporting` / `event/log-batch`), so re-sorting on a joined
   string in future fails the suite.
8. `python -m pytest -q` green.
9. `docs/changelogs/upcoming.md` `Fixed` entry; `docs/release-notes/upcoming.md`
   entry — the wrong output was user-visible and is what the issue reports.

## Risks

- **An orphaned nested term still renders indented under nothing.** If
  `event/log-batch` exists with no `event/meta.yaml`, it renders at depth 1 with
  no parent row above it. This is pre-existing, not introduced here, and an
  explicit tree would expose the same choice (hoist, or render a placeholder
  row). Out of scope: no such taxonomy is reachable through `tcw taxonomy add`,
  which creates the parent chain. Noted so the next reader knows it was
  considered rather than missed.
- **A taxonomy that relied on the old interleaved order** would see rows move.
  That order was the bug; anything depending on it was misreading the tree.
- **Sibling order for names differing only by case or punctuation** is plain
  string comparison per segment, unchanged from before.

## Notes

Reproduced at HEAD before writing this spec, in a throwaway repo using the
issue's exact commands — output matched the report character for character.

`tcw/taxonomy/cli.py:56` is a single long line; the fix keeps it one expression.

GitHub issue #11's closeout is deferred until the containing minor version is cut
and pushed, per the user's sequencing decision on 2026-07-30.
