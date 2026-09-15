# Spec — Surface an item's tracker binding in the board, the projection and the web app

## Capability changes

Planned deltas only; nothing is written to the ledger here.

| Capability | Delta | Why |
| ---------- | ----- | --- |
| `work/read-a-work-item` | changed | `tcw work show` gains a `tracker:` line, and `--json` gains a `tracker` property. |
| `work/view-the-board` | changed | `tcw work list` rows for bound items gain a `ticket:` segment. |
| `work/manage-external-tracker-intake` | changed | Its text says the binding is written by commands and the web app offers no edit for it; it should now also say where the binding can be read. |

**The epic's table named `work/open-a-work-item`, not `work/view-the-board`.**
That was a slip: `open-a-work-item` describes `tcw work new`
(`tcw capabilities show work/open-a-work-item`), which this item does not touch,
and `tcw work list` is described by `work/view-the-board`. The epic's `spec.md` is
corrected in a commit beside this one.

No capability is added, and `web` (the local web app) is not changed: its text
describes browsing and editing objects in general and names no field.

The taxonomy is unchanged. The `external-work-tracker` Feature
(`tcw taxonomy show external-work-tracker`) already covers the binding, and the
two capabilities above that do not name it (`read-a-work-item`, `view-the-board`)
are general work-item reading capabilities whose Feature is not changed by adding
one more field.

## Problem

`tcw work tracker import` and `tcw work tracker link` record a binding between an
item and a tracker ticket in the `tracker.yaml` sidecar (`tcw/store/base.py:2095`),
and nothing shows that binding to a person afterwards:

- `tcw work show` prints a fixed set of `WorkItem` fields and the first twelve
  body lines (`tcw/work/cli.py:151`). No tracker field exists to print.
- `tcw work list` builds each row from the item and its artifacts
  (`tcw/work/cli.py:400`); a sidecar is never consulted.
- `tcw work show --json` projects every `WorkItem` field plus `schema` and
  `artifacts` (`tcw/work/projection.py:142`), against a closed schema
  (`tcw/work/projection.py:102`). `WorkItem` has no tracker field
  (`tcw/store/base.py:2157`), so the document cannot carry one.
- The web app lists `tracker.yaml` by file name under "Sidecars" with a
  "generated" label instead of an edit button
  (`web/client/src/ui/content-views.tsx:548`), and its item fields
  (`web/client/src/ui/content-views.tsx:357`) have no ticket.

So the only way to learn which ticket an item answers is to open the file.

## Goals

1. Anyone reading an item — at the terminal, through `--json`, or in the web app —
   sees whether it is bound, and if so to which ticket, on which provider, for
   which part, with the ticket's link.
2. A `tracker.yaml` that cannot be read is reported where the item is read, and
   never breaks the read.
3. Items with no binding read exactly as they do today on the text surfaces and in
   the web app.
4. None of this contacts the tracker or loads the tracker package.

## Non-goals

- **Whether the ticket is in step with the item** — current, pending or
  conflicting. That state is created by C3
  (`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`), which adds
  its own indicator beside what this item prints.
- **What the tracker says now.** Nothing here reads the ticket. What is shown is
  what the binding records, which is never proof of a claim
  (`tcw/tracker/intake.py:8`).
- **Who took the ticket.** The binding stopped recording it when C6 removed
  `claimed-by`; there is nothing to show.
- **The `unlinked` history.** An unlinked item is shown as unbound. Showing the
  history of past bindings is not asked for.
- **Whether the binding's site matches the configured site.**
  `docs/work/inbox/2026-09-14-a-tracker-binding-does-not-record-its-site.md`
  describes a binding outliving a change of `base-url`. The URL shown here is the
  one recorded, which is the correct thing to show. Acting on a mismatch matters
  where a ticket is changed, which is C3.
- **Editing the binding in the web app.** It is already offered no edit button;
  the server-side refusal for generated sidecars is
  `docs/work/inbox/2026-09-14-serve-accepts-writes-to-generated-sidecars.md`.
- **The web app's tree rows.** The detail view shows the binding; the tree does not
  gain a column.
- **Reusing the new field inside `find_binding`** (`tcw/tracker/intake.py:131`),
  which reads each item's sidecar again after `query()` already has. It needs the
  revision for writes as well, so it is not a drop-in change.

## Design

### The JSON route: a `WorkItem` field

The epic requires one of two routes for `--json` (epic `spec.md` § Design C5): a
`WorkItem` field or a `SCHEMA_VERSION` bump. **This item adds a field,
`WorkItem.tracker`.**

- A binding is item data any store could supply — a tracker-backed store would
  hold the same facts in its own fields — so it passes the abstraction litmus test
  as a model field, as the epic's own verdict table already says ("Surfacing
  tracker state in the JSON projection | model").
- A field flows into `work_item_json` and into `tcw serve`'s item payload
  (`tcw/serve/__init__.py:79`) with no new code, so the CLI and the web app cannot
  disagree about it.
- **Adding a property is not an incompatible change, so the version stays 1.** The
  spec that introduced the document set that rule: every new `WorkItem` field must
  be declared, and "if the shape has to change incompatibly later,
  `SCHEMA_VERSION` goes to 2"
  (`docs/work/completed/2026-08-12-project-a-work-item-as-json/spec.md`, § Risks).
  A consumer reading fields is unaffected. A consumer that validates against its
  own copy of the version-1 schema will reject the new property; that is named
  under Risks rather than hidden.
- A bump alone does not work: a projection-only property fails
  `test_the_schema_declares_exactly_the_model_plus_two`
  (`tests/test_projection.py:113`), which may not be edited (epic criterion 10).

The value is JSON-native and has exactly three shapes:

| The item's `tracker.yaml` | `WorkItem.tracker` |
| ------------------------- | ------------------ |
| absent, or no `ticket` key (what `unlink` leaves) | `null` |
| a binding `read_binding` accepts | `{"provider", "project", "part", "ticket": {"id", "key", "url"}, "bound"}` — all strings |
| anything `read_binding` refuses | `{"problem": "<reason>"}` |

`url` and `bound` are strings that may be empty: `read_binding` does not require a
URL (`tcw/tracker/intake.py:105`), and a hand-written binding may have no `bound`
date. A `bound` that YAML reads as a date is rendered as its ISO string. Neither
missing value makes a binding malformed, because today's classifier does not treat
them so and this item does not change what counts as bound.

`WORK_ITEM_SCHEMA` declares the property as a closed `oneOf` of `null`, the bound
object, and the problem object, each object with `additionalProperties: false`.

### Where the classification lives

The filesystem adapter builds every `WorkItem` (`FsWorkStore._read_item`,
`tcw/store/fs.py:4205`), and `tcw work list` on a node with no tracker must import
no `tcw.tracker` module (`tests/test_tracker_absent.py:126`). The adapter cannot
call `tcw.tracker.intake.read_binding` for that reason, and a store importing the
tracker package would also invert the layering `tcw/tracker/__init__.py` states.

So the classification moves into the model, following the pattern
`declared_capabilities` already sets (`tcw/store/base.py:289`): `base.py` classifies
an **already-parsed** sidecar and imports no YAML library, and the caller parses.

- `Unbound`, `Malformed`, `Bound` and a classifier over the parsed value move to
  `tcw/store/base.py`. `Bound` gains `bound`.
- `tcw/tracker/intake.py` keeps `read_binding(content)` as "parse, then classify",
  and re-exports the three names, so every existing caller and test keeps working
  unedited.
- `_read_item` parses `tracker.yaml` when it exists, the way it already parses
  `capabilities.yaml` (`tcw/store/fs.py:4208`), and stores the table's value.

### What each surface prints

**`tcw work show`** gains one line, printed after every existing field line and
before the body, and only when `tracker` is not `null`:

```
tracker: EX-1 (jira-cloud, part default) https://example.atlassian.net/browse/EX-1
tracker: tracker.yaml cannot be read (missing or empty: ticket.key)
```

The URL is omitted when empty. The part is always named here, because `show` is
where the whole binding is read.

**`tcw work list`** appends one segment to the end of a row, after the claim
segment, and only when `tracker` is not `null`:

```
… | owner: a@b | started: 2026-09-14T10:00:00Z | ticket: EX-1
… | ticket: EX-1 (part api)
… | ticket: unreadable
```

At the end so no existing segment moves; the default part is left out, and the
reason for an unreadable file is left to `show`, to keep a row one short line. C3
extends the segment rather than adding a second ticket segment.

**The web app's item detail** gains a "Ticket" field beside the other item fields,
only when `tracker` is not `null`: the ticket key as a link to the URL (plain text
when the URL is empty), followed by the provider and the part; or, for a problem,
the text "tracker.yaml cannot be read" and the reason. The sidecar list and its
"generated" label are unchanged. The built client under `tcw/serve/dist/` is
rebuilt, since that is what `tcw serve` runs.

### Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| `WorkItem.tracker` | **model** | The binding's facts are portable data; any store can populate the field. |
| Classifying a parsed binding | **model** | Pure over a mapping; no file, path or YAML in it. |
| Parsing `tracker.yaml` into that mapping | **filesystem adapter** | Where the bytes live is the adapter's business, exactly as for `capabilities.yaml`. |
| The text and web renderings | **presentation** | Read only the field. |

## Acceptance criteria

Each is checked by a test unless it says otherwise. "A bound item" is one whose
`tracker.yaml` was written by `binding_document` for ticket `EX-1`, id `10001`,
provider `jira-cloud`, part `default`, URL `https://example.invalid/browse/EX-1`,
bound `2026-09-14`.

1. `tcw work show <bound item>` exits 0 and prints exactly one line starting
   `tracker: `, which is
   `tracker: EX-1 (jira-cloud, part default) https://example.invalid/browse/EX-1`,
   after every other field line and before the body.
2. `tcw work list` prints the bound item's row ending in ` | ticket: EX-1`; with
   part `api` it ends in ` | ticket: EX-1 (part api)`. Every segment before it is
   what the row printed before this change.
3. For an item with no `tracker.yaml`, and for one whose binding was removed by
   `tcw work tracker unlink`, `show` prints no line starting `tracker:`, the `list`
   row contains no `ticket:`, and `show --json` has `"tracker": null`.
4. For an item whose `tracker.yaml` is `ticket: {id: "1"}` (no key, provider,
   project or part), `show` exits 0 and prints
   `tracker: tracker.yaml cannot be read (missing or empty: ticket.key, provider, project, part)`,
   the `list` row ends ` | ticket: unreadable`, and `show --json` has
   `"tracker": {"problem": "missing or empty: ticket.key, provider, project, part"}`.
   A `tracker.yaml` that is not valid YAML behaves the same way with its own reason.
5. `show --json` validates against `WORK_ITEM_SCHEMA` for a bound item, an unbound
   one, an unlinked one and a malformed one, and for the bound item `tracker`
   equals `{"provider": "jira-cloud", "project": <node id>, "part": "default",
   "ticket": {"id": "10001", "key": "EX-1", "url": "https://example.invalid/browse/EX-1"},
   "bound": "2026-09-14"}`.
6. `WORK_ITEM_SCHEMA` rejects a document whose `tracker` object carries an extra
   key, at the top level and inside `ticket`.
7. `tests/test_projection.py` and `tests/test_tracker_absent.py` pass without being
   edited.
8. On a node with **no** tracker configured and a bound item, `tcw work list` and
   `tcw work show <slug>` run in a fresh interpreter import no module whose name
   starts `tcw.tracker`.
9. `tcw serve`'s item detail payload for the bound item carries the same `tracker`
   value as `show --json`.
10. The web app's item detail renders a "Ticket" field with a link to the URL for a
    bound item, the problem text for a malformed one, and no "Ticket" field for an
    unbound one (a `vitest` test in `web/client/`), and `pnpm check:build` passes,
    showing the built client was regenerated.
11. Every existing caller of `read_binding`, `Bound`, `Malformed` and `Unbound`
    through `tcw.tracker.intake` works unchanged: the tracker test files pass
    without being edited.
12. `tcw validate` and `tcw capabilities check` exit 0, and the three capabilities
    in the table above read `Supported` with text describing the new output.

### Criterion 1 of the epic, stated rather than waived

Epic criterion 1 asks that, with no tracker configured, every existing command's
output be byte-identical. **`tcw work show --json` is not**: every item's document
gains `"tracker": null`. The schema requires every `WorkItem` field, so no route
through a field avoids it, and the version-bump route fails criterion 10. Text
output of `show` and `list`, and what the web app renders, are unchanged for
unbound items (criterion 3 above). Recorded here and in the epic so the next reader
does not have to re-derive whether it was noticed.

## Risks

1. **A consumer validating against a saved copy of the version-1 schema rejects
   the new property.** The rule this project set is that an addition is not an
   incompatible change. Called out in the changelog so a script author learns it
   from there.
2. **Every item read now checks for one more file.** One existence check per item,
   and a parse only when the file exists. The board already reads each item's
   artifacts (`tcw/work/cli.py:415`), so this is not a new kind of cost.
3. **C3 has to extend this item's output rather than replace it.** The design puts
   the `list` segment last and the `show` line in one place so the sync indicator
   has an obvious home. If C3 needs a different shape, it changes this item's
   format deliberately, with its own spec saying why.
4. **Moving the classifier changes the module a reader looks in.** Mitigated by the
   re-export and by `intake.py`'s docstring pointing at the new home.

## Notes

- **Advisors consulted on the design** (autonomous run; no user available). Codex
  and an Opus subagent were given the same brief. Both chose the `WorkItem` field
  over a raw-YAML field and over a version bump. Both said epic criterion 1 cannot
  hold for `--json` on any route, which is why the exception above exists. On
  where the classifier lives they split: Codex preferred a new small module outside
  `tcw.tracker`; the Opus subagent preferred `base.py` classifying an
  already-parsed value, citing `declared_capabilities` as the existing pattern.
  Taken: the Opus subagent's, because it follows a pattern already in the model
  rather than adding a module for three small classes. The Opus subagent also
  proposed placing the `list` segment before the claim segment; not taken, because
  appending at the end is the only placement that moves no existing segment.
- **Order among the epic's remaining children.** C3's sync indicator is added to the
  same two text surfaces. This item goes first so C3 extends an identity that
  already prints, rather than this item fitting itself around C3's indicator.
