# Spec — Project a work item as JSON

Child **C2**. The initiative's `spec.md` decides the boundaries; this decides how
C2 is built. Where the two disagree the initiative wins, and the disagreement is
a defect in this document — except in one place, where the initiative's spec is
amended instead and says so (`body`, below).

> Revised after adversarial review by `codex` and `bllm-review`. Every claimed
> edge case was reproduced against PyYAML before being accepted; two findings
> were rejected with reasons. See `## Review corrections`.

## Problem

Two things are true at once and they pull in opposite directions.

**A projection already exists.** `tcw/serve/__init__.py:51-66` ships
`_jsonable`/`_json_bytes`: an `asdict()` dump, patched for three attributes that
are properties rather than fields, finished with `json.dumps(…, default=str)`.
The web API has served it since `serve` shipped, and the web client reads it.

**It is not a contract.** It has no version, so nothing downstream can detect a
change. Its field types are whatever the dataclass happened to hold. Its answer
to a value JSON cannot represent is `default=str`, which is not a decision so
much as the absence of one — it fires at `json.dumps` time, silently, for any
value anywhere in the tree, and the caller never learns it happened. It does not
even fully work: `default=` is never consulted for a `float`, so a `NaN` in a
capabilities blob emits bare `NaN` today, which is not valid JSON.

C3's `generate` hooks are about to make that payload a public interface: a node
writes a script, TCW pipes an item into it, and the script decides what a stage's
instructions say. A script author needs a version to check and types to rely on.

Building a second projection for the CLI would be the cheap way to get there, and
it is the specific thing the initiative exists to prevent.

## Goals

1. One work-item projection, consumed by `tcw work show --json`, by `serve`, and
   (in C3) by `generate` hooks.
2. It is versioned and its fields are declared, so a consumer can check both.
3. It is JSON-native **by construction** — `json.dumps` on it needs no `default=`
   escape hatch, because nothing that cannot be represented ever reaches it.
4. `serve`'s current responses keep working for the client that reads them today.

## Non-goals

- Changing the taxonomy or capability projections. `_jsonable` stays for those;
  only the work-item call sites move. Unifying those too is a different item with
  a different blast radius.
- A schema registry, content negotiation, or more than one live schema version.
  There is one version and it is an integer that goes up.
- Deciding what `generate` hooks receive. That is C3's contract; C2 supplies the
  document it will carry.
- Repairing a hand-mangled `state.yaml`. The projection must not *crash* on one,
  but TCW writes these files and the rest of the codebase already assumes the
  shapes it writes.

## Design

### Where it lives

A new module, `tcw/work/projection.py`, holding three things and no I/O:

```python
SCHEMA_VERSION = 1
WORK_ITEM_SCHEMA: dict          # a JSON Schema document
def work_item_json(item: WorkItem, artifacts: Sequence[Artifact]) -> dict
```

It imports `WorkItem`, `Artifact`, and `WORK_ARTIFACTS`, and nothing else from
the tree. It never touches a store, a path, or a file — the caller has already
resolved the item and the artifact list, both through abstract store methods. The
litmus test is not a close call here: every field is a `WorkItem` field,
`artifacts()` is an existing abstract primitive, and no folder name appears
anywhere.

`work_item_json` takes the artifacts rather than fetching them, for two reasons:
it keeps the function pure and therefore testable without a store, and `serve`'s
detail handler has already called `artifacts()` by the time it projects the item,
so fetching again would be a second round-trip for the same answer. The parameter
is a `Sequence`, not an `Iterable` — a caller passing a spent generator would get
an all-absent artifact map and no error, and that is not a failure mode worth
having.

### The document

```json
{
  "schema": 1,
  "slug": "...", "title": "...", "status": "backlog",
  "created": "", "modified": "", "resolution": null,
  "priority": null, "effort": "", "complexity": "",
  "tags": [], "body": "",
  "blocked_by": [{"slug": "..."}, {"external": "..."}],
  "capabilities": null,
  "initiative": "", "type": "", "worktree": "", "branch": "",
  "parent": "", "owner": "", "started": "",
  "artifacts": {"initial-request": true, "spec": false, "...": false}
}
```

Every `WorkItem` field appears under its own name, at the JSON type
`WORK_ITEM_SCHEMA` declares. Two keys are added: `schema` and `artifacts`.

**The schema is the source, not a description of one.** `WORK_ITEM_SCHEMA` is a
real JSON Schema document with `"additionalProperties": false` and every property
required. That last part is what makes it load-bearing: a field dropped from the
projection fails validation instead of quietly disappearing, and a field added
without declaring it fails too.

**But a closed schema is not enough on its own,** and this is the trap review
found. Criteria that say "the emitted document validates against the schema" and
"the schema is closed and fully required" can *both* pass while the projection
and the schema agree on an incomplete contract — drop `started` from both and
nothing fails. So a third criterion ties the schema to the model: the schema's
property set must equal `WorkItem`'s dataclass field names plus exactly `schema`
and `artifacts`. A field added to `WorkItem` and forgotten here then fails a
test, which is the only place that fact can be checked from.

`artifacts` is a name→boolean map over `WORK_ARTIFACTS`, built from the presence
values C1's canonical resolver produces. Its schema pins the key set the same
way, so an artifact added to the registry without appearing here fails too.

`blocked_by` entries are declared as an object with optional `slug` and optional
`external`, both strings, no additional properties, at least one present. That is
exactly what `_entry_for` (`base.py:1240`) writes, and what `cli.py:132` and
`recursion.py:86` already read.

### JSON-safety: one walker, and what it does with each shape

`WorkItem.capabilities` is typed `object` and filled from arbitrary YAML
(`fs.py:2460`), so it can hold anything the loader produces. `blocked_by` is read
straight from `state.yaml` (`fs.py:2479`) and has the same exposure. Both go
through one normalizer, and every rule below was reproduced against
`yaml.safe_load` rather than assumed:

- `None`, `bool`, `int`, `str` pass through.
- A `float` passes through **unless** it is `NaN` or an infinity, which become
  `str(value)`. `json.dumps` does not consult `default=` for floats, so this is
  the only place it can be caught.
- `bytes` — what `!!binary` produces — becomes a **base64 string**. `str()` on it
  would emit `"b'hi'"`, which is a Python repr masquerading as data.
- A mapping becomes an object with `str()`-ed keys. **A collision raises.** YAML
  can produce `{1: "a", "1": "b"}`, and stringifying both to `"1"` silently
  deletes one value. Refusing names the key; dropping a value quietly is the
  defect class this initiative keeps paying for.
- A list or tuple becomes an array. A `set` — what `!!set` produces — becomes an
  array sorted with `key=str`, because JSON has no set and an unordered dump
  would make the projection non-deterministic for identical input.
- Anything else becomes `str(value)`. `datetime.date` and `datetime.datetime`,
  which a bare `2026-01-01` in YAML produces, land here and render ISO-8601.
- **Cycles are detected.** `yaml.safe_load("a: &x\n  b: *x\n")` produces a
  self-referential dict; a naive recursive walker raises `RecursionError` and
  `json.dumps` raises `ValueError: Circular reference detected`. The walker
  tracks the `id()` of each container it is inside and renders a repeat as the
  string `"<circular reference>"`. It is not silent — it appears in the output —
  and it cannot hang.

The encoder is called as `json.dumps(dto, allow_nan=False)` with **no
`default=`**. The walker should make both redundant; they are there so that if it
ever does not, the command fails loudly instead of emitting invalid JSON. A
guard that never fires is the point of a guard.

For ordinary capability blobs — `{new: [...], changed: [...]}`, which is what
this field actually holds — the output is what `default=str` produced. What
changes is *where* the coercion happens: in one function, shared by the CLI and
`serve`, before anything reaches an encoder.

### `body` — amending the initiative's spec rather than disregarding it

The initiative's spec says `body` is "bounded or excluded for the same reason —
it can be arbitrarily large" (epic `spec.md:400`). C2 carries it in full, which
is a conflict, and a child quietly overruling its epic is not a resolution. **The
epic's spec is amended in the same commit as this one**, with the reasoning
recorded there.

The reasoning: excluding it is not available, because `serve`'s core editor reads
`item.body` to seed its draft (`app.tsx:403`) and C1 spent an entire rework round
on the consequences of that editor being seeded from the wrong place. Truncating
is worse than excluding — a body silently cut and then saved back through the
editor is data loss that presents as a successful save, which is the same defect
class again.

The size concern is real and it belongs at a different boundary. Review correctly
noted that `MAX_BODY_BYTES` bounds HTTP *requests*, not bodies read out of a
store, so it does not bound this document — the earlier draft of this spec cited
it as if it did. When C3 pipes this document into a `generate` hook's stdin,
*that* is where a cap earns its keep, and the amendment assigns it to C3
explicitly rather than leaving it implied.

### Moving `serve`

Five call sites project a work item: `serve/__init__.py:632`, `:789`, `:820`,
`:843`, `:994`. They move to `work_item_json`. The taxonomy and capability call
sites do not move, and `_jsonable`/`_json_bytes` stay for them.

The resulting payload is a **superset** of today's: same field names, same
values, plus `schema` and `artifacts`. The web client declares `WorkItem` as
extending `Record<string, unknown>` (`types.ts:13`) and reads named fields, so it
tolerates the additions — but structural tolerance is not behavioral
compatibility, and the check for that is running the existing web unit and
end-to-end suites against the new payload, not a type declaration.

One redundancy is accepted knowingly: `/api/work/<slug>` already returns a
top-level `artifacts` list carrying name, presence, revision, and media type,
and the item now carries a presence-only map of the same names. They are not in
conflict — the list is the editing view and the map is the contract's view — but
a reader will see both. The alternative is a projection whose shape depends on
its caller, which is worse.

### `tcw work show --json`

`--json` on the existing `show` subcommand. With it, stdout is
`json.dumps(dto, indent=2, sort_keys=True, allow_nan=False)` and nothing else;
without it, output is byte-identical to today.

Errors keep the current behavior: an unresolvable ref, an ambiguous slug, or a
missing item goes to stderr and exits 1, with **nothing** on stdout — a consumer
piping to `jq` gets empty input and a non-zero status rather than a fragment.
A projection or encoding failure is handled the same way: caught at the CLI
boundary, reported to stderr naming the item, exit 1, no partial JSON.

## Acceptance criteria

The initiative's criterion 5 is the requirement; these are how it is checked.
Each was written by asking what implementation could satisfy it while the
property behind it was false.

1. `tcw work show <ref> --json` emits a document whose `schema` equals
   `SCHEMA_VERSION`, and which **validates against `WORK_ITEM_SCHEMA`** under a
   real JSON Schema validator. The test validates the bytes the CLI actually
   printed, parsed back — not a dict built beside it.
2. `WORK_ITEM_SCHEMA` declares every property required and forbids additional
   ones, asserted directly.
3. **The schema's property set equals `{f.name for f in fields(WorkItem)} | {"schema", "artifacts"}`,
   asserted as set equality.** This is what stops criteria 1 and 2 from agreeing
   with each other about an incomplete contract: adding a field to `WorkItem`
   without declaring it here fails, and so does declaring one that does not
   exist. The failure message names the offending fields and what to do.
4. The `artifacts` map's key set equals `WORK_ARTIFACTS` exactly, and its values
   agree with `store.artifacts()` for the same item — checked on an item with
   some artifacts present and some absent, not only on an empty one.
5. A `capabilities` blob holding each shape YAML actually produces emits valid
   JSON, enumerated rather than sampled: `datetime.date`, `datetime.datetime`,
   `bytes` (base64, asserted as the decoded value rather than as "some string"),
   `set` (array, and the same input twice gives the same order), `NaN`, `+inf`,
   `-inf`, and a self-referential structure built through a YAML anchor. Each is
   built by round-tripping real YAML through `yaml.safe_load`, so the test cannot
   drift from what the loader does.
6. A `capabilities` mapping with keys that collide when stringified — `{1: "a",
   "1": "b"}` — **raises**, the message names the colliding key, and
   `tcw work show --json` exits non-zero with nothing on stdout. Asserting the
   raise is the point: an implementation that keeps one value and drops the other
   passes any test that only checks the output is valid JSON.
7. `tcw work show <ref>` without `--json` produces byte-identical output to
   before this change, checked against **baselines captured from the CLI before
   `_show` is touched** and committed as fixture data in their own commit, so the
   expected bytes cannot be edited into agreement with a regression. Covers an
   item with a request, an intake-only item, an item with neither, and one with
   blockers, an owner, and tags.
8. Every work-item payload `serve` emits carries `schema` — asserted over
   `/api/work` (the list) as well as `/api/work/<slug>` (the detail) and the
   PATCH and POST responses, by walking the response for item objects rather than
   by checking the endpoints someone remembered. A call site left on `_jsonable`
   fails here.
9. `/api/work/<slug>`'s item payload contains every key it contained before, plus
   exactly `schema` and `artifacts`, pinned as set equality against a literal key
   list.
10. The web unit and end-to-end suites pass unmodified against the new payload.
11. Under `--json`, every error path prints nothing on stdout and exits non-zero:
    an unknown slug, an ambiguous slug, a ref outside the store, and a projection
    failure. Enumerated, because testing one error class would let another print
    a diagnostic to stdout.

## Risks

- **The schema becomes a maintenance tax.** Every new `WorkItem` field must be
  declared or criterion 3 fails. That is the intended cost — it is what makes the
  document a contract — but it will read as friction to whoever adds field
  number twenty, so the assertion's failure message has to say what to do rather
  than just print two sets.
- **Refusing on a key collision turns a weird config into a hard failure**, in
  `serve` as well as the CLI, where it will surface as a 500 on one item's page.
  Accepted: the alternative is losing a value silently. The message names the
  key, which is what makes the failure actionable rather than mysterious.
- **`set` rendering changes.** `default=str` produced `"{1, 2}"`; the walker
  produces `[1, 2]`. Anything parsing the old string breaks. `!!set` in a
  capabilities blob is close to hypothetical, so no migration is built — but it
  goes in the changelog rather than being discovered.
- **One version means no migration story.** If the shape has to change
  incompatibly later, `SCHEMA_VERSION` goes to 2 and consumers break loudly.
  Supporting both at once is not built, and should not be until something needs
  it.
- **`jsonschema` becomes a test dependency.** It is added to the `dev` extra, not
  to runtime `dependencies`; nothing TCW ships imports it. Writing a validator by
  hand instead would mean the test and the projection could share a bug.

## Review corrections

Findings from the `codex` and `bllm-review` passes. Each was reproduced before
being accepted; the two rejected ones are named with why.

**Accepted and folded in:**

- Criteria 1 and 2 could jointly validate a self-consistent but incomplete
  contract (codex 6) → criterion 3 ties the schema to `WorkItem`'s fields. This
  is the same fallacy that has cost this initiative three verify passes, found
  before implementation this time.
- `capabilities` normalization was incomplete (codex 4, bllm) → cycles, `bytes`,
  colliding stringified keys, `datetime`, and non-finite floats are each named
  and tested, all reproduced through `yaml.safe_load` first.
- `json.dumps` without `default=` is not strict (codex 4) → `allow_nan=False`.
  Verified: `json.dumps(float("nan"))` emits bare `NaN` today.
- `MAX_BODY_BYTES` bounds HTTP requests, not store reads (codex 3) → the earlier
  draft's justification cited it wrongly. The cap is assigned to C3 explicitly,
  and the epic's spec is amended rather than quietly overruled.
- `blocked_by`'s shape was undeclared (codex 5) → declared for both the `slug`
  and `external` forms.
- Criterion 5's "before" oracle was not independent (codex 7) → baselines are
  captured from the CLI and committed before `_show` is touched.
- Only one `serve` endpoint was covered (codex 6, bllm) → criterion 8 walks every
  work-item payload, and criterion 10 runs the web suites.
- Error paths were one word (codex 8, bllm) → criterion 11 enumerates them.
- `Iterable` artifacts (bllm) → `Sequence`.

**Rejected:**

- *Sorting a set by `str()` raises `TypeError` on mixed types* (bllm).
  `sorted({1, "a", 2.5}, key=str)` returns `[1, 2.5, "a"]`. The key is a string;
  the elements are never compared to each other.
- *`body` and `capabilities` in `--json` are a privacy exposure* (bllm).
  `tcw work show` prints the body today and `serve` ships it over HTTP. No new
  boundary is crossed, and a filtering step would be a feature nobody asked for
  in an item about serialization.
- *A configurable recursion depth limit* (bllm). Cycle detection is the real
  fix and is adopted; a depth limit protects against a legitimately deep
  document, which is not a failure mode anyone has.
