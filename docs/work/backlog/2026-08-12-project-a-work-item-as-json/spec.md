# Spec — Project a work item as JSON

Child **C2**. The initiative's `spec.md` decides the boundaries; this decides how
C2 is built. Where the two disagree the initiative wins, and the disagreement is
a defect in this document.

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
value anywhere in the tree, and the caller never learns it happened.

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

## Design

### Where it lives

A new module, `tcw/work/projection.py`, holding three things and no I/O:

```python
SCHEMA_VERSION = 1
WORK_ITEM_SCHEMA: dict          # a JSON Schema document
def work_item_json(item: WorkItem, artifacts: Iterable[Artifact]) -> dict
```

It imports `WorkItem` and `Artifact` and nothing else from the tree. It never
touches a store, a path, or a file — the caller has already resolved the item and
the artifact list, both through abstract store methods. The litmus test is not a
close call here: every field is a `WorkItem` field, `artifacts()` is an existing
abstract primitive, and no folder name appears anywhere.

`work_item_json` takes the artifacts rather than fetching them, for two reasons:
it keeps the function pure and therefore testable without a store, and `serve`'s
detail handler has already called `artifacts()` by the time it projects the item,
so fetching again would be a second round-trip for the same answer.

### The document

```json
{
  "schema": 1,
  "slug": "...", "title": "...", "status": "backlog",
  "created": "", "modified": "", "resolution": null,
  "priority": null, "effort": "", "complexity": "",
  "tags": [], "body": "",
  "blocked_by": [{"slug": "..."}],
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
without declaring it fails too. A schema that only listed types would let both
through.

`artifacts` is a name→boolean map over `WORK_ARTIFACTS`, built from the presence
values C1's canonical resolver produces. Its schema pins the key set the same
way, so an artifact added to the registry without appearing here fails the test.

### The two decisions the initiative's spec demanded

**`capabilities` is normalized, eagerly and recursively, rather than left to
`default=str`.** `WorkItem.capabilities` is typed `object` and filled from
arbitrary YAML, so it can hold a `date`, a `set`, a tuple key — anything the YAML
loader produces. The projection walks it:

- `None`, `bool`, `int`, `float`, `str` pass through.
- A mapping becomes an object with `str()`-ed keys, values walked.
- A list, tuple, or set becomes an array, values walked. A set is sorted by its
  rendered form first, because JSON has no set and an arbitrary order would make
  the projection non-deterministic for the same input.
- Anything else becomes `str(value)`.
- A `float` that is `NaN` or an infinity becomes `str(value)` too — `json.dumps`
  emits bare `NaN` and `Infinity` for those, which is not valid JSON and is
  exactly the kind of silent invalidity this item exists to remove.

The observable result for ordinary configurations is what `default=str` produced,
which is deliberate: this is not the item that changes what people's capability
blobs look like. What changes is *where* the coercion happens. Doing it in the
projection means the CLI and `serve` cannot disagree, the DTO is valid JSON
before it reaches any encoder, and the rule is written down in one function
instead of being an argument to `json.dumps` in one file.

**`body` is carried in full.** The initiative's spec says "bounded or excluded",
and this spec chooses neither, so it owes a reason.

Excluding it is not available: `serve`'s core editor reads `item.body` to seed
its draft, and C1 spent a whole rework round on the consequences of that editor
being seeded from the wrong place. Truncating it is worse than excluding it —
a body silently cut to 8 KiB and then saved back through the editor is data loss
that looks like a successful save, which is the same defect class again.

The size concern is real but it belongs at a different boundary. `serve` already
ships the full body over HTTP today and is bounded by `MAX_BODY_BYTES` on the way
in. When C3 pipes this document into a `generate` hook, *that* is where a cap
earns its keep, and C3 owns it. Adding a `body=False` knob here for a caller that
does not exist yet would be a parameter with one value.

### Moving `serve`

Five call sites project a work item: `serve/__init__.py:632`, `:789`, `:820`,
`:843`, `:994`. They move to `work_item_json`. The taxonomy and capability call
sites do not move, and `_jsonable`/`_json_bytes` stay for them.

The resulting payload is a **superset** of today's: same field names, same
values, plus `schema` and `artifacts`. The web client reads named fields, so it
is unaffected — and this is asserted rather than assumed, by a test that pins the
key set of the item payload.

One redundancy is accepted knowingly: `/api/work/<slug>` already returns a
top-level `artifacts` list carrying name, presence, revision, and media type,
and the item now carries a presence-only map of the same names. They are not in
conflict — the list is the editing view and the map is the contract's view — but
a reader will see both. The alternative is a projection whose shape depends on
its caller, which is worse.

### `tcw work show --json`

`--json` on the existing `show` subcommand. With it, stdout is
`json.dumps(dto, indent=2, sort_keys=True)` and nothing else; without it, output
is byte-identical to today.

**No `default=` argument.** The DTO is JSON-native by construction, so if
`json.dumps` raises, something is wrong and the command should say so rather than
stringify its way past it. That is the whole difference between this and the
projection it replaces.

Errors keep the current behavior: an unresolvable ref, an ambiguous slug, or a
missing item goes to stderr and exits 1, with no JSON on stdout — a consumer
piping to `jq` gets empty input and a non-zero status rather than a fragment.

## Acceptance criteria

The initiative's criterion 5 is the requirement; these are how it is checked.

1. `tcw work show <ref> --json` emits a document whose `schema` equals
   `SCHEMA_VERSION`, and which **validates against `WORK_ITEM_SCHEMA`** under a
   real JSON Schema validator. Not a field enumeration — the test constructs the
   document the CLI actually prints and validates it.
2. `WORK_ITEM_SCHEMA` declares every property required and forbids additional
   ones, asserted directly, so criterion 1 fails on both a dropped field and an
   undeclared one.
3. The `artifacts` map's key set equals `WORK_ARTIFACTS` exactly, and its values
   agree with `store.artifacts()` for the same item — checked on an item with
   some artifacts present and some absent, not only on an empty one.
4. An item whose `capabilities` blob holds a value with no JSON equivalent — at
   minimum a `date`, a set, and a non-string mapping key, since those are what
   YAML actually produces — emits valid JSON, and `json.dumps` is called with no
   `default=`. A `NaN` float does not produce bare `NaN` in the output.
5. `tcw work show <ref>` without `--json` produces byte-identical output to
   before this change.
6. `serve`'s `/api/work/<slug>` item payload contains every key it contained
   before, plus exactly `schema` and `artifacts`. Pinned as set equality against
   a literal key list, so a later field rename fails here rather than in the
   browser.
7. Errors print nothing on stdout under `--json` and exit non-zero.

## Risks

- **The schema becomes a maintenance tax.** Every new `WorkItem` field must be
  declared or the tests fail. That is the intended cost — it is what makes the
  document a contract — but it will read as friction to whoever adds field
  number twenty. The failure message should say what to do.
- **`serve`'s payload grows.** Two keys per item, on every list and detail
  response. Immaterial for a local tool; noted because "immaterial" is a judgment
  and not a measurement.
- **One version means no migration story.** If the shape has to change
  incompatibly later, `SCHEMA_VERSION` goes to 2 and consumers break loudly.
  Supporting both at once is not built, and should not be until something needs
  it.
