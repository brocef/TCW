# Outcome — `tcw provision` fetches a project the checkout already has

## What shipped

One task, as planned.

`_provision_nodes` builds the set of project ids reachable from the starting
node — `registry.current`, `ancestors()`, `descendants()` — before working the
queue, and adds each node's id as the walk obtains or finds it. A queued
declaration whose id is in that set is skipped and reported `already available`,
with no location claimed: the project may be in the working checkout or in a copy
provisioned earlier, and both mean "do not fetch it again". `--refresh` bypasses
the skip.

Documentation: changelog, README's transitive paragraph, and the
`cli/provision-declared-stores` body, whose "running it again does nothing"
promise now covers projects as well as stores.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2307 passed in 355.05s (0:05:55)
```

The established environmental failures.

One new test in `tests/test_store_provisioning.py`: a node declares repositories
for two projects, one the caller already has and one it does not. The present one
is reported available and never cloned; the absent one is obtained in the same
run; the cache holds two directories and none of them is a second copy of the
caller's own repository.

### The real reproduction

In `apps/server` of a `proposit-app`-only checkout, with the orchestration node
provisioned and carrying its merged configuration:

```
  work: already available
  proposit-app: already available
→ proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …
  proposit-core: obtained at …
  proposit-app-repo: already available
```

`proposit-app-repo` was the line that read `would obtain into
…-proposit-app-7df9029374a6` before the fix. Two cache directories afterwards —
orchestration and core — and no second copy of `proposit-app`.

## Corrections

- **The dry-run half of criterion 2 needed the declaring node present.** A
  `--dry-run` from scratch never fetches the node that carries the declaration,
  so it cannot report a skip it has not read — and says so, by design. The test
  provisions first and then plans, which is the shape the real reproduction had.
- **The skip message claims no location.** "Already available in this checkout"
  was the first wording and it is false for a project available through an
  earlier provision. It says `already available` and stops there.

## Notes

Found by configuring the Proposit repositories rather than by a test, one item
after the feature it corrects. The declaration that triggered it is correct and
should stay: a session starting from the orchestration node genuinely needs to
know where the monorepo comes from. It is the walk that had to learn not to act
on a declaration it does not need.
