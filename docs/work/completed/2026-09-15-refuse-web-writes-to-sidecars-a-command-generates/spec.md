# Spec: Refuse web writes to sidecars a command generates

## Capability changes

- **changed:** `web/editing` — its "A sidecar a command writes rather than a person"
  paragraph names `tracker.yaml` beside `rollup.md`, and says a write to either is
  refused with the command that owns it, not only that no edit control is offered.

## Problem

`WORK_SIDECARS` (`tcw/store/base.py:2484-2509`) marks `rollup.md` (written by
`tcw work reconcile`) and `tracker.yaml` (written by `tcw work tracker import`,
`link` and `unlink`) as `generated: "yes"`. The server reports that flag
(`tcw/serve/__init__.py:675`, `:739`) and the client hides the Edit button
(`web/client/src/ui/content-views.tsx:571-578`), but
`PUT /api/work/<slug>/sidecars/<name>` (`tcw/serve/__init__.py:1316-1359`) checks
only that the name is registered and the item exists. The one exception is
`tracker.yaml` under strict tracker mode (`:1337`, via `_strict_refuses`'s
`"tracker.yaml"` branch at `:239-240`). Anything else passing the origin and
content-type checks overwrites either file: a `rollup.md` edit is lost on the next
`reconcile`; a `tracker.yaml` edit can make `tracker import` report a ticket as
bound, or refuse over a malformed binding.

`GET` is the only other sidecar route (`:615`, `:648`); there is no sidecar
`DELETE`.

## Goals

- `PUT` of a `generated` sidecar is refused before anything is written, in every
  mode, with a message naming the command that writes it.
- The command name lives in one place, the registry, so the refusal and any future
  surface cannot disagree.

## Non-goals

- `write_sidecar` itself — the owning commands write through it.
- The web client, which already hides the control.
- Treating this as a security boundary; a text editor can still change both files.

## Design

- The registry's `generated` value becomes the owning command instead of `"yes"`:
  `rollup.md` → `tcw work reconcile`; `tracker.yaml` →
  `tcw work tracker import, link or unlink`. It stays a string, so the discovery
  endpoints' `bool(...)` is unchanged, and the comment above the registry says the
  value names the command.
- In the `PUT` route, after the registered-name check and before resolving the item,
  refuse with **409 Conflict** (the status the strict refusal already uses for this
  route) and the message `<name> is written by <command>, not edited; run that
  command instead.`
- Remove the now-unreachable strict special case: the `name == "tracker.yaml"`
  check in the route and the `"tracker.yaml"` branch of `_strict_refuses`.

Litmus test: the registry is store-neutral metadata and the refusal is a surface
rule; nothing depends on files.

## Acceptance criteria

1. With strict mode off, `PUT /api/work/<slug>/sidecars/rollup.md` and
   `…/tracker.yaml` return 409 with a body naming `tcw work reconcile` and
   `tcw work tracker` respectively, and the item folder's bytes are unchanged.
2. The same `PUT` of `tracker.yaml` under strict mode returns 409 and changes
   nothing (the existing strict web test keeps passing with `tracker.yaml`
   asserted by its new message).
3. `PUT …/capabilities.yaml` still succeeds (existing `tests/test_serve_write.py`
   sidecar test).
4. `GET /api/work/<slug>/sidecars` still reports `"generated": true` for both and
   `false` for `capabilities.yaml`.
5. `grep -n '"tracker.yaml"' tcw/serve/__init__.py` finds no strict-mode branch.
6. The full suite passes.

## Risks

- A refusal before the item lookup means a generated name on a missing item
  returns 409 rather than 404. Accepted: the answer for that name is the same
  whatever the item.
