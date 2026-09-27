# Spec: show the server's message for a web save refused for a reason other than a stale revision

## Capability changes

None. The web app's save keeps its behaviour for a stale revision; other refusals
now show the server's message instead of the stale-write banner.

## Problem

The server answers 409 in five places (`tcw/serve/__init__.py`):

- `_map_store_error` for `StaleRevision` (line 294-295) — every stale-revision
  refusal goes through it (lines 928, 958, 983, 1192, 1235, 1268, 1329, 1357,
  1404, 1440);
- strict-tracker refusals on create, actions and delete (lines 883, 948, 1455);
- a write to a generated sidecar (line 1373).

The client's two save branches (`web/client/src/ui/app.tsx:629` for the PATCH of
an item's fields and `:661` for the PUT of an artifact or sidecar) treat *every*
409 as a stale write: they open the "Stale write detected" banner
(`content-views.tsx:836`) and drop `result.error`. Today the only non-stale 409
that reaches those two branches is the generated-sidecar refusal; the strict
refusals are on routes whose client handler (`doAction`) already shows
`result.error`. The plan-stage delete (`app.tsx:744`) also treats 409 as
"changed", but its route can only 409 through `StaleRevision`.

## Goals

1. A stale-revision refusal carries a machine-readable marker in its JSON body:
   `"code": "stale-revision"`, alongside the existing `"error"` text. Status stays 409.
2. Both save branches open the conflict banner only for that marker. Any other
   failed save, 409 included, shows the server's `error` text and keeps the draft.
3. No other status code or message changes.

## Non-goals

- Changing the HTTP status of strict or generated-sidecar refusals (tests pin
  409: `tests/test_tracker_strict.py:1021,1025`, `tests/test_serve_write.py:737`).
- The plan-stage delete handler: correct today, and it uses raw `fetch`.

## Design

Server: `_map_store_error` passes `code="stale-revision"` to `_err` (which
already merges extra fields). Client: one exported helper in
`web/client/src/model/api.ts`, `isStaleWrite(result)` → `status === 409 &&
data?.code === "stale-revision"`, used by both save branches. Option chosen over
a new status code or parsing the message text after consulting two advisors;
see `outcome.md`.

## Acceptance criteria

1. `test_update_stale_revision_409` (and a PUT counterpart) assert the body's
   `code == "stale-revision"`; the generated-sidecar and strict refusals assert
   no `code` key.
2. A vitest test of `isStaleWrite`: true for 409 with the marker; false for 409
   without it, for 409 with no body, and for other statuses.
3. The Playwright stale-write test in `web/e2e/parity.spec.ts` still passes
   (banner shown on a real concurrent edit).
4. Python suite, vitest, typecheck and lint pass.

## Risks

- An outside client relying on the exact 409 body: the change only adds a key.
