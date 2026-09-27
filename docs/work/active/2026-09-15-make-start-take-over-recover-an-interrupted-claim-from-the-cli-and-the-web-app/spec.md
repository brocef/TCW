# Spec: make start --take-over recover an interrupted claim from the CLI and the web app

## Capability changes

None to the ledger's wording: recovering an interrupted claim is part of the
existing start capability; this makes the documented remedy reachable.

## Problem

`FsWorkStore.start` (`tcw/store/fs.py:3997`) moves an item backlog →
`.claiming/<slug>-<uuid>` → active. A process that dies in between leaves the item
only in `.claiming/`. Every ordinary read (`FsWorkStore.get`, `fs.py:5555-5576`)
then raises "`<slug>` has an interrupted claim; use --take-over --owner
<identity>". The store's take-over branch reads with `_get_now` and recovers
(`fs.py:4009-4040`), but nothing reaches it:

- **CLI.** `_start` (`tcw/work/cli.py:1388-1460`) evaluates `st.get(bare)` as an
  argument to `run_pre` (`cli.py:1405-1406`) and again for `before`
  (`cli.py:1411`), both before `st.start`; the first raises.
- **Web.** The start action (`tcw/serve/__init__.py:950-963`) calls
  `work.start(slug, force=force)` — no take-over, no owner — and an item mid-claim
  is absent from `query()`, so the board never lists it. `_strict_refuses` also
  calls `work.get` before the action's error handling.

## Goals

1. `tcw work start <slug> --take-over [--owner X]` recovers an interrupted claim:
   the `pre` hook still runs first, against the item as it was (tags, type), and
   a refusing hook still changes nothing.
2. The web board shows each interrupted claim distinctly, with a Recover control
   that finishes the claim for the server's own identity (the CLI's order:
   `TCW_WORK_OWNER`, git email, git name).
3. The web's recover is recovery only: it is refused for an item that is not an
   interrupted claim, so a browser cannot take an active item from its owner.

## Non-goals

- Taking over an *active* item from its owner in the web app (CLI keeps that).
- Running `pre` hooks from the web app (it runs none today, for any transition).

## Design

- **Store (abstract).** `WorkStore.interrupted_claims() -> list[WorkItem]`,
  default `[]`: items whose start began and never finished, each reported as it
  was before the claim (status `backlog`, its own slug). Storage-neutral: a
  transactional store answers it by listing uncommitted claims.
  FS: one item per `.claiming/<slug>-<32 hex>` folder whose slug has no settled
  folder, read from its `state.yaml`, slug taken from the folder name.
- **CLI `_start`.** Read the item once. When `--take-over` is given and the
  ordinary read has nothing (checked with `interrupted_claims()` before `get`, so
  no error text is matched), use the interrupted claim for `run_pre`, `before`
  and `previous`. `item_path` is None for the hook (the item has no settled
  folder); `source` keeps using `_tracked_source`.
- **Strict tracker mode.** *(Revised after code review.)* Recovery claims the
  ticket exactly as a strict start does: the interrupted start may have run
  before strict mode was on, or the ticket may have changed hands. The binding
  comes from the claimed item's `tracker` field, since no store read reaches a
  claim.
- **Web.** `GET /api/work/interrupted-claims` → `[{slug, title}]` for every node
  the board shows. The start action accepts `recover: true` and calls
  `work.start(slug, owner=<server identity>, recover=True)` — *(revised after code
  review)* a store-level recover-only take-over that refuses a settled item
  against the same read it acts on, so the check cannot race the claim.
  `_strict_refuses` no longer calls a read that raises on such a slug.
  Client: a notice above the work list naming each interrupted claim, with a
  Recover button that posts `recover: true`.

## Acceptance criteria

1. With an item left in `.claiming/` (created by moving its folder there, as a
   dead process would), `tcw work start <slug> --take-over --owner me` exits 0 and
   the item is active, owner `me`.
2. A `pre` hook bound to `start` with `when: {tags: [<the item's tag>]}` that
   exits non-zero refuses that recovery, and the item is still in `.claiming/`.
3. Without `--take-over`, `start` still refuses with the interrupted-claim message.
4. `--take-over` on an active item owned by someone else still takes it over (CLI).
5. `GET /api/work/interrupted-claims` lists the item; `POST
   /api/work/<slug>/actions/start {"recover": true}` makes it active with the
   server's identity as owner; the same call on a backlog or active item is
   refused (422, "not an interrupted claim") and changes nothing.
6. The board shows the notice and the Recover button (vitest), and clicking it
   posts `recover: true`.
7. Full Python suite, vitest, typecheck, lint, and Playwright pass.

## Risks

- A claim still genuinely in flight (another process mid-start) is listed as
  interrupted at once, without `get`'s 500 ms wait. Recovering it then races the
  claimant's own rename; one of the two fails. That race is the store's existing
  take-over race, shared with the CLI, and is not widened here.
