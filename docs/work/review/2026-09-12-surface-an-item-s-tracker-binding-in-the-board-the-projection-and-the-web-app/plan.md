# Plan — Surface an item's tracker binding in the board, the projection and the web app

Implementation happens in `.worktrees/<slug>/` on `work/<slug>` (`tcw work start
--worktree`). Python tests run with the current directory set to the worktree and
the editable install re-pointed at it (`pip install -e <worktree> --no-deps`),
restored to the primary checkout before `tcw work complete`.

Every new Python test goes in one new file, `tests/test_tracker_surface.py`, so the
existing tracker and projection test files stay unedited (spec criteria 7 and 11).
Its fixture is a git-initialised node with no `work.tracker` block, one item per
case, and `tracker.yaml` written through `store.write_sidecar` with content from
`binding_document` — no fake tracker is needed, because nothing here calls one.

## Task 1 — Move the binding classification into the model

**Files:** `tcw/store/base.py`, `tcw/tracker/intake.py`,
`tests/test_tracker_surface.py` (new).

- In `base.py`, beside `declared_capabilities`: `Unbound`, `Malformed`, `Bound`
  (moved unchanged, plus `bound: str = ""`), and `classify_binding(parsed)` —
  today's `read_binding` body from "not a mapping" onwards, taking the
  already-parsed value. `bound` is `str(value)` when present and not `None`, else
  `""`. Also `binding_value(result) -> dict | None`, the three shapes of the spec's
  table.
- In `intake.py`: `read_binding(content)` keeps its signature — `None` → `Unbound`,
  a YAML error → `Malformed("not valid YAML (…)")`, otherwise
  `classify_binding(yaml.safe_load(content))` — and imports `Unbound`, `Malformed`,
  `Bound` from `base.py` so `from tcw.tracker.intake import Bound` keeps working.
  The module docstring points at the new home.
- Tests: `binding_value` for a `binding_document` binding, one whose `bound` YAML
  reads as a date, one with no `url` and no `bound`, an unlinked document, and the
  two malformed cases of spec criterion 4.

**Proves:** the new tests; the whole of `tests/test_tracker_*.py` passing unedited
(criterion 11).

## Task 2 — `WorkItem.tracker`, populated by the filesystem adapter, declared in the schema

**Files:** `tcw/store/base.py`, `tcw/store/fs.py`, `tcw/work/projection.py`,
`tests/test_tracker_surface.py`.

- `WorkItem.tracker: dict | None = None`, last in the dataclass, with a comment
  naming the three shapes.
- `FsWorkStore._read_item`: when `tracker.yaml` exists, read it, parse with
  `yaml.safe_load` (a `YAMLError` becomes the `Malformed` value, with the same
  reason text `intake.read_binding` gives), and set
  `tracker=binding_value(classify_binding(parsed))`. Imports nothing from
  `tcw.tracker`.
- `WORK_ITEM_SCHEMA["properties"]["tracker"]`: `oneOf` of `{"type": "null"}`, the
  closed bound object (a closed `ticket` inside it), and the closed problem object.
- Tests:
  - `show --json` validates against the schema for bound, unbound, unlinked and
    malformed items, and the bound value equals the spec's criterion 5 (criterion
    3's JSON half, criterion 5).
  - The schema rejects an extra key at the `tracker` level and inside `ticket`
    (criterion 6).
  - In a fresh interpreter, `work list` and `work show <bound slug>` on a node with
    no tracker configured import no `tcw.tracker*` module, using the same
    subprocess approach as `tests/test_tracker_absent.py` (criterion 8).
  - `tcw serve`'s detail payload, through `tcw/serve/__init__.py`'s item-payload
    function, carries the same `tracker` value as `show --json` (criterion 9).

**Proves:** the new tests, plus `tests/test_projection.py` and
`tests/test_tracker_absent.py` unedited (criterion 7).

**Mutation check:** make `_read_item` import from `tcw.tracker.intake` and confirm
the fresh-interpreter test fails naming the module; drop the `additionalProperties`
from the ticket object and confirm the extra-key test fails.

## Task 3 — Print the binding in `show` and `list`

**Files:** `tcw/work/cli.py`, `tests/test_tracker_surface.py`.

- A small `_tracker_text(value, *, row: bool) -> str` in `cli.py` returns the
  `show` line body or the `list` segment body from the field, per the spec's
  "What each surface prints". `_print_item` prints `tracker: …` after the
  `blocked_by` line and before the body; `_render_board_item` appends
  ` | ticket: …` after the claim segment. Both print nothing for `None`.
- Tests: criteria 1, 2, 3 (text half) and 4 (text half), including that a bound
  row's text before ` | ticket:` equals the same row rendered with the field
  cleared, and that an active bound item keeps its `owner`/`started` segment
  ahead of the ticket segment.

**Proves:** the new tests; `tests/test_tracker_absent.py` unedited.

**Mutation check:** print the `list` segment for `None` as ` | ticket: -` and confirm
criterion 3's test fails.

## Task 4 — Show the binding in the web app

**Files:** `web/client/src/model/types.ts`, `web/client/src/ui/content-views.tsx`,
`web/client/src/ui/content-views.test.tsx`, `tcw/serve/dist/**` (rebuilt).

- `types.ts`: `TTrackerBinding` for the bound object and the problem object;
  `WorkItem.tracker?: TTrackerBinding | null`.
- `content-views.tsx`: inside the work detail `<Fields>`, after `Initiative`, a
  "Ticket" card when `item.tracker` is set — the key as an `<a href>` (with
  `target="_blank" rel="noreferrer"`) when the URL is non-empty, else plain text,
  then ` · jira-cloud · part default`; for a problem, "tracker.yaml cannot be read:
  <reason>". Written as a small `TrackerField` component beside `Field` rather than
  widening `Field`'s `value: unknown` contract.
- `content-views.test.tsx`: render `DetailView` for a bound, a malformed and an
  unbound item; assert the link's `href`, the problem text, and that no "Ticket"
  label renders for the unbound one (criterion 10).
- `pnpm build`, and commit `tcw/serve/dist`.

**Proves:** `pnpm test`, `pnpm typecheck`, `pnpm lint`, and `pnpm check:build`
(which rebuilds and fails on any difference under `tcw/serve/dist`).

## Task 5 — Reconcile the capabilities

**Files:** the item's `capabilities.yaml` (sidecar, written with the store's sidecar
write), and the ledger through `tcw capabilities set`.

- `capabilities.yaml`: `changed:` `work/read-a-work-item`, `work/view-the-board`,
  `work/manage-external-tracker-intake`.
- `work/read-a-work-item`: `show` names a bound item's ticket, provider, part and
  link, reports an unreadable binding, and `--json` carries `tracker`.
- `work/view-the-board`: a bound item's row ends with its ticket.
- `work/manage-external-tracker-intake`: the binding is shown by `show`, `list`,
  `--json` and the web app's item detail, still with no edit in the web app.

**Proves:** `tcw capabilities check` and `tcw validate` exit 0 (criterion 12).

## Documentation Sync

Evaluated against `tcw work docs`; all four code-facing entries fire, the
configuration entry does not.

| Entry | Fires | Change |
| ----- | ----- | ------ |
| `README.md` [Public-API] | yes | In the tracker section, after "Recording that a ticket and an item are the same work": where a binding can be read (`show`, `list`, `--json`, web app) and that what is shown is what the file records, not what Jira says. |
| `docs/release-notes/upcoming.md` [Public-API] | yes | One plain entry: bound items now show their ticket on the board, in `show`, and in the web app. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | yes | Added: `WorkItem.tracker` and the schema property (no `SCHEMA_VERSION` change; a saved copy of the old schema rejects it); `show`/`list` output. Changed: the binding classes moved to `tcw/store/base.py`, re-exported from `tcw.tracker.intake`. |
| `skills/tcw-work/…` [Skill-Driven-Component] | yes | `skills/tcw-work/references/commands.md`, "Working from an external tracker": how to read a binding, and that `show --json`'s `tracker` is `null` when unbound. |
| `skills/tcw-configure/references/…` [Configuration-Key-Change] | no | No configuration key is added or changed. |

## Verification

What the suite cannot check, done by hand at `verify`:

1. In a scratch node, bind an item by writing `tracker.yaml` with
   `binding_document`, leave one item unbound, make one malformed, and read all
   three with the installed `tcw work show`, `tcw work show --json` and
   `tcw work list`. Output matches the spec's examples.
2. Run `tcw serve` on that node and read the bound item in a browser (the dedicated
   Claude Chrome profile): the "Ticket" field links to the URL, the malformed item
   shows its reason, the unbound item has no field, and the sidecar list still
   shows `tracker.yaml` as generated with no edit button.
3. Bare `pytest` from the primary checkout on merged `main`, `tcw validate`,
   `tcw capabilities check`.

## Notes

- Sequential, not delegated: every task touches `tests/test_tracker_surface.py`, and
  Tasks 2 and 3 depend on Task 1's names.
- No blockers to record: C2 and C6 are complete, and nothing depends on C3.
