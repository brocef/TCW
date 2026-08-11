# Fix TypeError when a work claim loses the race at _find

## Product changes

Two agents starting the same work item concurrently: the loser gets a clear
"already claimed by X" instead of an internal `TypeError`.

## Technical changes

`FsWorkStore.start` treats `_find` returning `None` as the same lost-race event
as `os.replace` raising `FileNotFoundError`.

## Meta changes

None.

---

## Requested outcome

Found by CI on 2026-08-11 — the first run of the test workflow added by
`2026-08-11-publish-tcw-to-pypi-with-automated-releases`:

```
FAILED tests/test_external_work_store.py::test_two_store_claim_has_one_winner_and_visible_metadata
  TypeError: replace: src should be string, bytes or os.PathLike, not NoneType
  tcw/store/fs.py:2025
1 failed, 1202 passed
```

**Flaky, not deterministic** — the same job passed on re-run, and the suite
passes locally on Python 3.14.6. It is a thread interleaving, so it surfaces on
a 2-core runner far more often than on a developer machine.

The loser of the claim race has two possible timings, and only one is handled:

| Loser's timing | Result | Handled |
| --- | --- | --- |
| `_find` succeeds, `os.replace` then loses | `FileNotFoundError` → retry loop → `AlreadyClaimed` | yes (`fs.py:2026`) |
| `_find` itself returns `None` | `os.replace(None, …)` → `TypeError` | **no** |

`_find` is declared `-> Path | None` (`fs.py:2065`), so returning `None` is
correct behavior, not a bug in `_find`. The defect is `start()` assuming a Path.

## Why a separate item

The code belongs to
`2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp`,
which is in `review`. Sending that back to rework was the alternative considered;
the requester chose a separate small item on 2026-08-11 so the fix lands now
rather than waiting on that item's lifecycle. The release of `v0.20.0` is held
until CI is deterministic.

## Sibling, deliberately out of scope

`_effect_transition` (`fs.py:2726`) has the identical shape — `src =
self._find(slug)` then `self._mv(src, dst)` — and would fail the same way if two
processes raced a `submit`/`complete`/`rework`. That path is **not** covered by
the claiming mechanism, so deciding what a losing transition should do is a
design question, not this fix. Recorded here so it is not silently ignored.

## Non-goals

- No redesign of the claiming protocol.
- No fix to `_effect_transition` (see above).
- No change to the other 20-odd `_find` call sites, which run after the item's
  existence has already been established in a non-racing path.

## Notes

- Planning artifacts are compressed at the requester's direction: this is a
  three-line change with one new test.
