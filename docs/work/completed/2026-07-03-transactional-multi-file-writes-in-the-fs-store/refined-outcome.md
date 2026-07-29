# Refined outcome: Transactional multi-file writes in the Fs store

**Accepted.** The user's condition was "do some dogfooding tests and then accept
if it works." It works — 1081 tests green, 22 dogfood checks green against the
real CLI and store with unfaked failures — so the condition is met and the item
closes.

## The decision

Accepted after four implementation passes, one verification cycle by an
independent read-only agent, and two rounds of dogfooding that each found
something the suite could not.

## Evidence

- **Suite: 1081 passed**, run by the coordinating session, not taken from a
  report. Baseline 1066; the 15 new tests are all fault-injection.
- **Independent verification** confirmed all eight acceptance criteria met, and
  proved the fault tests genuinely pinned by running the final test file against
  the pre-fix commit — six of six fail there.
- **Dogfooding, no monkeypatching.** 16 CLI-level checks (`work new`,
  `work edit`, `taxonomy add`, `capabilities add`/`set`, federation,
  `tcw validate`) and 6 store-level checks against `update_capability`. Failures
  came from real filesystem state: a directory occupying a `<file>.tmp` path, and
  a genuine `.git/index.lock` making `git add` fail for real.
- **The key fix proven non-vacuous** by restoring `fs.py` to its pre-fix commit:
  the override is deleted without `f2c5f9b`, survives with it.
- `tcw capabilities check`, `drift`, and `validate` all clean — no capability
  delta, as the spec predicted.

## What verification and dogfooding changed

Neither was a formality; each found something real.

1. **Verification** found `update_capability` defeating `_write_node`'s rollback,
   and `outcome.md` describing the call sites inaccurately. → pass 2.
2. **Reviewing pass 2** found that its own fix put staging inside the rollback,
   so a failed `git add` would delete a fully-written override — the exact
   outcome pass 1 engineered against. → pass 3.
3. **Dogfooding** found `tcw capabilities set` never reaches `update_capability`
   at all (that method is web-editor-only), so the CLI's capability-write path
   had no rollback and none of the first three passes had touched it. → pass 4.

Dogfooding also invalidated two of its own earlier assertions, which were
corrected rather than believed: one blocked a file the tested path never writes,
and one credited a fix for an outcome that would have happened anyway.

## Closeout choices

- **Merge route:** committed directly on `main`. No branch, no PR.
- **Documentation:** current. `docs/release-notes/upcoming.md` and
  `docs/changelogs/upcoming.md` updated during implementation and amended in
  passes 3 and 4. `README.md` and the driving skills correctly did not fire.
- **Follow-ups:** none filed. The one candidate — `FsCapabilitiesStore.set`
  lacking a rollback — was fixed in pass 4 at the user's direction instead.
- **Version:** no cut. Staying on `0.16.0`; the entries accumulate in
  `upcoming.md` for a later release.

## Notes

Three things worth carrying forward, none of which belong in the changelog:

- **`_write_node` and `_write_meta` stage internally.** Any caller wrapping them
  in a rollback also catches a `git add` failure that happened after content
  landed, and will delete good files unless the rollback keys on whether content
  landed. This trap was hit twice during this item. Both now carry a warning in
  the source, which is the durable fix.
- **`git stash push -- <path>` is a no-op against an already-committed change**
  and yields a false green when testing whether a fix is load-bearing. Reverting
  a committed fix needs `git checkout <sha>~1 -- <path>`.
- **The editable install's import finder beats `PYTHONPATH`**, so worktree-based
  verification silently imports the primary checkout unless the
  `__editable__.tcw-*.pth` MetaPathFinder is stripped in a root `conftest.py`.

A post-mortem was offered and is still available — four passes on a "low effort"
item is a reasonable trigger — but was not run.
