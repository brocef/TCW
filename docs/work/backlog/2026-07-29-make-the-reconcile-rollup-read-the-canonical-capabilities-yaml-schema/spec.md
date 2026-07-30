# Spec: make the reconcile rollup read the canonical capabilities.yaml schema

## Capability changes

None. Checked against the ledger rather than assumed: `tcw capabilities list`
carries an entry for the reconcile rollup, but its body describes *what the
rollup is for*, not the sidecar shape it parses. No capability gains, loses, or
changes status — this is a defect in how an existing capability behaves, not a
change in what a user can do. No `capabilities.yaml` sidecar for this item.

## Problem

Two readers, two schemas, one file.

- `capability_gate` (`tcw/work/recursion.py:37`) calls
  `declared_capabilities(item.capabilities)` (`tcw/store/base.py:97`), which
  reads the canonical mapping — `new:` / `changed:` lists of `namespace/path`
  strings, with `added:` accepted as a deprecated alias of `new:`.
- `_capability_deltas` (`tcw/work/recursion.py:89`), which builds the
  **Capability deltas** section of the reconcile rollup
  (`tcw/work/recursion.py:135-137`), instead tests `isinstance(caps, list)` over
  entries shaped `{file, heading, from, to}` and falls through to
  `elif caps:` → `"capabilities.yaml present but not a list — skipped"` for
  everything else.

So a sidecar authored in the schema the `tcw-capabilities` skill documents as
canonical — and which `tcw capabilities check` and the `complete` gate both
accept — is reported by the rollup as malformed. Following the documentation is
what triggers the warning.

The damage is bounded but real: `complete` still gates correctly, so nothing
breaks. The cost is that the message asserts a defect in a file that has none,
which sends the reader looking for it. The reporter records that it cost a detour
through the tcw source to establish that closeout would not fail.

`{file, heading, from, to}` is the older *reconcile display* shape.
`tests/test_capabilities_sidecar.py:43-44` pins the distinction deliberately —
"reconcile's `{file, heading, from, to}` list shape is not a gate declaration" —
so the two schemas are known to coexist; only the rollup's blindness to the
canonical one is the bug.

## Goals

- The rollup renders the canonical `new:` / `changed:` paths.
- The rollup and the gate share one reader of the sidecar schema, so they cannot
  disagree again.
- No sidecar that the gate accepts is ever described by the rollup as malformed.
- The rollup keeps degrading rather than crashing on genuinely unreadable input —
  it is a read-only reporting surface invoked during `reconcile`.

## Non-goals

- **Changing the gate.** `capability_gate` is correct and untouched.
- **Changing the sidecar schema, or deprecating either shape.** This item makes
  the rollup read what already exists.
- **Fixing `tcw capabilities check` or `complete`.** Both already behave.
- **Rendering capability *status* in the rollup.** The gate resolves each path
  against `FsCapabilitiesStore` to check status; the rollup will render the
  declared paths as declared, without resolving them. Resolution is a
  per-child-node store open inside a display loop, and the rollup is not the
  place to discover that a path is broken — the gate already fails closed on it.

## Design

### One reader, with the legacy shape as an explicit fallback

`_capability_deltas` gains a three-way read per task, in this order:

1. **Canonical mapping** — `declared_capabilities(item.capabilities)`. When it
   yields any `new:` or `changed:` entries, render one line per path:

    ```
    - <rel>/<slug>: new capability/path
    - <rel>/<slug>: changed capability/path
    ```

2. **Legacy list** — `isinstance(caps, list)`, rendered exactly as today
   (`{file}#{heading} {from} → {to}`). Unchanged, so the existing rollup output
   for that shape is byte-identical.

3. **Neither** — a truthy `capabilities` that is neither a recognized mapping nor
   a list gets a note, as today. The wording changes: `"present but not a list"`
   is now false as a diagnosis, since a mapping is the *expected* shape. It
   becomes `"capabilities.yaml has no new:/changed: entries — skipped"`.

### Failing soft on an unreadable sidecar

`declared_capabilities` raises `SidecarError` in two cases the current
`isinstance` check cannot reach: the `_tcw_parse_error` sentinel the FS adapter
produces on bad YAML, and a `new:`/`changed:` key whose value is not a list
(`tcw/store/base.py:114-121`). The gate *wants* that to raise — it fails closed.
The rollup must not: `reconcile` renders a status block across a whole epic, and
one child node's broken sidecar must not take the rollup down with it.

So the call is wrapped, and the error becomes a rendered line:
`"capabilities.yaml is unreadable: <e> — skipped"`. This mirrors
`capability_gate`'s own wording at `tcw/work/recursion.py:38-39` while producing
a display row instead of a gate failure.

### Why the legacy branch stays

The request asks whether the legacy shape still has a live producer, and the
answer here is **no**: of the 39 `capabilities.yaml` sidecars in this repo, zero
begin with a list; the only producer is `tests/test_recursion.py:248`.

It stays anyway, and the reason is specific to this function rather than general
caution. `_capability_deltas` is fed by `_tasks_for`
(`tcw/work/recursion.py:70-81`), which walks `child_nodes(node_root)` and reads
items out of **other nodes** — separate repositories this repo cannot inspect.
"No producer in this checkout" is therefore not evidence of "no producer". The
branch is five lines, already written, already tested, and removing it would
convert a graceful render into a `skipped` note for anyone who does still have
one. Ponytail's rule against dead flexibility does not apply to a code path whose
inputs live outside the repository.

## Acceptance criteria

1. A task whose `capabilities.yaml` is
   `new:\n  - a/b\nchanged:\n  - c/d\n` produces rollup lines naming both `a/b`
   and `c/d`, and the block contains no `skipped` note for that task.
2. `added:` is honored as an alias of `new:` in the rollup, matching
   `declared_capabilities` — a sidecar using `added:` renders as new.
3. A task whose `capabilities.yaml` is the legacy list
   `- file: routes/login\n  heading: sso\n  from: Missing\n  to: Supported\n`
   renders exactly as before (`routes/login#sso Missing → Supported`).
   `tests/test_recursion.py::test_reconcile_surfaces_capability_deltas` passes
   unmodified.
4. A task whose `capabilities.yaml` is a mapping with neither `new:` nor
   `changed:` still yields a `skipped` note, so
   `tests/test_recursion.py::test_reconcile_tolerates_malformed_capabilities`
   passes unmodified — but the note no longer claims the file is "not a list".
5. A task whose `capabilities.yaml` is unparseable YAML yields a `skipped` note
   naming it unreadable, and `reconcile` returns a block rather than raising.
6. `_capability_deltas` contains no second implementation of the sidecar mapping
   schema: `declared_capabilities` is the only thing that reads `new:`/`changed:`.
7. `python -m pytest -q` green.
8. `docs/changelogs/upcoming.md` carries a `Fixed` entry. No
   `docs/release-notes/upcoming.md` entry is required by the trigger, but one is
   warranted here — the false "malformed" message is user-visible, so the
   release note says the rollup now lists declared capabilities correctly.

## Risks

- **The rollup's output for canonical sidecars is new text**, so any consumer
  parsing the **Capability deltas** block sees rows it has not seen before. Low:
  the block is prose inside a `<!-- tcw:rollup -->` marker
  (`tcw/work/recursion.py:21`) meant for human reading, and it previously emitted
  only a `skipped` note for these sidecars — there is nothing to have parsed.
- **`SidecarError` is now swallowed in one more place.** Mitigated by scope: only
  inside the display function, and `capability_gate` — the enforcement path — is
  untouched, so a broken sidecar still fails `complete` closed.
- **Two schemas remain readable**, which is the state this item found and does not
  resolve. Deliberate: unifying them is a migration with cross-node blast radius,
  and the reported defect does not require it.

## Notes

Grounding for the "no live producer" claim: `find docs -name capabilities.yaml`
returns 39 files; none has a first line beginning `-`. The legacy shape appears
only in `tests/test_recursion.py:248` and, as a documented negative, in
`tests/test_capabilities_sidecar.py:43-44`.

The issue (#8) is one of four in this batch whose closeout is deferred until the
containing version is cut and pushed, per the user's sequencing decision on
2026-07-30. Nothing is posted to the issue at completion time.
