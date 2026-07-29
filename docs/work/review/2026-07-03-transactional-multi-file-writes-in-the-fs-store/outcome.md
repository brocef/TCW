# Outcome: Transactional multi-file writes in the Fs store

All five plan tasks shipped in order, one commit each, plus the Documentation
Sync block. The full suite is green: **1077 passed in 152s** (`python -m pytest -q`,
repo root) — baseline was 1066, and the 11 new tests are all fault-injection
coverage. No existing test call site was edited (AC 8).

## What shipped

| Task | Commit | What landed |
|---|---|---|
| 1 | `7381d82` | `_atomic_write_all(pairs)` — module-level sibling of `_atomic_write`. Stage every `<path>.tmp`, then `replace` each in turn; one `except BaseException` spans both phases and unlinks every temp. No callers yet, 5 tests of its own. |
| 2 | `d4f9dd8` | `FsTreeStore._write_node` uses the helper, captures `existed` before `mkdir`, and `rmtree`s only a directory it created. `self._stage` stays outside the rollback. 2 tests. |
| 3 | `f1e7744` | `FsWorkStore.update_work` builds a 1- or 2-entry pair list (body only when it changed) and makes one `_atomic_write_all` call. No directory rollback — the item directory already exists. 1 test. |
| 4 | `d9e6967` | `FsWorkStore.create_work` wraps its two writes in `try` / `rmtree(..., ignore_errors=True)` / `raise`. `mkdir` without `exist_ok` proves the directory is ours, so the rollback is unconditional. 1 test. |
| 5 | `56edcd4` | `FsWorkStore.create` deleted down to a single delegating `return self.create_work(...).item`. 2 tests (rollback inherited through the delegate; empty title now `ValueError`). |
| D1+D2 | `7beef98` | `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`. |

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
  `2026-06-22-concurrency-safe-work-claims-…`), and 2335 (the single create path
  on `create`).
- **The fault injection really injects.** Every unchanged-state test is a
  `pytest.raises(OSError)` around the call, not a bare call. Proven non-vacuous
  by mutation: repointing `_fail_writing` at a filename that is never written
  fails all six of the store-level fault tests (`DID NOT RAISE OSError`). The
  mutation was reverted; `git status` clean.

## What the plan got wrong

**One correction, made in `plan.md` in place.**

The Verification section said AC 7 should be checked with
`git diff --stat main -- tcw/store/base.py`, "empty at the end of the branch."
There is no branch — this item is being worked on `main` itself, so that command
compares `main` to `main` and is empty regardless of what the change did. It
would have passed even if `base.py` had been rewritten. `plan.md` now says to
diff against the item's start commit (the `→ active` commit, `080d3f7`), which is
what was actually run.

Nothing else in the spec or plan was contradicted by the code. Specifically
re-verified rather than assumed:

- `FsWorkStore.create` still has **no caller under `tcw/`** —
  `grep -rn "\.create(" --include=*.py tcw/` returns nothing, so the delegation's
  stricter empty-title path is unreachable from the CLI and from `tcw serve`.
- `_write_node` has exactly the **four** call sites the spec names (now at
  fs.py:799, 1028, 1280, 1665 after the line shift) — `add`/`update` for both
  terms and capabilities, fixed in one place.
- Both accepted behavioral deltas of the delegation landed with **zero** existing
  test failures across the 262 `.create(` call sites. The delta the plan called
  "the one change whose blast radius is the whole test suite" cost nothing.

## Documentation Sync

Evaluated once over the finished diff, and the plan's prediction was confirmed
against the actual diff rather than trusted:

| Entry | Predicted | Actual | Why |
|---|---|---|---|
| `README.md` [Public-API] | No | **No** | No command, flag, argument, or output changed. Its "atomic" hits are about git commits and the motivation, not file-write durability. |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | **Yes** | A save that fails no longer leaves a half-written item or term. Written in plain language with the honest limit (power loss during the final instant is still not covered). |
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
- The suite runs 2m26s–3m09s wall clock across the five runs, a bit above the
  plan's "~2m45s" estimate on the slow end. Not worth a plan correction, but the
  inner-loop subset the plan names is genuinely the difference between a 3-second
  and a 150-second edit cycle.
