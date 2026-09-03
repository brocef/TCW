# Outcome — An unreachable edge is reported for a project the graph resolved anyway

## What shipped

One task, as planned. `unreachable()` returns only recorded edges whose id is not
in `_by_id`, and `unreachable_project` reads through it rather than the raw list —
see Corrections.

Documentation: changelog, README's partial-graph paragraph (now "each project it
could not reach", with the reason a resolved one is not listed), and the
`cli/host-multiple-projects-in-one-repo` body.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2309 passed in 353.74s (0:05:53)
```

The established environmental failures.

Two new tests in `tests/test_project_registry.py`: a graph where the parent's
locator for its child does not resolve while the child's for its parent does
reports nothing unreachable; a project no route resolves is still reported.

### The real verification

`tcw validate` in each of the three Proposit nodes, in a checkout holding only
`proposit-app`, with orchestration and core provisioned:

```
apps/server     → validate OK
packages/shared → validate OK
apps/mobile     → validate OK
```

Before this, the first two printed a report for `proposit-app` and one for
`proposit-app-repo` — the latter telling the reader to `tcw provision` the
repository they were standing in.

## Corrections

- **`unreachable_project` read the raw list.** The plan said it "already reads
  through" the accessor; it did not, and the fix is incomplete without it —
  that method is what every "declared but not reachable" message consults, so the
  filter has to be on the path those messages take.

## Notes

The trade the spec names is real and worth restating: a mistyped locator that
some other declaration papers over is now invisible. That is the right side to
err on — the project is reachable, nothing the user does is broken, and a message
that fires on a routine condition is one they learn to skip past.
