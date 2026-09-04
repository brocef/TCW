# Outcome — Docstrings and branches the last round left false or dead

## What shipped

**Two false docstrings.**

1. `_extended_component_stores` explained "`seen_nodes` carries the *projects*
   already on the federation path". The parameter is `walk`, and the sentence
   described a name that no longer existed. It now names `_FederationWalk` and
   says which half of it does the cycle detection — the substance was right, only
   its subject had been renamed out from under it.
2. `hook_env` asserted both that "**Every** transition has an item folder, and
   every caller passes it" *and*, six lines later, that "a caller with no answer
   — the item is already gone — passes None and the variable is absent". Both
   cannot hold. The resolution is that the two variables are conditional on
   different things: `TCW_RESOLUTION` on the *transition*, `TCW_ITEM_PATH` on the
   *state*. Every caller passes what the store answers, and that answer is None
   once the item is gone — which is the state `tcw work delete` resumes into, and
   is observable: a binding's `"$TCW_ITEM_PATH"` expands to empty there. The
   docstring now says so, and says what it means for an archive command, which is
   the thing a reader is actually deciding.

**Two dead branches, resolved differently, because they were dead for different
reasons.**

3. `describe_location`'s `if not location:` branch was unreachable because
   `_show` guarded on `if grave.location:` before calling it. The guard was the
   defect, not the branch: it skipped the one case a reader most needs told — an
   item whose documents were never retained anywhere — and printed nothing at
   all. `_show` now always prints the `content:` line and lets
   `describe_location` say what is true, which makes the branch reachable and the
   output honest.
4. `misdirected()`'s `cfg.path == Path(str(entry.locator)) / SENTINEL` could
   never be true: an entry reaches `_unreachable` only from the branch that could
   not read a config file, while `cfg.path` is by construction one that was read.
   Deleted, with the reason written down — a guard that cannot fire tells the
   next reader a state exists when it does not, which is the whole subject of
   this item.

## Tests

One new test: `tcw work show` on an item whose documents no commit held prints a
`content:` line saying they were not retained. It fails against the previous
code, where the line was absent entirely.

The rest are covered by the existing suites — the two docstrings change no
behaviour, and the deleted comparison is exercised by the four `misdirected`
tests added earlier, which continue to pass.

```
$ python -m pytest -q -p no:randomly tests/
4 failed, 2373 passed in 354.98s (0:05:54)
```

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted.

1. **Whether to delete each dead branch or make it reachable.** Different answers
   for the two, and the difference is the point. `describe_location`'s wording
   was the *right* answer to a question nobody was asking it, so the fix was to
   ask; `misdirected()`'s comparison had no answer to give, so the fix was to
   remove it. Deleting both would have lost a real improvement; keeping both
   would have left a lie in place.

## Notes

All four are the same failure this branch has been correcting throughout: prose
or code that was true when written and survived the change that falsified it —
a renamed parameter, a widened caller, a guard that moved. Nothing here is a
mistake anybody made; each is a thing nobody went back to.
