# Add a discarded work status for non-done closures

## Origin

Raised 2026-07-23 after the backlog audit, which closed three items — two
`superseded`, one `wontfix` — and put all three in `completed/` alongside genuinely
shipped work. Two frictions surfaced in that one session:

- `completed/` conflates "we built this" with "we decided not to build this".
  Answering "what shipped?" requires reading every item's `resolution`.
- Closing a backlog item requires a throwaway `backlog → active → completed`
  round-trip, because `complete` only accepts `active`. Three items got a fake
  `start` for the sole purpose of being abandonable.

## Product changes

Add **`discarded`** as a fourth work status, alongside `backlog`, `active`, and
`completed`.

### Routing rule

Resolution decides the destination, with no per-item judgment:

| Resolution | Lands in |
| --- | --- |
| `done` | `completed/` |
| `wontfix`, `duplicate`, `superseded` | `discarded/` |

`completed/` then means exactly "we shipped this", which is the property that
makes the board readable at a glance.

### Transitions

- `active → discarded` — the normal abandonment path.
- **`backlog → discarded` directly** — no throwaway `start`. This is the friction
  that prompted the request; a backlog item is the *most* likely thing to be
  abandoned and today it is the hardest.
- `discarded` is terminal: no reopen transition in this item. (Re-raising an
  abandoned idea should be a fresh item with fresh context, which is what the
  audit recommended when it closed `additional-capability-sidecars`.)

### `drop` survives unchanged

`tcw work drop` stays a hard delete for genuine mis-creations (a typo'd item, an
accidental duplicate made seconds ago). `discarded` is for decisions worth
keeping a record of. Different intents; both legitimate.

### Migration

One-time move of every existing `completed/` item carrying a non-`done`
resolution into `discarded/`, so one rule holds across the whole history. Its own
commit, separate from the feature.

## Technical changes

Blast radius, scoped from a grep of the status model:

- `tcw/store/base.py` — `WORK_STATUSES` gains `"discarded"`; `LEGAL_TRANSITIONS`
  gains `("active", "discarded")` and `("backlog", "discarded")`. `complete()`
  picks the destination from the resolution rather than hard-coding `"completed"`
  (note it already has a scoped `backlog → completed` exception for completable
  epics — that path needs re-checking against the new routing).
- `tcw/store/fs.py` — the adapter creates and scans a fourth status folder;
  status-path locators (`_ref` / line ~204) accept `discarded/<slug>`;
  `init` scaffolds it (line ~323).
- `tcw/work/cli.py` — `--status` choices pick it up from `WORK_STATUSES`
  automatically; `list` must decide whether `discarded` is hidden by default the
  way `completed` is (it should be).
- `web/client/src/ui/app.tsx` and `content-views.tsx` — both hard-code
  `const WORK_STATUSES = ["backlog", "active", "completed"]`; `model/tree.ts`
  hard-codes a status sort order. All three need the new status, and the status
  filter toggles need a fourth button.
- Migration script or one-off command for the existing non-`done` items.

## Meta changes

- **Litmus test:** a status is already the core abstract vocabulary, and the
  filesystem adapter merely realizes it as a folder. A Jira-backed store would
  express `discarded` as a resolved-but-not-done state — awkward perhaps, but
  entirely expressible. Passes.
- **Known redundancy to settle in the spec:** status and resolution now encode
  overlapping facts, so they can drift (an item in `completed/` with
  `resolution: wontfix`). Either derive status from resolution at write time and
  make the pair unforgeable, or have `tcw validate` flag disagreement. Pick one
  in the spec — do not ship a second source of truth with no reconciliation.
- Docs to sync: `README.md` (status model, `list` behavior, the lifecycle
  diagram), `docs/release-notes/upcoming.md` (user-facing status change),
  `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md` (the lifecycle
  handshake, quick-reference rows, and `references/lifecycle.md`).
- Existing `tcw://` and status-path locators pointing at migrated items will
  break if they used the `completed/<slug>` form. The status segment is
  documented as "must match the item's real status", so the spec should check
  whether anything in-repo relies on it.

## Open questions for spec

- Does `list` hide `discarded` by default (like `completed`), and does `--all`
  include it?
- Do the DoD acknowledgments still apply when discarding? Requiring "tests pass"
  to abandon an item is nonsense; the gate probably reduces to a resolution plus
  a reason.
- Does the capabilities reconciliation gate fire on discard? An item that
  declared `new:` capabilities but was abandoned should presumably mark them
  `Omitted`, not be blocked from closing.
- Do completable epics (the existing `backlog → completed` exception) need any
  change, or does the new `backlog → discarded` transition subsume that special
  case cleanly?
