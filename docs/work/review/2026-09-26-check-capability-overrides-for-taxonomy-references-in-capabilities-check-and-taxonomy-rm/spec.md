# Spec — Check capability overrides for taxonomy references in capabilities check and taxonomy rm

## Capability changes

None. `tcw capabilities check` and `tcw taxonomy rm` exist; this makes them see
references an override sets.

## Reproduction

Scratch script `repro3.py` (session scratchpad), against `bug-run` at
`daaf5850`: a `base` node with capability `cap-aaa111`; a `child` node with
taxonomy and capabilities that extends `base`, holds local term `zed`, and an
override folder `ov` with `overrides: cap-aaa111`, `Subject: [zed]`,
`Feature: nope`.

- The composed capability reads `Subject: ['zed']`, `Feature: nope`.
- `FsCapabilitiesStore.open(child).check()` → `[]`. Should report
  `ov: Feature → dangling ref 'nope'`.
- `FsTaxonomyStore.open(child).remove("zed")` removes the term. Should refuse,
  naming the override.

## Problem

- `check` (`tcw/store/fs.py:3227`) validates field references only for
  `list_all(local_only=True)` (fs.py:3273), and `_local_paths` (fs.py:2774)
  excludes every folder with `overrides:`. Its second loop over every meta
  folder (fs.py:3305–3323) checks an override's attachments and target, never
  its fields.
- `FsTaxonomyStore._capability_referrers` (fs.py:2411) reads the same
  `list_all(local_only=True)` (fs.py:2424).
- Overrides merge onto the inherited capability in `_apply_override`
  (fs.py:2823): every key outside `_CAP_STRUCTURAL` (fs.py:2699) replaces the
  inherited value, and `null` clears it.

**Sibling sweep, repo-wide** (`grep -n "_ref_problems(\|_term_refs(\|list_all(local_only=True)" tcw/`):

- The write path (`set` → `_validate_fields` → `_ref_problems`, fs.py:3094)
  validates the references a write supplies, override writes included — no gap.
- `check` skips **every** reference an override sets, not only `Subject` and
  `Feature`: `Superseded by`, `Blocked by`, `Roles` and `When` go through the
  same `_ref_problems` renderer for local capabilities and are equally unchecked
  in an override. Same defect, same fix — included.
- `tcw/capabilities/cli.py:216` (the shipped-but-Missing report) reads
  `Status`/`Planning doc`, not references — out of scope.

## Goals

1. `check` reports every reference problem in the fields an override sets —
   the same `_ref_problems` a local capability gets — prefixed with the override
   folder's path.
2. `taxonomy rm` refuses to remove a local term an override's `Subject` or
   `Feature` names, naming the override.

## Non-goals

- Validating an override's field *values* (unknown field, invalid `Status`,
  `Partial` without `Gaps`). Those are checked on the composed capability's
  write; a hand-edited override that breaks them is a different question
  (whether the check runs on the composed view) and not a reference problem.
- Checking the references of an inherited capability's *unoverridden* fields —
  those belong to the upstream ledger's own `check`.

## Design

- `FsCapabilitiesStore._override_fields() -> list[tuple[str, dict]]`: for every
  meta folder with `overrides:`, `(path, fields)` where `fields` is the meta
  minus `_CAP_STRUCTURAL` keys and minus `null` values (a clear sets no
  reference). One definition, read by both callers.
- `check`: in the existing loop over meta folders, for an override add
  `f"{p}: {problem}"` for each of `self._ref_problems(fields, taxonomy)`, and
  emit the "Subject and Feature not checked" note the same way the local loop
  does — for a whole-node check only. When `check(identifier)` selects one
  capability, its composed fields (override included) are already checked by
  the capability loop, so the override branch is skipped there; checking both
  reported each problem twice. *(Amended at review: the first draft said the
  override was reached through `selected.path`, but an inherited capability's
  path is upstream's, and when no local folder of that name exists the attachment
  loop crashed. That crash predates this change and is fixed with it: a
  selected path with no local folder is skipped.)*
- `_capability_referrers`: also walk `caps._override_fields()` through
  `_term_refs`, labelling a hit `capability override <path> (<field>)`.

## Abstraction litmus test

No new store-interface operation. "An override's references are references"
is a rule about the capabilities model that any store holding overrides would
apply; `_override_fields` is a private helper of the filesystem adapter.

## Acceptance criteria

1. With the reproduction's override, `check()` includes
   `ov: Feature → dangling ref 'nope'`, and with `Subject: [ghost]`,
   `ov: Subject → dangling ref 'ghost'`.
2. An override with `Blocked by: missing-cap` reports
   `ov: Blocked by → dangling identifier 'missing-cap'`.
3. An override that sets `Subject: null` (clearing it) reports nothing for
   Subject.
4. `FsTaxonomyStore.remove("zed")` with an override naming `zed` in `Subject`
   (and, separately, in `Feature` on a Feature-kind term) raises naming
   `capability override ov (Subject)` / `(Feature)`, and `zed` still lists.
   `tcw taxonomy rm zed` exits 1 with that text.
5. An override naming a different term does not block removing `zed`.
6. The full test suite passes.

## Risks

- A node whose overrides already carry broken references starts failing
  `tcw capabilities check` (and `tcw validate`, which runs it) after upgrading.
  That is the fix working; the release note says so.
