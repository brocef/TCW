# Let a node declare its own work item state fields

A project should be able to say which extra fields its work items carry — a
worktree name, a machine name, whatever its process needs in order to say where
a piece of in-flight work actually is — rather than living with whatever field
set TCW happens to ship.

The field set should be **extensible by the node**, not fixed by TCW, and not
open. A declared field should behave the way a tag does: registered in
`tcw-config.yaml`, refused by the store when it was never registered,
displayable, and filterable from `list`.

## Where this came from

This is one half of
`2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`,
which arrived as two asks: record the branch a work item is being implemented
on, and let a node declare its own fields. The request paired them because the
second was assumed to be what makes the first acceptable to a project that does
not want a `branch` field.

Reading the code at the spec stage broke that assumption. `branch` is already a
real `WorkItem` field (`tcw/store/base.py:1880`), already emitted by
`WORK_ITEM_SCHEMA` (`tcw/work/projection.py`), and already written by
`tcw work start --worktree` (`tcw/work/cli.py:790-791`) — so recording it on a
plain start adds no field and needs no extension mechanism. The two halves turned
out to be independent, and very differently sized. They were split rather than
specced together. The branch half keeps the original slug; this item is the
other half, and it is the larger one.

The original request's words on this half are preserved below.

## The original request, on this half

> **Not every project wants that field, and some want others** — a worktree
> name, a machine name, whatever their process needs in order to say where a
> piece of in-flight work actually is. So the field set should be extensible by
> the node rather than fixed by TCW.

### What does not exist

> There is no notion of caller-supplied metadata anywhere in the work model. The
> field vocabulary is closed at three layers: the `WorkItem` dataclass, the
> adapter read that populates it, and the JSON projection, which sets
> `additionalProperties: false` and requires every declared key.
>
> One thing that is true today but is not a contract: the filesystem adapter
> writes state by read-modify-write over the whole mapping (`_set_fields_at`,
> and the `edit` path), so a key added to a `state.yaml` by hand survives
> subsequent edits and transitions. Nothing reads it, nothing shows it, nothing
> can filter on it, and another adapter is free to drop it. It should not be
> mistaken for support.

### Notes carried over

> - **An open per-item map is the wrong shape.** The abstraction litmus test
>   names this case directly, under what to keep out of the model: "Globbing a
>   store folder as an open namespace — bound it: body + named fields + named
>   attachments." An operation defined as "set any key on any item" is one no
>   shared interface can promise: Jira holds arbitrary custom fields, GitHub
>   Issues holds none.
> - **Tags are the precedent that does fit.** They are a node-declared
>   vocabulary: registered in `tcw-config.yaml`, refused by the store when
>   unregistered, and filterable from `list`. A declared set of named fields
>   would follow the same rule, stay bounded, and let a non-filesystem adapter
>   map each declared field onto a real custom field or refuse the declaration
>   up front rather than silently dropping writes.
> - **Machine name deserves scrutiny at the spec stage.** A branch is a property
>   of the work. A hostname is a property of whoever last touched it, it goes
>   stale with no event to correct it, and no store can verify it. `owner` and
>   `started` already answer who holds an item and since when. This is an
>   argument about that one field, not about the extension mechanism, which
>   should not care what a node declares.

## Notes

- The machine-name argument above is an argument about **one candidate field**,
  and it stays out of this item's scope either way. Whether a node may declare
  such a field is the mechanism's business; whether TCW ships it is not this
  item.
- No new reference material was asked for at the split; this item inherits the
  original request's references, which were filed with it.

## References

- `tcw/store/base.py` — `WorkItem`, the closed dataclass a declared field has to
  reach, and `WorkStore`, whose abstract surface would have to carry the
  registry and the refusal.
- `tcw/work/projection.py` — `WORK_ITEM_SCHEMA`, which sets
  `additionalProperties: false` and requires every declared key, and
  `SCHEMA_VERSION`, which a new field would have to move.
- `tcw/store/fs.py` — `registered_tags` / `register_tags` / `_validate_tags` /
  `check`, the whole tag-registry pattern this would follow, and `_read_item` /
  `_set_fields_at`, which would have to read and write a declared field.
- `tcw/work/cli.py` — `_print_item`, the `list` parser, `_edit`, and the
  `tcw work tags` subcommand group, the surfaces that would have to show,
  filter, set, and register.
- `web/client/src/model/types.ts` — the web client's own view of the item
  document, which moves with the schema.
- `docs/lifecycle/abstraction.md` — the bounded-fields rule an open metadata map
  would break.
- `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`
  — the other half of the original request. Independent of this one, and
  deliberately not blocked on it.
- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge` —
  adjacent, not a duplicate. That item syncs lifecycle state to an external
  tracker; this one would give that bridge a declared field to map.
