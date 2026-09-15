# Outcome — Make the reconcile rollup read the canonical capabilities.yaml schema

Shipped as planned. `_capability_deltas` now shares `declared_capabilities` with
`capability_gate`, so the rollup and the gate read one schema.

## What shipped

### Task 1 — rewrite `_capability_deltas` (`befc3d5`)

`fix(reconcile): read the canonical capabilities.yaml schema in the rollup`

`tcw/work/recursion.py`, `_capability_deltas` only. Four-way read per task, in
the plan's order:

1. `declared_capabilities(caps)` inside `try/except SidecarError`; on error,
   `- {rel}/{slug}: capabilities.yaml is unreadable: {e} — skipped`, continue.
2. Any `new:`/`changed:` entries → one line per path, `- {rel}/{slug}: {kind} {path}`.
3. Else `isinstance(caps, list)` → the legacy `{file}#{heading} {from} → {to}`
   rendering, character-for-character as before.
4. Else truthy → `- {rel}/{slug}: capabilities.yaml has no new:/changed: entries — skipped`.

Docstring rewritten to state that `declared_capabilities` is the only reader of
the canonical schema, why this function swallows `SidecarError` where the gate
does not, and why the legacy branch survives.

### Task 2 — coverage (`c4cf8d3`)

`test(reconcile): cover canonical, added-alias, and unreadable sidecar rollup paths`

Three cases added to `tests/test_recursion.py`:

- `test_reconcile_surfaces_canonical_capability_deltas` — `new:`/`changed:`
  sidecar renders both paths, no `skipped`.
- `test_reconcile_honors_added_alias` — `added:` renders as `new a/b`, inherited
  free from the shared reader.
- `test_reconcile_tolerates_unreadable_capabilities` — invalid YAML
  (`new:\n  - [unclosed`) yields `unreadable` + `skipped` and does not raise.

### Task 3 — documentation sync (`1cff54d`)

`docs: record the reconcile rollup schema fix`

| Entry | Trigger | Result |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fired** — new `## Fixed` entry covering the two-readers cause, the shared-reader fix, and all three follow-on changes |
| `docs/release-notes/upcoming.md` | `Public-API` | **fired** — "Epic summaries now list the capabilities an item declares", in plain language with sample output |
| `README.md` | `Public-API` | did not fire — no CLI surface change; grep confirms README never quotes the rollup block |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | did not fire — grep for `not a list` and `Capability deltas` across `README.md`, `skills/`, `commands/`, `docs/capabilities/` returns **nothing**, so no document claimed the stale behavior and none went stale |

All four plan predictions held, including the flagged "check, do not assume" on
the skills entry.

## Test result

```
$ python -m pytest tests/test_recursion.py -q
26 passed in 8.55s          # 23 before; the two pre-existing cases unmodified

$ python -m pytest -q
1130 passed in 156.43s (0:02:36)
```

**Criteria 3 and 4 were satisfied without editing a single assertion.**
`test_reconcile_surfaces_capability_deltas` (legacy list) and
`test_reconcile_tolerates_malformed_capabilities` (mapping with no recognized
keys) both pass untouched — the plan named editing them as a failure signal, and
neither needed it.

Criterion 6 checked by reading the finished function: `declared_capabilities` is
the only thing in `recursion.py` that parses `new:`/`changed:`.

## Manual verification against real data

The plan asked for a real-epic check. The repo has exactly one epic
(`2026-07-27-redefine-the-tcw-work-lifecycle-…`, completed) with 6 children, and
**none of the 6 carries a `capabilities.yaml`** — so reconciling it produces an
empty deltas block and demonstrates nothing. Rather than invent an epic, the real
code path was exercised read-only over the repo's actual sidecars (calling
`_capability_deltas` directly; `reconcile` itself was **not** run, as it writes a
rollup block into the epic's body and that epic is completed).

Result — 39 real items carry a canonical sidecar, and **every one of them** would
have been reported malformed by the old code:

```
NEW: - ./2026-06-21-list-hides-completed-items-by-default: changed work#view-the-board
OLD: - ./2026-06-21-list-hides-completed-items-by-default: capabilities.yaml present but not a list — skipped
```

39 of 39. The synthetic tests prove the branches; this proves the blast radius
was total — no sidecar in this repository ever rendered correctly.

## What the plan or spec got wrong

Nothing material; every task landed as written.

Two refinements worth recording:

1. **The spec's "no live producer" finding understated the case in one direction
   and overstated it in another.** It correctly found zero legacy-list sidecars
   among the 39. What it did not say is that all 39 are *canonical* — i.e. the
   defect affected 100% of real sidecars, not some fraction. The legacy branch is
   retained purely for child nodes in other repositories, exactly as the spec
   reasoned, but its expected traffic in this repo is zero rather than merely low.
2. **The manual-verification step was planned against an epic that turned out not
   to exist in a usable form.** The plan said "if no suitable epic exists, say so
   rather than inventing one", which is what happened — and substituting a
   read-only call over real sidecars produced better evidence than the planned
   check would have.

## Notes

- The rendered paths in old sidecars use the pre-0.11 `file#heading` addressing
  (`work#view-the-board`) rather than today's `namespace/path`.
  `declared_capabilities` returns them verbatim, so the rollup displays them
  as-authored. Not a defect and out of scope — but anyone reading a rollup over
  historical items will see two addressing styles side by side.
- The release-note entry was kept. The plan flagged it as a borderline
  `Public-API` call and licensed dropping it if it read as noise; it does not —
  the false "malformed" message is precisely what the reporter experienced, and
  39-of-39 impact makes it worth a user-facing line.
- **GitHub issue #8 is deliberately not closed by this item.** Per the user's
  sequencing decision on 2026-07-30, the four issue-backed items in this batch
  have their issues answered and closed only after the containing minor version
  is cut and pushed.
