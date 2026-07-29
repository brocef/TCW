# Rework: Transactional multi-file writes in the Fs store

Verification (independent, read-only) found **all eight acceptance criteria met**
and the suite green at 1077. The change ships as designed. This rework closes one
real coverage gap and corrects three factual errors in prose. Nothing here
reverses a design decision.

## 1. `update_capability` defeats `_write_node`'s rollback — close it

**The defect.** `update_capability` calls `d.mkdir(parents=True, exist_ok=True)`
at `fs.py:1652`, *before* dispatching to `_write_node` at `fs.py:1665`. So
`_write_node`'s `existed = d.exists()` computes `True` for a directory its own
caller created microseconds earlier, and the rollback is skipped.

This bites on the **fresh-override materialization** path: `_write_target`
(`fs.py:1349-1358`) materializes a new override directory for an inherited
capability. Reproduced, not inferred — a failed `description.md` write leaves
`docs/capabilities/<path>/` on disk with contents `[]`, plus an empty parent.
The success case of this path is live and tested at
`tests/test_capabilities_federation.py:242`.

**Severity is low and the change already improves this path** — pre-fix, the same
failure left a directory containing `meta.yaml` and no `description.md`, a bogus
half-materialized override that would have read as a real node. Now it leaves an
inert empty directory. But it does not reach AC 4, and `outcome.md` describes the
call sites as a clean two-create / two-update split, which is wrong.

**The requirement:** when `update_capability` materializes a fresh override
directory and the write then fails, no directory is left behind.

**Do not use the naive edit.** Deleting the caller's `mkdir` and letting
`_write_node` own it breaks the other two branches: both
`is_override and not desc_text.strip()` and `body is _UNSET and not desc.exists()`
call `_write_meta`, which writes `meta.yaml` **without** creating the directory,
so they would raise `FileNotFoundError`. Any of these is acceptable — pick the
smallest that reads clearly:

- Capture `existed` before the `mkdir` in `update_capability` and wrap the whole
  three-branch block in the same `if not existed: shutil.rmtree(...)` rollback.
  This covers all three branches uniformly, including the two `_write_meta` ones,
  which have the same empty-directory residue.
- Or move the `mkdir` into just the two `_write_meta` branches and let
  `_write_node` own its own.

Prefer the first if it comes out smaller — the two `_write_meta` branches have
the same residue and fixing only the `_write_node` one leaves a known sibling.

**Test:** a fresh-override materialization whose `description.md` write fails
leaves no override directory. Extend the existing `_fail_writing` mechanism in
`tests/test_store_editor.py`; the federation fixture at
`tests/test_capabilities_federation.py:242` shows how to set up an inherited
capability. Confirm the test fails before the fix.

**Then correct `outcome.md`'s call-site description** — it is currently inaccurate
about `fs.py:1665`.

## 2. `create`'s docstring claims a saving it does not make

`fs.py:2331` says `get_detail(...).item` *is* the old `self.get(slug)` "without a
second read." The first half is exactly right and worth keeping — `get_detail`'s
first line is `item = self.get(slug)`, returned untouched, so the equality is
literal for every field. The second half is backwards: `get_detail` then reads
`state.yaml`, the body, and every artifact file to compute revision hashes
(`fs.py:2425-2440`). `create` now does strictly *more* I/O than the code it
replaced. Harmless to correctness; wrong as written. Drop the clause.

## 3. Changelog: "only when it changed"

`docs/changelogs/upcoming.md` says the body is "still written only when it
changed." The guard is `body is not _UNSET` — the body is rewritten whenever one
is *supplied*, including an identical one. The follow-on claim ("an unchanged
body never churns its revision hash") does hold, since `_revision_multi` hashes
content. Fix the phrasing to "only when one is supplied."

## 4. Release note narrows the residual window to power loss

`docs/release-notes/upcoming.md` says "a machine losing power during the final
instant of a save is still not covered." An ordinary OS error mid-`replace()`
produces the same partial state with no power loss involved. The code's own
`# ponytail:` comment at `fs.py:572` and
`test_atomic_write_all_promote_failure_is_the_recorded_ceiling` are honest about
this; the user-facing note should be too, in plain language — something closer to
"if the very last step of a save fails, one file can land while another does not."

## Notes

Two things from verification worth keeping:

- **The editable install's import finder beats `PYTHONPATH`.** A worktree-based
  check of pre-fix behavior silently imported HEAD's `fs.py` from the primary
  checkout and reported a false green (11 passed). Only stripping the
  `__editable__.tcw-*.pth` MetaPathFinder in a root `conftest.py` loaded the
  worktree source. Any future worktree verification in this repo needs that guard.
- **Mutation evidence for the existing tests is strong** and does not need
  redoing: against the pre-fix commit, all six store-level fault tests fail and
  the five `_atomic_write_all` unit tests pass. The new test from item 1 should
  meet the same bar.
- AC 6's "no masking" clause is tested only as `pytest.raises(OSError)`, which
  cannot distinguish the injected `OSError(28)` from a rollback-raised one.
  Asserting `excinfo.value.errno == 28` would close that. Optional — the masking
  path needs a temp that exists but cannot be unlinked, which the spec's target
  failure class does not reach.
