# Spec — Fix TypeError when a work claim loses the race at _find

## Capability changes

None. `work/start-a-work-item` already promises the claim is atomic and that a
loser is told so; this makes an existing promise true on one timing it missed.
No ledger delta, no `capabilities.yaml`.

## Problem

`FsWorkStore.start` (`tcw/store/fs.py:2020-2030`) reads `src = self._find(slug)`
and passes it to `os.replace`. `_find` is typed `-> Path | None`
(`fs.py:2065-2069`) and returns `None` once a competing process has moved the
item's folder out of `backlog/`. `os.replace(None, …)` then raises `TypeError`,
skipping the `except FileNotFoundError` block at `fs.py:2026` that exists to turn
exactly this situation into `AlreadyClaimed`.

## Goals

One recovery path covers both timings by which a claimant can lose the race.

## Non-goals

- `_effect_transition` (`fs.py:2726`), same shape, unprotected path — out of
  scope per the request.
- Any change to `_find`, whose `None` return is correct.
- Any redesign of the claim protocol.

## Design

Normalize the two signals before the `try` body branches on them:

```python
try:
    if src is None:
        raise FileNotFoundError(slug)
    os.replace(src, private)
except FileNotFoundError:
    ...          # unchanged: retry loop → AlreadyClaimed
```

Raising to be caught two lines down is deliberate. The alternative — extracting
the retry loop into a helper called from two places — is more code and splits the
one thing a reader needs to see whole: that both lost-race timings converge on
the same recovery.

## Acceptance criteria

1. `FsWorkStore.start` raises `AlreadyClaimed` — not `TypeError` — when `_find`
   returns `None` for an item another claimant has already taken active.
2. A test forces that timing deterministically (not by racing threads and hoping)
   and fails against the current code.
3. `tests/test_external_work_store.py::test_two_store_claim_has_one_winner_and_visible_metadata`
   passes.
4. Full suite green locally, and both CI legs green on GitHub.

## Risks

- **A deterministic test needs the `None` return forced**, since reproducing the
  interleaving reliably is what the existing thread-race test already fails to
  do. Forcing it via monkeypatch tests the handler rather than the race — an
  accepted limitation: the race itself stays covered by the existing threaded
  test, which is what caught this.
- **Flakiness is proof-by-absence.** A green CI run does not prove the fix; the
  bug was already passing most runs. The deterministic test is the real evidence.
