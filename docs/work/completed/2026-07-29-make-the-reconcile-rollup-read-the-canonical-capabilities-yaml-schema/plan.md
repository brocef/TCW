# Plan — Make the reconcile rollup read the canonical capabilities.yaml schema

Two code/test tasks and one documentation block. One function changes
(`_capability_deltas`); everything else is coverage and docs. No bounded stage
DAG — the whole change is under 20 lines.

Ordering: task 1 is the fix and is self-verifying against the two existing
`test_recursion.py` cases, which must keep passing **unmodified** (criteria 3 and
4) — that is what proves the legacy and degrade paths were not disturbed. Task 2
adds the coverage the new behavior needs. Docs last, per `stage-plan.md` step 4.

## Task 1 — rewrite `_capability_deltas`

**Changes:** `tcw/work/recursion.py`, `_capability_deltas` (`:89-103`) only.

Three-way read per task, in order:

1. `declared_capabilities(item.capabilities)` inside `try/except SidecarError`.
   On error, append `- {rel}/{slug}: capabilities.yaml is unreadable: {e} — skipped`
   and continue to the next task.
2. If the result has any `new:`/`changed:` entries, append one line per path:
   `- {rel}/{slug}: new {path}` / `- {rel}/{slug}: changed {path}`.
3. Else if `isinstance(caps, list)`, run today's legacy rendering **verbatim** —
   `{file}#{heading} {from} → {to}`.
4. Else if `caps` is truthy, append
   `- {rel}/{slug}: capabilities.yaml has no new:/changed: entries — skipped`.

Update the docstring: it currently says the function "Expects an optional
top-level list of `{file, heading, from, to}` mappings", which becomes the
secondary case. State that `declared_capabilities` is the single reader of the
canonical schema and that the legacy branch survives for child nodes in other
repositories (spec → "Why the legacy branch stays").

The word `skipped` must survive in both note branches — criterion 4 pins it via
an existing assertion.

**Verified by:** `python -m pytest tests/test_recursion.py -q` green with **no
edits to `test_reconcile_surfaces_capability_deltas` or
`test_reconcile_tolerates_malformed_capabilities`**. If either needs editing to
pass, the fix disturbed behavior it was not supposed to touch — treat that as a
failure, not as a test to update.

## Task 2 — cover the canonical, alias, and unreadable paths

**Changes:** `tests/test_recursion.py`, new cases beside the two existing ones
(`:243-260`), reusing the `mk_node` / `_child_task` helpers already there.

- `test_reconcile_surfaces_canonical_capability_deltas` — `_child_task` with
  `caps="new:\n  - a/b\nchanged:\n  - c/d\n"`; assert both `a/b` and `c/d` appear
  and that `skipped` does **not**. (Criterion 1.)
- `test_reconcile_honors_added_alias` — `caps="added:\n  - a/b\n"`; assert `a/b`
  renders as new. (Criterion 2.)
- `test_reconcile_tolerates_unreadable_capabilities` — `caps` set to YAML that
  trips the FS adapter's `_tcw_parse_error` sentinel (check how
  `tests/test_capabilities_sidecar.py` provokes it and reuse that input rather
  than inventing one); assert `reconcile` returns a block containing `skipped`
  and does not raise. (Criterion 5.)

**Verified by:** the three new cases pass; `python -m pytest -q` green overall.
Criterion 6 is checked by reading the finished function — no second
`new:`/`changed:` parse anywhere in `recursion.py`.

## Task 3 — documentation sync

Evaluated over the finished diff in one pass, per `stage-implement.md` step 6.
Predicted:

| Entry | Trigger | Expected |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fires** — `Fixed`: the reconcile rollup read an older list-only schema and reported canonical `new:`/`changed:` sidecars as malformed; it now shares `declared_capabilities` with the gate, with the legacy list kept as a fallback and unreadable sidecars degrading to a note instead of raising. |
| `docs/release-notes/upcoming.md` | `Public-API` | **fires** — the false "your file is malformed" message was user-visible and is the whole reason the issue was filed. Plain language: `tcw work reconcile` now lists the capabilities an item declares, instead of warning that a correctly-written file was skipped. (Criterion 8 asks for this even though the trigger reads as a borderline call — see Notes.) |
| `README.md` | `Public-API` | **does not fire** — no CLI surface change; README does not quote the rollup block. Confirm by grep before concluding. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **likely fires — check, do not assume.** The `tcw-capabilities` skill documents the canonical sidecar schema and the `tcw-work` skill documents `reconcile`. Neither's *contract* changes, but if either states or implies that the rollup does not understand the canonical shape, that sentence is now stale and must go. |

## Verification

Everything in the acceptance criteria is machine-checkable except criterion 6
(no second schema reader), which is a read of the finished function.

One manual check worth doing because the automated ones all use synthetic
fixtures: run `tcw work reconcile` against a real epic in this repo, if one with
child tasks exists, and eyeball the **Capability deltas** block. Record the
actual output in `outcome.md`. If no suitable epic exists, say so rather than
inventing one.

Full `python -m pytest -q` green before `submit`.

## Notes

No blockers to record. This item is independent of the other six in the batch.

On the release-note call: the `Public-API` trigger is written for API/schema
changes, and strictly this is a message-text fix. It is included anyway because
the message is the defect — a user was told their correct file was broken. If
implementation finds the note reads as noise next to the other entries, drop it
and say so in `outcome.md` rather than padding the release notes.

GitHub issue #8 is **not** closed at completion. Per the user's sequencing
decision on 2026-07-30, the four issue-backed items in this batch have their
issues answered only after the containing minor version is cut and pushed. The
Definition-of-Done entry for it is deferred deliberately, and `refined-outcome.md`
must say so.
