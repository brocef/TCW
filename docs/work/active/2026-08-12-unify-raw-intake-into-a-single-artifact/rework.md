# Rework — Unify raw intake into a single artifact

Rejected at `verify`. Criteria 1–7 and 9–12 are met and were re-confirmed by hand
after the merge with `main` (scratch node: all three inbox shapes, all four board
states, promotion by direct file write, empty-request-beside-real-intake, an item
with neither artifact). The suite is green at 1310.

**Criterion 8 is met at the API and false at the surface a user touches.** The
web app was never taught about intake, and `verify` is where that showed up —
`outcome.md` predicted it under "Not done: clicking through `tcw serve`'s
editor."

## What still has to be done

### 1. The request tab must stop rendering intake under the request's name

`web/client/src/ui/work-document-tabs.tsx:140` renders `item.body` in the
"Initial Request" tab. After this item, `body` resolves through the fallback, so
an **intake-only item shows its raw intake labelled "Initial Request"** — the
exact conflation this work exists to remove, reintroduced one layer up. Worse,
"Edit Initial Request" then opens that intake text in the body editor, and saving
writes it into `initial-request.md`: the user promotes an item while believing
they are editing the document they are looking at.

Gate the tab's body on the `initial-request` artifact being **present**, using
the `artifacts` prop the component already receives. When it is absent, show the
not-yet-present notice the spec and plan tabs already use
(`work-document-tabs.tsx:142-147`) and keep the Edit button — writing it is how
the request comes into being.

`item.body`'s fallback is correct for `tcw work show`, which has one body surface
and says so. It is wrong for a tab that names which document it is showing.

### 2. Saving a body that created the request must say so

`serve/__init__.py:1002` puts `"promoted"` in the PATCH response and **nothing
reads it** — `grep -rn "promoted" web/ tcw/serve/dist` is empty. The capability
`work/capture-raw-intake` claims "that edit promotes the item and says so"; the
CLI has no body-write path at all, so `serve` is the only place that sentence can
be true, and today it is not.

`app.tsx:630` calls `showSaveResult("Saved", result.data)` on the work core
PATCH. Distinguish the promoting save there.

### 3. Intake needs no new tab

Already reachable: `content-views.tsx:393-431` renders every present artifact
outside the three-tab set as a button row, and `intake` now qualifies. Adding a
fourth tab would be scope this rejection does not ask for. Confirm it renders and
leave it.

### 4. Re-run the checks

`pnpm` test suite for the changed components, a rebuilt `tcw/serve/dist` (it is
tracked, and a stale build is what let this ship), and the by-hand click-through
that `outcome.md` deferred: an intake-only item in `tcw serve`, the request tab,
the edit, the notice.

## Not in this rework

**`tcw work reconcile` still writes `initial-request.md`** for an epic with no
request, which remains the one path that can light `R` on an item nobody wrote
up. `outcome.md` raised it deliberately and it is out of scope here — it is a
reconcile defect, not an intake one. File it as its own item at closeout.

## Notes

- The spec is not wrong, and this is not a spec defect. Criterion 8 says
  "verified through `serve`'s PATCH path", and the PATCH path is verified. What
  it did not say is that `serve` is more than its API — a criterion written
  against a handler cannot catch a frontend that ignores the handler's answer.
  Worth carrying into C2, which also touches a projection `serve` consumes.
- Both fixes are small and local. The reason this is rework rather than a
  follow-up is that shipping otherwise would land a capability whose only
  interactive surface contradicts it.
