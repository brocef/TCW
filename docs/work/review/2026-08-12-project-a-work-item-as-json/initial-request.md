# Project a work item as JSON

Child **C2** of the initiative
[`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`][epic]. The
initiative's spec is the source of truth for the design; this request states what
C2 in particular is being asked for and why it comes second.

## Product changes

A work item can be read as a machine-readable document: `tcw work show <ref>
--json` emits the item as JSON on stdout, with an explicit `schema` version, each
field at a documented JSON type, and a map of which lifecycle artifacts are
present.

That is useful on its own — piping a work item into `jq` is something the CLI
cannot do today — but it is not why it is being built now. It is the payload the
rest of the initiative hands to code a node owns: a `generate` hook receives this
document on stdin and decides what a stage's instructions should say. A hook
author writes against a version they can check, not against whatever shape the
dataclass happened to have on the day they wrote it.

## Technical changes

**One projection, not two.** `tcw/serve/__init__.py` already ships a projection —
`_jsonable`/`_json_bytes`, an `asdict()` dump finished with
`json.dumps(…, default=str)` — and the web API serves it today. Adding a second
one for the CLI would create exactly the two-sources drift this initiative exists
to remove. C2 replaces the ad-hoc dump with a real DTO and moves `serve` onto it.

Two things that dump papers over have to be decided rather than inherited:

- **`WorkItem.capabilities` is an opaque `object`** filled from arbitrary YAML.
  It can hold values with no JSON equivalent; `default=str` currently stringifies
  them, lossily, in production. Keep that behavior or replace it — but state
  which and why.
- **`body` is unbounded.** It is the item's whole request document. Whether the
  projection carries it, truncates it, or omits it is a decision, not a default.

The `artifacts` map is built on the canonical presence rule C1 established, so
the JSON and the board cannot disagree about whether a document exists.

## Meta changes

**Blocked by C1**, and the reason is not sequencing convenience: the projection
has to describe the body surface C1 introduced — a body that resolves through
`initial-request.md` → `intake.md` → `""` — and the `intake` artifact. Publishing
a versioned DTO before that lands would mean versioning it twice, and the first
version would be wrong about the thing hook authors most need to read.

**The acceptance criterion is deliberately awkward.** Criterion 5 requires a test
that the emitted document *validates against the declared schema*, explicitly not
one that enumerates dataclass fields. Review flagged the latter as a test that
would pass for an unusable payload. This item has watched two of its siblings'
criteria pass while the property behind them was false; the criterion is written
this way on purpose.

`serve`'s existing API responses must not change shape except where C2 changes
them deliberately and says so.

[epic]: ../../active/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/initial-request.md
