# Outcome — Project a work item as JSON

All nine plan tasks shipped. Suite green at 1346 Python (baseline before this
item: 1314), 52 web unit, 14 end-to-end. Every acceptance criterion is met.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Capture the pre-change `show` baselines | `c2fe1fc` |
| 2–4 | `projection.py`: the walker, the schema, the DTO | `d80e0c2` |
| 5 | `tcw work show --json` | `c37740a` |
| 6 | `serve`'s work-item call sites | `d2dc780` |
| 7 | The web suites against the new payload | (no diff — they passed unmodified) |
| 8–9 | Documentation Sync and the capability ledger | `8e87adb` |

## The dual review earned its keep before a line was written

`codex` and `bllm-review` were run against the first draft of the spec, and one
finding is worth naming above the rest.

**Criteria 1 and 2 could have passed while the contract was wrong.** The draft
said the emitted document must validate against `WORK_ITEM_SCHEMA`, and that the
schema must be closed and fully required. Both would hold if the projection and
the schema agreed on an *incomplete* document — drop `started` from both and
nothing fails. That is the same fallacy that cost C1 three verify passes
(verified at the API, false in the client; verified by a grep, false for the
path), found this time before implementation instead of after.

The fix is criterion 3: the schema's property set must equal
`{f.name for f in fields(WorkItem)} | {"schema", "artifacts"}`. Only the model
can settle what the contract owes, so the model is what it is checked against.

**Everything the reviews claimed about YAML was reproduced before being
believed**, which is how two findings got rejected:

| Claim | Reproduced? |
| ----- | ----------- |
| Anchors produce self-referential structures | Yes — `json.dumps` raises `ValueError: Circular reference detected` |
| `!!binary` produces `bytes` | Yes — `str()` gives `"b'hi'"`, a repr posing as data |
| `!!set` produces a `set` | Yes |
| A bare date produces `datetime.date` | Yes |
| `{1: "a", "1": "b"}` keeps both keys | Yes — stringifying loses one |
| `json.dumps(nan)` emits bare `NaN` | Yes — and `default=` is never consulted for floats |
| Sorting a set by `str()` raises on mixed types | **No** — `sorted({1,"a",2.5}, key=str)` works; the key is a string and the elements are never compared |
| `--json` is a privacy exposure | **No** — `show` prints the body today and `serve` ships it over HTTP |

## Decisions the spec owed, and what they came out as

**`capabilities` is normalized in the projection.** Not `default=str`, which is
not a decision so much as the absence of one: it fires silently, anywhere in the
tree, and never for a float. Every branch of the walker exists for a shape
`yaml.safe_load` actually produces.

**A key collision raises.** `{1: "a", "1": "b"}` is the only place this item
chooses failure over output, and it is deliberate — keeping one value and
dropping the other is precisely the silent data loss the initiative keeps paying
for. The message names both keys. It will surface in `serve` as a failure on one
item's page; that is the accepted cost, recorded in the spec's risks.

**`body` is carried in full, and the epic's spec was amended rather than
overruled.** The epic required "bounded or excluded"; neither is available to a
projection `serve`'s editor reads. Excluding breaks the editor; truncating means
a body silently cut and then saved back, which is data loss presenting as
success — the exact defect C1's first rework round closed. The cap moves to C3,
at the `generate` boundary where size actually costs something, and the epic's
`spec.md` says so in the same commit as C2's spec (`0cd2f54`). Review was right
that a child quietly disregarding its epic is not a resolution.

The earlier draft also justified the decision with `MAX_BODY_BYTES`, which bounds
HTTP *requests* and not store reads. That was simply wrong and is gone.

## What the plan got wrong

**The plan said five `serve` call sites. There are six.** `_board()` projects
every row of `/api/work` through `_json_bytes`, and the plan's list — inherited
from the epic's spec — missed it.

That mattered more than a miscount, because the board was the one site with a
real argument for staying behind: projecting it costs an `artifacts()` call per
row, for data the web client does not render. Leaving it out and narrowing
criterion 8 to "the endpoints that matter" was available and would have looked
reasonable. It is also exactly the shape of carve-out this initiative keeps
getting burned by, so the board moved too. The cost is one `stat` sweep per row,
which `tcw work list` has always paid (`work/cli.py:331`).

**`update_work` takes `blockers`, not `blocked_by`.** A test written from the
field name failed immediately; the store's keyword is the older one.

## A test that was written, run, and then deleted

The first version of `test_serve_projection.py` contained
`test_the_board_still_qualifies_a_descendant_slug`, which built no descendant
node and therefore asserted that a bare slug equals itself. It passed. Given
this initiative's history, a green test that checks nothing is worse than no test,
so it was removed and replaced with a comment pointing at
`test_serve_descendants.py::test_board_flag_on_qualifies_descendant`, which
builds a real two-node tree and passed unmodified through the change.

`test_the_helper_finds_an_unmigrated_payload` exists for the same reason in the
opposite direction: criterion 8's walker identifies work items by
`slug`+`title`+`status` rather than by `schema`, because keying on `schema` would
have found only the payloads that were already migrated. The guard has its own
guard.

## Verified by hand

- **`tcw work show --json` on this repository's own items**, including the epic
  and an intake-only item. The `artifacts` map matches the board's letters.
- **The four `show` baselines**, captured from the CLI at `c2fe1fc` before
  `_show` was touched, reproduce byte-for-byte from the changed binary. That is
  the one check in this item the implementer could not have written to agree with
  the implementation.
- **`tcw validate`, `tcw capabilities check`, `tcw capabilities drift`** all
  clean.

## Notes

- The projection is pure and takes a `Sequence`, not an `Iterable`: a caller
  passing a spent generator would have got an all-absent artifact map and no
  error.
- `worktree` and `branch` are filesystem-flavored fields, and criterion 3 forces
  them into the published contract. They are declared rather than filtered —
  `serve` already ships them, and a filter would be a second contract to keep in
  sync with the first.
- Carrying `schema` on every board row is two extra keys per item on a local
  tool. Noted as a judgment rather than a measurement.
