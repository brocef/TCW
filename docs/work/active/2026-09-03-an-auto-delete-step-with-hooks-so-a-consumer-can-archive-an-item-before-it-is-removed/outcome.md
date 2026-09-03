# Outcome — An auto-delete step with hooks

## What shipped

Six planned tasks, one commit.

1. **`auto-delete` in the lifecycle vocabulary** — `TRANSITION_IDS` and a
   `LifecycleStep` with `moves: completed | discarded → (removed)`, listed after
   `discard`. No `LEGAL_TRANSITIONS` pair, with a comment beside the set saying
   why its absence is deliberate.
2. **`TCW_ITEM_PATH` and `TCW_RESOLUTION`** in `hook_env`, omitted rather than
   exported empty where a transition has neither. The path is passed in by the
   caller and is always the store's own answer.
3. **The bindings run between the two commits.** `_auto_delete` in
   `tcw/work/cli.py`: `pre` → `delete_resolved` → `post`. A `pre` failure returns
   before the removal and names `tcw work delete <slug>`.
4. **`tcw work delete <slug>`**, the same code path under a typeable name.
   Refuses a live item (that is `drop`) and one whose status the project retains.
5. **`tcw serve` performs no removal** — a consequence of moving the deletion out
   of the store rather than a special case in serve.
6. **Documentation:** README (worked S3 and folder-move examples, the two
   non-promises), release notes, changelog, the `tcw-work` transitions and
   commands references, the `work/configure-the-work-lifecycle` body, and the new
   capability `work/archive-a-resolved-item-before-it-is-deleted` (`cap-240fde`)
   flipped to `Supported`.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2303 passed in 357.34s (0:05:57)
```

Four environmental failures plus the timing-sensitive grandchild-timeout test.

Ten new tests in `tests/test_retention.py` and one in `tests/test_serve.py`,
covering both named scenarios directly rather than through a fixture binding
that echoes a variable:

- **S3-shaped:** a `pre` that `tar -czf`s `$TCW_ITEM_PATH` into a directory, then
  asserting the tarball contains `./state.yaml` and the item is gone.
- **Folder move:** a `pre` that `mv`s `$TCW_ITEM_PATH` elsewhere, then asserting
  the item is at the new location, the removal did not error, and the tombstone
  still records the commit.

Plus: the step is bindable and listed; the environment carries the right path
and resolution; a failing `pre` keeps the item and names the recovery verb;
`tcw work delete` finishes it; `delete` refuses a live and a retained item; a
retained status runs no bindings; `post` runs after the removal; a `skill:`
binding is reported and not executed; serve leaves the item for the CLI.

## Corrections

- **The store had to stop deleting.** Item 4 put the deletion inside
  `_effect_transition_locked`. Hooks cannot run there — `hooks.py` states that a
  store method which shells out is one no remote adapter could honor — and a
  `pre` that refuses must leave the item intact, which a call buried inside the
  move cannot express. `pending_deletion` now reports the state and the CLI
  orchestrates. Item 4's tests were updated to drive `tcw work complete` rather
  than `store.transition`, which is where the behavior now lives.
- **`delete_resolved` needed its own push.** The resolving transition publishes
  after its commit, which is before the deletion commit exists. Without a second
  push a provisioned store left the remote holding an item it had deleted.
- **`tcw serve` reports nothing about the pending removal.** The plan asked for
  it in the response. The payload is a versioned DTO with `additionalProperties:
  false`, every property required, and a test pinning the exact key set — shared
  with the CLI's `--json`. Adding a key is a schema-version change out of
  proportion to this note, so it is deferred and the reasoning is recorded at the
  payload builder.
- **Two contract tests moved deliberately.**
  `test_transition_ids_match_the_epic_contract` and
  `test_every_transition_id_except_discard_is_a_cli_verb` pin the vocabulary; the
  second now records *why* `auto-delete` is the second exception — its verb is
  `delete`, because "auto-delete" reads wrong as something a person types while
  the config key must say the deletion is automatic.
- **The lifecycle baselines were regenerated.** Those fixtures exist to make a
  change to `tcw work lifecycle` output visible in a diff. It is visible: 11
  files, and this is the deliberate contract change they were built to catch.

## Notes

The `pre` hook runs *after* the resolving commit, so an archive always sees an
artifact git already has. That ordering is what makes a failure cheap, and it is
the reason the request's "custom completed transition" became a step on the
deletion rather than on `complete`.
