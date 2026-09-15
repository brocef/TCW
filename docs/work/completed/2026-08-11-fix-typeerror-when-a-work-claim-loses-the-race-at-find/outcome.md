# Outcome — Fix TypeError when a work claim loses the race at _find

**Suite:** 1204 passed (1203 + the new deterministic test).

## What shipped

| Task | Commit | Result |
| --- | --- | --- |
| 1 — failing test first | `0eacc67` | shipped, after two rejected approaches |
| 2 — normalize the lost-race signals | `bd5a79a` | shipped as specced |
| 3 — documentation | `b703ba2` | shipped, into `v0.20.0.md` rather than `upcoming.md` |

### Task 1 — the test, and two approaches that did not work

The plan said "monkeypatch `_find` to return `None`". That is what the spec
assumed, and it was wrong twice before it was right.

1. **Patching `_find` globally** broke `self.get(slug)` too, so `start()` raised
   `ValueError: no such work item` at `fs.py:1996` — failing well short of the
   defect.
2. **Constructing the state instead** — putting the folder in `.claiming/`, as
   `test_takeover_recovers_interrupted_private_claim` does — cannot reach it
   either. With the folder there, `get()` returns `None` and `start()` again
   raises "no such work item".

The reason is worth recording, because it is the whole character of this bug:
**no arrangement of files reproduces it.** Whatever makes `get()` succeed also
makes `_find` succeed. The defect lives in the *gap between the two calls*, so
only a timing difference exposes it.

Tracing `_find` on a winning backlog start gives `['backlog', 'backlog',
'active']` — the claim lookup is call #2. The test therefore lets `_find` be
real for the status read and returns `None` for the claim lookup that follows,
which is exactly the window in which the winner's folder sits in `.claiming/`.

**Deviation from the spec's acceptance criterion 1.** The spec asked the test to
assert `AlreadyClaimed`. It asserts the *recovery path* is reached — a
`ValueError: … interrupted claim` — instead. Which error ends the recovery
depends on whether the competitor finishes claiming, which is a second timing the
test would have to fake as well; the `AlreadyClaimed` outcome is already covered
by the threaded test that caught this. The assertion that matters is that
`os.replace` is never handed `None`.

Verified failing before the fix with `TypeError: replace: src should be string,
bytes or os.PathLike, not NoneType` at `tcw/store/fs.py:2025` — byte-identical to
the CI failure.

### Task 2 — the fix

Three lines in `FsWorkStore.start`: `if src is None: raise FileNotFoundError(slug)`
inside the existing `try`, so both tells of a lost race converge on the one
recovery block. As specced.

### Task 3 — documentation

Both predicted triggers fired. The entries went into `docs/changelogs/v0.20.0.md`
and `docs/release-notes/v0.20.0.md` rather than the `upcoming.md` files the plan
named, because the requester chose to fold this fix into the already-cut,
unpushed `v0.20.0`. `upcoming.md` was restored to headers only.

## What the plan got wrong

1. **"Monkeypatch `_find` to return `None`"** — too blunt; it breaks `get()`.
   The patch has to be scoped to the claim lookup.
2. **Acceptance criterion 1's `AlreadyClaimed` assertion** — needs a second faked
   timing to be meaningful. Superseded, see Task 1.
3. The spec's risk note ("forcing it via monkeypatch tests the handler rather
   than the race") was right, and is the accepted limitation.

## Evidence, and what is not evidence

- **Evidence:** the deterministic test reproduces the exact CI failure and now
  passes.
- **Not evidence:** the threaded test passing 30/30 locally after the fix. It
  passed 1202/1203 times *before* the fix too. A green run of a flaky test proves
  nothing, which is precisely why the deterministic test was written first.

## Notes

- The sibling at `_effect_transition` (`fs.py:2726`) is untouched, per the
  request's explicit non-goal. Same shape — `src = self._find(slug)` then
  `self._mv(src, dst)` — on a path the claiming mechanism does not cover.
  Deciding what a losing `submit`/`complete`/`rework` should do is design work,
  not this fix. It remains recorded in `initial-request.md` and has no item of
  its own yet.
- Planning artifacts were compressed at the requester's direction; the spine is
  intact but each document is short.
