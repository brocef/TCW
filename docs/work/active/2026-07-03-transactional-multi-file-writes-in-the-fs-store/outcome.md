# Outcome: Transactional multi-file writes in the Fs store

Two implementation passes. The first shipped all five plan tasks in order, one
commit each, plus the Documentation Sync block; verification then found every
acceptance criterion met and asked for one coverage gap closed and three prose
errors corrected, which is the second pass. The full suite is green:
**1078 passed in 152s** (`python -m pytest -q`, repo root) — baseline was 1066,
and the 12 new tests are all fault-injection coverage. No existing test call site
was edited (AC 8).

## What shipped — first pass

| Task | Commit | What landed |
|---|---|---|
| 1 | `7381d82` | `_atomic_write_all(pairs)` — module-level sibling of `_atomic_write`. Stage every `<path>.tmp`, then `replace` each in turn; one `except BaseException` spans both phases and unlinks every temp. No callers yet, 5 tests of its own. |
| 2 | `d4f9dd8` | `FsTreeStore._write_node` uses the helper, captures `existed` before `mkdir`, and `rmtree`s only a directory it created. `self._stage` stays outside the rollback. 2 tests. |
| 3 | `f1e7744` | `FsWorkStore.update_work` builds a 1- or 2-entry pair list (body only when one is supplied) and makes one `_atomic_write_all` call. No directory rollback — the item directory already exists. 1 test. |
| 4 | `d9e6967` | `FsWorkStore.create_work` wraps its two writes in `try` / `rmtree(..., ignore_errors=True)` / `raise`. `mkdir` without `exist_ok` proves the directory is ours, so the rollback is unconditional. 1 test. |
| 5 | `56edcd4` | `FsWorkStore.create` deleted down to a single delegating `return self.create_work(...).item`. 2 tests (rollback inherited through the delegate; empty title now `ValueError`). |
| D1+D2 | `7beef98` | `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`. |

## What shipped — rework pass

Driven by `rework.md`, which reversed no design decision.

| Item | Commit | What landed |
|---|---|---|
| 1 | `82c944a` | `FsCapabilitiesStore.update_capability` captures `existed` before its own `mkdir` and wraps all three write branches in the same `rmtree(..., ignore_errors=True)` rollback. Fresh-override materialization is now all-or-nothing. 1 test. |
| 2–4 | `370f5f9` | Three prose corrections: `create`'s docstring, one changelog line, one release-note sentence. Plus a changelog entry for item 1, which made the existing "`update_capability` inherits it without being patched individually" line stale. |

**Why the naive edit does not work**, since it is the first thing a later reader
will reach for: deleting `update_capability`'s `mkdir` and letting `_write_node`
own the directory breaks the other two branches. Both
`is_override and not desc_text.strip()` and `body is _UNSET and not desc.exists()`
call `_write_meta`, which writes `meta.yaml` **without** creating the directory,
so they would raise `FileNotFoundError`. The rollback therefore lives at the
caller, wrapping all three branches — the two `_write_meta` ones leave the same
empty-directory residue.

The new test
(`test_update_capability_failure_removes_override_it_materialized`,
`tests/test_store_editor.py`) was confirmed non-vacuous by stashing the `fs.py`
fix and re-running: it fails at `assert not d.exists()` pre-fix and passes
post-fix. The `errno == 28` assertion passes in both directions, which is the
point — it proves the injected `OSError` reached the caller rather than a
rollback-raised one, in the state where the assertion could not be satisfied
trivially.

Reaching the federated fresh-override path needs a base+child pair, so the test
imports `child_of` from `tests/test_capabilities_federation.py` — the first
cross-test-module import in this repo. The alternative was duplicating ~12 lines
of registry/sentinel/`extends_add` setup, or moving the test away from the
fault-injection family it belongs to.

## Acceptance criteria

1–6 and 8 are covered by the suite. The four checks `pytest` cannot make were run
by hand, and all four pass:

- **AC 7 — `base.py` unchanged.** `git diff --stat 080d3f7..HEAD -- tcw/store/base.py`
  is empty. (The plan's version of this check was wrong — see below.)
- **AC 2's second half — `create` has no write path of its own.** The final
  `create` is a docstring plus one `return`. `grep -n "write_text\|dump_yaml"`
  has no hit inside it.
- **The three `# ponytail:` ceilings are written down.** `grep -n "ponytail:"
  tcw/store/fs.py` → lines 572 (the promote window on `_atomic_write_all`), 668
  (the TOCTOU window on `_write_node`'s rollback, pointing at
  `2026-06-22-concurrency-safe-work-claims-…`), and 2346 (the single create path
  on `create`). The rework's rollback adds no fourth ceiling — it points at the
  same two caveats as `_write_node`'s.
- **The fault injection really injects.** Every unchanged-state test is a
  `pytest.raises(OSError)` around the call, not a bare call. Proven non-vacuous
  by mutation: repointing `_fail_writing` at a filename that is never written
  fails all six of the first pass's store-level fault tests (`DID NOT RAISE
  OSError`). The mutation was reverted; `git status` clean. The rework's seventh
  test has equivalent evidence of its own — see the rework section.

## What the plan got wrong

**Two corrections, both made in `plan.md` in place.**

**1 (first pass).** The Verification section said AC 7 should be checked with
`git diff --stat main -- tcw/store/base.py`, "empty at the end of the branch."
There is no branch — this item is being worked on `main` itself, so that command
compares `main` to `main` and is empty regardless of what the change did. It
would have passed even if `base.py` had been rewritten. `plan.md` now says to
diff against the item's start commit (the `→ active` commit, `080d3f7`), which is
what was actually run.

**2 (rework).** Task 5 justified `create_work(...).item` as "the `self.get(slug)`
the spec asks for, **without a second read**." The second half is backwards, and
the first pass copied it verbatim into `create`'s docstring: `get_detail` returns
`self.get(slug)` untouched — so the equality is literal for every field — but it
then reads `state.yaml`, the body, and every artifact file to compute revision
hashes. `create` does strictly *more* I/O than the code it replaced. Harmless to
correctness, wrong as written; the clause is gone from both `plan.md` and the
docstring, and the item-equality justification (which is the real one) stays.

Nothing else in the spec or plan was contradicted by the code. Specifically
re-verified rather than assumed:

- `FsWorkStore.create` still has **no caller under `tcw/`** —
  `grep -rn "\.create(" --include=*.py tcw/` returns nothing, so the delegation's
  stricter empty-title path is unreachable from the CLI and from `tcw serve`.
- `_write_node` has exactly the **four** call sites the spec names (now at
  fs.py:799, 1028, 1280, 1667 after the line shift) — `add`/`update` for both
  terms and capabilities, fixed in one place. **They are not a clean two-create /
  two-update split**, which is what the first pass of this document claimed and
  what the rework corrected. Three of them are: `FsTaxonomyStore.add` (799) and
  `FsCapabilitiesStore.add` (1280) always create, and both pre-check
  `d.exists()` and raise, so `existed` is False by construction;
  `update_term` (1028) always updates an existing node. The fourth,
  `update_capability` (1667), is **both** — it updates an existing capability
  *and* materializes a fresh override directory for an inherited one
  (`_write_target`, fs.py:1349–1358). Because it `mkdir`s that directory itself
  before dispatching, `_write_node`'s `existed` reads True and its rollback never
  fires on the create case. That is the gap the rework closed.
- Both accepted behavioral deltas of the delegation landed with **zero** existing
  test failures across the 262 `.create(` call sites. The delta the plan called
  "the one change whose blast radius is the whole test suite" cost nothing.

## Documentation Sync

Evaluated once over the finished diff, and the plan's prediction was confirmed
against the actual diff rather than trusted:

| Entry | Predicted | Actual | Why |
|---|---|---|---|
| `README.md` [Public-API] | No | **No** | No command, flag, argument, or output changed. Its "atomic" hits are about git commits and the motivation, not file-write durability. |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | **Yes** | A save that fails no longer leaves a half-written item or term. Written in plain language with the honest limit — which the rework restated: the first wording narrowed it to power loss, where an ordinary OS error at the last step does the same thing. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | **Yes** | New **Fixed** section for the helper and the two rollbacks; the `create` delegation and its two deltas under **Changed**. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | No | **No** | No component's CLI surface, model/fields, lifecycle, or guardrails changed. Nothing a driving skill says became untrue. |

Version cross-check ran clean: `pyproject.toml` is `0.16.0`, `v0.16.0.md` exists
in both directories, and `upcoming.md` holds only post-0.16.0 work. Nothing
rotated. No version cut — that belongs after `tcw work complete`.

## Notes

- The changelog entries deliberately carry **no** `<changes starting-hash=…>`
  wrappers. The skill's reference describes them, but this repo's existing
  changelog files have never used them; matching the project won out.
- `_atomic_write` is still live and still has callers (`create_work`'s two
  writes, `write_artifact`, `write_sidecar`, and others) — the helper did not
  replace it, and Task 4 deliberately kept `create_work` on the two single-file
  calls rather than folding them into `_atomic_write_all`. The directory rollback
  is the stronger guarantee there, so the batch helper would have been redundant.
- `_write_meta` was left alone, per the plan's note: it writes one file, so it
  has nothing to gain from the batch helper.
- **One sibling left unfixed, deliberately.** `FsCapabilitiesStore.set`
  (fs.py:1375–1380) has the same shape as the branch the rework closed —
  `_write_target`, then its own `mkdir(parents=True, exist_ok=True)`, then
  `_write_meta` — so a failed `set` on a fresh override leaves the same empty
  directory. It is out of the rework's scope and is a smaller residue (an
  override materialized by `set` is a pure meta delta, so the only file at risk
  is `meta.yaml` itself, written through `_atomic_write`). Recorded here rather
  than fixed, since widening scope mid-rework is how an item stops being
  reviewable. The fix, if wanted, is the same six lines.
- The suite runs 2m26s–3m09s wall clock across the five runs, a bit above the
  plan's "~2m45s" estimate on the slow end. Not worth a plan correction, but the
  inner-loop subset the plan names is genuinely the difference between a 3-second
  and a 150-second edit cycle.
